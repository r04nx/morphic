import os
import json
import requests
from typing import List, Dict, Optional, Any

from config.settings import Config

class OllamaClient:
    """Simple Ollama REST client for chat completions"""

    def __init__(self):
        self.api_key = Config.OLLAMA_API_KEY
        self.host = Config.OLLAMA_HOST or 'http://localhost:11434'
        # For Ollama Cloud, API endpoint is api.ollama.com, not ollama.com
        if 'ollama.com' in self.host and not self.host.startswith('http://localhost'):
            self.api_host = 'https://api.ollama.com'
        else:
            self.api_host = self.host
        self.model = Config.OLLAMA_MODEL

    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Call Ollama /api/chat and return the JSON response"""
        url = f"{self.api_host}/api/chat"
        headers = {}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        payload = {
            'model': self.model,
            'messages': messages,
            'stream': False,
            **kwargs
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise RuntimeError(f'Ollama API error: {e}') from e

    @property
    def model_name(self) -> str:
        return self.model
