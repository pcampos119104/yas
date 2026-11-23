compose := "docker compose -f compose.yml"

# List all available commands
default:
    just --list

# Create the local environment file without overwriting an existing one
setup:
    test -f .env || cp .env.example .env

# Build the development image
build:
    {{ compose }} build agent

# Transcribe and organize one audio file from the repository directory
agent audio:
    {{ compose }} run --rm agent uv run --frozen python -m agent.main "/workspace/{{ audio }}"

# Publish existing Markdown files without invoking transcription or the LLM
publish:
    {{ compose }} run --rm agent uv run --frozen python -m agent.publish

# Run the audio-only Telegram bot with long polling
telegram:
    {{ compose }} run --rm agent uv run --frozen python -m agent.telegram

# Validate the Telegram token through getMe
test-telegram:
    {{ compose }} run --rm --no-deps agent uv run --frozen python -m agent.check_telegram

# Validate SilverBullet connectivity and authentication without changing pages
test-silverbullet:
    {{ compose }} run --rm --no-deps agent uv run --frozen python -m agent.check_silverbullet

# Run the test suite in a container
test:
    {{ compose }} run --rm --no-deps agent uv run --frozen pytest

# Run static checks in a container
check:
    {{ compose }} run --rm --no-deps agent uv run --frozen ruff check .

# Build the production image
prod-build:
    docker build -f agent/Dockerfile -t yas-agent:prod agent
