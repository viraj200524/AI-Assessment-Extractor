"""Shared-key gating and rate limiting on the endpoints that cost quota or destroy data.

Reads stay open by design: a reviewer must be able to explore the deployed demo without a
signup wall. Only mutating endpoints are gated.
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.api.v1.endpoints.parse as parse_module
from app.core.config import Settings, get_settings
from app.core.rate_limit import parse_rate_limiter
from app.core.security import ACCESS_KEY_HEADER
from app.main import app
from tests.test_parse_jobs import FILES, StubGemini, _fake_rasterize, _wait_for_terminal

DEMO_KEY = "s3cret-demo-key"


@pytest.fixture(autouse=True)
def clean_rate_limiter():
    parse_rate_limiter.reset()
    yield
    parse_rate_limiter.reset()
    app.dependency_overrides.pop(get_settings, None)
    get_settings.cache_clear()


@pytest.fixture
def stubbed_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parse_module, "rasterize_document", _fake_rasterize)
    monkeypatch.setattr(parse_module, "GeminiAssessmentService", StubGemini)
    monkeypatch.setattr(
        parse_module, "SupabaseService", lambda *a, **k: SimpleNamespace(is_available=False)
    )


def _use_settings(**overrides) -> None:
    base = get_settings().model_dump()
    base.update(overrides)
    app.dependency_overrides[get_settings] = lambda: Settings(**base)


# --------------------------------------------------------------------------------------
# Unconfigured: everything stays open (local development and CI)
# --------------------------------------------------------------------------------------

def test_writes_are_open_when_no_key_is_configured(stubbed_pipeline: None) -> None:
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json()["access_key_required"] is False
        assert client.post("/api/v1/parse/jobs", files=FILES).status_code == 202


# --------------------------------------------------------------------------------------
# Configured: reads open, writes gated
# --------------------------------------------------------------------------------------

def test_health_advertises_that_a_key_is_required() -> None:
    _use_settings(demo_access_key=DEMO_KEY)
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json()["access_key_required"] is True


def test_reads_remain_public_when_a_key_is_configured() -> None:
    """A reviewer must be able to browse the demo without any credential."""
    _use_settings(demo_access_key=DEMO_KEY)
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/api/v1/assessments").status_code == 200
        # Unknown ids still 404 rather than leaking a 401 on a read path.
        assert client.get("/api/v1/parse/jobs/unknown").status_code == 404


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/v1/parse/jobs"),
        ("POST", "/api/v1/parse"),
        ("DELETE", "/api/v1/assessments/00000000-0000-0000-0000-000000000000"),
    ],
)
def test_mutating_endpoints_reject_a_missing_key(method: str, path: str) -> None:
    _use_settings(demo_access_key=DEMO_KEY)
    with TestClient(app) as client:
        response = client.request(method, path, files=FILES if method == "POST" else None)
    assert response.status_code == 401
    assert "access key" in response.json()["detail"].lower()


def test_mutating_endpoints_reject_a_wrong_key() -> None:
    _use_settings(demo_access_key=DEMO_KEY)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/parse/jobs", files=FILES, headers={ACCESS_KEY_HEADER: "not-the-key"}
        )
    assert response.status_code == 401


def test_correct_key_is_accepted(stubbed_pipeline: None) -> None:
    _use_settings(demo_access_key=DEMO_KEY)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/parse/jobs", files=FILES, headers={ACCESS_KEY_HEADER: DEMO_KEY}
        )
        assert response.status_code == 202
        final = _wait_for_terminal(client, response.json()["job_id"])
        assert final["state"] == "succeeded"


def test_key_comparison_is_not_prefix_based() -> None:
    _use_settings(demo_access_key=DEMO_KEY)
    with TestClient(app) as client:
        for candidate in (DEMO_KEY[:-1], DEMO_KEY + "x", DEMO_KEY.upper(), ""):
            response = client.post(
                "/api/v1/parse/jobs", files=FILES, headers={ACCESS_KEY_HEADER: candidate}
            )
            assert response.status_code == 401, f"{candidate!r} was accepted"


# --------------------------------------------------------------------------------------
# Rate limiting
# --------------------------------------------------------------------------------------

def test_parse_rate_limit_returns_429_with_retry_after(stubbed_pipeline: None) -> None:
    _use_settings(parse_rate_limit_per_hour=2)
    with TestClient(app) as client:
        assert client.post("/api/v1/parse/jobs", files=FILES).status_code == 202
        assert client.post("/api/v1/parse/jobs", files=FILES).status_code == 202

        blocked = client.post("/api/v1/parse/jobs", files=FILES)
        assert blocked.status_code == 429
        assert int(blocked.headers["retry-after"]) > 0
        assert "2 assessment(s) per hour" in blocked.json()["detail"]


def test_rate_limit_is_per_client_ip(stubbed_pipeline: None) -> None:
    _use_settings(parse_rate_limit_per_hour=1)
    with TestClient(app) as client:
        first = {"x-forwarded-for": "203.0.113.10"}
        second = {"x-forwarded-for": "203.0.113.11"}
        assert client.post("/api/v1/parse/jobs", files=FILES, headers=first).status_code == 202
        assert client.post("/api/v1/parse/jobs", files=FILES, headers=first).status_code == 429
        # A different caller is unaffected by the first one's budget.
        assert client.post("/api/v1/parse/jobs", files=FILES, headers=second).status_code == 202


def test_rate_limit_disabled_by_default(stubbed_pipeline: None) -> None:
    """Zero means off, so local development and the suite are never throttled."""
    with TestClient(app) as client:
        for _ in range(4):
            assert client.post("/api/v1/parse/jobs", files=FILES).status_code == 202


def test_reads_are_never_rate_limited(stubbed_pipeline: None) -> None:
    _use_settings(parse_rate_limit_per_hour=1)
    with TestClient(app) as client:
        client.post("/api/v1/parse/jobs", files=FILES)
        for _ in range(5):
            assert client.get("/api/v1/health").status_code == 200
            assert client.get("/api/v1/assessments").status_code == 200
