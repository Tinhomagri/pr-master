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


def render(pr, findings, conflicts, summary, cfg):
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
                origin = "check" if finding.get("source") == "check" else "ia"
                lines.append(
                    f"- `{finding['rule']}`{_location(finding)} — {finding['message']} _({origin})_"
                )
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
    lines = [f"# {name} — resumo", "", "| PR | autor | branch → base | achados | conflito |", "|---|---|---|---|---|"]
    for row in rows:
        conflicted = [c["branch"] for c in row["conflicts"] if c["status"] == "conflict"]
        lines.append(
            f"| [#{row['number']}]({row['url']}) | @{row['author']} | "
            f"`{row['head']}` → `{row['base']}` | {badge(row['findings'])} | "
            f"{'❌ ' + ', '.join(conflicted) if conflicted else '✅'} |"
        )
    return "\n".join(lines)
