import json
import shutil
import subprocess


class GhError(RuntimeError):
    pass


def _gh(args):
    """Somente leitura: nenhuma chamada deste modulo escreve no GitHub."""
    if not shutil.which("gh"):
        raise GhError("gh CLI nao instalado. veja README.")
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise GhError(f"gh {' '.join(args)} falhou: {proc.stderr.strip()}")
    return proc.stdout


def pr(repo, number):
    data = json.loads(
        _gh([
            "pr", "view", str(number), "--repo", repo, "--json",
            "number,title,body,author,baseRefName,headRefName,headRefOid,"
            "additions,deletions,changedFiles,isDraft,mergeable,labels,commits,url",
        ])
    )
    return data


def diff(repo, number, max_bytes):
    out = _gh(["pr", "diff", str(number), "--repo", repo])
    if len(out.encode("utf-8")) > max_bytes:
        out = out.encode("utf-8")[:max_bytes].decode("utf-8", "ignore")
        out += "\n\n[... diff truncado pelo bot ...]"
    return out


def files(repo, number):
    out = _gh([
        "api", "--paginate",
        f"repos/{repo}/pulls/{number}/files",
        "--jq", ".[] | {path: .filename, status: .status, additions: .additions, deletions: .deletions}",
    ])
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def default_branch(repo):
    return json.loads(
        _gh(["repo", "view", repo, "--json", "defaultBranchRef"])
    )["defaultBranchRef"]["name"]


def branches(repo):
    out = _gh([
        "api", "--paginate", f"repos/{repo}/branches",
        "--jq", ".[].name",
    ])
    return [line.strip() for line in out.splitlines() if line.strip()]
