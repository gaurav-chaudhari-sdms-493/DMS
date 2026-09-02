import logging

from app.ai.base import VLMProvider

logger = logging.getLogger(__name__)


class FallbackVLMProvider(VLMProvider):
    """Wraps a primary VLMProvider with a fallback: on ANY failure from
    the primary (a bad status, a timeout, a malformed response -- every
    real provider in this codebase raises a plain Exception, not a typed
    hierarchy, so there's nothing narrower to catch), retries once against
    the fallback before giving up.

    Built 2026-09-02 after a real live incident: the OpenRouter account
    ran out of credits mid-run (402), and the only way to keep working
    was a manual .env edit (AI_VLM_PROVIDER=gemini) plus a container
    restart. A configured GOOGLE_API_KEY was sitting there unused the
    whole time. This makes that recovery automatic instead of manual.

    Deliberately no retry-with-backoff, no circuit breaker, no per-call
    provider selection -- one primary, one fallback, try both, raise the
    primary's error (the more actionable one, since the fallback is by
    definition the less-configured path) if both fail. A fancier policy
    can be built once real failure-rate data justifies it.
    """

    def __init__(self, primary: VLMProvider, fallback: VLMProvider, fallback_name: str):
        self.primary = primary
        self.fallback = fallback
        self.fallback_name = fallback_name

    async def extract_structured(self, image_bytes: bytes, prompt: str) -> str:
        try:
            return await self.primary.extract_structured(image_bytes, prompt)
        except Exception as primary_error:
            logger.warning(
                f"VLM primary provider ({type(self.primary).__name__}) failed, "
                f"retrying with fallback ({self.fallback_name}): "
                f"{type(primary_error).__name__}: {primary_error}"
            )
            try:
                return await self.fallback.extract_structured(image_bytes, prompt)
            except Exception as fallback_error:
                logger.warning(
                    f"VLM fallback provider ({self.fallback_name}) also failed: "
                    f"{type(fallback_error).__name__}: {fallback_error}"
                )
                raise primary_error
