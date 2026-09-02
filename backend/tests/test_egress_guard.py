import httpx
import pytest

from app.ai.egress_guard import (
    BLOCKED_AI_HOSTS,
    EgressBlockedError,
    install_egress_guard,
    uninstall_egress_guard,
)


def _stub_sync_handle(self, request):
    return httpx.Response(200)


async def _stub_async_handle(self, request):
    return httpx.Response(200)


@pytest.fixture(autouse=True)
def _isolate_guard():
    """Ensures no test leaks a patched httpx transport into another — and,
    found via T92's real AIR_GAPPED=true CI run, ensures no test STARTS
    with a leftover install either. app.ai.airgapped installs the real
    guard as an import-time side effect whenever AIR_GAPPED=true (by
    design, so the API/worker processes are protected without extra
    startup wiring) — every test in this file previously assumed it was
    the one calling install_egress_guard() from a clean slate, which was
    only ever true because CI never actually ran with AIR_GAPPED=true.
    The moment it did, the real import-time install had already wrapped
    httpx.HTTPTransport.handle_request BEFORE a test's own monkeypatch +
    install_egress_guard() ran — monkeypatch overwrote the guard with the
    test's stub, and the test's install_egress_guard() call was a no-op
    (idempotency check saw _installed=True from the real one), so no
    guard was actually protecting the stubbed client at all."""
    uninstall_egress_guard()
    yield
    uninstall_egress_guard()


def test_egress_guard_blocks_all_known_external_ai_hosts(monkeypatch):
    """T92 — network-level defense-in-depth: even if a bug bypassed
    app.ai.airgapped.enforce_local(), a real outbound request to any of
    the six external AI provider hosts must still be refused."""
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _stub_sync_handle)
    install_egress_guard()

    with httpx.Client(transport=httpx.HTTPTransport()) as client:
        for host in BLOCKED_AI_HOSTS:
            with pytest.raises(EgressBlockedError):
                client.get(f"https://{host}/v1/probe")


@pytest.mark.asyncio
async def test_egress_guard_blocks_all_known_external_ai_hosts_async(monkeypatch):
    """Same as above, but for the async transport — this is the path
    every provider SDK in this codebase actually uses (they're all
    async)."""
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", _stub_async_handle)
    install_egress_guard()

    async with httpx.AsyncClient(transport=httpx.AsyncHTTPTransport()) as client:
        for host in BLOCKED_AI_HOSTS:
            with pytest.raises(EgressBlockedError):
                await client.get(f"https://{host}/v1/probe")


def test_egress_guard_allows_non_ai_hosts(monkeypatch):
    """The guard must not become a general network blocker — Postgres,
    Redis, MinIO, and a mirrored local registry are all legitimate."""
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _stub_sync_handle)
    install_egress_guard()

    with httpx.Client(transport=httpx.HTTPTransport()) as client:
        res = client.get("https://registry.airgapped.local/health")
        assert res.status_code == 200


def test_egress_guard_uninstall_restores_original_behavior(monkeypatch):
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _stub_sync_handle)
    install_egress_guard()
    uninstall_egress_guard()

    with httpx.Client(transport=httpx.HTTPTransport()) as client:
        # guard removed — the (stubbed) original now runs unguarded
        res = client.get("https://api.openai.com/v1/probe")
        assert res.status_code == 200


def test_egress_guard_install_is_idempotent(monkeypatch):
    """Calling install twice must not double-wrap the transport (which
    would make uninstall() only peel off one layer, leaving the guard
    still active)."""
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _stub_sync_handle)
    install_egress_guard()
    install_egress_guard()
    uninstall_egress_guard()

    with httpx.Client(transport=httpx.HTTPTransport()) as client:
        res = client.get("https://api.openai.com/v1/probe")
        assert res.status_code == 200
