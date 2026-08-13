from __future__ import annotations

import base64
import json
import re
from typing import Any

import httpx

from app.core.config import settings


class OpenRouterUnavailable(RuntimeError):
    pass


def _json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("OpenRouter response must be a JSON object.")
    return value


class OpenRouterService:
    """Small OpenRouter client for the Qwen fallback path."""

    def __init__(self) -> None:
        self.api_key = settings.qwen_fallback
        self.model = settings.qwen_fallback_model
        self.base_url = settings.openrouter_base_url.rstrip("/")

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip())

    async def complete(
        self,
        prompt: str,
        *,
        image_bytes: bytes | None = None,
        mime_type: str = "image/jpeg",
        json_response: bool = False,
        temperature: float = 0.2,
    ) -> str:
        if not self.configured:
            raise OpenRouterUnavailable("OpenRouter fallback is not configured.")

        content: str | list[dict[str, Any]] = prompt
        if image_bytes is not None:
            encoded = base64.b64encode(image_bytes).decode("ascii")
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
            ]

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
            "provider": {"sort": "throughput", "allow_fallbacks": True},
        }
        if json_response:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://bitebuddy.local",
                        "X-Title": "BiteBuddy",
                    },
                    json=payload,
                )
            response.raise_for_status()
            body = response.json()
            result = body["choices"][0]["message"]["content"]
            if not isinstance(result, str) or not result.strip():
                raise ValueError("OpenRouter returned empty content.")
            return result.strip()
        except Exception as exc:
            raise OpenRouterUnavailable("OpenRouter fallback request failed.") from exc

    async def complete_json(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        return _json_object(await self.complete(prompt, json_response=True, **kwargs))
