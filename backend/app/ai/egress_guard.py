import httpx

# T92 — every external AI/OCR provider SDK in this codebase (openai, groq,
# anthropic, cohere) as well as the direct httpx usage in gemini_provider.py,
# openrouter_provider.py, and llamaparse_provider.py all route through
# httpx's transport layer. Patching it here is a single interception point
# covering all of them.
BLOCKED_AI_HOSTS = {
    "api.openai.com",
    "api.anthropic.com",
    "api.groq.com",
    "generativelanguage.googleapis.com",
    "api.cohere.ai",
    "api.cloud.llamaindex.ai",
    "openrouter.ai",
}


class EgressBlockedError(RuntimeError):
    """Raised when AIR_GAPPED=true and an outbound request reaches httpx
    for a known external AI provider host. This is defense-in-depth,
    independent of app.ai.airgapped.enforce_local() (which refuses at
    provider-resolution time, before any client is even constructed) — if
    this fires, something reached the network layer without going
    through the provider factories' checks, which is itself a bug worth
    surfacing loudly rather than silently letting the request through."""


_installed = False
_orig_async_handle = None
_orig_sync_handle = None


def _check_host(request: httpx.Request) -> None:
    host = request.url.host
    if host in BLOCKED_AI_HOSTS:
        raise EgressBlockedError(
            f"AIR_GAPPED=true — blocked outbound request to '{host}' "
            f"({request.method} {request.url}). No local provider exists "
            f"for this surface yet (see backlog T90)."
        )


def install_egress_guard() -> None:
    """Idempotent — call once at startup when settings.air_gapped is True.
    Patches httpx's transport classes globally, so it covers every client
    instance any provider constructs, not just ones created after this
    call."""
    global _installed, _orig_async_handle, _orig_sync_handle
    if _installed:
        return

    _orig_async_handle = httpx.AsyncHTTPTransport.handle_async_request
    _orig_sync_handle = httpx.HTTPTransport.handle_request

    async def guarded_async_handle(self, request):
        _check_host(request)
        return await _orig_async_handle(self, request)

    def guarded_sync_handle(self, request):
        _check_host(request)
        return _orig_sync_handle(self, request)

    httpx.AsyncHTTPTransport.handle_async_request = guarded_async_handle
    httpx.HTTPTransport.handle_request = guarded_sync_handle
    _installed = True


def uninstall_egress_guard() -> None:
    """For tests that need to toggle the guard on/off within one process."""
    global _installed
    if not _installed:
        return
    httpx.AsyncHTTPTransport.handle_async_request = _orig_async_handle
    httpx.HTTPTransport.handle_request = _orig_sync_handle
    _installed = False
