from __future__ import annotations

import json
import re
from statistics import mean
from typing import Any, Dict, Iterable, List


def extract_json_block(text: str) -> str:
    text = text.strip()
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    candidates = fenced + [text]
    for candidate in candidates:
        candidate = candidate.strip()
        for opener, closer in [("[", "]"), ("{", "}")]:
            start = candidate.find(opener)
            end = candidate.rfind(closer)
            if start != -1 and end != -1 and end > start:
                return candidate[start : end + 1]
    raise ValueError("Failed to extract JSON from the model output")


def parse_json(text: str) -> Any:
    block = extract_json_block(text)
    return json.loads(block)


def clamp_score(x: Any) -> float:
    try:
        value = float(x)
    except Exception:
        value = 0.0
    return max(0.0, min(10.0, value))


def average_dicts(items: List[Dict[str, Any]], keys: Iterable[str]) -> Dict[str, float]:
    return {k: mean(clamp_score(item.get(k, 0.0)) for item in items) for k in keys}


class DebugPrinter:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def log(self, msg: str) -> None:
        if self.enabled:
            print(msg)
