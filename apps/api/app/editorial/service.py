from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Iterable
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings
from app.editorial.validator import (
    EditorialBlock,
    EditorialStatus,
    EditorialValidationReport,
    validate_editorial_blocks,
)


class EditorialPost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    slug: str
    title: str
    summary: str | None
    blocks: tuple[EditorialBlock, ...]
    status: EditorialStatus
    version: int
    created_at: datetime
    published_at: datetime | None = None
    validation_report: EditorialValidationReport | None = None


class InMemoryEditorialService:
    def __init__(self) -> None:
        self._posts: dict[str, EditorialPost] = {}

    def create_draft(
        self, *, slug: str, title: str, blocks: Iterable[EditorialBlock], summary: str | None = None
    ) -> EditorialPost:
        if slug in self._posts:
            raise ValueError("editorial slug already exists")
        post = EditorialPost(
            id=str(uuid4()),
            slug=slug,
            title=title,
            summary=summary,
            blocks=tuple(blocks),
            status=EditorialStatus.DRAFT,
            version=1,
            created_at=datetime.now(timezone.utc),
        )
        self._posts[slug] = post
        return post

    def transition(self, slug: str, target: EditorialStatus) -> EditorialPost:
        post = self._posts[slug]
        allowed = {
            EditorialStatus.DRAFT: {EditorialStatus.UNDER_REVIEW},
            EditorialStatus.UNDER_REVIEW: {EditorialStatus.APPROVED},
            EditorialStatus.APPROVED: {EditorialStatus.PUBLISHED},
            EditorialStatus.PUBLISHED: {EditorialStatus.ARCHIVED},
            EditorialStatus.ARCHIVED: set(),
        }
        if target not in allowed[post.status]:
            raise ValueError(f"invalid editorial transition: {post.status} -> {target}")
        report = validate_editorial_blocks(post.blocks)
        if target is EditorialStatus.PUBLISHED and not report.valid:
            raise ValueError("editorial validation failed")
        published_at = (
            datetime.now(timezone.utc)
            if target is EditorialStatus.PUBLISHED
            else post.published_at
        )
        updated = post.model_copy(
            update={
                "status": target,
                "published_at": published_at,
                "validation_report": report,
            }
        )
        self._posts[slug] = updated
        return updated

    def delete(self, slug: str) -> None:
        post = self._posts[slug]
        if post.status is EditorialStatus.PUBLISHED:
            raise ValueError("published editorial content is append-only")
        raise ValueError("editorial posts are append-only")

    def list_published(self) -> list[EditorialPost]:
        return sorted(
            (post for post in self._posts.values() if post.status is EditorialStatus.PUBLISHED),
            key=lambda post: post.published_at or post.created_at,
            reverse=True,
        )

    def get_published(self, slug: str) -> EditorialPost | None:
        post = self._posts.get(slug)
        return post if post and post.status is EditorialStatus.PUBLISHED else None

    def latest_published(self) -> EditorialPost | None:
        posts = self.list_published()
        return posts[0] if posts else None


class PostgresEditorialService(InMemoryEditorialService):
    """PostgreSQL adapter for published reads and append-only editorial writes."""

    def _connect(self):
        return psycopg.connect(get_settings().database_url, row_factory=dict_row)

    @staticmethod
    def _post(row: dict) -> EditorialPost:
        raw_blocks = row["blocks"] or []
        if isinstance(raw_blocks, str):
            raw_blocks = json.loads(raw_blocks)
        blocks = tuple(EditorialBlock.model_validate(block) for block in raw_blocks)
        return EditorialPost(
            id=str(row["id"]), slug=row["slug"], title=row["title"], summary=row["summary"],
            blocks=blocks, status=EditorialStatus(row["status_snapshot"]),
            version=row["version_number"], created_at=row["created_at"],
            published_at=row["published_at"],
        )

    def list_published(self) -> list[EditorialPost]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT p.id, p.slug, p.title, p.summary, p.published_at,
                          v.blocks, v.status_snapshot, v.version_number, v.created_at
                   FROM editorial_posts p
                   JOIN LATERAL (
                     SELECT * FROM editorial_post_versions v0
                     WHERE v0.post_id=p.id AND v0.status_snapshot='PUBLISHED'
                     ORDER BY v0.version_number DESC LIMIT 1
                   ) v ON TRUE
                   WHERE p.status='PUBLISHED'
                   ORDER BY p.published_at DESC, p.id DESC"""
            ).fetchall()
        return [self._post(row) for row in rows]

    def get_published(self, slug: str) -> EditorialPost | None:
        return next((post for post in self.list_published() if post.slug == slug), None)

    def latest_published(self) -> EditorialPost | None:
        posts = self.list_published()
        return posts[0] if posts else None
