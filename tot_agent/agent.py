from __future__ import annotations

import json
from typing import Any, Dict, List

from .config import LLMConfig, ToTConfig, UserProblem
from .evaluator import Evaluator
from .llm_client import OpenAICompatibleLLM
from .planner import Planner
from .searcher import Searcher
from .utils import DebugPrinter


class ToTAgent:
    def __init__(self, llm_cfg: LLMConfig | None = None, tot_cfg: ToTConfig | None = None):
        self.llm_cfg = llm_cfg or LLMConfig.from_env()
        self.tot_cfg = tot_cfg or ToTConfig()
        self.debug = DebugPrinter(enabled=self.tot_cfg.debug)
        self.llm = OpenAICompatibleLLM(self.llm_cfg)
        self.planner = Planner(self.llm, self.tot_cfg)
        self.evaluator = Evaluator(self.llm, self.tot_cfg)
        self.searcher = Searcher(self.planner, self.evaluator, self.tot_cfg, self.debug)

    def run(self, problem: UserProblem) -> List[Dict[str, Any]]:
        states = self.searcher.run(problem)
        return [state.to_strategy_dict(strategy_id=f"S{i}") for i, state in enumerate(states, start=1)]

    def run_to_json(self, problem: UserProblem) -> str:
        return json.dumps(self.run(problem), ensure_ascii=False, indent=2)
