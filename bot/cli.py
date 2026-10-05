import argparse
import json
import re
import subprocess
import sys
from datetime import date

from . import checks, config, github, gitops, report


def _load_env():
    env = config.ROOT / ".env"
    if not env.exists():
        return
    import os
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def analyze(args, cfg, number):
    pr = github.pr(args.repo, number)

    if cfg.get("auto_detect_branches", True):
        default = args.default_branch or github.default_branch(args.repo)
        heads = gitops.remote_heads(args.repo)
        main_branches = gitops.resolve_main_branches(
            default, heads, cfg, base=pr["baseRefName"]
        )
        integration = gitops.integration_branch(default, main_branches, cfg)
        cfg = {**cfg, "detected": {
            "default_branch": default,
            "integration_branch": integration,
            "main_branches": main_branches,
        }}
        if args.verbose:
            print(
                f"  [branches] default={default} integracao={integration} "
                f"principais={','.join(main_branches)}", file=sys.stderr,
            )
    else:
        main_branches = list(cfg["main_branches"])
        if pr["baseRefName"] not in main_branches:
            main_branches.insert(0, pr["baseRefName"])

    files = github.files(args.repo, number)
    for pattern in cfg["rules"].get("ignore_paths", []):
        files = [f for f in files if not re.search(pattern, f["path"])]

    mirror = gitops.mirror(args.repo, number, main_branches)
    conflicts = gitops.conflicts(mirror, number, main_branches)
    commits = gitops.commit_subjects(mirror, number, pr["baseRefName"])

    findings = checks.run(pr, files, commits, conflicts, cfg)
    try:
        diff_text = github.diff(args.repo, number)
    except github.GhError as exc:
        if "exceeded the maximum number of lines" not in str(exc):
            raise
        # PR grande: o gh recusa o diff, o mirror local nao tem esse limite.
        if args.verbose:
            print("  [diff] gh recusou por tamanho, usando o mirror", file=sys.stderr)
        diff_text = gitops.diff(mirror, number, pr["baseRefName"])

    # ignore_paths tem de sair do diff antes do corte: lockfile e bundle minificado
    # geram falso positivo e consomem o orcamento de bytes antes do codigo real.
    before = len(diff_text)
    diff_text = checks.filter_diff(diff_text, cfg["rules"].get("ignore_paths", []))
    diff_text = checks.truncate_diff(diff_text, cfg["max_diff_bytes"])
    if args.verbose:
        print(
            f"  [diff] {before} bytes -> {len(diff_text)} apos ignore_paths/corte",
            file=sys.stderr,
        )

    findings += checks.diff_patterns(diff_text, cfg)

    summary = None
    if not args.no_ai:
        from . import reviewer
        result = reviewer.review(
            pr, diff_text, files,
            config.persona(cfg), config.project_standards(cfg),
            findings, cfg,
        )
        findings += checks.normalize(result.get("findings", []))
        summary = (result.get("summary") or "").strip() or None
        if args.verbose:
            print(f"  [tokens] {result['usage']}", file=sys.stderr)

    findings = checks.sort_findings(findings)[: cfg["max_findings_total"]]
    return pr, files, conflicts, findings, summary


def _save(args, cfg, pr, body):
    out = config.ROOT / args.out / args.repo.replace("/", "_")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{date.today():%Y-%m-%d}-pr-{pr['number']}.md"
    path.write_text(body, encoding="utf-8")
    return path


def cmd_review(args):
    cfg = config.load(args.project)
    if args.model:
        cfg["model"] = args.model

    pr, files, conflicts, findings, summary = analyze(args, cfg, args.pr)

    if args.json:
        print(json.dumps({
            "number": pr["number"], "url": pr["url"],
            "author": pr["author"].get("login"),
            "head": pr["headRefName"], "base": pr["baseRefName"],
            "conflicts": conflicts, "findings": findings, "summary": summary,
        }, ensure_ascii=False, indent=2))
        return 0

    body = report.render(pr, findings, conflicts, summary, cfg)
    print(body)
    if args.save:
        print(f"\n→ {_save(args, cfg, pr, body)}", file=sys.stderr)

    blockers = sum(1 for f in findings if f["severity"] == "blocker")
    return 1 if (blockers and args.fail_on_blocker) else 0


def cmd_scan(args):
    cfg = config.load(args.project)
    if args.model:
        cfg["model"] = args.model
    if cfg.get("auto_detect_branches", True) and not args.default_branch:
        args.default_branch = github.default_branch(args.repo)

    query = ["pr", "list", "--repo", args.repo, "--state", "open",
             "--json", "number,author,isDraft,title", "--limit", str(args.limit)]
    if args.author:
        query += ["--author", args.author]
    prs = json.loads(
        subprocess.run(["gh", *query], capture_output=True, text=True, check=True).stdout
    )
    rows, rc = [], 0
    for item in prs:
        if item["isDraft"] and cfg["rules"].get("skip_draft"):
            continue
        print(f"analisando PR #{item['number']} …", file=sys.stderr)
        pr, files, conflicts, findings, summary = analyze(args, cfg, item["number"])
        body = report.render(pr, findings, conflicts, summary, cfg)
        saved = _save(args, cfg, pr, body) if args.save else None
        rows.append({
            "number": pr["number"], "url": pr["url"],
            "author": pr["author"].get("login"),
            "head": pr["headRefName"], "base": pr["baseRefName"],
            "conflicts": conflicts, "findings": findings,
            "summary": summary, "report": str(saved) if saved else None,
        })
        if any(f["severity"] == "blocker" for f in findings):
            rc = 1

    if not rows:
        print("nenhuma PR aberta no filtro.")
        return 0

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(report.digest(rows, cfg))
        if args.save:
            print("\nRelatorios completos:")
            for row in rows:
                print(f"- #{row['number']}: {row['report']}")
    return rc if args.fail_on_blocker else 0


def cmd_branches(args):
    print("\n".join(github.branches(args.repo)))
    return 0


def main(argv=None):
    _load_env()
    parser = argparse.ArgumentParser(
        prog="pr-master",
        description="Analisa PRs e entrega o relatorio localmente. Nao publica nada no GitHub.",
    )
    parser.add_argument("--repo", required=True, help="owner/nome")
    parser.add_argument("--project", help="config/projects/<nome>.json")
    parser.add_argument("--model")
    parser.add_argument("--no-ai", action="store_true", help="so os checks deterministicos")
    parser.add_argument("--json", action="store_true", help="saida estruturada")
    parser.add_argument("--save", action="store_true", help="grava o relatorio em reports/")
    parser.add_argument("--out", default="reports", help="pasta de saida (default: reports)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--fail-on-blocker", action="store_true")
    parser.add_argument("--author", help="filtra PRs deste autor (apenas em scan)")
    parser.add_argument("--default-branch", help="forca a branch principal (pula a deteccao)")

    sub = parser.add_subparsers(dest="cmd", required=True)
    rev = sub.add_parser("review", help="analisa uma PR")
    rev.add_argument("pr", type=int)
    rev.set_defaults(func=cmd_review)

    scan = sub.add_parser("scan", help="analisa todas as PRs abertas")
    scan.add_argument("--limit", type=int, default=20)
    scan.set_defaults(func=cmd_scan, pr=None)

    br = sub.add_parser("branches", help="lista branches do remoto")
    br.set_defaults(func=cmd_branches, pr=None)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except github.GhError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
