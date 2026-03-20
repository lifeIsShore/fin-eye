import logging
import httpx
from typing import Optional, List, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

class OllamaService:
    """
    Service to interact with local Ollama instance for LLM-based analysis and 'thinking'.
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3:8b"):
        self.base_url = base_url
        self.model = model
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=180.0)

    async def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Generate a text response from Ollama.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response")
        except Exception as exc:
            logger.error(f"Ollama generation failed: {exc}")
            return None

    async def get_explanation(
        self, 
        symbol: str, 
        tech_score: float, 
        sent_score: Optional[float], 
        macro_score: float,
        gas_score: float,
        ml_output: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a natural language explanation for a symbol's movement.
        """
        sent_str = f"{sent_score:+.2f}" if sent_score is not None else "N/A"
        ml_str = ml_output if ml_output else "No specific ML anomalies detected."
        
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

    async def close(self):
        await self.client.aclose()

# Optional: Singleton instance pattern if preferred, or use dependency injection in FastAPI.
_ollama_service: Optional[OllamaService] = None

def get_ollama_service() -> OllamaService:
    global _ollama_service
    if _ollama_service is None:
        # Load from settings if available (need to add these to Settings class in config.py)
        base_url = getattr(settings, "ollama_base_url", "http://localhost:11434")
        model = getattr(settings, "ollama_model", "llama3:8b")
        _ollama_service = OllamaService(base_url=base_url, model=model)
    return _ollama_service
