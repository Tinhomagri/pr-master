# Padroes — Java + Spring Boot (backend)

## Camadas

- `controller/` (ou `web/`) — apenas entrada/saida: valida DTO, chama service, devolve response. Sem regra de negocio e sem repository.
- `service/` (ou `application/`) — caso de uso. Uma responsabilidade por metodo publico.
- `domain/` — entidades e regras puras. Sem anotacao de framework web.
- `repository/`/`infrastructure/` — JPA, clientes HTTP, mensageria, integracoes.

## Regras obrigatorias

- Controller nao injeta repository: injeta service.
- DTO de entrada com Bean Validation (`@NotNull`, `@Size`, `@Valid`); entidade JPA nunca e exposta como request/response.
- `@Transactional` no service, nunca no controller; metodo `@Transactional` nao faz chamada HTTP nem laco pesado dentro.
- Leitura que atravessa relacionamento usa `JOIN FETCH` ou `@EntityGraph` — `FetchType.EAGER` e fetch dentro de laco sao N+1.
- Query com parametro nomeado/`?1`; sem concatenar string em `createQuery`/`jdbcTemplate`.
- `RestTemplate`/`WebClient`/OkHttp com timeout de conexao e de leitura explicitos.
- Contador/versao concorrente usa `@Version` (optimistic) ou `@Lock(PESSIMISTIC_WRITE)`; nao `max()+1`.
- `catch` nunca vazio nem so com comentario: log com contexto ou rethrow de excecao de dominio.
- Sem `System.out.println`/`printStackTrace`: usar SLF4J.
- Segredo e URL em `application.yml`/variavel de ambiente, nunca no codigo.
- Migration Flyway/Liquibase: versionada, reversivel e citada na descricao da PR.
- Teste de service novo e obrigatorio (`src/test/java/...`); getter/setter nao precisa teste.
