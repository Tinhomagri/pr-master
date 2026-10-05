# Padroes — React + TypeScript (frontend)

## Estrutura

- Componente em PascalCase, um componente publico por arquivo.
- Hook customizado em `use*`, sem chamada direta de API dentro de componente de UI.
- Chamada de API isolada em camada de servico, com tipos de request/response.
- Estado de servidor via React Query; estado global de UI via store (Zustand/Redux), nao prop drilling.

## Regras obrigatorias

- Sem `any` e sem `@ts-ignore`. Tipo desconhecido usa `unknown` + narrowing.
- `useEffect` sempre com array de dependencias correto; sem fetch em efeito que roda a cada render.
- Lista renderizada precisa de `key` estavel (nao indice quando a lista reordena).
- Sem `dangerouslySetInnerHTML` sem sanitizacao.
- Estado de loading e de erro tratados em toda tela que consome API.
- Sem URL de API hardcoded; usar variavel de ambiente.
- Formulario com validacao de schema, nao validacao manual espalhada.
- Acessibilidade minima: label em input, botao com nome acessivel, foco visivel.
