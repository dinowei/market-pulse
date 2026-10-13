"""The secret scanner must catch Redis-over-TLS URLs, and only real credentials.

Fixtures are assembled by concatenation: a literal credential-shaped URL in this file
would make the scanner flag the repository itself.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def scan_repository(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    shutil.copy2(REPO_ROOT / "scripts/week1_gate.py", tmp_path / "scripts/week1_gate.py")
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True, capture_output=True)
    return tmp_path


def run_scan(root: Path, content: str) -> subprocess.CompletedProcess[str]:
    (root / "fixture.md").write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "--", "fixture.md"], cwd=root, check=True, capture_output=True)
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
        "rediss://default:" + "FAKE_TOKEN_123@exemplo.invalid:6379",
        "REDISS://default:" + "FAKE_TOKEN_123@exemplo.invalid:6379",
        "rediss://" + ":FAKE_TOKEN_123@exemplo.invalid:6379",
        "redis://" + ":FAKE_TOKEN_123@exemplo.invalid:6379",
        "MARKET_PULSE_TEST_REDIS_URL=rediss://default:" + "FAKE_TOKEN_123@exemplo.invalid:6379",
    ],
    ids=["rediss", "rediss-uppercase", "rediss-empty-user", "redis-empty-user", "env-assignment"],
)
def test_redis_urls_with_a_credential_are_reported_without_echoing_it(
    scan_repository: Path, candidate: str
) -> None:
    result = run_scan(scan_repository, candidate)

    assert result.returncode == 1
    assert "fixture.md:" in result.stdout
    assert "FAKE_TOKEN_123" not in result.stdout + result.stderr
    assert "SECRET_SCAN=PASS" not in result.stdout


@pytest.mark.parametrize(
    "placeholder",
    [
        "MARKET_PULSE_TEST_REDIS_URL=rediss://<credenciais>@<host-do-upstash>:6379\n",
        "rediss://<credenciais>@<host-do-upstash>:6379\n",
        "postgresql://<credenciais>@<host-direto-do-neon>/market_pulse_test?sslmode=require\n",
    ],
    ids=["env-assignment", "rediss", "postgres"],
)
def test_the_credentials_placeholder_is_not_reported(
    scan_repository: Path, placeholder: str
) -> None:
    result = run_scan(scan_repository, placeholder)

    assert result.returncode == 0
    assert "SECRET_SCAN=PASS" in result.stdout


@pytest.mark.parametrize("password", ["local_only", "market_pulse_local_only"])
def test_exact_local_placeholders_stay_usable_over_tls_too(
    scan_repository: Path, password: str
) -> None:
    result = run_scan(scan_repository, "rediss://demo:" + password + "@127.0.0.1:6379/0\n")

    assert result.returncode == 0
    assert "SECRET_SCAN=PASS" in result.stdout


@pytest.mark.parametrize(
    "harmless",
    ["redis://127.0.0.1:6379/15\n", "rediss://exemplo.invalid:6379\n", "redis://:6379/0\n"],
    ids=["no-credential", "tls-no-credential", "port-only"],
)
def test_urls_without_credentials_are_not_reported(scan_repository: Path, harmless: str) -> None:
    result = run_scan(scan_repository, harmless)

    assert result.returncode == 0
    assert "SECRET_SCAN=PASS" in result.stdout


def test_the_committed_env_example_passes_the_scanner(scan_repository: Path) -> None:
    # Guards the real file: its Neon and Upstash format lines must never trip the scan.
    result = run_scan(scan_repository, (REPO_ROOT / ".env.example").read_text(encoding="utf-8"))

    assert result.returncode == 0, result.stdout
    assert "SECRET_SCAN=PASS" in result.stdout
