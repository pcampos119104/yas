# YAS

Projeto de um assistente de ballet organizado como um monorepo:

- `agent/`: agente conversacional com LangChain e OpenAI.
- `app/`: reservado para o futuro webapp e mantido vazio nesta versão.

O conteúdo de `reference/` serve apenas como material local de consulta e não
faz parte do projeto.

## Requisitos

- Docker com Docker Compose
- `just`

Para executar sem containers, use Python 3.13 e `uv`.

## Configuração

Crie o arquivo local de ambiente e informe sua chave da OpenAI:

```bash
just setup
```

Edite `.env`:

```dotenv
OPENAI_API_KEY=sua-chave
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TEMPERATURE=0
```

## Uso com Docker

```bash
just build
just agent
```

O comando `just agent` abre uma sessão para digitar uma pergunta. O container
encerra depois de exibir a resposta.

Outros comandos disponíveis:

```bash
just test
just check
just prod-build
```

## Uso local

```bash
uv sync --project agent
uv run --project agent ballet-agent "Explique as cinco posições básicas."
```

As configurações são lidas das variáveis de ambiente ou do arquivo `.env` no
diretório em que o comando é executado.
