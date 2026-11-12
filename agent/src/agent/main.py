import argparse
from collections.abc import Sequence

from agent.agent import create_ballet_agent


def run(prompt: str) -> str:
    """Send one prompt to the agent and return its final response."""
    ballet_agent = create_ballet_agent()
    result = ballet_agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]}
    )
    return str(result["messages"][-1].content)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YAS ballet agent")
    parser.add_argument(
        "prompt",
        nargs="?",
        help="mensagem enviada ao agente; se omitida, será solicitada no terminal",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    prompt = args.prompt
    if prompt is None:
        try:
            prompt = input("Você: ")
        except EOFError:
            parser.error("informe uma mensagem para o agente")

    if not prompt.strip():
        parser.error("a mensagem não pode estar vazia")

    try:
        response = run(prompt)
    except ValueError as error:
        parser.error(str(error))

    print(f"Agente: {response}")


if __name__ == "__main__":
    main()
