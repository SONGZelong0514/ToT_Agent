from __future__ import annotations

import json
import random
from typing import Any, Dict, List

import requests

from .config import LLMConfig
from .domain import VALID_QUARTERS


class OpenAICompatibleLLM:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg

    def chat(self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int) -> str:
        if self.cfg.use_mock:
            return self._mock_chat(system_prompt=system_prompt, user_prompt=user_prompt)

        if not self.cfg.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY was not detected. Configure .env first, or set TOT_USE_MOCK=true to use mock mode."
            )

        url = self.cfg.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.cfg.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"} if "Output ONLY a single JSON object" in system_prompt else None,
        }
        if payload["response_format"] is None:
            payload.pop("response_format")

        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=self.cfg.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _mock_chat(self, system_prompt: str, user_prompt: str) -> str:
        lower = system_prompt.lower()
        if "planner" in lower:
            candidates: List[Dict[str, Any]] = [
                {
                    "mode": "parallel",
                    "assignments": [
                        {"quarter": "upper_left", "method": "auto"},
                        {"quarter": "lower_left", "method": "manual"},
                    ],
                },
                {
                    "mode": "parallel",
                    "assignments": [
                        {"quarter": "upper_right", "method": "auto"},
                        {"quarter": "lower_right", "method": "manual"},
                    ],
                },
                {"mode": "serial", "assignments": [{"quarter": "upper_left", "method": "manual"}]},
                {"mode": "serial", "assignments": [{"quarter": "lower_left", "method": "auto"}]},
                {
                    "mode": "parallel",
                    "assignments": [
                        {"quarter": "upper_left", "method": "manual"},
                        {"quarter": "upper_right", "method": "manual"},
                    ],
                },
            ]
            random.shuffle(candidates)
            return json.dumps(candidates[:5], ensure_ascii=False)

        base = {
            "constraint_consistency": random.uniform(6.5, 9.5),
            "completion_potential": random.uniform(6.0, 9.5),
            "resource_risk": random.uniform(5.0, 9.0),
            "design_tendency": random.uniform(5.5, 9.0),
        }
        base["overall_score"] = round(sum(base.values()) / 4.0, 2)
        base["reason"] = "Mock evaluator: branch looks feasible and preserves flexibility."
        return json.dumps(base, ensure_ascii=False)
