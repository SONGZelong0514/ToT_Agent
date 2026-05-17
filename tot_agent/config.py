from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchWeights:
    constraint_consistency: float = 0.30
    completion_potential: float = 0.10
    resource_risk: float = 0.30
    design_tendency: float = 0.30


@dataclass
class ToTConfig:
    max_depth: int = 4
    planner_k: int = 7
    beam_width: int = 5
    final_top_m: int = 20
    evaluator_repeat_n: int = 2
    terminal_pool_limit: int = 100
    diversity_min_batch_difference: int = 1
    temp_plan: float = 0.7
    temp_eval: float = 0.2
    debug: bool = True
    weights: SearchWeights = field(default_factory=SearchWeights)


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    timeout: int
    planner_max_tokens: int
    evaluator_max_tokens: int
    use_mock: bool = False

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            model=os.getenv("OPENAI_MODEL"),
            timeout=int(os.getenv("OPENAI_TIMEOUT")),
            planner_max_tokens=int(os.getenv("PLANNER_MAX_TOKENS")),
            evaluator_max_tokens=int(os.getenv("EVALUATOR_MAX_TOKENS")),
            use_mock=os.getenv("TOT_USE_MOCK", "false").lower() in {"1", "true", "yes"},
        )


@dataclass
class UserProblem:
    task_description: str
    engineering_constraints: str
    design_tendency: str
    resource_hint: str
