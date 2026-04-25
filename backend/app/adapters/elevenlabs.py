"""ElevenLabs adapter — text-to-speech v3, plus image/video stubs."""
from __future__ import annotations

from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings


_COST_PER_1K_CHARS = 0.3  # $0.003 / char → 0.3 cents / char at 1K chars
_COST_PER_IMAGE_CENTS = 5   # placeholder cost estimate
_COST_PER_SECOND_CENTS = 10  # placeholder cost estimate for video


class ElevenLabsAdapter:
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.elevenlabs_api_key
        self._voice_id = getattr(settings, "elevenlabs_voice_id", "21m00Tcm4TlvDq8ikWAM")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def synthesize(
        self,
        *,
        text: str,
        performance_notes: dict[str, Any] | None = None,
        model_id: str = "eleven_multilingual_v2",
    ) -> tuple[bytes, int, str]:
        """Return (audio_bytes, cost_cents, method)."""
        import httpx

        method = "description"
        headers = {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }
        if performance_notes:
            pacing = performance_notes.get("pacing", "")
            if pacing:
                payload["text"] = f"[{pacing}] {text}"

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self._voice_id}"

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            audio_bytes = response.content

        cost_cents = int((len(text) / 1000) * _COST_PER_1K_CHARS * 100)
        return audio_bytes, max(cost_cents, 1), method

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def generate_image(
        self,
        *,
        prompt: str,
        aspect_ratio: str = "16:9",
    ) -> tuple[bytes, int]:
        """Return (image_bytes, cost_cents).

        ElevenLabs does not currently offer an image-generation API.
        This method returns a 1x1 transparent PNG placeholder so the pipeline
        continues to function.  Swap in a real implementation when ElevenLabs
        (or a connected partner service) exposes an image endpoint under the
        same API key.
        """
        # Minimal valid 1×1 transparent PNG (68 bytes)
        placeholder_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return placeholder_png, _COST_PER_IMAGE_CENTS

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=5, max=60))
    async def generate_clip(
        self,
        *,
        image_url: str,
        prompt: str,
        duration_s: int = 4,
    ) -> tuple[bytes, int]:
        """Return (video_bytes, cost_cents).

        ElevenLabs does not currently offer a video-generation API.
        This method returns empty bytes as a placeholder so the pipeline
        continues to function.  Swap in a real implementation when ElevenLabs
        (or a connected partner service) exposes a video endpoint under the
        same API key.
        """
        return b"", _COST_PER_SECOND_CENTS * duration_s
