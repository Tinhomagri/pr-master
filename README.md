# PR Master

Analisa Pull Requests e entrega o relatorio **no seu terminal ou em arquivo local**.
Nao comenta, nao aprova, nao escreve nada no GitHub — so leitura.

Checa tres coisas:

1. **A PR nao sai do padrao do projeto** — base errada para o prefixo da branch,
   descricao vazia, codigo fora da pasta do dominio, debug esquecido, segredo no diff,
   SQL concatenado, teste faltando, arquivo de infra entrando sem motivo.
2. **Nao ha risco classico de producao** (`bot/expert.py`, deterministico) — contador/versao
   calculado sem lock, chave de idempotencia conferida sem reservar a linha antes da chamada
   externa, N+1 dentro de laco, transacao com lock segurando IO pesado, chamada HTTP sem
   timeout, excecao engolida, lista de entrada sem limite, migration/variavel de ambiente/
   dependencia que nao estao na descricao, reformatacao em massa misturada com a feature e
   PR empilhada sobre outra PR aberta (ordem de merge).
3. **Nao ha conflito com as branches principais** — merge a seco (`git merge-tree`) do
   head da PR contra as branches principais, listando os arquivos em conflito e quantos
   commits a branch esta defasada.

As branches principais sao **detectadas no proprio repo**, sem configuracao: o bot le a
default branch (`gh repo view`), lista os heads do remoto (`git ls-remote`) e fica com o
que casa com `main_branch_patterns`. A branch de integracao (para onde `feature/*` e
`fix/*` devem apontar) e a primeira de `integration_branch_priority` que existe ali.

```
<NAME PROJECT>  → default=main    integracao=dev
 <NAME PROJECT> → default=master  integracao=develop
```

Por isso a mesma configuracao serve para repos com convencoes diferentes. Para forcar,
use `--default-branch NOME` ou `"auto_detect_branches": false` + `"main_branches": [...]`.

Os achados deterministicos vem de regex e git (rapido, sem custo, sem falso positivo de
opiniao). A analise de arquitetura e logica vem do Claude, usando o padrao de review do
time em `standards/time-t4e.md` + os padroes de stack em `standards/*.md`.

## Instalacao

```bash
cd ~/"Área de trabalho"/pr-master
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env     # coloque sua ANTHROPIC_API_KEY
gh auth status           # precisa estar logado no GitHub
```

## Uso

```bash
# uma PR, relatorio no terminal
./run.sh --project  --repo  <NAME PROJECT> review 221

# so os checks deterministicos (sem custo de IA, roda em segundos)
./run.sh --project django-ddd --repo   <NAME PROJECT> --no-ai review 221

# todas as PRs abertas: tabela resumo + relatorio por PR em reports/
./run.sh --project django-ddd --repo   <NAME PROJECT>--save scan

# so as PRs de um autor
./run.sh --project react-ts --repo   <NAME PROJECT>--author <NAME> scan

# saida estruturada para dashboard/script
./run.sh --project django-ddd --repo  <NAME PROJECT> --json review 221

# ver quais branches o bot detectou
./run.sh --project django-ddd --repo  <NAME PROJECT> --no-ai -v review 221

# branches do remoto
./run.sh --repo  <NAME PROJECT> branches
```

| Flag | Efeito |
|---|---|
| `--save` | grava `reports/<owner>_<repo>/<data>-pr-<n>.md` |
| `--out DIR` | muda a pasta de saida |
| `--no-ai` | pula a chamada ao modelo |
| `--json` | saida estruturada |
| `--model claude-opus-5` | analise mais profunda |
| `--default-branch X` | força a branch principal, pula a deteccao |
| `--fail-on-blocker` | exit 1 se houver bloqueante |
| `--strict` | exigente: achado importante tambem reprova (veredito e exit code) |
| `--no-stack` | pula a deteccao de PR empilhada |
| `-v` | mostra tokens gastos |

## Perfis prontos

| `--project` | stack | padroes |
|---|---|---|
| `django-ddd` | Python + Django + DDD | `standards/django-ddd.md` |
| `java-spring` | Java + Spring Boot | `standards/java-spring.md` |
| `node-api` | Node + TypeScript (API) | `standards/node-api.md` |
| `react-ts` | React + TypeScript | `standards/react-ts.md` |
| `flutter-dart` | Flutter + Dart | `standards/flutter-dart.md` |

As heuristicas de risco (`bot/expert.py`) rodam em qualquer perfil e conhecem os idiomas
das tres stacks de backend: JPA/`@Transactional`/`RestTemplate` em Java, Prisma/TypeORM/
`fetch`/`axios` em Node e ORM/`transaction.atomic`/`requests` em Python.

## Adicionar um projeto

1. `cp config/projects/django-ddd.json config/projects/meu-projeto.json`
2. Ajuste `rules` e `standards_files` (branches sao detectadas automaticamente).
3. Escreva os padroes da stack em `standards/meu-projeto.md`.
4. Rode com `--project meu-projeto`.

`config/default.json` e herdado; o arquivo do projeto sobrescreve por chave (merge
profundo), exceto listas, que sao substituidas por inteiro.

## Configuracao

| Chave | Efeito |
|---|---|
| `bot_name` | nome no cabecalho do relatorio |
| `persona` | arquivo em `standards/` com o padrao de review do time |
| `auto_detect_branches` | detecta default/integracao no repo (default: `true`) |
| `main_branch_patterns` | regex das branches que contam como principais |
| `integration_branch_priority` | ordem de preferencia da branch de integracao |
| `max_diff_bytes` | corta o diff antes de enviar ao modelo (controle de custo) |
| `max_findings` | teto de achados que o modelo pode gerar |
| `rules.base_by_branch_prefix` | prefixo → `"integration"` ou `"default"` (resolvido na deteccao) |
| `rules.forbidden_diff_patterns` | regex sobre **linhas adicionadas** (nome + severidade) |
| `rules.forbidden_paths` | `.env`, `.pem`, credenciais |
| `rules.require_tests` | exige teste quando certos caminhos de codigo sao tocados |
| `rules.ignore_paths` | lockfiles, `dist/`, minificados |

## Garantia de somente-leitura

`bot/github.py` nao tem nenhuma funcao de escrita: so `gh pr view`, `gh pr diff` e
`gh api` em GET. O clone fica em `.cache/` como mirror bare e nunca recebe push.
O padrao de review em `standards/time-t4e.md` descreve o estilo do time, nao uma pessoa.
