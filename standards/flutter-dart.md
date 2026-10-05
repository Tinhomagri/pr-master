# Padroes — Flutter + Dart (mobile)

## Camadas (feature-first)

- `domain/` — models, value objects, regras puras. Sem import de Dio, Flutter ou storage.
- `data/` — `*_api.dart` fala HTTP (Dio); `*_repository.dart` orquestra api + cache + fila.
- `application/` — providers (Riverpod), casos de uso. Sem widget.
- `presentation/` — screens e widgets. Sem HTTP, sem SQL, sem regra de negocio.

Violacao tipica: screen chamando `*_api.dart` direto, ou repository importando `material.dart`.

## Modelos

- `fromJson`/`toJson` explicitos e tolerantes a campo ausente/nulo do backend.
- Nao usar `json['x'] as String` em campo que o backend pode omitir — quebra em runtime.
- `==`/`hashCode` em model usado como chave de lista ou de `Set`.

## Rede

- Toda chamada passa pelo `DioClient`; nunca instanciar `Dio()` solto.
- Erro de rede sobe como `ApiException` tipada, nao como `DioException` cru para a UI.
- Nenhuma URL de base no codigo: vem de `--dart-define` / config.

## Async e estado

- `setState`/`ref.read` depois de `await` exige checar `mounted` antes.
- `Future` sem `await` em caminho que precisa do resultado e bug (unawaited silencioso).
- Timer/StreamSubscription criado precisa de `dispose`/`cancel` — vazamento garantido sem isso.

## Offline / fila de sincronizacao

- Operacao pendente precisa ser idempotente: reenvio nao pode duplicar registro no servidor.
- Falha permanente (4xx de validacao) nao deve ficar em retry infinito — precisa de descarte ou DLQ.
- Ordem de dependencia entre operacoes enfileiradas tem de ser respeitada (criar antes de atualizar).
- Fila persistida precisa tolerar payload de versao antiga sem explodir ao desserializar.

## Testes

- Mudanca em `lib/**` acompanha teste em `test/**`.
- Fakes em `test/support/`, nao mocks ad hoc dentro do teste.
- Teste de repository cobre o caminho de erro, nao so o happy path.
