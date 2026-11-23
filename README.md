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

Crie o arquivo local de ambiente:

```bash
just setup
```

Edite `.env` para usar a CLI:

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

## Bot do Telegram

O bot recebe somente mensagens de voz e arquivos de áudio `.ogg`, `.mp3` ou
`.wav`. Mensagens de texto e comandos são ignorados. O bot usa long polling,
portanto não precisa de domínio, webhook nem porta pública.

### 1. Criar e preparar o bot

1. Abra uma conversa com o `@BotFather` no Telegram.
2. Execute `/newbot`, escolha o nome e guarde o token recebido.
3. Adicione o bot à conversa privada ou ao grupo que será usado.
4. Para uso em grupo, execute `/setprivacy` no `@BotFather`, selecione o bot e
   escolha `Disable`. Isso permite que ele receba os áudios enviados ao grupo.

### 2. Descobrir os IDs autorizados

Antes de iniciar o YAS, envie uma mensagem ou áudio para o bot e consulte a API
oficial do Telegram:

```bash
read -s TELEGRAM_BOT_TOKEN
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates"
```

No JSON retornado:

- `message.chat.id` é o `TELEGRAM_ALLOWED_CHAT_ID`;
- `message.from.id` é um item de `TELEGRAM_ALLOWED_USER_IDS`.

IDs de grupos normalmente começam com `-100`. Faça essa consulta antes de
iniciar o long polling, pois somente um consumidor pode chamar `getUpdates` para
o mesmo bot.

### 3. Configurar o ambiente

Adicione ao `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=token-fornecido-pelo-botfather
TELEGRAM_ALLOWED_CHAT_ID=-1001234567890
TELEGRAM_ALLOWED_USER_IDS=[123456789]
TELEGRAM_MAX_AUDIO_BYTES=20971520
TELEGRAM_RETRY_INTERVAL_SECONDS=300
OUTBOX_DIR=data/outbox
```

`TELEGRAM_ALLOWED_USER_IDS` deve ser uma lista JSON. Mais de uma pessoa pode ser
autorizada, por exemplo `[123456789,987654321]`. O limite padrão de áudio é
20 MiB e a fila de publicação é verificada a cada 300 segundos.

### 4. Executar localmente

Com Docker:

```bash
just build
just telegram
```

Sem Docker:

```bash
uv sync --project agent
uv run --project agent python -m agent.telegram
```

Ao receber um áudio autorizado, o bot:

1. baixa o arquivo temporariamente;
2. transcreve e organiza os exercícios;
3. salva os Markdown em uma fila persistente;
4. tenta publicá-los no SilverBullet;
5. responde com os links publicados.

Cada áudio recebe um identificador de seis caracteres. Uma aula de pliés pode
ser publicada, por exemplo, em:

```text
https://notes.faramir.com.br/ballet/aulas/plies-01jabc
```

Se o SilverBullet estiver indisponível ou mal configurado, o Markdown permanece
em `OUTBOX_DIR`. O bot tenta novamente no intervalo configurado e apresenta o
botão **Tentar novamente**. Depois que a publicação é confirmada, o arquivo
local é excluído. As ambiguidades são enviadas pelo Telegram, mas não são
publicadas no SilverBullet.

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
just test-telegram
just test-silverbullet
just test
just check
just prod-build
```

`test-telegram` valida o token pela operação `getMe`. `test-silverbullet` faz
uma leitura autenticada da API. Os dois testes são somente leitura e não criam,
alteram nem excluem páginas.

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

## Deploy no Dokploy

O deploy usa `compose.prod.yml` e executa um único worker de long polling. Não
configure domínio ou porta para esse serviço.

### 1. Preparar o repositório

Envie o projeto para um repositório Git acessível pelo Dokploy. O Dockerfile de
produção está em `agent/Dockerfile`, e o Compose de produção está na raiz como
`compose.prod.yml`.

### 2. Criar o serviço

1. No Dokploy, crie um projeto.
2. Adicione um serviço do tipo **Docker Compose**.
3. Conecte o repositório e a branch desejada.
4. Informe `compose.prod.yml` como caminho do Compose.
5. Não adicione domínio e não exponha portas.

### 3. Configurar variáveis

Cadastre as variáveis no ambiente de produção do serviço:

```dotenv
OPENAI_API_KEY=sua-chave-openai
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TEMPERATURE=0
OPENAI_TRANSCRIPTION_MODEL=gpt-transcribe

SILVERBULLET_URL=https://notes.faramir.com.br
SILVERBULLET_TOKEN=sua-chave-do-silverbullet
SILVERBULLET_PUBLISH_PATH=ballet/aulas

TELEGRAM_BOT_TOKEN=token-fornecido-pelo-botfather
TELEGRAM_ALLOWED_CHAT_ID=-1001234567890
TELEGRAM_ALLOWED_USER_IDS=[123456789]
TELEGRAM_MAX_AUDIO_BYTES=20971520
TELEGRAM_RETRY_INTERVAL_SECONDS=300
```

Não salve tokens no repositório. O `compose.prod.yml` define
`OUTBOX_DIR=/agent/data/outbox`.

### 4. Persistência e deploy

O Compose declara o volume nomeado `yas-data`, montado em `/agent/data`. Ele
preserva os Markdown pendentes quando o container é reiniciado ou recriado.

Faça o deploy e acompanhe os logs. A inicialização bem-sucedida mantém o
container em execução aguardando áudios. Erros como token ausente ou IDs não
configurados encerram o processo e aparecem nos logs do serviço.

Após o primeiro deploy:

1. envie um áudio curto de uma conta autorizada;
2. confirme nos logs que ele foi processado;
3. verifique o link retornado pelo bot;
4. interrompa temporariamente o SilverBullet para validar que o arquivo fica na
   fila e é publicado após o serviço voltar.

Mantenha apenas uma réplica do bot. O long polling do Telegram e a fila local
não foram projetados para múltiplos containers simultâneos.
