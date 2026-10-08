"""H-25 D-5: archiving records the archive instant, not the publication instant."""

from datetime import UTC, datetime, timedelta

from app.editorial.service import EditorialPost, PostgresEditorialService
from app.editorial.validator import EditorialBlock, EditorialSource, EditorialStatus

PUBLISHED_AT = datetime(2026, 1, 30, 11, tzinfo=UTC)


class _Connection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None

    def execute(self, sql: str, params: tuple = ()):
        self.calls.append((sql, params))
        return self

    def fetchone(self):
        return {"current_version_id": "version-1"}

    def commit(self) -> None:
        return None


class _Service(PostgresEditorialService):
    def __init__(self, status: EditorialStatus) -> None:
        self.connection = _Connection()
        self.post = EditorialPost(
            id="post-1",
            slug="morning-call",
            title="Morning Call",
            summary=None,
            blocks=(
                EditorialBlock(
                    content_type="FACT",
                    text="A Fonte A publicou o indicador X.",
                    sources=(EditorialSource(label="Indicador X", publisher="Fonte A"),),
                ),
            ),
            status=status,
            version=1,
            created_at=PUBLISHED_AT - timedelta(hours=1),
            published_at=PUBLISHED_AT if status is EditorialStatus.PUBLISHED else None,
        )

    def _connect(self):
        return self.connection

    def get_by_id(self, post_id: str) -> EditorialPost:
        return self.post


def _update_params(service: _Service) -> tuple:
    return next(params for sql, params in service.connection.calls if "UPDATE" in sql)


def test_archiving_keeps_the_publication_time_and_stamps_the_archive_time() -> None:
    service = _Service(EditorialStatus.PUBLISHED)
    before = datetime.now(UTC)
    result = service.transition_by_id("post-1", EditorialStatus.ARCHIVED, actor_user_id="r")
    status, published_at, archived_at, *_ = _update_params(service)
    assert status == "ARCHIVED"
    assert published_at == PUBLISHED_AT, "the publication instant is preserved"
    assert archived_at >= before, "archived_at is the archive instant"
    assert result.published_at == PUBLISHED_AT


def test_publishing_stamps_publication_and_leaves_archive_empty() -> None:
    service = _Service(EditorialStatus.APPROVED)
    before = datetime.now(UTC)
    service.transition_by_id("post-1", EditorialStatus.PUBLISHED, actor_user_id="r")
    _, published_at, archived_at, *_ = _update_params(service)
    assert published_at >= before
    assert archived_at is None
