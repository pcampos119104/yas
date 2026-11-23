from pydantic import ValidationError

from agent.config import Settings
from agent.silverbullet import SilverBulletError, create_publisher


def check_connection(settings: Settings) -> str:
    """Check the configured SilverBullet API without changing pages."""
    publisher = create_publisher(settings)
    if publisher is None:
        raise ValueError(
            "configure SILVERBULLET_URL e SILVERBULLET_TOKEN para testar"
        )
    publisher.check_connection()
    return publisher.base_url


def main() -> None:
    try:
        base_url = check_connection(Settings())
    except (ValidationError, OSError, ValueError, SilverBulletError) as error:
        print(f"Falha na conexão com o SilverBullet: {error}")
        raise SystemExit(1) from error
    print(f"Conexão com o SilverBullet confirmada: {base_url}")


if __name__ == "__main__":
    main()
