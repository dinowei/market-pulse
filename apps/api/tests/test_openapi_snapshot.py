import json
from pathlib import Path

from app.main import app


def test_openapi_snapshot_paths_match_application() -> None:
    snapshot_path = Path(__file__).parents[3] / "docs" / "api" / "openapi.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

    assert set(snapshot["paths"]) == set(app.openapi()["paths"])
    assert "/api/v1/portfolio-events" in snapshot["paths"]
