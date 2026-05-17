from __future__ import annotations

from typing import List

from .config import ToTConfig, UserProblem
from .domain import BatchAction, StrategyState, parse_batch_action
from .llm_client import OpenAICompatibleLLM
from .prompts import PLANNER_SYSTEM_PROMPT, planner_user_prompt
from .utils import parse_json


class Planner:
    def __init__(self, llm: OpenAICompatibleLLM, cfg: ToTConfig):
        self.llm = llm
        self.cfg = cfg

    def propose(self, problem: UserProblem, state: StrategyState) -> List[BatchAction]:
        prompt = planner_user_prompt(
            task_description=problem.task_description,
            engineering_constraints=problem.engineering_constraints,
            design_tendency=problem.design_tendency,
            resource_hint=problem.resource_hint,
            current_batches=[b.to_dict() for b in state.batches],
            remaining_quarters=state.remaining_quarters,
            k=self.cfg.planner_k,
        )
        raw = self.llm.chat(
            system_prompt=PLANNER_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=self.cfg.temp_plan,
            max_tokens=self.llm.cfg.planner_max_tokens,
        )
        data = parse_json(raw)
        if isinstance(data, dict):
            data = data.get("candidates", [])
        if not isinstance(data, list):
            raise ValueError(f"Planner output is not an array: {data}")
        return [parse_batch_action(item) for item in data[: self.cfg.planner_k]]
