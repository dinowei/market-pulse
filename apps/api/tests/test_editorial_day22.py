import psycopg
import pytest
from fastapi.testclient import TestClient

import app.routers as routers
from app.editorial.service import InMemoryEditorialService
from app.editorial.validator import (
    EditorialBlock,
    EditorialBlockType,
    EditorialSource,
    EditorialStatus,
    validate_editorial_blocks,
)
from app.main import app


def source() -> EditorialSource:
    return EditorialSource(label="Fonte demonstrativa", publisher="Mercado Pulse")


def test_validator_accepts_factual_vendas_and_requires_source_for_fact() -> None:
    valid = EditorialBlock(
        content_type=EditorialBlockType.FACT,
        text="As vendas reportadas no período foram de 10 unidades.",
        sources=(source(),),
    )
    assert validate_editorial_blocks((valid,)).valid

    missing_source = valid.model_copy(update={"sources": ()})
    report = validate_editorial_blocks((missing_source,))
    assert not report.valid
    assert any(v.code == "FACT_SOURCE_REQUIRED" for v in report.violations)


@pytest.mark.parametrize(
    "text",
    ["Compre PETR4 agora", "Venda PETR4", "Mantenha sua posição", "Lucro garantido"],
)
def test_validator_blocks_prescriptive_context(text: str) -> None:
    block = EditorialBlock(
        content_type=EditorialBlockType.RISK, text=text, sources=(source(),)
    )
    report = validate_editorial_blocks((block,))
    assert not report.valid
    assert any(v.code == "PRESCRIPTIVE_LANGUAGE" for v in report.violations)


def test_validator_requires_attribution_and_conditional_language() -> None:
    consensus = EditorialBlock(
        content_type=EditorialBlockType.THIRD_PARTY_CONSENSUS,
        text="A mediana publicada pela fonte foi 10.",
        sources=(),
    )
    scenario = EditorialBlock(
        content_type=EditorialBlockType.CONDITIONAL_SCENARIO,
        text="O ativo subirá no próximo mês.",
        sources=(source(),),
    )
    report = validate_editorial_blocks((consensus, scenario))
    assert {v.code for v in report.violations} >= {
        "CONSENSUS_SOURCE_REQUIRED",
        "SCENARIO_CONDITIONAL_LANGUAGE_REQUIRED",
    }


def test_status_transitions_are_explicit_and_append_only() -> None:
    service = InMemoryEditorialService()
    post = service.create_draft(
        slug="morning-call-demo",
        title="Morning Call demonstrativo",
        blocks=(
            EditorialBlock(
                content_type=EditorialBlockType.LIMITATION,
                text="Dados sintéticos de demonstração.",
            ),
        ),
    )
    assert post.status is EditorialStatus.DRAFT
    service.transition(post.slug, EditorialStatus.UNDER_REVIEW)
    service.transition(post.slug, EditorialStatus.APPROVED)
    service.transition(post.slug, EditorialStatus.PUBLISHED)
    with pytest.raises(ValueError):
        service.transition(post.slug, EditorialStatus.DRAFT)
    with pytest.raises(ValueError):
        service.delete(post.slug)


def test_public_routes_return_only_published_posts(monkeypatch) -> None:
    service = InMemoryEditorialService()
    service.create_draft(
        slug="draft-post", title="Rascunho", blocks=(),
    )
    published = service.create_draft(
        slug="morning-call-demo",
        title="Morning Call",
        blocks=(EditorialBlock(content_type=EditorialBlockType.LIMITATION, text="DEMO"),),
    )
    service.transition(published.slug, EditorialStatus.UNDER_REVIEW)
    service.transition(published.slug, EditorialStatus.APPROVED)
    service.transition(published.slug, EditorialStatus.PUBLISHED)
    app.dependency_overrides[routers.get_editorial_service] = lambda: service

    response = TestClient(app).get("/api/v1/editorial/posts")
    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["morning-call-demo"]
    assert TestClient(app).get("/api/v1/editorial/morning-call/latest").status_code == 200
    assert TestClient(app).get("/api/v1/editorial/posts/draft-post").status_code == 404
    app.dependency_overrides.pop(routers.get_editorial_service, None)


def test_editorial_schema_has_provenance_and_published_versions_are_immutable() -> None:
    from app.core.config import get_settings

    with psycopg.connect(get_settings().database_url) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            ).fetchall()
        }
        assert {"editorial_posts", "editorial_post_versions", "editorial_sources"} <= tables
        columns = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='editorial_sources'"
            ).fetchall()
        }
        assert {"publisher", "url", "retrieved_at", "justification"} <= columns
        post_id = conn.execute(
            "INSERT INTO editorial_posts (slug, title, status, published_at) "
            "VALUES (%s, %s, 'PUBLISHED', now()) RETURNING id",
            ("schema-editorial-test", "Schema test"),
        ).fetchone()[0]
        version_id = conn.execute(
            "INSERT INTO editorial_post_versions "
            "(post_id, version_number, title, blocks, status_snapshot) "
            "VALUES (%s, 1, %s, %s::jsonb, 'PUBLISHED') RETURNING id",
            (post_id, "Schema test", "[]"),
        ).fetchone()[0]
        conn.commit()
        try:
            with pytest.raises(psycopg.DatabaseError):
                conn.execute(
                    "UPDATE editorial_post_versions SET title='blocked' WHERE id=%s",
                    (version_id,),
                )
            conn.rollback()
        finally:
            conn.execute("TRUNCATE editorial_posts CASCADE")
            conn.commit()
