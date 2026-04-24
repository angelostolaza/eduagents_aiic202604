"""Google Gemini adapter — image generation via Imagen 3."""
from __future__ import annotations

import base64

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings


# Rough cost estimate: Imagen 3 ~$0.03 / image → 3 cents
_IMAGE_COST_CENTS = 3


class GoogleAdapter:
    def __init__(self) -> None:
        import google.generativeai as genai

        settings = get_settings()
        genai.configure(api_key=settings.google_api_key)
        self._genai = genai

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def generate_image(
        self,
        *,
        prompt: str,
        aspect_ratio: str = "16:9",
    ) -> tuple[bytes, int]:
        """Return (image_bytes, cost_cents)."""
        import asyncio

        model = self._genai.ImageGenerationModel("imagen-3.0-generate-001")

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_images(
                prompt=prompt,
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                safety_filter_level="block_few",
                person_generation="allow_adult",
            ),
        )

        image = response.images[0]
        image_bytes: bytes = image._image_bytes  # type: ignore[attr-defined]
        return image_bytes, _IMAGE_COST_CENTS
