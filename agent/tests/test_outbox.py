from pathlib import Path
from unittest.mock import patch

from agent.config import Settings
from agent.models import BalletExercise, BalletLesson, ExerciseStep
from agent.outbox import Outbox
from agent.silverbullet import PublishedPage


def sample_lesson() -> BalletLesson:
    return BalletLesson(
        exercises=[
            BalletExercise(
                title="Pliés",
                steps=[ExerciseStep(order=1, action="Fazer um demi-plié")],
            )
        ],
        ambiguities=["A posição dos braços não ficou clara."],
    )


def settings() -> Settings:
    return Settings(
        _env_file=None,
        silverbullet_url="https://notes.example.com",
        silverbullet_token="secret",
    )


def test_outbox_keeps_markdown_after_publication_failure(tmp_path: Path) -> None:
    outbox = Outbox(tmp_path / "outbox")
    job = outbox.create_job(
        sample_lesson(),
        telegram_chat_id=123,
        telegram_message_id=456,
    )

    with patch("agent.outbox.create_publisher") as create_publisher:
        publisher = create_publisher.return_value
        publisher.publish_idempotent.side_effect = RuntimeError("offline")
        attempt = outbox.attempt_publish(job.id, settings())

    pending = outbox.get_job(job.id)
    assert attempt.complete is False
    assert pending is not None
    assert pending.attempts == 1
    assert "offline" in (pending.last_error or "")
    assert (tmp_path / "outbox" / job.id / f"plies-{job.id}.md").is_file()


def test_outbox_deletes_job_after_successful_publication(tmp_path: Path) -> None:
    outbox = Outbox(tmp_path / "outbox")
    job = outbox.create_job(
        sample_lesson(),
        telegram_chat_id=123,
        telegram_message_id=456,
    )

    with patch("agent.outbox.create_publisher") as create_publisher:
        publisher = create_publisher.return_value
        publisher.publish_idempotent.side_effect = lambda path: PublishedPage(
            path,
            f"https://notes.example.com/ballet/aulas/{path.stem}",
        )
        attempt = outbox.attempt_publish(job.id, settings())

    assert attempt.complete is True
    assert attempt.pages[0].url.endswith(f"/plies-{job.id}")
    assert outbox.get_job(job.id) is None
    assert not (tmp_path / "outbox" / job.id).exists()
