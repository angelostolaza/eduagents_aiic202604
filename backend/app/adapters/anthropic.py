"""Anthropic adapter — wraps the Anthropic Messages API."""
from __future__ import annotations

from typing import Any

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings


# Cost in USD per million tokens (Claude 3.5 Sonnet as of 2024)
_COST_PER_M_IN = 3.0   # $3 / 1M input tokens
_COST_PER_M_OUT = 15.0  # $15 / 1M output tokens


class AnthropicAdapter:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )

        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens
        # Convert to cents
        cost_cents = int(
            (tokens_in / 1_000_000) * _COST_PER_M_IN * 100
            + (tokens_out / 1_000_000) * _COST_PER_M_OUT * 100
        )

        return {
            "content": response.content[0].text,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_cents": cost_cents,
        }
