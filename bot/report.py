ICON = {"blocker": "🔴", "major": "🟠", "minor": "🟡"}
LABEL = {"blocker": "Bloqueante", "major": "Importante", "minor": "Menor"}


def _location(finding):
    if not finding.get("path"):
        return ""
    if finding.get("line"):
        return f" — `{finding['path']}:{finding['line']}`"
    return f" — `{finding['path']}`"


def counts(findings):
    return {s: sum(1 for f in findings if f["severity"] == s) for s in ICON}


def badge(findings):
    c = counts(findings)
    hit = " ".join(f"{ICON[s]}{c[s]}" for s in ICON if c[s])
    return hit or "✅ limpo"


VERDICT_RULES = (
    ("blocker", "🔴", "NAO APTA PARA MERGE", "bloqueante(s) para resolver antes de qualquer merge"),
    ("major", "🟠", "APTA COM RESSALVAS", "ponto(s) importante(s): decida com o autor antes de mergear"),
    ("minor", "🟡", "APTA", "ponto(s) menor(es), nao travam o merge"),
)


def verdict(findings, conflicts, pr, strict=False):
    """Resposta a pergunta que importa: pode mergear?"""
    base_conflict = any(
        c["status"] == "conflict" and c["branch"] == pr["baseRefName"] for c in conflicts
    )
    if base_conflict:
        return "🔴", "NAO APTA PARA MERGE", f"conflito com a base `{pr['baseRefName']}` — resolva o merge primeiro"
    c = counts(findings)
    for severity, icon, label, tail in VERDICT_RULES:
        if c[severity]:
            if severity == "major" and strict:
                return "🔴", "NAO APTA PARA MERGE", f"{c[severity]} {tail} (modo --strict)"
            return icon, label, f"{c[severity]} {tail}"
    return "✅", "APTA PARA MERGE", "nenhum desvio nos checks deterministicos"


def render(pr, findings, conflicts, summary, cfg, strict=False):
    name = cfg.get("bot_name", "PR Master")
    author = pr["author"].get("login", "?")
    lines = [
        f"# {name} — PR #{pr['number']}",
        "",
        f"**{pr['title']}**",
        "",
        f"- autor: @{author}",
        f"- branch: `{pr['headRefName']}` → `{pr['baseRefName']}`",
        f"- tamanho: {pr['changedFiles']} arquivos, +{pr['additions']}/-{pr['deletions']}",
        f"- link: {pr['url']}",
        "",
    ]
    icon, label, reason = verdict(findings, conflicts, pr, strict=strict)
    lines += [f"## Veredito: {icon} {label}", "", f"{reason}.", ""]

    if summary:
        lines += [f"> {summary}", ""]

    lines.append("## Merge com as branches principais")
    for item in conflicts:
        if item["status"] == "clean":
            behind = item.get("behind")
            tail = f" — branch {behind} commits atras" if behind else ""
            lines.append(f"- ✅ `{item['branch']}` sem conflito{tail}")
        elif item["status"] == "conflict":
            lines.append(
                f"- ❌ `{item['branch']}` **conflito** em {len(item['files'])} arquivo(s)"
            )
            for path in item["files"][:15]:
                lines.append(f"  - `{path}`")
            if len(item["files"]) > 15:
                lines.append(f"  - … +{len(item['files']) - 15}")
        elif item["status"] == "missing":
            lines.append(f"- ⚪ `{item['branch']}` nao existe no remoto")
        else:
            lines.append(f"- ⚠️ `{item['branch']}` nao foi possivel verificar")
    lines.append("")

    lines.append("## Padroes do projeto")
    if not findings:
        lines.append("Nenhum desvio encontrado.")
    else:
        c = counts(findings)
        lines.append(
            " · ".join(f"{ICON[s]} {c[s]} {LABEL[s].lower()}" for s in ICON if c[s])
        )
        lines.append("")
        for severity in ("blocker", "major", "minor"):
            group = [f for f in findings if f["severity"] == severity]
            if not group:
                continue
            lines.append(f"### {ICON[severity]} {LABEL[severity]}")
            for finding in group:
                origin = {"check": "check", "expert": "risco"}.get(finding.get("source"), "ia")
                lines.append(
                    f"- `{finding['rule']}`{_location(finding)} — {finding['message']} _({origin})_"
                )
            lines.append("")

    from .expert import CHECKLIST

    lines.append("## O que foi conferido")
    lines += [f"- {item}" for item in CHECKLIST]
    lines.append("")
    lines.append("---")
    lines.append(
        f"_padrao `{cfg.get('persona')}` · modelo `{cfg['model']}` · "
        "relatorio local, nada foi publicado na PR._"
    )
    return "\n".join(lines)


def digest(rows, cfg):
    """Resumo de varias PRs, uma linha cada."""
    name = cfg.get("bot_name", "PR Master")
    lines = [
        f"# {name} — resumo", "",
        "| PR | autor | branch → base | achados | veredito |", "|---|---|---|---|---|",
    ]
    for row in rows:
        icon, label, _ = verdict(
            row["findings"], row["conflicts"],
            {"baseRefName": row["base"]}, strict=row.get("strict", False),
        )
        lines.append(
            f"| [#{row['number']}]({row['url']}) | @{row['author']} | "
            f"`{row['head']}` → `{row['base']}` | {badge(row['findings'])} | {icon} {label} |"
        )
    return "\n".join(lines)
