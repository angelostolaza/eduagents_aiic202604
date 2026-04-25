"""Bust Agent — generates a textured 3D GLB bust of a historical figure.

Pipeline per pipeline doc (CUNYAIIC 2026-04):
  1. GPT-Image-1  →  1024x1024 portrait PNG
  2. rembg        →  remove background, crop tight to bust
  3. TripoSR (dev) | Hunyuan3D-2GP (prod)  →  GLB mesh
  4. Upload GLB to object storage
  5. Record BustAsset in DB

Configuration (env vars / settings):
  BUST_METHOD       "triposr" (default) | "hunyuan3d"
  TRIPOSR_DIR       path to cloned TripoSR repo (default: ./TripoSR)
  HUNYUAN3D_DIR     path to cloned Hunyuan3D-2GP repo (default: ./Hunyuan3D-2GP)
"""
from __future__ import annotations

import asyncio
import base64
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent

log = logging.getLogger(__name__)

# GPT-Image-1 portrait prompt template
_PORTRAIT_PROMPT = (
    "Photorealistic portrait bust of {figure_name}, {year}, "
    "{physical_description}. "
    "Neutral expression, facing slightly left, soft studio lighting, "
    "plain dark background, high detail on face and clothing. "
    "No text, no watermarks."
)


class BustAgent(BaseAgent):
    agent_name = "bust"

    async def _execute(self, state: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
        from app.adapters.storage import StorageAdapter
        from app.config import get_settings
        from app.ids import make_id
        from app.models.bust import BustAsset
        from app.speeches.catalog import get_speech_by_id
        from sqlalchemy import select

        settings = get_settings()
        session_id = state["session_id"]
        speech_id = state.get("speech_id", "")
        speech = get_speech_by_id(speech_id) or {}

        figure_name: str = speech.get("figure", state.get("figure_name", "Unknown Figure"))
        year: str = str(speech.get("year", "unknown era"))
        physical_description: str = state.get("physical_description", "period-accurate attire, distinguished appearance")

        method: str = getattr(settings, "bust_method", "triposr")

        # ── Create or fetch BustAsset record ─────────────────────────────────
        existing = (await db.execute(
            select(BustAsset)
            .where(BustAsset.session_id == session_id)
            .where(BustAsset.figure_name == figure_name)
            .where(BustAsset.status.in_(["ready"]))
        )).scalar_one_or_none()

        if existing:
            return {
                "bust_id": existing.id,
                "glb_url": existing.glb_url,
                "portrait_url": existing.portrait_url,
                "method": existing.method,
                "cost_cents": 0,
                "extras": {"cached": True},
            }

        bust_id = make_id("bust")
        bust = BustAsset(
            id=bust_id,
            session_id=session_id,
            figure_name=figure_name,
            method=method,
            status="generating",
            confidence="speculative",
            manifest={"speech_id": speech_id, "year": year},
        )
        db.add(bust)
        await db.flush()

        cost_cents = 0
        portrait_url: str | None = None
        glb_url: str | None = None

        try:
            storage = StorageAdapter()

            # ── Step 1: Generate portrait via GPT-Image-1 ────────────────────
            portrait_bytes, img_cost = await _generate_portrait(
                figure_name=figure_name,
                year=year,
                physical_description=physical_description,
                openai_api_key=settings.openai_api_key,
            )
            cost_cents += img_cost
            portrait_key = f"sessions/{session_id}/bust/{bust_id}_portrait.png"
            portrait_url = await storage.upload(portrait_key, portrait_bytes, "image/png")
            bust.portrait_url = portrait_url
            await db.flush()

            # ── Step 2: Remove background ────────────────────────────────────
            nobg_bytes = await asyncio.get_event_loop().run_in_executor(
                None, _remove_background, portrait_bytes
            )

            # ── Step 3: Generate 3D mesh ─────────────────────────────────────
            triposr_dir = Path(getattr(settings, "triposr_dir", "TripoSR"))
            hunyuan3d_dir = Path(getattr(settings, "hunyuan3d_dir", "Hunyuan3D-2GP"))

            glb_bytes = await asyncio.get_event_loop().run_in_executor(
                None,
                _generate_glb,
                nobg_bytes,
                method,
                triposr_dir,
                hunyuan3d_dir,
            )

            # ── Step 4: Upload GLB ────────────────────────────────────────────
            glb_key = f"sessions/{session_id}/bust/{bust_id}.glb"
            glb_url = await storage.upload(glb_key, glb_bytes, "model/gltf-binary")
            content_hash = StorageAdapter.content_hash(glb_bytes)

            bust.glb_url = glb_url
            bust.status = "ready"
            bust.manifest = {
                **bust.manifest,
                "portrait_key": portrait_key,
                "glb_key": glb_key,
                "content_hash": content_hash,
                "physical_description": physical_description,
            }

        except Exception as exc:
            log.exception("bust_agent_failed", extra={"session_id": session_id, "bust_id": bust_id})
            bust.status = "failed"
            bust.error_message = str(exc)
            await db.flush()
            raise

        return {
            "bust_id": bust_id,
            "glb_url": glb_url,
            "portrait_url": portrait_url,
            "method": method,
            "cost_cents": cost_cents,
            "extras": {"figure_name": figure_name, "confidence": "speculative"},
        }


# ── Portrait generation ────────────────────────────────────────────────────────

async def _generate_portrait(
    *,
    figure_name: str,
    year: str,
    physical_description: str,
    openai_api_key: str,
) -> tuple[bytes, int]:
    """Call gpt-image-1 and return (png_bytes, cost_cents)."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=openai_api_key)
    prompt = _PORTRAIT_PROMPT.format(
        figure_name=figure_name,
        year=year,
        physical_description=physical_description,
    )

    response = await client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        n=1,
        size="1024x1024",
        quality="high",
    )

    image_b64 = response.data[0].b64_json
    if image_b64 is None:
        raise RuntimeError("gpt-image-1 returned no image data")

    image_bytes = base64.b64decode(image_b64)
    # gpt-image-1 high quality 1024x1024 ≈ $0.04 per image = 4 cents
    cost_cents = 4
    return image_bytes, cost_cents


# ── Background removal ─────────────────────────────────────────────────────────

def _remove_background(image_bytes: bytes) -> bytes:
    """Remove background and crop tight to bust (run in executor)."""
    from io import BytesIO

    from PIL import Image
    from rembg import remove

    input_img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    output_img: Image.Image = remove(input_img)  # type: ignore[assignment]

    bbox = output_img.getbbox()
    if bbox:
        output_img = output_img.crop(bbox)

    buf = BytesIO()
    output_img.save(buf, format="PNG")
    return buf.getvalue()


# ── 3D mesh generation ─────────────────────────────────────────────────────────

def _generate_glb(
    image_bytes: bytes,
    method: str,
    triposr_dir: Path,
    hunyuan3d_dir: Path,
) -> bytes:
    """Run TripoSR or Hunyuan3D-2GP in a subprocess and return GLB bytes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        img_path = tmp / "bust_nobg.png"
        img_path.write_bytes(image_bytes)

        if method == "hunyuan3d":
            return _run_hunyuan3d(img_path, tmp, hunyuan3d_dir)
        return _run_triposr(img_path, tmp, triposr_dir)


def _run_triposr(img_path: Path, work_dir: Path, triposr_dir: Path) -> bytes:
    """Run TripoSR and return GLB bytes.

    Adds --model-chunk-size 8000 to keep VRAM under 4 GB on the RTX 3050.
    """
    if not triposr_dir.exists():
        raise FileNotFoundError(
            f"TripoSR not found at {triposr_dir}. "
            "Clone it: git clone https://github.com/VAST-AI-Research/TripoSR.git"
        )

    out_dir = work_dir / "triposr_out"
    out_dir.mkdir()

    cmd = [
        "python", str(triposr_dir / "run.py"),
        str(img_path),
        "--output-dir", str(out_dir),
        "--device", "cuda",
        "--model-chunk-size", "8000",
    ]

    result = subprocess.run(
        cmd,
        cwd=str(triposr_dir),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"TripoSR failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")

    glb_path = out_dir / "0" / "mesh.glb"
    if not glb_path.exists():
        raise FileNotFoundError(f"TripoSR output GLB not found at {glb_path}")

    return glb_path.read_bytes()


def _run_hunyuan3d(img_path: Path, work_dir: Path, hunyuan3d_dir: Path) -> bytes:
    """Run Hunyuan3D-2GP with --profile 4 (4 GB VRAM + shared RAM offload)."""
    if not hunyuan3d_dir.exists():
        raise FileNotFoundError(
            f"Hunyuan3D-2GP not found at {hunyuan3d_dir}. "
            "Clone it: git clone https://github.com/deepbeepmeep/Hunyuan3D-2GP.git"
        )

    glb_path = work_dir / "bust_output.glb"

    cmd = [
        "python", str(hunyuan3d_dir / "infer.py"),
        "--image", str(img_path),
        "--output", str(glb_path),
        "--profile", "4",
    ]

    result = subprocess.run(
        cmd,
        cwd=str(hunyuan3d_dir),
        capture_output=True,
        text=True,
        timeout=1200,  # up to 20 min for heavy offloading
    )
    if result.returncode != 0:
        raise RuntimeError(f"Hunyuan3D-2GP failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")

    if not glb_path.exists():
        raise FileNotFoundError(f"Hunyuan3D-2GP output GLB not found at {glb_path}")

    return glb_path.read_bytes()
