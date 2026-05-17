from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple

VALID_QUARTERS = ["upper_left", "upper_right", "lower_left", "lower_right"]
VALID_METHODS = ["auto", "manual"]

@dataclass
class Assignment:
    quarter: str
    method: str

    def to_dict(self) -> Dict[str, str]:
        return {"quarter": self.quarter, "method": self.method}


@dataclass
class BatchAction:
    mode: str
    assignments: List[Assignment]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "assignments": [a.to_dict() for a in self.assignments],
        }


@dataclass
class EvalScore:
    constraint_consistency: float
    completion_potential: float
    resource_risk: float
    design_tendency: float
    overall_score: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_consistency": self.constraint_consistency,
            "completion_potential": self.completion_potential,
            "resource_risk": self.resource_risk,
            "design_tendency": self.design_tendency,
            "overall_score": self.overall_score,
            "reason": self.reason,
        }


@dataclass
class StrategyState:
    batches: List[BatchAction] = field(default_factory=list)
    completed_quarters: List[str] = field(default_factory=list)
    score: float = 0.0
    eval_detail: Dict[str, Any] = field(default_factory=dict)

    @property
    def remaining_quarters(self) -> List[str]:
        return [q for q in VALID_QUARTERS if q not in self.completed_quarters]

    @property
    def depth(self) -> int:
        return len(self.batches)

    def is_terminal(self) -> bool:
        return len(self.completed_quarters) == len(VALID_QUARTERS)

    def to_strategy_dict(self, strategy_id: str) -> Dict[str, Any]:
        return {
            "strategy_id": strategy_id,
            "score": round(self.score, 4),
            "batches": [b.to_dict() for b in self.batches],
            "eval_detail": self.eval_detail,
        }


def parse_batch_action(obj: Dict[str, Any]) -> BatchAction:
    mode = obj.get("mode", "").strip().lower()
    assignments_raw = obj.get("assignments", [])
    assignments = [
        Assignment(
            quarter=str(a.get("quarter", "")).strip(),
            method=str(a.get("method", "")).strip().lower(),
        )
        for a in assignments_raw
    ]
    return BatchAction(mode=mode, assignments=assignments)


def canonical_batch(batch: BatchAction) -> Tuple[str, Tuple[Tuple[str, str], ...]]:
    return (
        batch.mode,
        tuple(sorted((a.quarter, a.method) for a in batch.assignments)),
    )


def canonical_state_signature(state: StrategyState) -> Tuple[Any, ...]:
    return tuple(canonical_batch(b) for b in state.batches)


def batch_difference_count(a: StrategyState, b: StrategyState) -> int:
    seq_a = [canonical_batch(x) for x in a.batches]
    seq_b = [canonical_batch(x) for x in b.batches]
    max_len = max(len(seq_a), len(seq_b))
    diff = 0
    for i in range(max_len):
        item_a = seq_a[i] if i < len(seq_a) else None
        item_b = seq_b[i] if i < len(seq_b) else None
        if item_a != item_b:
            diff += 1
    return diff


def validate_batch_action(batch: BatchAction, remaining_quarters: Sequence[str]) -> Tuple[bool, str]:
    if batch.mode not in {"serial", "parallel"}:
        return False, "mode must be serial or parallel"
    if not batch.assignments:
        return False, "assignments cannot be empty"
    if batch.mode == "serial" and len(batch.assignments) != 1:
        return False, "serial mode requires exactly one assignment"

    seen = set()
    for assn in batch.assignments:
        if assn.quarter not in VALID_QUARTERS:
            return False, f"Invalid quarter: {assn.quarter}"
        if assn.method not in VALID_METHODS:
            return False, f"Invalid method: {assn.method}"
        if assn.quarter not in remaining_quarters:
            return False, f"Quarter has already been completed and cannot be assigned again: {assn.quarter}"
        if assn.quarter in seen:
            return False, f"Duplicate quarter within the same batch: {assn.quarter}"
        seen.add(assn.quarter)


    return True, "ok"


def apply_action(state: StrategyState, batch: BatchAction) -> StrategyState:
    completed = state.completed_quarters + [a.quarter for a in batch.assignments]
    return StrategyState(
        batches=state.batches + [batch],
        completed_quarters=completed,
        score=state.score,
        eval_detail=dict(state.eval_detail),
    )
