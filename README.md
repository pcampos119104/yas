# YAS

Projeto para transcrever e organizar exercícios de balé narrados em áudio,
organizado como um monorepo:

- `agent/`: pipeline de transcrição e organização com LangChain e OpenRouter.
- `app/`: reservado para o futuro webapp e mantido vazio nesta versão.

O conteúdo de `reference/` serve apenas como material local de consulta e não
faz parte do projeto.

## Requisitos

- Docker com Docker Compose
- `just`

Para executar sem containers, use Python 3.13 e `uv`.

## Configuração

Crie o arquivo local de ambiente e informe sua chave do OpenRouter:

```bash
just setup
```

Edite `.env`:

```dotenv
OPENROUTER_API_KEY=sua-chave
OPENROUTER_MODEL=openai/gpt-4.1-mini
OPENROUTER_TEMPERATURE=0
OPENROUTER_TRANSCRIPTION_MODEL=openai/gpt-transcribe
```

## Uso com Docker

```bash
just build
just agent aula.ogg
```

O arquivo de áudio deve estar dentro do diretório do repositório. O comando
transcreve o áudio, organiza os exercícios e imprime os dois resultados no
terminal. São aceitos arquivos `.ogg`, `.mp3` e `.wav`.

Outros comandos disponíveis:

```bash
just test
just check
just prod-build
```

## Uso local

```bash
uv sync --project agent
uv run --project agent ballet-agent aula.ogg
```

As configurações são lidas das variáveis de ambiente ou do arquivo `.env` no
diretório em que o comando é executado.

O fluxo usa `openai/gpt-transcribe` pelo endpoint de Speech-to-Text do
OpenRouter. A mesma `OPENROUTER_API_KEY` é usada para a transcrição e para o
modelo que organiza os exercícios.
