# YAS

Projeto para transcrever e organizar exercícios de balé narrados em áudio,
organizado como um monorepo:

- `agent/`: pipeline de transcrição e organização com OpenAI e LangChain.
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
OPENAI_API_KEY=sua-chave-openai
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TEMPERATURE=0
OPENAI_TRANSCRIPTION_MODEL=gpt-transcribe
SILVERBULLET_URL=https://notes.faramir.com.br
SILVERBULLET_TOKEN=sua-chave-do-silverbullet
SILVERBULLET_PUBLISH_PATH=ballet/aulas
```

As variáveis `SILVERBULLET_URL` e `SILVERBULLET_TOKEN` são opcionais, mas devem
ser informadas juntas. Quando configuradas, cada exercício também é publicado
em `https://notes.faramir.com.br/ballet/aulas/<nome-do-exercicio>`. A página
`/ballet/aulas` é criada automaticamente com uma lista dinâmica dos exercícios,
caso ainda não exista. Páginas existentes nunca são sobrescritas.

## Uso com Docker

```bash
just build
just agent aula.ogg
```

O arquivo de áudio deve estar dentro do diretório do repositório. O comando
transcreve o áudio, organiza os exercícios e cria um arquivo Markdown para cada
exercício no diretório `output/`. Cada arquivo apresenta a sequência na forma
vertical e também como uma linha do tempo Mermaid. As ambiguidades da aula são
salvas separadamente em `output/ambiguidades.md`. São aceitos arquivos `.ogg`,
`.mp3` e `.wav`.

Para publicar novamente os arquivos Markdown que já estão em `output/`, sem
transcrever áudio nem chamar o LLM:

```bash
just publish
```

O comando publica todos os arquivos `.md`, ignora outros formatos e preserva
páginas que já existam no SilverBullet.

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

O fluxo usa `gpt-transcribe` diretamente pela API oficial da OpenAI. O agente
LangChain usa `ChatOpenAI` com `gpt-4.1-mini` para interpretar e organizar os
exercícios. As duas etapas compartilham a mesma `OPENAI_API_KEY`.
