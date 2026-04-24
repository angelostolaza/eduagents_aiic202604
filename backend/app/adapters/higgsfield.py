"""HiggsField adapter — video clip generation (Veo / Kling fallback)."""
from __future__ import annotations

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings


_COST_PER_SECOND_CENTS = 10  # rough estimate: $0.10 / second of video


class HiggsFieldAdapter:
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = getattr(settings, "higgsfield_api_key", "")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=5, max=60))
    async def generate_clip(
        self,
        *,
        image_url: str,
        prompt: str,
        duration_s: int = 4,
    ) -> tuple[bytes, int]:
        """Return (video_bytes, cost_cents).

        Calls the HiggsField /animate endpoint which takes a seed image + prompt
        and returns an MP4.  Falls back to an empty bytes placeholder when the
        API key is not configured (local dev mode).
        """
        import httpx

        if not self._api_key:
            # Local dev: return a tiny valid placeholder MP4-like bytes
            return b"", _COST_PER_SECOND_CENTS * duration_s

        url = "https://api.higgsfield.ai/v1/animate"
        payload = {
            "image_url": image_url,
            "prompt": prompt,
            "duration_seconds": duration_s,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            video_bytes = response.content

        cost_cents = _COST_PER_SECOND_CENTS * duration_s
        return video_bytes, cost_cents
