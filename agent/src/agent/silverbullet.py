import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from agent.config import Settings


class SilverBulletError(RuntimeError):
    """Raised when a page cannot be published to SilverBullet."""


class PageAlreadyExistsError(SilverBulletError):
    """Raised when create-only publication finds an existing page."""


def _normalize_page_path(value: str) -> str:
    path = PurePosixPath(value.strip("/"))
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("SILVERBULLET_PUBLISH_PATH deve ser um caminho válido")
    return path.as_posix()


def _index_markdown(page_path: str) -> str:
    escaped_path = re.escape(page_path).replace("\\", "\\\\").replace('"', '\\"')
    return (
        "# Aulas de balé\n\n"
        "${query[[\n"
        "  from p = index.pages()\n"
        f'  where string.matchRegex(p.name, "^{escaped_path}/[^/]+$")\n'
        "  order by p.name desc\n"
        "  select templates.pageItem(p)\n"
        "]]}\n"
    )


@dataclass(frozen=True)
class PublishedPage:
    local_path: Path
    url: str


class SilverBulletPublisher:
    """Publish generated Markdown through SilverBullet's HTTP file API."""

    def __init__(self, base_url: str, token: str, publish_path: str) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("SILVERBULLET_URL deve começar com http:// ou https://")
        if not token:
            raise ValueError("SILVERBULLET_TOKEN não pode estar vazio")

        self.base_url = base_url.rstrip("/")
        self.token = token
        self.publish_path = _normalize_page_path(publish_path)

    def _page_url(self, page_path: str) -> str:
        return f"{self.base_url}/{quote(page_path, safe='/')}"

    def _api_url(self, file_path: str) -> str:
        return f"{self.base_url}/.fs/{quote(file_path, safe='/')}"

    def _create_page(self, file_path: str, content: str) -> None:
        request = Request(
            self._api_url(file_path),
            data=content.encode("utf-8"),
            method="PUT",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "text/markdown; charset=utf-8",
                "If-None-Match": "*",
            },
        )
        try:
            with urlopen(request, timeout=30):
                pass
        except HTTPError as error:
            if error.code == 412:
                raise PageAlreadyExistsError(
                    f"a página {self._page_url(file_path.removesuffix('.md'))} já existe"
                ) from error
            raise SilverBulletError(
                f"SilverBullet respondeu com HTTP {error.code} ao publicar {file_path}"
            ) from error
        except URLError as error:
            raise SilverBulletError(
                f"não foi possível acessar o SilverBullet: {error.reason}"
            ) from error

    def ensure_index(self) -> None:
        """Create the dynamic lesson index without replacing an existing page."""
        try:
            self._create_page(
                f"{self.publish_path}.md",
                _index_markdown(self.publish_path),
            )
        except PageAlreadyExistsError:
            pass

    def publish(self, local_path: Path) -> PublishedPage:
        """Publish one Markdown file without replacing an existing page."""
        remote_path = f"{self.publish_path}/{local_path.name}"
        self._create_page(remote_path, local_path.read_text(encoding="utf-8"))
        return PublishedPage(
            local_path=local_path,
            url=self._page_url(remote_path.removesuffix(".md")),
        )


def create_publisher(settings: Settings) -> SilverBulletPublisher | None:
    """Build the optional publisher and reject incomplete configuration."""
    if settings.silverbullet_url is None and settings.silverbullet_token is None:
        return None
    if settings.silverbullet_url is None:
        raise ValueError("SILVERBULLET_URL é obrigatório para publicar")
    if settings.silverbullet_token is None:
        raise ValueError("SILVERBULLET_TOKEN é obrigatório para publicar")

    return SilverBulletPublisher(
        base_url=settings.silverbullet_url,
        token=settings.silverbullet_token.get_secret_value(),
        publish_path=settings.silverbullet_publish_path,
    )
