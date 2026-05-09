import json
from typing import Any, Dict, List, Optional

import requests

from config.settings import Config


class OpenRouterClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        http_referer: Optional[str] = None,
        title: Optional[str] = None,
        timeout_seconds: int = 60,
    ):
        self.api_key = api_key or Config.OPENROUTER_API_KEY
        self.base_url = (base_url or Config.OPENROUTER_BASE_URL).rstrip("/")
        self.model = model or Config.OPENROUTER_MODEL
        self.http_referer = http_referer or Config.OPENROUTER_HTTP_REFERER
        self.title = title or Config.OPENROUTER_TITLE
        self.timeout_seconds = timeout_seconds

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")

    def chat_completions(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1800,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"

        headers: Dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
        if self.title:
            headers["X-OpenRouter-Title"] = self.title

        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if extra:
            payload.update(extra)

        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=self.timeout_seconds)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def extract_text(response_json: Dict[str, Any]) -> str:
        choices = response_json.get("choices") or []
        if not choices:
            return ""
        msg = (choices[0].get("message") or {})
        return msg.get("content") or ""
