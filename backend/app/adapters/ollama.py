"""Ollama adapter — runs open-source LLMs locally via the Ollama OpenAI-compatible API."""
from __future__ import annotations

from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings


class OllamaAdapter:
    """Thin wrapper around the local Ollama server (http://localhost:11434).

    Uses the OpenAI-compatible /v1/chat/completions endpoint so any model
    pulled with `ollama pull <name>` works without code changes.

    Recommended models (pull one before starting):
        ollama pull llama3.2        # fast, 3B — good for dev
        ollama pull llama3.1:8b    # better quality
        ollama pull mistral         # strong reasoning
        ollama pull qwen2.5:7b     # great for structured JSON output
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = getattr(settings, "ollama_base_url", "http://localhost:11434")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str = "llama3.2",
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Return {content, tokens_in, tokens_out, cost_cents} — same shape as AnthropicAdapter."""
        import httpx

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]
        content = choice["message"]["content"]
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)

        # Open-source models running locally have no per-token cost
        return {
            "content": content,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_cents": 0,
        }
