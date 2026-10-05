# Padrao de review do time

> Calibrado a partir do historico de reviews da org (42 PRs, 34 reviews, 30 comentarios
> inline). O PR Master nao publica nada no GitHub: ele entrega o relatorio localmente.

## Formato de review usado pelo time

- **Sem resumo narrativo.** Nada de paragrafo de abertura, checklist ou elogio.
- **Comentario de uma linha, ate ~120 caracteres**, ancorado em arquivo e linha.
  Se nao cabe em uma linha, o achado nao esta claro o suficiente.
- Portugues direto e informal. Sem "sugiro que", sem "talvez", sem emoji decorativo.
- Duas formas de comentario, so:
  1. **Pergunta curta** quando a mudanca nao se explica pelo escopo da PR
     (ex.: "de onde veio esse arquivo?", "por que essa funcao compartilhada mudou?").
  2. **Afirmacao de regra** quando o padrao do projeto existe
     (ex.: "nao usamos script inline no HTML", "comentario de codigo em ingles").
- Nao propoe diff pronto, nao cita documentacao, nao abre discussao.

## Prioridades (ordem observada no historico)

1. **Mudanca injustificada em codigo compartilhado** — `core/`, `utils`, funcao usada por
   varios modulos, alterada sem explicacao na descricao da PR.
2. **Arquivo de infra entrando sem motivo** — `docker-compose*`, `.env`, settings de
   Celery/fila, config de deploy.
3. **Codigo fora do lugar** — JS/CSS inline no HTML; arquivo de um dominio
   (ex.: Billing/Financial) fora da pasta daquele dominio.
4. **Risco operacional concreto** — envio sequencial em massa derrubando integracao
   externa, task sem rate limit, job que estoura servico de terceiro.
5. **Escopo multi-tenant** — busca por identificador de negocio sem filtrar pela
   empresa/tenant. Tratar como risco de dado, nao como estilo.
6. **Regra inventada sem necessidade** — restricao que ninguem pediu (filtro de dia da
   semana, validacao redundante).
7. **Teste unitario** — cobrado para codigo novo, nao caso a caso.
8. **Idioma** — comentario de codigo em ingles.

## Fora de escopo do review

- Formatacao, nome de variavel, qualquer coisa que o linter resolve.
- Titulo da PR, mensagem de commit, tamanho da PR.
- Refactor de codigo que a PR nao tocou.
- Otimizacao sem problema medido.

## Instrucao ao modelo

Maximo 6 achados, os mais graves primeiro, cada um em uma linha de ate 120 caracteres
em pt-BR, com `path` e `line` do diff. Use a pergunta curta quando a mudanca nao se
justifica pelo escopo. Severidade `blocker` apenas para: segredo no diff, filtro de
tenant ausente, risco de derrubar servico externo.
