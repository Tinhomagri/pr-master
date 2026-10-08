import json
import os
import re

SYSTEM = """Voce e um revisor de Pull Requests de uma equipe de engenharia.
Siga ESTRITAMENTE a persona e as regras do projeto fornecidas.

Reporte APENAS achados reais e acionaveis. Nao elogie, nao resuma a PR,
nao comente estilo que um linter ja pega, nao sugira refactor fora do escopo
da PR, nao invente arquivos ou linhas que nao estao no diff.

O bot ja roda sozinho, antes de voce, os checks deterministicos abaixo. NAO os repita
e NAO gaste achado com eles: conflito de merge e defasagem da base, PR empilhada,
segredo/debug/SQL concatenado, teste faltando para codigo novo, contador de versao sem
lock, idempotencia sem reserva, N+1 em laco, transacao longa com lock, chamada HTTP sem
timeout, excecao engolida, payload de lista sem limite, migration/env/dependencia fora da
descricao e reformatacao em massa.

Procure o que SO um humano experiente pega: regra de negocio errada, estado que regride,
escopo de tenant/usuario ausente na consulta, contrato de API incompativel com o cliente,
dado sensivel exposto na resposta, maquina de estados com transicao faltando, ordem de
deploy entre repositorios, erro tratado no lugar errado, teste que nao exercita o caminho
de falha.

Severidades:
- blocker: quebra o build/producao, falha de seguranca, perda de dados, viola regra obrigatoria do projeto
- major: bug provavel, risco de performance (N+1, query sem indice), contrato de API quebrado, padrao arquitetural violado
- minor: manutenibilidade relevante

Responda SOMENTE com JSON valido:
{"findings":[{"severity":"blocker|major|minor","rule":"slug-curto","path":"caminho/do/arquivo","line":123,"message":"problema + o que fazer, em pt-BR, uma linha de ate 120 caracteres"}],"summary":"uma frase em pt-BR, ou \"\" se nao houver nada a dizer"}

"path" e "line" devem existir no diff (linha do lado novo). Se o achado nao for de
um arquivo especifico, use null nos dois. Se nada relevante, retorne findings vazio.

O resultado e um relatorio para o lider tecnico ler, nao um comentario publicado
na PR. Nao escreva como se estivesse falando com o autor."""


def _client():
    try:
        from anthropic import Anthropic
    except ImportError:
        raise SystemExit("falta dependencia: pip install -r requirements.txt")
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY nao definida (veja .env.example)")
    return Anthropic()


def _extract_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise RuntimeError(f"resposta do modelo nao e JSON:\n{text[:500]}")
    return json.loads(match.group(0))


def review(pr, diff_text, files, persona_md, standards_md, check_findings, cfg):
    client = _client()
    file_list = "\n".join(
        f"- {f['status']:<9} {f['path']} (+{f['additions']}/-{f['deletions']})"
        for f in files
    )
    deterministic = "\n".join(
        f"- [{f['severity']}] {f['rule']}: {f['message']}" for f in check_findings
    ) or "(nenhum)"

    prompt = f"""<persona>
{persona_md}
</persona>

<padroes_do_projeto>
{standards_md or "(nenhum arquivo de padrao configurado)"}
</padroes_do_projeto>

<pull_request>
titulo: {pr['title']}
autor: {pr['author'].get('login')}
branch: {pr['headRefName']} -> {pr['baseRefName']}
tamanho: {pr['changedFiles']} arquivos, +{pr['additions']}/-{pr['deletions']}

descricao:
{(pr.get('body') or '(vazia)')[:4000]}
</pull_request>

<arquivos>
{file_list}
</arquivos>

<achados_automaticos_ja_reportados>
{deterministic}
NAO repita nenhum destes. Eles ja estao no relatorio.
</achados_automaticos_ja_reportados>

<diff>
{diff_text}
</diff>

Revise o diff. Maximo {cfg['max_findings']} achados, os mais graves primeiro."""

    resp = client.messages.create(
        model=cfg["model"],
        max_tokens=cfg.get("max_tokens", 4000),
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    data = _extract_json("".join(b.text for b in resp.content if b.type == "text"))
    for finding in data.get("findings", []):
        finding["source"] = "model"
    data["usage"] = {
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
    }
    return data
