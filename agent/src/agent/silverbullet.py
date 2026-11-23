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

    USER_AGENT = "YAS-Ballet-Agent/0.1"

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

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": self.USER_AGENT,
            "X-Sync-Mode": "true",
        }

    def _http_error(self, error: HTTPError, action: str, file_path: str) -> None:
        try:
            details = error.read().decode("utf-8", errors="replace").strip()
        except (AttributeError, OSError):
            details = ""
        message = (
            f"SilverBullet respondeu com HTTP {error.code} "
            f"ao {action} {file_path}"
        )
        if details:
            message += f": {details}"
        raise SilverBulletError(message) from error

    def _page_exists(self, file_path: str) -> bool:
        request = Request(
            self._api_url(file_path),
            method="GET",
            headers=self._headers(),
        )
        try:
            with urlopen(request, timeout=30):
                return True
        except HTTPError as error:
            if error.code == 404:
                return False
            self._http_error(error, "consultar", file_path)
        except URLError as error:
            raise SilverBulletError(
                f"não foi possível acessar o SilverBullet: {error.reason}"
            ) from error
        return False

    def _create_page(self, file_path: str, content: str) -> None:
        if self._page_exists(file_path):
            raise PageAlreadyExistsError(
                f"a página {self._page_url(file_path.removesuffix('.md'))} já existe"
            )

        request = Request(
            self._api_url(file_path),
            data=content.encode("utf-8"),
            method="PUT",
            headers={
                **self._headers(),
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
            self._http_error(error, "publicar", file_path)
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

    def check_connection(self) -> None:
        """Validate connectivity and authentication without changing pages."""
        file_path = f"{self.publish_path}.md"
        request = Request(
            self._api_url(file_path),
            method="GET",
            headers=self._headers(),
        )
        try:
            with urlopen(request, timeout=30):
                pass
        except HTTPError as error:
            if error.code != 404:
                self._http_error(error, "testar conexão com", file_path)
        except URLError as error:
            raise SilverBulletError(
                f"não foi possível acessar o SilverBullet: {error.reason}"
            ) from error

    def publish(self, local_path: Path) -> PublishedPage:
        """Publish one Markdown file without replacing an existing page."""
        remote_path = f"{self.publish_path}/{local_path.name}"
        self._create_page(remote_path, local_path.read_text(encoding="utf-8"))
        return PublishedPage(
            local_path=local_path,
            url=self._page_url(remote_path.removesuffix(".md")),
        )

    def publish_idempotent(self, local_path: Path) -> PublishedPage:
        """Publish once and accept an existing page only when content matches."""
        remote_path = f"{self.publish_path}/{local_path.name}"
        content = local_path.read_text(encoding="utf-8")
        request = Request(
            self._api_url(remote_path),
            method="GET",
            headers=self._headers(),
        )
        try:
            with urlopen(request, timeout=30) as response:
                existing_content = response.read().decode("utf-8")
        except HTTPError as error:
            if error.code != 404:
                self._http_error(error, "consultar", remote_path)
        except URLError as error:
            raise SilverBulletError(
                f"não foi possível acessar o SilverBullet: {error.reason}"
            ) from error
        else:
            if existing_content == content:
                return PublishedPage(
                    local_path=local_path,
                    url=self._page_url(remote_path.removesuffix(".md")),
                )
            raise PageAlreadyExistsError(
                f"a página {self._page_url(remote_path.removesuffix('.md'))} "
                "já existe com conteúdo diferente"
            )

        try:
            self._create_page(remote_path, content)
        except PageAlreadyExistsError:
            # Another retry may have completed between the GET and PUT.
            return self.publish_idempotent(local_path)
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
