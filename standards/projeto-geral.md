# Padroes gerais do projeto

> Edite este arquivo. Ele e enviado ao modelo em toda revisao.
> Regras que podem ser verificadas por regex devem ir para `config/*.json`, nao aqui.

## Git

- Branch: `feat|fix|hotfix|refactor|chore|docs|test|release` + `/` + slug em kebab-case.
- Feature e fix vao para `develop`. Somente `release/*` e `hotfix/*` vao para `main`.
- Commits em Conventional Commits.
- Rebase (nao merge) para atualizar a branch com a base.

## Pull Request

- Uma PR = uma intencao. Nao misturar refactor com feature.
- Descricao obrigatoria: o que muda, por que, como testar, o que pode quebrar.
- PR acima de ~40 arquivos ou ~1200 linhas precisa justificar o tamanho.
- Nenhum `.env`, chave, certificado ou dump no diff.

## Codigo

- Nada de debug esquecido (`console.log`, `print`, `pdb`, `debugger`, `.only(`).
- Sem segredo hardcoded; tudo via variavel de ambiente.
- SQL sempre parametrizado.
- Validacao de entrada na borda (endpoint, form, parser de arquivo).
- Tratamento de erro apenas onde a falha e possivel e a recuperacao faz sentido.
- Sem URL/IP hardcoded apontando para localhost ou ambiente especifico.
