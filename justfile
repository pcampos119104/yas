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

# Run the test suite in a container
test:
    {{ compose }} run --rm --no-deps agent uv run --frozen pytest

# Run static checks in a container
check:
    {{ compose }} run --rm --no-deps agent uv run --frozen ruff check .

# Build the production image
prod-build:
    docker build -f agent/Dockerfile -t yas-agent:prod agent
