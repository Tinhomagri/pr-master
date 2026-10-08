# Padroes — Node + TypeScript (backend/API)

## Camadas

- `routes/`/`controllers/` — entrada/saida: valida payload, chama use case, devolve status. Sem acesso direto ao banco.
- `services/`/`usecases/` — regra de negocio. Uma responsabilidade por funcao.
- `repositories/`/`infra/` — Prisma/TypeORM/Knex, clientes HTTP, filas.

## Regras obrigatorias

- Sem `any` e sem `@ts-ignore`; tipo desconhecido usa `unknown` + narrowing.
- Payload de entrada validado por schema na borda (Zod/class-validator), com limite de tamanho em lista.
- Toda rota async com tratamento de erro (middleware de erro ou wrapper): sem promise sem `catch`.
- `await` dentro de laco que bate no banco e N+1: usar `in`/`include`/`createMany`/`Promise.all` com limite.
- Query sempre parametrizada; sem template string em `$queryRawUnsafe`/`knex.raw`.
- `fetch`/`axios` com timeout explicito (`AbortSignal.timeout`/`timeout:`) e tratamento de status.
- Transacao (`$transaction`/`manager.transaction`) nao envolve chamada HTTP nem laco pesado.
- Idempotencia de webhook/pagamento reserva a chave antes de chamar o provedor externo.
- Segredo e URL via `process.env` validado no boot; nunca hardcoded, nunca `rejectUnauthorized: false`.
- Sem `console.log` em codigo de producao: logger estruturado (pino/winston).
- Teste de use case novo e obrigatorio; `.only`/`.skip` nao entram na PR.
