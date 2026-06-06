"""
providers/image/image_providers.py
Provedores de geração de imagem intercambiáveis: anime, mangá, wallpapers, fantasia.
"""
from __future__ import annotations
import asyncio
from core.entities.models import ImageStyle
from core.ports.interfaces import ImageGenerationPort
from infrastructure.logging.logger import logger


# ─── Style Prompt Templates ───────────────────────────────────────────────────

STYLE_MODIFIERS: dict[ImageStyle, str] = {
    ImageStyle.ANIME:     "anime style, vibrant colors, cel-shaded, high quality",
    ImageStyle.MANGA:     "manga style, black and white, detailed linework, N2 detail",
    ImageStyle.WALLPAPER: "4K wallpaper, cinematic lighting, ultra-detailed, atmospheric",
    ImageStyle.FANTASY:   "fantasy art, epic, magical, detailed environment, studio quality",
    ImageStyle.REALISTIC: "photorealistic, 8K, DSLR, sharp focus, studio lighting",
}


# ─── Local / Placeholder Provider ────────────────────────────────────────────

class LocalImageProvider(ImageGenerationPort):
    """Provedor local — placeholder que retorna PNG dummy. Substitua por SD local."""

    @property
    def provider_name(self) -> str:
        return "local"

    async def generate(
        self,
        prompt: str,
        style: ImageStyle = ImageStyle.ANIME,
        width: int = 512,
        height: int = 512,
    ) -> bytes:
        logger.warning("[ImageGen] using local placeholder provider")
        # Retorna PNG mínimo válido (1x1 transparente)
        import base64
        png_1x1 = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        return png_1x1


# ─── Replicate Provider ───────────────────────────────────────────────────────

class ReplicateImageProvider(ImageGenerationPort):
    """Provedor Replicate — modelos de última geração via API."""

    def __init__(self, api_key: str, model: str = "stability-ai/sdxl:latest") -> None:
        self._api_key = api_key
        self._model = model
        logger.info(f"[ImageGen] Replicate initialized model={model}")

    @property
    def provider_name(self) -> str:
        return "replicate"

    async def generate(
        self,
        prompt: str,
        style: ImageStyle = ImageStyle.ANIME,
        width: int = 512,
        height: int = 512,
    ) -> bytes:
        import httpx

        style_mod = STYLE_MODIFIERS.get(style, "")
        full_prompt = f"{prompt}, {style_mod}"

        async with httpx.AsyncClient(timeout=120) as client:
            # Criar predição
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={
                    "Authorization": f"Token {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "version": self._model,
                    "input": {
                        "prompt": full_prompt,
                        "width": width,
                        "height": height,
                    },
                },
            )
            prediction = response.json()
            prediction_id = prediction["id"]

            # Polling até concluir
            for _ in range(60):
                await asyncio.sleep(2)
                poll = await client.get(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers={"Authorization": f"Token {self._api_key}"},
                )
                data = poll.json()
                if data["status"] == "succeeded":
                    img_url = data["output"][0]
                    img_response = await client.get(img_url)
                    logger.info(f"[ImageGen] Replicate image generated: {img_url}")
                    return img_response.content
                if data["status"] == "failed":
                    raise RuntimeError(f"Replicate failed: {data.get('error')}")

        raise TimeoutError("Replicate prediction timed out")


# ─── Factory ─────────────────────────────────────────────────────────────────

def create_image_provider(
    provider: str,
    api_key: str = "",
) -> ImageGenerationPort:
    """Fábrica de provedores de imagem."""
    match provider:
        case "replicate":
            return ReplicateImageProvider(api_key)
        case _:
            return LocalImageProvider()
