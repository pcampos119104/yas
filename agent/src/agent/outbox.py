import json
import secrets
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from agent.config import Settings
from agent.markdown import save_lesson
from agent.models import BalletLesson
from agent.silverbullet import PublishedPage, create_publisher

JOB_ID_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
JOB_ID_LENGTH = 6
METADATA_FILENAME = "job.json"


class OutboxJob(BaseModel):
    """Durable state for one audio awaiting publication."""

    id: str
    telegram_chat_id: int
    telegram_message_id: int
    created_at: datetime
    attempts: int = Field(default=0, ge=0)
    last_attempt_at: datetime | None = None
    last_error: str | None = None
    files: list[str]
    ambiguities: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class PublishAttempt:
    job_id: str
    pages: list[PublishedPage]
    complete: bool
    error: str | None = None


class Outbox:
    """Filesystem-backed publication queue that survives container restarts."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _new_job_id(self) -> str:
        self.directory.mkdir(parents=True, exist_ok=True)
        for _ in range(100):
            job_id = "".join(
                secrets.choice(JOB_ID_ALPHABET) for _ in range(JOB_ID_LENGTH)
            )
            if not (self.directory / job_id).exists():
                return job_id
        raise RuntimeError("não foi possível gerar um identificador único")

    @staticmethod
    def _metadata_path(job_directory: Path) -> Path:
        return job_directory / METADATA_FILENAME

    def _write_job(self, job_directory: Path, job: OutboxJob) -> None:
        metadata_path = self._metadata_path(job_directory)
        temporary_path = metadata_path.with_suffix(".tmp")
        temporary_path.write_text(
            job.model_dump_json(indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(metadata_path)

    def create_job(
        self,
        lesson: BalletLesson,
        *,
        telegram_chat_id: int,
        telegram_message_id: int,
    ) -> OutboxJob:
        """Persist generated Markdown before any publication attempt."""
        job_id = self._new_job_id()
        temporary_directory = self.directory / f".{job_id}.tmp"
        job_directory = self.directory / job_id
        temporary_directory.mkdir()
        try:
            paths = save_lesson(
                lesson,
                temporary_directory,
                filename_suffix=job_id,
            )
            exercise_files = [
                path.name for path in paths if path.name != "ambiguidades.md"
            ]
            job = OutboxJob(
                id=job_id,
                telegram_chat_id=telegram_chat_id,
                telegram_message_id=telegram_message_id,
                created_at=datetime.now(UTC),
                files=exercise_files,
                ambiguities=lesson.ambiguities,
            )
            self._write_job(temporary_directory, job)
            temporary_directory.replace(job_directory)
        except Exception:
            shutil.rmtree(temporary_directory, ignore_errors=True)
            raise
        return job

    def get_job(self, job_id: str) -> OutboxJob | None:
        if (
            len(job_id) != JOB_ID_LENGTH
            or any(character not in JOB_ID_ALPHABET for character in job_id)
        ):
            return None
        metadata_path = self._metadata_path(self.directory / job_id)
        if not metadata_path.is_file():
            return None
        try:
            return OutboxJob.model_validate_json(
                metadata_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError, json.JSONDecodeError):
            return None

    def pending_jobs(self) -> list[OutboxJob]:
        if not self.directory.is_dir():
            return []
        jobs = (
            job
            for path in self.directory.iterdir()
            if path.is_dir() and not path.name.startswith(".")
            if (job := self.get_job(path.name)) is not None
        )
        return sorted(jobs, key=lambda job: job.created_at)

    @staticmethod
    def _safe_file_path(job_directory: Path, filename: str) -> Path:
        if Path(filename).name != filename or not filename.endswith(".md"):
            raise ValueError("a fila contém um nome de arquivo inválido")
        return job_directory / filename

    def _complete_job(self, job_directory: Path) -> None:
        shutil.rmtree(job_directory)

    def attempt_publish(self, job_id: str, settings: Settings) -> PublishAttempt:
        """Try every pending file and retain only files that still failed."""
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"publicação pendente não encontrada: {job_id}")

        job_directory = self.directory / job.id
        job.attempts += 1
        job.last_attempt_at = datetime.now(UTC)
        pages: list[PublishedPage] = []
        errors: list[str] = []

        if not job.files:
            self._complete_job(job_directory)
            return PublishAttempt(job.id, pages, True)

        try:
            publisher = create_publisher(settings)
            if publisher is None:
                raise ValueError(
                    "configure SILVERBULLET_URL e SILVERBULLET_TOKEN para publicar"
                )
            publisher.ensure_index()
        except (OSError, ValueError, RuntimeError) as error:
            job.last_error = str(error)
            self._write_job(job_directory, job)
            return PublishAttempt(job.id, pages, False, job.last_error)

        for filename in list(job.files):
            try:
                path = self._safe_file_path(job_directory, filename)
                if not path.is_file():
                    raise OSError(f"arquivo pendente não encontrado: {filename}")
                page = publisher.publish_idempotent(path)
                pages.append(page)
                job.files.remove(filename)
                job.last_error = None
                self._write_job(job_directory, job)
                path.unlink(missing_ok=True)
            except (OSError, ValueError, RuntimeError) as error:
                errors.append(f"{filename}: {error}")

        if not job.files:
            self._complete_job(job_directory)
            return PublishAttempt(job.id, pages, True)

        job.last_error = "; ".join(errors) or "publicação incompleta"
        self._write_job(job_directory, job)
        return PublishAttempt(job.id, pages, False, job.last_error)
