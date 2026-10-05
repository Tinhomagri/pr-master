import re
import subprocess

from . import config


TIMEOUT = 300


def _git(repo_dir, args, check=True):
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_dir), *args],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"git {' '.join(args)} estourou {TIMEOUT}s")
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc


def remote_heads(repo):
    try:
        proc = subprocess.run(
            ["git", "ls-remote", "--heads", f"https://github.com/{repo}.git"],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"git ls-remote {repo} estourou {TIMEOUT}s")
    if proc.returncode != 0:
        raise RuntimeError(f"git ls-remote {repo}: {proc.stderr.strip()}")
    return [
        ln.split("refs/heads/", 1)[1]
        for ln in proc.stdout.splitlines() if "refs/heads/" in ln
    ]


def resolve_main_branches(default, heads, cfg, base=None):
    """Branches principais que existem de fato: default do repo + integracao + base da PR."""
    patterns = cfg.get("main_branch_patterns", [])
    present = set(heads)
    ordered = []
    for name in [default, *(b for p in patterns for b in heads if re.fullmatch(p, b))]:
        if name in present and name not in ordered:
            ordered.append(name)
    if base and base in present and base not in ordered:
        ordered.insert(0, base)
    return ordered


def integration_branch(default, main_branches, cfg):
    """Para onde feature/fix devem apontar: a primeira branch de integracao que existe."""
    for name in cfg.get("integration_branch_priority", []):
        if name in main_branches:
            return name
    return default


def mirror(repo, pr_number, main_branches):
    """Garante um mirror bare local com as branches principais e o head da PR."""
    slug = re.sub(r"[^A-Za-z0-9._-]", "_", repo)
    path = config.CACHE / f"{slug}.git"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "init", "--bare", "--quiet", str(path)],
            check=True, timeout=TIMEOUT,
        )
        _git(path, ["remote", "add", "origin", f"https://github.com/{repo}.git"])
    # fetch de uma branch inexistente aborta o fetch inteiro: filtra pelo que existe
    listed = _git(path, ["ls-remote", "--heads", "origin"], check=False).stdout
    remote = {ln.split("refs/heads/", 1)[1] for ln in listed.splitlines() if "refs/heads/" in ln}
    refspecs = [
        f"+refs/heads/{b}:refs/remotes/origin/{b}" for b in main_branches if b in remote
    ]
    refspecs.append(f"+refs/pull/{pr_number}/head:refs/pr/{pr_number}")
    _git(path, ["fetch", "--quiet", "--prune", "origin", *refspecs])
    return path


def conflicts(repo_dir, pr_number, main_branches):
    """Merge a seco (sem working tree) do head da PR contra cada branch principal."""
    head = f"refs/pr/{pr_number}"
    results = []
    for branch in main_branches:
        ref = f"refs/remotes/origin/{branch}"
        if _git(repo_dir, ["rev-parse", "--verify", "--quiet", ref], check=False).returncode != 0:
            results.append({"branch": branch, "status": "missing", "files": []})
            continue
        proc = _git(
            repo_dir,
            ["merge-tree", "--write-tree", "--name-only", ref, head],
            check=False,
        )
        if proc.returncode == 0:
            status = "clean"
            files = []
        elif proc.returncode == 1:
            status = "conflict"
            lines = proc.stdout.splitlines()
            files = sorted({ln.strip() for ln in lines[1:] if ln.strip()})
        else:
            status = "error"
            files = [proc.stderr.strip()[:300]]
        behind = _git(
            repo_dir, ["rev-list", "--count", f"{head}..{ref}"], check=False
        ).stdout.strip()
        results.append({
            "branch": branch,
            "status": status,
            "files": files,
            "behind": int(behind) if behind.isdigit() else None,
        })
    return results


def commit_subjects(repo_dir, pr_number, base_branch, limit=50):
    base = f"refs/remotes/origin/{base_branch}"
    proc = _git(
        repo_dir,
        ["log", "--format=%s", f"-{limit}", f"{base}..refs/pr/{pr_number}"],
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def diff(repo_dir, pr_number, base_branch):
    """Diff do head da PR contra a base, direto do mirror.

    Saida alternativa para quando `gh pr diff` recusa a PR por tamanho (406).
    """
    base = f"refs/remotes/origin/{base_branch}"
    head = f"refs/pr/{pr_number}"
    merge_base = _git(repo_dir, ["merge-base", base, head], check=False).stdout.strip()
    proc = _git(
        repo_dir,
        ["diff", "--no-color", merge_base or base, head],
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git diff {base}..{head}: {proc.stderr.strip()}")
    return proc.stdout
