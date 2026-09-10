"""Run the actual CLI against synthetic files in disposable Git repositories."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def scan_repository(tmp_path: Path) -> Path:
    root = Path(__file__).resolve().parents[3]
    (tmp_path / "scripts").mkdir()
    shutil.copy2(root / "scripts/week1_gate.py", tmp_path / "scripts/week1_gate.py")
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True, capture_output=True)
    return tmp_path


def run_scan(root: Path, content: str, *, tracked: bool = True) -> subprocess.CompletedProcess[str]:
    (root / "fixture.md").write_text(content, encoding="utf-8")
    if tracked:
        subprocess.run(
            ["git", "add", "--", "fixture.md"], cwd=root, check=True, capture_output=True
        )
    return subprocess.run(
        [sys.executable, str(root / "scripts/week1_gate.py"), "secrets"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "candidate",
    [
        "BEGIN " + "PRIVATE KEY",
        "BEGIN RSA " + "PRIVATE KEY",
        "AKIA" + "A" * 16,
        "sk_" + "live_" + "synthetic_scan_fixture",
        "rk_" + "live_" + "synthetic_scan_fixture",
        "ghp" + "_synthetic_scan_fixture",
        "github_pat" + "_synthetic_scan_fixture",
        "postgresql://fixture:" + "synthetic_scan_fixture@localhost/db",
        "redis://fixture:" + "synthetic_scan_fixture@localhost/0",
        "BRAPI_API_TOKEN=" + "synthetic_scan_fixture",
    ],
    ids=[
        "private",
        "rsa",
        "aws",
        "stripe",
        "restricted",
        "github",
        "pat",
        "pg",
        "redis",
        "provider",
    ],
)
def test_secret_scan_blocks_candidates_without_echoing_values(
    scan_repository: Path, candidate: str
) -> None:
    result = run_scan(scan_repository, candidate)

    assert result.returncode == 1
    assert "fixture.md:" in result.stdout
    assert candidate not in result.stdout + result.stderr
    assert "SECRET_SCAN=PASS" not in result.stdout


@pytest.mark.parametrize("marker", ["local_only", "demo", "example", "YOUR_", "SEU_"])
@pytest.mark.parametrize("kind", ["token", "provider", "connection"])
def test_placeholder_substrings_do_not_hide_candidates(
    scan_repository: Path, marker: str, kind: str
) -> None:
    synthetic = marker + "_synthetic_scan_fixture"
    if kind == "token":
        candidate = "sk_" + "live_" + synthetic
    elif kind == "provider":
        candidate = "BRAPI_API_TOKEN=" + synthetic
    else:
        candidate = "postgresql://fixture:" + synthetic + "@localhost/db"

    result = run_scan(scan_repository, candidate)

    assert result.returncode == 1
    assert candidate not in result.stdout + result.stderr


@pytest.mark.parametrize(
    "placeholder", ["", "YOUR_TOKEN", "YOUR_API_KEY", "SEU_TOKEN", "SEU_API_KEY", "local_only"]
)
def test_exact_provider_placeholders_remain_usable(scan_repository: Path, placeholder: str) -> None:
    result = run_scan(scan_repository, "BRAPI_API_TOKEN=" + f'"{placeholder}"\n')

    assert result.returncode == 0
    assert "SECRET_SCAN=PASS" in result.stdout


@pytest.mark.parametrize("password", ["local_only", "market_pulse_local_only"])
def test_exact_local_connection_placeholders_remain_usable(
    scan_repository: Path, password: str
) -> None:
    result = run_scan(scan_repository, "postgresql://demo:" + password + "@127.0.0.1/demo\n")

    assert result.returncode == 0
    assert "SECRET_SCAN=PASS" in result.stdout


def test_untracked_files_are_scanned(scan_repository: Path) -> None:
    candidate = "ghp" + "_synthetic_scan_fixture"

    result = run_scan(scan_repository, candidate, tracked=False)

    assert result.returncode == 1
    assert "fixture.md:" in result.stdout
    assert candidate not in result.stdout + result.stderr


def test_ignored_files_stay_outside_scan(scan_repository: Path) -> None:
    (scan_repository / ".gitignore").write_text("fixture.md\n", encoding="utf-8")

    result = run_scan(scan_repository, "ghp" + "_synthetic_scan_fixture", tracked=False)

    assert result.returncode == 0
    assert "SECRET_SCAN=PASS" in result.stdout


def test_blank_env_assignment_does_not_consume_the_next_line(scan_repository: Path):
    result = run_scan(scan_repository, "BRAPI_API_TOKEN=" + "\nNEXT_VARIABLE=\n# commentary\n")
    assert result.returncode == 0
