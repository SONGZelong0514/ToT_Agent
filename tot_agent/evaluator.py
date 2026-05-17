from __future__ import annotations

from typing import Any, Dict, List

from .config import ToTConfig, UserProblem
from .domain import EvalScore, StrategyState
from .llm_client import OpenAICompatibleLLM
from .prompts import EVALUATOR_SYSTEM_PROMPT, evaluator_user_prompt
from .utils import average_dicts, clamp_score, parse_json


class Evaluator:
    def __init__(self, llm: OpenAICompatibleLLM, cfg: ToTConfig):
        self.llm = llm
        self.cfg = cfg

    def score(self, problem: UserProblem, state: StrategyState) -> EvalScore:
        results: List[Dict[str, Any]] = []
        for _ in range(self.cfg.evaluator_repeat_n):
            prompt = evaluator_user_prompt(
                task_description=problem.task_description,
                engineering_constraints=problem.engineering_constraints,
                design_tendency=problem.design_tendency,
                new_state={
                    "batches": [b.to_dict() for b in state.batches],
                    "completed_quarters": state.completed_quarters,
                    "remaining_quarters": state.remaining_quarters,
                    "depth": state.depth,
                },
                resource_hint=problem.resource_hint,
            )
            raw = self.llm.chat(
                system_prompt=EVALUATOR_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=self.cfg.temp_eval,
                max_tokens=self.llm.cfg.evaluator_max_tokens,
            )
            data = parse_json(raw)
            if not isinstance(data, dict):
                raise ValueError(f"Evaluator output is not an object: {data}")
            results.append(data)

        avg = average_dicts(
            results,
            keys=[
                "constraint_consistency",
                "completion_potential",
                "resource_risk",
                "design_tendency",
            ],
        )
        weighted = (
            avg["constraint_consistency"] * self.cfg.weights.constraint_consistency
            + avg["completion_potential"] * self.cfg.weights.completion_potential
            + avg["resource_risk"] * self.cfg.weights.resource_risk
            + avg["design_tendency"] * self.cfg.weights.design_tendency
        )
        reason = " | ".join(str(r.get("reason", "")) for r in results if r.get("reason"))[:500]
        return EvalScore(
            constraint_consistency=clamp_score(avg["constraint_consistency"]),
            completion_potential=clamp_score(avg["completion_potential"]),
            resource_risk=clamp_score(avg["resource_risk"]),
            design_tendency=clamp_score(avg["design_tendency"]),
            overall_score=round(weighted, 4),
            reason=reason or "No reason provided.",
        )
