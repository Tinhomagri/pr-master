"""Heuristicas de risco: o que um revisor senior olha antes de liberar o merge.

Cada regra daqui nasceu de um achado real em review — contador de versao
calculado sem lock, chamada externa disparada antes de reservar a chave de
idempotencia, laco pesado dentro de transacao com lock, chamada HTTP sem
timeout, arquivo de infra entrando de carona, reformatacao em massa misturada
com a feature. Tudo deterministico, sem custo de IA e sem dependencia nova.

As regras olham SOMENTE linhas adicionadas (e o contexto imediato delas), para
nao cobrar o autor por codigo que ele nao escreveu nesta PR.
"""

import re

SOURCE = "expert"

TEST_PATH = re.compile(
    r"(^|/)(tests?|spec|__tests__)/|(^|/)test_[^/]*\.py$|_(test|spec)\.(py|dart|ts|tsx|js)$"
    r"|\.(test|spec)\.[mc]?[tj]sx?$|(^|/)conftest\.py$"
    r"|(^|/)src/test/(java|kotlin|resources)/|(Test|Tests|IT)\.(java|kt)$"
)
CODE_PATH = re.compile(r"\.(py|ts|tsx|js|jsx|mjs|cjs|mts|cts|dart|go|rb|java|kt)$")
MIGRATION_PATH = re.compile(
    r"(^|/)migrations?/|\.sql$|(^|/)db/(migration|changelog)/"
    r"|(^|/)(changelog|liquibase)[^/]*\.(xml|ya?ml|json)$"
)
DEP_MANIFEST = re.compile(
    r"(^|/)(requirements[^/]*\.txt|pyproject\.toml|Pipfile|package\.json|pubspec\.yaml|go\.mod|Gemfile"
    r"|pom\.xml|build\.gradle(\.kts)?|settings\.gradle(\.kts)?|libs\.versions\.toml)$"
)
INFRA_PATH = re.compile(
    r"(^|/)(docker-compose[^/]*\.ya?ml|Dockerfile[^/]*|Makefile|nginx[^/]*\.conf|Procfile"
    r"|\.github/workflows/[^/]+|k8s/[^/]+|(terraform|helm)/[^/]+|celery[_-]?settings\.py"
    r"|ruff\.toml|\.eslintrc[^/]*|\.prettierrc[^/]*|tsconfig[^/]*\.json|\.env\.example"
    r"|application[^/]*\.(ya?ml|properties)|bootstrap[^/]*\.(ya?ml|properties)"
    r"|ecosystem\.config\.[cm]?js|nest-cli\.json|\.npmrc)$"
)

LOCK = re.compile(
    r"select_for_update|with_for_update|FOR UPDATE|get_or_create|update_or_create"
    r"|advisory_lock|SELECT \.\.\. FOR|\.lock\(|Lock\(|F\("
    r"|@Lock\(|PESSIMISTIC_(WRITE|READ)|setLockMode|LockModeType|@Version\b"
    r"|synchronized|ReentrantLock|Mutex\(|Semaphore\(|redlock|\.acquire\("
)
VERSION_CALC = re.compile(
    r"(?i)(aggregate\([^)]*Max\(|Max\(\s*[\"']?(version|numero|number|sequence|seq)"
    r"|\b(version|numero|number|sequence|counter|contador)\w*\s*(\+=\s*1|=\s*[\w.\[\]\"']+\s*\+\s*1))"
)
IDEMPOTENCY = re.compile(r"(?i)idempot")
# Escrita em sistema externo: exige sintaxe de chamada e um receptor de borda,
# senao palavras como `refunded` em constante de status viram falso positivo.
EXTERNAL_WRITE = re.compile(
    r"(?i)((gateway|client|api|http|provider|sdk|service|processor)\w*\.\w*"
    r"(pay|charge|capture|transfer|payout|refund|create|send|post|execute)\w*\s*\("
    r"|\b(create_payment|create_charge|create_order|create_subscription|send_message)\s*\()"
)
QUERY_CALL = re.compile(
    r"\.objects\.|\.filter\(|\.exclude\(|\.aggregate\(|\.count\(\)|\.exists\(\)|\.save\(\)"
    r"|\.delete\(\)|\.create\(|cursor\.execute|await \w+\.(find|get|fetch|query)"
    r"|(repository|repo|entityManager|em|jdbcTemplate|prisma|knex|queryRunner|manager|db)\s*\.\s*"
    r"(\w+\s*\.\s*)?"
    r"(find\w*|save\w*|delete\w*|update\w*|insert\w*|count|exists\w*|query\w*|create\w*|upsert|persist|merge|remove)\s*\("
    r"|createQuery\(|createNativeQuery\(|\$queryRaw|\$executeRaw"
)
LOOP_START = re.compile(r"^(\s*)(for |while |.*\.forEach\(|.*\.map\()")
HEAVY_IO = re.compile(
    r"\.read\(\)|\.open\(|open\(|loadtxt|imread|requests\.|httpx\.|urlopen\(|range\(\s*(size|len|total)"
    r"|readFileSync|Files\.read|restTemplate\.|webClient\.|HttpClient|axios\.|fetch\("
)
HTTP_CALL = re.compile(
    r"(requests|httpx|session|client)\.(get|post|put|patch|delete|request)\(|urlopen\("
    r"|axios\s*(\.(get|post|put|patch|delete|request))?\s*\(|(?<!\w)fetch\s*\("
    r"|restTemplate\.(getFor\w+|postFor\w+|put|delete|exchange|execute)\s*\("
    r"|webClient\s*\.\s*(get|post|put|patch|delete|method)\s*\(|\.newCall\s*\("
)
TIMEOUT_HINT = re.compile(
    r"timeout|deadline|Timeout|AbortSignal|AbortController|signal\s*:"
    r"|responseTimeout|connectTimeout|readTimeout"
)
LIST_FIELD = re.compile(r"ListField\(|ArrayField\(|ListSerializer\(|z\.array\(|@RequestBody\s+List<")
# Escopo transacional nas tres stacks (Django, Spring, Prisma/TypeORM/Knex).
TX_SCOPE = re.compile(
    r"transaction\.atomic|@Transactional|\$transaction\(|\.transaction\(|beginTransaction\("
)
LIST_BOUND = re.compile(
    r"max_length|max_items|max_num|max_count|maxItems|@Size\(|@ArrayMaxSize|\.max\(\s*\d"
)
TODO = re.compile(r"(?<![A-Za-z])(TODO|FIXME|XXX|HACK)(?![A-Za-z])")
ENV_VAR = re.compile(
    r"os\.environ(?:\.get)?[\(\[]\s*[\"'](\w+)[\"']|process\.env\.(\w+)"
    r"|String\.fromEnvironment\(\s*[\"'](\w+)[\"']|import\.meta\.env\.(\w+)"
    r"|System\.getenv\(\s*[\"'](\w+)[\"']|@Value\(\s*[\"']\$\{([\w.]+)"
    r"|config(?:Service)?\.get(?:OrThrow)?(?:<[^>]*>)?\(\s*[\"'](\w+)[\"']"
)
EXCEPT_LINE = re.compile(
    r"^\s*\}?\s*(except\b[^:]*:|catch\s*(\([^)]*\)|\w+)?\s*\{?)\s*$"
)
SWALLOW = re.compile(r"^\s*(pass|continue|\.\.\.|return;?|\}?\s*)$")


def _finding(severity, rule, message, path=None, line=None):
    return {
        "severity": severity,
        "rule": rule,
        "message": message,
        "path": path,
        "line": line,
        "source": SOURCE,
    }


def parse(diff_text):
    """Diff unificado -> lista de arquivos com linhas adicionadas, removidas e contexto."""
    files, current, new_line = [], None, 0
    for raw in diff_text.splitlines():
        if raw.startswith("diff --git"):
            current = None
            continue
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            path = None if target == "/dev/null" else (target[2:] if target[1:2] == "/" else target)
            current = {"path": path, "added": [], "removed": [], "rows": []}
            files.append(current)
            continue
        if current is None or raw.startswith("---"):
            continue
        if raw.startswith("@@"):
            match = re.search(r"\+(\d+)", raw)
            new_line = int(match.group(1)) if match else 0
            current["rows"].append(("@", new_line, raw))
            continue
        if raw.startswith("+"):
            current["added"].append((new_line, raw[1:]))
            current["rows"].append(("+", new_line, raw[1:]))
            new_line += 1
        elif raw.startswith("-"):
            current["removed"].append(raw[1:])
            current["rows"].append(("-", new_line, raw[1:]))
        else:
            current["rows"].append((" ", new_line, raw[1:] if raw.startswith(" ") else raw))
            new_line += 1
    return [f for f in files if f["path"]]


def _is_churn(entry):
    """Arquivo cujo conteudo adicionado e identico ao removido ignorando espaco:
    reformatacao, nao mudanca de comportamento."""
    if not entry["added"] or not entry["removed"]:
        return False
    added = re.sub(r"\s+", "", "".join(text for _, text in entry["added"]))
    removed = re.sub(r"\s+", "", "".join(entry["removed"]))
    return bool(added) and added == removed


CLIENT_PATH = re.compile(
    r"\.dart$|\.(tsx|jsx)$|(^|/)(components|screens|pages|widgets|presentation)/"
)

LOOP_EXEMPT = re.compile(
    r"(^|/)tasks\.py$|/management/commands/|celery|(^|/)migrations?/"
    r"|(^|/)(scripts|jobs|workers|seeds?|seeders)/|(Job|Scheduler|Seeder)\.(java|kt|ts|js)$"
)


def _risk(entry, cfg):
    path = entry["path"]
    out = []
    if not CODE_PATH.search(path) or TEST_PATH.search(path) or MIGRATION_PATH.search(path):
        return out
    added_text = "\n".join(text for _, text in entry["added"])
    has_lock = bool(LOCK.search(added_text))

    # 1) contador/versao calculado sem lock -> duas requisicoes concorrentes colidem
    if not has_lock:
        for line, text in entry["added"]:
            if VERSION_CALC.search(text):
                out.append(_finding(
                    "major", "versao-sem-lock",
                    "Versao/contador calculado sem lock na linha: duas requisicoes simultaneas "
                    "geram o mesmo numero (unique estoura como 500).",
                    path=path, line=line,
                ))
                break

    # 2) idempotencia conferida sem reservar a chave antes da chamada externa.
    # Vale so no servidor: no cliente nao existe linha para travar, a chave e so reenviada.
    if (
        not CLIENT_PATH.search(path)
        and IDEMPOTENCY.search(added_text)
        and EXTERNAL_WRITE.search(added_text)
        and not has_lock
    ):
        line = next(
            (ln for ln, text in entry["added"] if EXTERNAL_WRITE.search(text)), None
        )
        out.append(_finding(
            "blocker", "idempotencia-sem-reserva",
            "Chave de idempotencia conferida sem reservar a linha antes da chamada externa: "
            "dois envios simultaneos com a mesma chave executam a operacao duas vezes.",
            path=path, line=line,
        ))

    # 3) query dentro de laco (N+1) — laco de task/command faz isso de proposito
    loop_indent = None
    if LOOP_EXEMPT.search(path):
        entry_rows = []
    else:
        entry_rows = entry["rows"]
    for kind, line, text in entry_rows:
        if kind == "-":
            continue
        stripped = text.rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip())
        if loop_indent is not None and indent <= loop_indent:
            loop_indent = None
        match = LOOP_START.match(stripped)
        if match and (kind == "+" or loop_indent is None):
            loop_indent = indent
            continue
        if (
            loop_indent is not None
            and kind == "+"
            and QUERY_CALL.search(stripped)
            and not LOCK.search(stripped)
        ):
            out.append(_finding(
                "major", "query-em-laco",
                "Query dentro de laco (N+1): uma ida ao banco por item. "
                "Resolva em uma consulta com `in`/`select_related`/`bulk_*`.",
                path=path, line=line,
            ))
            break

    # 4) lock + laco/IO pesado na mesma transacao
    if TX_SCOPE.search(added_text) and has_lock and HEAVY_IO.search(added_text):
        line = next((ln for ln, text in entry["added"] if TX_SCOPE.search(text)), None)
        out.append(_finding(
            "major", "transacao-longa",
            "Transacao com lock segurando laco/IO pesado: a requisicao prende a linha por "
            "segundos. Faca o trabalho pesado fora da transacao ou em task.",
            path=path, line=line,
        ))

    # 5) chamada HTTP sem timeout explicito
    for line, text in entry["added"]:
        if HTTP_CALL.search(text) and not TIMEOUT_HINT.search(text):
            window = added_text[max(0, added_text.find(text)): added_text.find(text) + 400]
            if not TIMEOUT_HINT.search(window):
                out.append(_finding(
                    "major", "sem-timeout",
                    "Chamada HTTP sem `timeout`: uma dependencia lenta prende o worker ate o fim.",
                    path=path, line=line,
                ))
                break

    # 6) excecao engolida
    previous = None
    for kind, line, text in entry["rows"]:
        if kind == "-":
            continue
        if previous is not None and SWALLOW.match(text) and kind == "+":
            out.append(_finding(
                "major", "excecao-silenciosa",
                "Excecao capturada e descartada: a falha desaparece sem log nem reacao.",
                path=path, line=previous,
            ))
            previous = None
            continue
        previous = line if EXCEPT_LINE.match(text) else None

    # 7) lista de entrada sem limite de tamanho
    if re.search(r"serializer|schema|dto|request|payload|validator", path.lower()):
        for line, text in entry["added"]:
            if LIST_FIELD.search(text) and not LIST_BOUND.search(text):
                out.append(_finding(
                    "minor", "payload-sem-limite",
                    "Lista de entrada sem limite de tamanho: um payload grande vira milhares de linhas.",
                    path=path, line=line,
                ))
                break

    # 8) TODO/FIXME novo
    for line, text in entry["added"]:
        if TODO.search(text):
            out.append(_finding(
                "minor", "todo-novo",
                f"Pendencia deixada no codigo: `{text.strip()[:80]}`.",
                path=path, line=line,
            ))
            break
    return out


def _context(pr, entries, cfg, churn):
    """Achados que dependem do conjunto da PR e da descricao."""
    body = (pr.get("body") or "")
    body_low = body.lower()
    out = []

    # migration sem passo de deploy na descricao
    migrations = [e["path"] for e in entries if MIGRATION_PATH.search(e["path"])]
    if migrations and not re.search(r"(?i)migrat|migra[cç]", body_low):
        out.append(_finding(
            "minor", "deploy-nao-documentado",
            f"{len(migrations)} arquivo(s) de migration sem o passo de deploy na descricao "
            f"(ex.: `{migrations[0]}`).",
        ))

    # variavel de ambiente nova nao citada na descricao
    names = set()
    for entry in entries:
        if TEST_PATH.search(entry["path"]) or entry["path"] in churn:
            continue
        removed = "\n".join(entry["removed"])
        for _, text in entry["added"]:
            for match in ENV_VAR.finditer(text):
                name = next(group for group in match.groups() if group)
                # nome que ja estava no arquivo nao e variavel nova (linha so reformatada)
                if name in removed or name in body:
                    continue
                if name.upper() == name and len(name) > 3:
                    names.add(name)
    if names:
        out.append(_finding(
            "major", "env-nao-documentada",
            "Variavel de ambiente nova fora da descricao: "
            + ", ".join(f"`{n}`" for n in sorted(names)[:5])
            + " — deploy sem ela quebra.",
        ))

    # dependencia nova nao citada
    deps = set()
    for entry in entries:
        if not DEP_MANIFEST.search(entry["path"]):
            continue
        for _, text in entry["added"]:
            match = re.match(r"\s*[\"']?([A-Za-z][\w.-]{2,})[\"']?\s*[:=><~^\s]", text)
            if match and match.group(1).lower() not in body_low:
                deps.add(match.group(1))
    if deps:
        out.append(_finding(
            "minor", "dependencia-nova",
            "Dependencia nova sem justificativa na descricao: "
            + ", ".join(f"`{d}`" for d in sorted(deps)[:5]) + ".",
        ))

    # arquivo de infra de carona
    infra = [
        e["path"] for e in entries
        if INFRA_PATH.search(e["path"]) and e["path"].rsplit("/", 1)[-1] not in body
    ]
    if infra:
        out.append(_finding(
            "major", "infra-de-carona",
            f"Arquivo de infra entrou sem estar na descricao: {', '.join(f'`{p}`' for p in infra[:4])}"
            + (f" (+{len(infra) - 4})" if len(infra) > 4 else "") + ".",
        ))

    # reformatacao em massa misturada com a feature
    churn = sorted(churn)
    threshold = (cfg.get("rules", {}) or {}).get("churn_file_threshold", 3)
    if len(churn) >= threshold:
        out.append(_finding(
            "major" if len(churn) >= 10 else "minor",
            "churn-de-formatacao",
            f"{len(churn)} arquivo(s) so reformatados, sem mudanca de comportamento, misturados "
            f"na feature ({', '.join(f'`{p}`' for p in churn[:4])}"
            + (f" +{len(churn) - 4}" if len(churn) > 4 else "")
            + "): separe em outra PR, isso esconde mudanca real no meio do diff.",
        ))
    return out


def run(pr, diff_text, cfg):
    """Achados de risco sobre o diff ja filtrado por ignore_paths."""
    if not (cfg.get("rules", {}) or {}).get("expert_checks", True):
        return []
    entries = parse(diff_text)
    churn = {e["path"] for e in entries if _is_churn(e)}
    out = []
    for entry in entries:
        if entry["path"] in churn:
            continue
        out += _risk(entry, cfg)
    out += _context(pr, entries, cfg, churn)
    # corrida de idempotencia e um achado da PR, nao de cada arquivo que a menciona
    return _only_first(out, "idempotencia-sem-reserva")


def _only_first(findings, rule):
    seen = False
    out = []
    for finding in findings:
        if finding["rule"] != rule:
            out.append(finding)
            continue
        if not seen:
            seen = True
            out.append(finding)
    return out


def stacked(pr, contained, cfg):
    """PRs abertas cujos commits ja estao dentro desta: definem a ordem de merge."""
    out = []
    for other in contained[:3]:
        out.append(_finding(
            "major", "pr-empilhada",
            f"Contem a PR #{other['number']} (`{other['headRefName']}`): mergeie #{other['number']} "
            "antes, senao ela vira um diff vazio e perde a revisao.",
        ))
    return out


# Lista do que o bot garante ter conferido — vai no rodape do relatorio.
CHECKLIST = [
    "base e nome da branch, descricao e tamanho da PR",
    "merge a seco contra a base e defasagem de commits",
    "PR empilhada (ordem de merge)",
    "segredo, debug, SQL concatenado, conflito nao resolvido",
    "teste acompanhando codigo novo",
    "corrida: versao/contador sem lock, idempotencia sem reserva",
    "N+1 em laco, transacao longa com lock, chamada externa sem timeout",
    "excecao engolida, payload sem limite, TODO novo",
    "migration/env/dependencia fora da descricao e churn de formatacao",
]
