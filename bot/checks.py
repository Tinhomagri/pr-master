import re

SEV_ORDER = {"blocker": 0, "major": 1, "minor": 2}


def _finding(severity, rule, message, path=None, line=None):
    return {
        "severity": severity,
        "rule": rule,
        "message": message,
        "path": path,
        "line": line,
        "source": "check",
    }


def run(pr, files, commits, conflicts, cfg):
    rules = cfg["rules"]
    out = []

    if pr.get("isDraft") and rules.get("skip_draft"):
        return [_finding("minor", "draft", "PR em draft - revisao automatica adiada.")]

    title_re = rules.get("pr_title_regex")
    if title_re and not re.match(title_re, pr["title"]):
        out.append(_finding(
            "major", "pr-title",
            f"Titulo fora do padrao `{title_re}`. Atual: `{pr['title']}`.",
        ))

    branch_re = rules.get("branch_regex")
    if branch_re and not re.match(branch_re, pr["headRefName"]):
        out.append(_finding(
            "major", "branch-name",
            f"Branch `{pr['headRefName']}` fora do padrao `{branch_re}`.",
        ))


    detected = cfg.get("detected") or {}
    by_role = rules.get("base_by_branch_prefix") or {}
    role_to_branch = {
        "integration": detected.get("integration_branch"),
        "default": detected.get("default_branch"),
    }
    prefix = pr["headRefName"].split("/", 1)[0]
    role = by_role.get(prefix)
    expected = None
    if role:
        if isinstance(role, str):
            target = role_to_branch.get(role, role)
            expected = [target] if target else None
        else:
            expected = [role_to_branch.get(r, r) for r in role]
            expected = [b for b in expected if b]
    if expected:
        if pr["baseRefName"] not in expected:
            out.append(_finding(
                "blocker", "base-branch",
                f"Branch `{prefix}/*` deve apontar para {' ou '.join(f'`{b}`' for b in expected)}, "
                f"nao para `{pr['baseRefName']}`.",
            ))
    else:
        allowed = rules.get("allowed_base_branches")
        if allowed and pr["baseRefName"] not in allowed:
            out.append(_finding(
                "blocker", "base-branch",
                f"PR aponta para `{pr['baseRefName']}`; permitido: {', '.join(allowed)}.",
            ))

    min_body = rules.get("min_description_chars", 0)
    if len((pr.get("body") or "").strip()) < min_body:
        out.append(_finding(
            "major", "pr-description",
            f"Descricao com menos de {min_body} caracteres. Explique o que muda e como testar.",
        ))

    commit_re = rules.get("commit_regex")
    if commit_re:
        bad = [c for c in commits if not re.match(commit_re, c)]
        if bad:
            out.append(_finding(
                "minor", "commit-message",
                f"{len(bad)} commit(s) fora do padrao `{commit_re}`: "
                + "; ".join(f"`{c[:60]}`" for c in bad[:5]),
            ))

    max_files = rules.get("max_changed_files")
    if max_files and pr["changedFiles"] > max_files:
        out.append(_finding(
            "minor", "pr-size",
            f"{pr['changedFiles']} arquivos alterados (limite sugerido {max_files}). "
            "Considere quebrar a PR.",
        ))

    max_lines = rules.get("max_changed_lines")
    total = pr["additions"] + pr["deletions"]
    if max_lines and total > max_lines:
        out.append(_finding(
            "minor", "pr-size",
            f"{total} linhas alteradas (limite sugerido {max_lines}).",
        ))

    paths = [f["path"] for f in files]
    forbidden = rules.get("forbidden_paths", [])
    for path in paths:
        for pattern in forbidden:
            if re.search(pattern, path):
                out.append(_finding(
                    "blocker", "forbidden-path",
                    f"Arquivo nao deveria entrar em PR (`{pattern}`).", path=path,
                ))

    tests = rules.get("require_tests")
    if tests:
        src_re = re.compile(tests["source_regex"])
        test_re = re.compile(tests["test_regex"])
        touched_src = [p for p in paths if src_re.search(p)]
        touched_test = [p for p in paths if test_re.search(p)]
        if touched_src and not touched_test:
            out.append(_finding(
                tests.get("severity", "major"), "missing-tests",
                f"{len(touched_src)} arquivo(s) de codigo alterados sem nenhum teste tocado.",
            ))

    for item in conflicts:
        if item["status"] == "conflict":
            listed = ", ".join(f"`{f}`" for f in item["files"][:10])
            extra = "" if len(item["files"]) <= 10 else f" (+{len(item['files']) - 10})"
            out.append(_finding(
                "blocker", "merge-conflict",
                f"Conflita com `{item['branch']}` em {len(item['files'])} arquivo(s): {listed}{extra}.",
            ))
        elif item["status"] == "error":
            out.append(_finding(
                "minor", "merge-conflict",
                f"Nao foi possivel testar merge contra `{item['branch']}`: {item['files'][0] if item['files'] else '?'}",
            ))

    stale = rules.get("warn_behind_commits")
    if stale:
        for item in conflicts:
            if item["branch"] != pr["baseRefName"]:
                continue
            if item["status"] == "clean" and (item.get("behind") or 0) > stale:
                out.append(_finding(
                    "minor", "stale-branch",
                    f"Branch esta {item['behind']} commits atras de `{item['branch']}`. "
                    "Faca rebase antes do merge.",
                ))

    if pr.get("mergeable") == "CONFLICTING":
        out.append(_finding(
            "blocker", "merge-conflict",
            f"GitHub reporta conflito com a base `{pr['baseRefName']}`.",
        ))

    return out


FILE_HEADER = re.compile(r"^diff --git a/(.*?) b/(.*)$")


def _diff_sections(diff_text):
    """Quebra um diff unificado em (path, bloco de texto) por arquivo."""
    path = None
    buffer = []
    for raw in diff_text.splitlines(keepends=True):
        match = FILE_HEADER.match(raw.rstrip("\n"))
        if match:
            if buffer:
                yield path, "".join(buffer)
            path = match.group(2)
            buffer = [raw]
            continue
        buffer.append(raw)
    if buffer:
        yield path, "".join(buffer)


def filter_diff(diff_text, patterns):
    """Remove do diff os arquivos que casam com ignore_paths."""
    if not patterns:
        return diff_text
    compiled = [re.compile(p) for p in patterns]
    kept = [
        block for path, block in _diff_sections(diff_text)
        if path is None or not any(r.search(path) for r in compiled)
    ]
    return "".join(kept)


def truncate_diff(diff_text, max_bytes):
    raw = diff_text.encode("utf-8")
    if len(raw) <= max_bytes:
        return diff_text
    return raw[:max_bytes].decode("utf-8", "ignore") + "\n\n[... diff truncado pelo bot ...]"


def diff_patterns(diff_text, cfg):
    """Procura padroes proibidos apenas em linhas adicionadas."""
    patterns = cfg["rules"].get("forbidden_diff_patterns", [])
    if not patterns:
        return []
    compiled = [(p["name"], re.compile(p["regex"]), p.get("severity", "major")) for p in patterns]
    max_per_file = cfg["rules"].get("max_diff_hits_per_file", 3)
    out = []
    path = None
    new_line = 0
    hits = {}
    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            path = None if target == "/dev/null" else target[2:] if target[1:2] == "/" else target
            continue
        if raw.startswith("---") or raw.startswith("diff --git"):
            continue
        if raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            new_line = int(m.group(1)) if m else 0
            continue
        if raw.startswith("+"):
            content = raw[1:]
            for name, regex, severity in compiled:
                if not regex.search(content):
                    continue
                key = (path, name)
                count = hits.get(key, 0)
                if count >= max_per_file:
                    continue
                hits[key] = count + 1
                out.append(_finding(
                    severity, name,
                    f"Padrao proibido encontrado: `{content.strip()[:120]}`",
                    path=path, line=new_line,
                ))
            new_line += 1
        elif not raw.startswith("-"):
            new_line += 1
    return out


def normalize(findings):
    """Descarta achado sem mensagem e forca severidade valida (saida de modelo e crua)."""
    out = []
    for f in findings:
        message = (f.get("message") or "").strip()
        if not message:
            continue
        f["message"] = message
        if f.get("severity") not in SEV_ORDER:
            f["severity"] = "minor"
        line = f.get("line")
        if isinstance(line, str) and line.isdigit():
            line = int(line)
        f["line"] = line if isinstance(line, int) and line > 0 else None
        if not f.get("path"):
            f["path"] = None
            f["line"] = None
        out.append(f)
    return out


def sort_findings(findings):
    return sorted(findings, key=lambda f: (SEV_ORDER.get(f["severity"], 3), f["rule"]))
