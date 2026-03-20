import asyncio
import logging
import httpx
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class OllamaService:
    """
    Async client for a local Ollama instance.

    Lifecycle: create once at startup via get_ollama_service(), reuse across
    requests, close at shutdown via close_ollama_service(). The httpx client
    is created lazily on first use so startup never blocks on Ollama being
    available.
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3:8b"):
        self.base_url = base_url
        self.model = model
        # BUG-FIX-4: Create the client lazily rather than in __init__ so that
        # startup (and tests that mock this class) never open a real connection.
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()

    @property
    async def client(self) -> httpx.AsyncClient:
        """Return (or lazily create) the shared async HTTP client."""
        if self._client is None or self._client.is_closed:
            async with self._lock:
                # Double-check after acquiring the lock
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(
                        base_url=self.base_url,
                        timeout=180.0,
                    )
        return self._client

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> Optional[str]:
        """Generate a text response from Ollama."""
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            c = await self.client
            response = await c.post("/api/generate", json=payload)
            response.raise_for_status()
            return response.json().get("response")
        except httpx.ConnectError:
            logger.warning(
                "Ollama is not reachable at %s — is it running? "
                "Start with: ollama serve",
                self.base_url,
            )
            return None
        except Exception as exc:
            logger.error("Ollama generation failed: %s", exc)
            return None

    async def get_explanation(
        self,
        symbol: str,
        tech_score: float,
        sent_score: Optional[float],
        macro_score: float,
        gas_score: float,
        ml_output: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a natural language explanation for a symbol's movement."""
        sent_str = f"{sent_score:+.2f}" if sent_score is not None else "N/A"
        ml_str = ml_output or "No ML signals available for this symbol yet."

        system_prompt = (
            "You are Fin-Eye AI, a professional financial analyst. "
            "Your task is to provide a concise, insightful explanation of a stock's current movement "
            "based on provided data points: Technical Score (0-100), Sentiment Score (-1 to +1), "
            "Macro Score (0-100), ML Signals, and a combined 'GAS' Score (0-100)."
        )

        prompt = (
            f"Symbol: {symbol}\n"
            f"Technical Score: {tech_score}/100\n"
            f"Sentiment (News) Score: {sent_str}\n"
            f"Macro Score: {macro_score}/100\n"
            f"Combined GAS Score: {gas_score}/100\n"
            f"ML Predictive Signals: {ml_str}\n\n"
            "Provide a human-readable summary (2-3 sentences) explaining what these signals suggest "
            "about the stock's current direction and key drivers. Be professional and objective."
        )

        return await self.generate_response(prompt, system_prompt=system_prompt)

    async def close(self) -> None:
        """Close the underlying HTTP client. Call during app shutdown."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# ── Module-level singleton ────────────────────────────────────────────────────
# BUG-FIX-4: The previous implementation had a bare global assignment race:
# two concurrent requests could both see _ollama_service is None and both
# create a new OllamaService, leaking the first client forever.
#
# Fix: the singleton is now created exactly once — either at module import
# time (safe, since Python's import lock serialises it) or via the explicit
# lifespan helpers below. Call get_ollama_service() for the current instance
# and close_ollama_service() at app shutdown.

_ollama_service: Optional[OllamaService] = None


def get_ollama_service() -> OllamaService:
    """Return the module-level singleton, creating it on first call."""
    global _ollama_service
    if _ollama_service is None:
        base_url = getattr(settings, "ollama_base_url", "http://localhost:11434")
        model    = getattr(settings, "ollama_model",    "llama3:8b")
        _ollama_service = OllamaService(base_url=base_url, model=model)
    return _ollama_service


async def close_ollama_service() -> None:
    """
    Cleanly close the HTTP client.  Call from the FastAPI lifespan shutdown
    block so the event loop is still running when aclose() is awaited.
    """
    global _ollama_service
    if _ollama_service is not None:
        await _ollama_service.close()
        _ollama_service = None
