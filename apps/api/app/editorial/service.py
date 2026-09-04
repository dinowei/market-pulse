from __future__ import annotations

import json
from datetime import date, datetime, timezone
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
    content_date: date | None = None
    blocks: tuple[EditorialBlock, ...]
    status: EditorialStatus
    version: int
    created_at: datetime
    published_at: datetime | None = None
    validation_report: EditorialValidationReport | None = None


class InMemoryEditorialService:
    def __init__(self) -> None:
        self._posts: dict[str, EditorialPost] = {}
        self._history: dict[str, list[EditorialPost]] = {}
        self.review_events: list[dict[str, object]] = []

    def create_draft(
        self,
        *,
        slug: str,
        title: str,
        blocks: Iterable[EditorialBlock],
        summary: str | None = None,
        content_date: date | None = None,
        created_by_user_id: str | None = None,
    ) -> EditorialPost:
        if slug in self._posts:
            raise ValueError("editorial slug already exists")
        post = EditorialPost(
            id=str(uuid4()),
            slug=slug,
            title=title,
            summary=summary,
            content_date=content_date,
            blocks=tuple(blocks),
            status=EditorialStatus.DRAFT,
            version=1,
            created_at=datetime.now(timezone.utc),
        )
        self._posts[slug] = post
        self._history[slug] = [post]
        self.review_events.append(
            {"event_type": "CREATED", "slug": slug, "actor_user_id": created_by_user_id}
        )
        return post

    def get_by_id(self, post_id: str) -> EditorialPost:
        for post in self._posts.values():
            if post.id == post_id:
                return post
        raise KeyError("editorial post not found")

    def add_version(
        self,
        post_id: str,
        *,
        title: str,
        summary: str | None,
        blocks: Iterable[EditorialBlock],
        content_date: date | None = None,
    ) -> EditorialPost:
        current = self.get_by_id(post_id)
        version = current.version + 1
        draft = current.model_copy(
            update={
                "title": title,
                "summary": summary,
                "blocks": tuple(blocks),
                "content_date": content_date or current.content_date,
                "version": version,
                "status": EditorialStatus.DRAFT,
                "published_at": None,
                "validation_report": None,
            }
        )
        self._posts[draft.slug] = draft
        self._history[draft.slug].append(draft)
        self.review_events.append(
            {"event_type": "CORRECTED", "slug": draft.slug, "version": version}
        )
        return draft

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
            datetime.now(timezone.utc) if target is EditorialStatus.PUBLISHED else post.published_at
        )
        updated = post.model_copy(
            update={
                "status": target,
                "published_at": published_at,
                "validation_report": report,
            }
        )
        self._posts[slug] = updated
        self._history[slug].append(updated)
        self.review_events.append(
            {"event_type": target.value, "slug": slug, "version": post.version}
        )
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

    def public_versions(self, slug: str) -> list[EditorialPost]:
        return [
            post for post in self._history.get(slug, []) if post.status is EditorialStatus.PUBLISHED
        ]

    def transition_by_id(
        self,
        post_id: str,
        target: EditorialStatus,
        *,
        actor_user_id: str | None = None,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> EditorialPost:
        post = self.get_by_id(post_id)
        updated = self.transition(post.slug, target)
        self.review_events.append(
            {
                "event_type": target.value,
                "post_id": post_id,
                "actor_user_id": actor_user_id,
                "reason": reason,
                "request_id": request_id,
            }
        )
        return updated

    def list_admin(self) -> list[EditorialPost]:
        return sorted(self._posts.values(), key=lambda post: post.created_at, reverse=True)


class PostgresEditorialService(InMemoryEditorialService):
    """PostgreSQL adapter for published reads and append-only editorial writes."""

    def _connect(self):
        return psycopg.connect(get_settings().database_url, row_factory=dict_row)

    @staticmethod
    def _persist_blocks(conn, version_id: str, blocks: tuple[EditorialBlock, ...]) -> None:
        for position, block in enumerate(blocks):
            block_row = conn.execute(
                "INSERT INTO editorial_blocks "
                "(post_version_id,position,content_type,body) VALUES (%s,%s,%s,%s) "
                "RETURNING id",
                (version_id, position, block.content_type.value, block.text),
            ).fetchone()
            for source in block.sources:
                conn.execute(
                    "INSERT INTO editorial_sources "
                    "(post_version_id,block_id,label,publisher,url,retrieved_at,justification) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (
                        version_id,
                        block_row["id"],
                        source.label,
                        source.publisher,
                        source.url,
                        source.retrieved_at,
                        source.justification,
                    ),
                )

    @staticmethod
    def _post(row: dict) -> EditorialPost:
        raw_blocks = row["blocks"] or []
        if isinstance(raw_blocks, str):
            raw_blocks = json.loads(raw_blocks)
        blocks = tuple(EditorialBlock.model_validate(block) for block in raw_blocks)
        return EditorialPost(
            id=str(row["id"]),
            slug=row["slug"],
            title=row["title"],
            summary=row["summary"],
            content_date=row.get("content_date"),
            blocks=blocks,
            status=EditorialStatus(row.get("status", row["status_snapshot"])),
            version=row["version_number"],
            created_at=row["created_at"],
            published_at=row["published_at"],
        )

    def create_draft(
        self,
        *,
        slug: str,
        title: str,
        blocks: Iterable[EditorialBlock],
        summary: str | None = None,
        content_date: date | None = None,
        created_by_user_id: str | None = None,
    ) -> EditorialPost:
        block_values = tuple(blocks)
        with self._connect() as conn:
            try:
                post = conn.execute(
                    "INSERT INTO editorial_posts "
                    "(slug,title,summary,content_date,status,created_by_user_id) "
                    "VALUES (%s,%s,%s,%s,'DRAFT',%s) "
                    "RETURNING id,slug,title,summary,content_date,created_at",
                    (slug, title, summary, content_date, created_by_user_id),
                ).fetchone()
                version = conn.execute(
                    "INSERT INTO editorial_post_versions "
                    "(post_id,version_number,title,summary,blocks,status_snapshot,"
                    "validation_report) "
                    "VALUES (%s,1,%s,%s,%s::jsonb,'DRAFT','{}'::jsonb) "
                    "RETURNING id,created_at",
                    (
                        post["id"],
                        title,
                        summary,
                        json.dumps([block.model_dump(mode="json") for block in block_values]),
                    ),
                ).fetchone()
                self._persist_blocks(conn, version["id"], block_values)
                conn.execute(
                    "UPDATE editorial_posts SET current_version_id=%s WHERE id=%s",
                    (version["id"], post["id"]),
                )
                conn.commit()
            except psycopg.errors.UniqueViolation as exc:
                conn.rollback()
                raise ValueError("editorial slug already exists") from exc
        return EditorialPost(
            id=str(post["id"]),
            slug=slug,
            title=title,
            summary=summary,
            content_date=content_date,
            blocks=block_values,
            status=EditorialStatus.DRAFT,
            version=1,
            created_at=post["created_at"],
        )

    def _admin_row(self, post_id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT p.id,p.slug,p.title,p.summary,p.content_date,p.status,p.published_at,
                          v.blocks,v.status_snapshot,v.version_number,v.created_at
                   FROM editorial_posts p
                   JOIN editorial_post_versions v ON v.id=COALESCE(
                     p.current_version_id,
                     (SELECT v2.id FROM editorial_post_versions v2
                      WHERE v2.post_id=p.id
                      ORDER BY v2.version_number DESC LIMIT 1)
                   )
                   WHERE p.id=%s""",
                (post_id,),
            ).fetchone()
        if row is None:
            raise KeyError("editorial post not found")
        return row

    def get_by_id(self, post_id: str) -> EditorialPost:
        return self._post(self._admin_row(post_id))

    def add_version(
        self,
        post_id: str,
        *,
        title: str,
        summary: str | None,
        blocks: Iterable[EditorialBlock],
        content_date: date | None = None,
    ) -> EditorialPost:
        current = self.get_by_id(post_id)
        block_values = tuple(blocks)
        report = validate_editorial_blocks(block_values)
        with self._connect() as conn:
            version = conn.execute(
                "INSERT INTO editorial_post_versions "
                "(post_id,version_number,title,summary,blocks,status_snapshot,validation_report) "
                "VALUES (%s,%s,%s,%s,%s::jsonb,'DRAFT',%s::jsonb) "
                "RETURNING id,created_at",
                (
                    post_id,
                    current.version + 1,
                    title,
                    summary,
                    json.dumps([b.model_dump(mode="json") for b in block_values]),
                    report.model_dump_json(),
                ),
            ).fetchone()
            self._persist_blocks(conn, version["id"], block_values)
            conn.execute(
                "UPDATE editorial_posts SET current_version_id=%s, "
                "content_date=COALESCE(%s,content_date), updated_at=now(), "
                "status='DRAFT' WHERE id=%s",
                (version["id"], content_date, post_id),
            )
            conn.commit()
        return current.model_copy(
            update={
                "title": title,
                "summary": summary,
                "blocks": block_values,
                "content_date": content_date or current.content_date,
                "version": current.version + 1,
                "status": EditorialStatus.DRAFT,
                "published_at": None,
                "validation_report": report,
            }
        )

    def transition_by_id(
        self,
        post_id: str,
        target: EditorialStatus,
        *,
        actor_user_id: str | None = None,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> EditorialPost:
        current = self.get_by_id(post_id)
        allowed = {
            EditorialStatus.DRAFT: {EditorialStatus.UNDER_REVIEW},
            EditorialStatus.UNDER_REVIEW: {EditorialStatus.APPROVED},
            EditorialStatus.APPROVED: {EditorialStatus.PUBLISHED},
            EditorialStatus.PUBLISHED: {EditorialStatus.ARCHIVED},
            EditorialStatus.ARCHIVED: set(),
        }
        if target not in allowed[current.status]:
            raise ValueError(f"invalid editorial transition: {current.status} -> {target}")
        report = validate_editorial_blocks(current.blocks)
        if target is EditorialStatus.PUBLISHED and not report.valid:
            raise ValueError("editorial validation failed")
        now = (
            datetime.now(timezone.utc)
            if target is EditorialStatus.PUBLISHED
            else current.published_at
        )
        with self._connect() as conn:
            version_row = conn.execute(
                "SELECT current_version_id FROM editorial_posts WHERE id=%s", (post_id,)
            ).fetchone()
            conn.execute(
                "UPDATE editorial_posts SET status=%s,published_at=%s,"
                "archived_at=%s, published_version_id=CASE WHEN %s='PUBLISHED' "
                "THEN current_version_id ELSE published_version_id END, "
                "updated_at=now() WHERE id=%s",
                (
                    target.value,
                    now,
                    now if target is EditorialStatus.ARCHIVED else None,
                    target.value,
                    post_id,
                ),
            )
            conn.execute(
                "INSERT INTO editorial_review_events "
                "(post_id,post_version_id,actor_user_id,event_type,from_status,"
                "to_status,reason,request_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    post_id,
                    version_row[0] if version_row else None,
                    actor_user_id,
                    target.value,
                    current.status.value,
                    target.value,
                    reason,
                    request_id,
                ),
            )
            conn.commit()
        return current.model_copy(
            update={"status": target, "published_at": now, "validation_report": report}
        )

    def list_admin(self) -> list[EditorialPost]:
        with self._connect() as conn:
            ids = conn.execute(
                "SELECT id FROM editorial_posts ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [self.get_by_id(str(row["id"] if isinstance(row, dict) else row[0])) for row in ids]

    def public_versions(self, slug: str) -> list[EditorialPost]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT p.id,p.slug,p.content_date,p.published_at,v.title,v.summary,"
                "v.blocks,'PUBLISHED' AS status_snapshot,v.version_number,v.created_at "
                "FROM editorial_posts p JOIN editorial_post_versions v "
                "ON v.post_id=p.id JOIN editorial_review_events e "
                "ON e.post_version_id=v.id AND e.to_status='PUBLISHED' "
                "WHERE p.slug=%s "
                "ORDER BY v.version_number DESC",
                (slug,),
            ).fetchall()
        return [self._post(row) for row in rows]

    def list_published(self) -> list[EditorialPost]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT p.id, p.slug, p.title, p.summary, p.published_at,
                          v.blocks, 'PUBLISHED' AS status_snapshot, v.version_number, v.created_at
                   FROM editorial_posts p
                   JOIN editorial_post_versions v ON v.id=p.published_version_id
                   WHERE p.status='PUBLISHED'
                   ORDER BY p.published_at DESC, p.id DESC"""
            ).fetchall()
        return [self._post(row) for row in rows]

    def get_published(self, slug: str) -> EditorialPost | None:
        return next((post for post in self.list_published() if post.slug == slug), None)

    def latest_published(self) -> EditorialPost | None:
        posts = self.list_published()
        return posts[0] if posts else None
