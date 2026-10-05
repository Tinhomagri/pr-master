# Padroes — Django + DDD (backend)

## Camadas

- `domain/` — entities, value objects, regras puras. Sem import de Django/ORM.
- `application/` — use cases. Orquestram repositorios e servicos. Uma responsabilidade por use case.
- `infrastructure/` — models Django, repositorios concretos, clientes HTTP, integracoes.
- `interfaces/` (views, serializers, urls) — apenas entrada/saida. Sem regra de negocio.

## Regras obrigatorias

- View/ViewSet nao contem regra de negocio e nao chama ORM direto: chama use case.
- Use case recebe e devolve entidades/DTOs, nao QuerySet nem Request.
- Repositorio e definido como interface no dominio e implementado em infrastructure.
- Serializer nao faz query nem calculo de negocio.
- `select_related`/`prefetch_related` em qualquer leitura que atravesse relacionamento.
- Migration: reversivel, sem `RunPython` com dado de producao, sem `ALTER` bloqueante
  em tabela grande sem aviso na descricao da PR.
- Integracao externa (iFood, WhatsApp, Prodata, TEF/SiTef) isolada em cliente proprio
  em infrastructure, com timeout explicito e tratamento de erro da borda.
- Teste de use case novo e obrigatorio. Teste de model trivial nao.
- Transacao (`atomic`) em operacao que escreve em mais de um agregado.
