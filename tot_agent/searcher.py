from __future__ import annotations
from typing import Any, Dict, List, Tuple
from .config import ToTConfig, UserProblem
from .domain import (
    BatchAction,
    StrategyState,
    apply_action,
    batch_difference_count,
    canonical_state_signature,
    validate_batch_action,
)
from .evaluator import Evaluator
from .planner import Planner
from .utils import DebugPrinter


def canonical_batch_signature(batch: BatchAction) -> Tuple[str, Tuple[Tuple[str, str], ...]]:
    """
    Normalize a batch into a hashable signature for deduplication.
    In parallel mode, different assignment orders are still treated as the same batch.
    """
    items = sorted((a.quarter, a.method) for a in batch.assignments)
    return batch.mode, tuple(items)


def deduplicate_batches(candidates: List[BatchAction]) -> Tuple[List[BatchAction], int]:
    """
    Deduplicate candidate batches returned by the planner for the same parent node.
    Keep the first occurrence of each batch and discard later duplicates.
    Returns: (deduplicated candidate list, number of removed duplicates)
    """
    seen = set()
    unique: List[BatchAction] = []
    duplicate_count = 0

    for batch in candidates:
        sig = canonical_batch_signature(batch)
        if sig in seen:
            duplicate_count += 1
            continue
        seen.add(sig)
        unique.append(batch)

    return unique, duplicate_count


class Searcher:
    def __init__(self, planner: Planner, evaluator: Evaluator, cfg: ToTConfig, debug: DebugPrinter):
        self.planner = planner
        self.evaluator = evaluator
        self.cfg = cfg
        self.debug = debug

    @staticmethod
    def _root_trace(state: StrategyState) -> Dict[str, Any]:
        return {
            "state": state,
            "source_label": "ROOT",
            "source_batch": None,
            "score": state.score,
        }

    @staticmethod
    def _state_header(trace: Dict[str, Any], beam_idx: int) -> str:
        state: StrategyState = trace["state"]
        source_label = trace.get("source_label", "UNKNOWN")
        header = (
            f"[State {beam_idx} | from {source_label}] "
            f"completed={state.completed_quarters}, "
            f"remaining={state.remaining_quarters}, depth={state.depth}"
        )
        return header

    @staticmethod
    def _candidate_label(depth: int, beam_idx: int, candidate_idx: int) -> str:
        return f"D{depth}-S{beam_idx}-C{candidate_idx}"

    @staticmethod
    def _trace_to_log_line(prefix: str, trace: Dict[str, Any]) -> str:
        batch = trace.get("source_batch")
        batch_repr = batch.to_dict() if batch is not None else "ROOT"
        return (
            f"{prefix}{trace['source_label']} | "
            f"score={trace['score']:.3f} | batch={batch_repr}"
        )

    def run(self, problem: UserProblem) -> List[StrategyState]:
        root = StrategyState()
        beam_traces: List[Dict[str, Any]] = [self._root_trace(root)]
        terminal_pool: List[StrategyState] = []
        visited = set()

        for depth in range(self.cfg.max_depth):
            if not beam_traces:
                self.debug.log(f"[Depth {depth}] The beam is empty, terminating early.")
                break

            self.debug.log(f"\n========== Depth {depth} | Beam Size = {len(beam_traces)} ==========")
            expanded_traces: List[Dict[str, Any]] = []

            for beam_idx, trace in enumerate(beam_traces, start=1):
                state: StrategyState = trace["state"]
                self.debug.log(self._state_header(trace, beam_idx))
                if trace.get("source_batch") is not None:
                    self.debug.log(f"  parent batch = {trace['source_batch'].to_dict()}")

                if state.is_terminal():
                    terminal_pool.append(state)
                    continue

                try:
                    candidates = self.planner.propose(problem, state)
                except Exception as e:
                    self.debug.log(f"  Planner call failed. Skipping this state. Error: {e}")
                    continue

                raw_count = len(candidates)
                candidates, duplicate_count = deduplicate_batches(candidates)
                deduped_count = len(candidates)

                if duplicate_count > 0:
                    self.debug.log(
                        f"  The planner originally returned {raw_count} candidate batches."
                        f"After deduplication, {deduped_count} batches are retained, with {duplicate_count} duplicate batches pruned."
                    )
                else:
                    self.debug.log(f"  The planner returned {deduped_count} candidate batches (no duplicates).")

                for candidate_idx, batch in enumerate(candidates, start=1):
                    candidate_label = self._candidate_label(depth, beam_idx, candidate_idx)
                    self.debug.log(f"    - Candidate {candidate_idx} [{candidate_label}]: {batch.to_dict()}")
                    ok, reason = validate_batch_action(batch, state.remaining_quarters)
                    if not ok:
                        self.debug.log(f"      -> Invalid batch, pruned. Reason: {reason}")
                        continue

                    new_state = apply_action(state, batch)
                    signature = canonical_state_signature(new_state)
                    if signature in visited:
                        self.debug.log("      -> Duplicate state, pruned.")
                        continue

                    try:
                        score = self.evaluator.score(problem, new_state)
                    except Exception as e:
                        self.debug.log(f"      -> Evaluator failed, pruned. Error: {e}")
                        continue

                    new_state.score = score.overall_score
                    new_state.eval_detail = score.to_dict()
                    visited.add(signature)

                    self.debug.log(
                        "      -> Score: "
                        f"overall={score.overall_score:.3f}, "
                        f"constraint={score.constraint_consistency:.2f}, "
                        f"potential={score.completion_potential:.2f}, "
                        f"resource={score.resource_risk:.2f}, "
                        f"tendency={score.design_tendency:.2f}"
                    )
                    self.debug.log(f"         reason: {score.reason}")

                    new_trace = {
                        "state": new_state,
                        "source_label": candidate_label,
                        "source_batch": batch,
                        "score": score.overall_score,
                    }

                    if new_state.is_terminal():
                        terminal_pool.append(new_state)
                        self.debug.log("      -> Terminal strategy, added to the terminal_pool.")
                    else:
                        expanded_traces.append(new_trace)

            expanded_traces.sort(key=lambda t: t["score"], reverse=True)
            kept_traces = expanded_traces[: self.cfg.beam_width]
            pruned_traces = expanded_traces[self.cfg.beam_width :]
            beam_traces = kept_traces

            self.debug.log(
                f"[Depth {depth}] After expansion, {len(expanded_traces)} candidates."
                f"Retained top-{self.cfg.beam_width}, pruned {len(pruned_traces)} from the beam."
            )

            if kept_traces:
                self.debug.log("  Proceeding to the next layer of states:")
                for next_idx, trace in enumerate(kept_traces, start=1):
                    self.debug.log(self._trace_to_log_line(f"    - Next State {next_idx} <= ", trace))

            if pruned_traces:
                self.debug.log("  Candidates pruned by the beam:")
                for trace in pruned_traces:
                    self.debug.log(self._trace_to_log_line("    - PRUNED ", trace))

            terminal_pool.sort(key=lambda s: s.score, reverse=True)
            terminal_pool = terminal_pool[: self.cfg.terminal_pool_limit]

        if not terminal_pool:
            self.debug.log("No complete terminal solution was found; returning the best partial strategy from the current beam.")
            terminal_pool = sorted([trace["state"] for trace in beam_traces], key=lambda s: s.score, reverse=True)

        terminal_count = len(terminal_pool)
        self.debug.log(f"[Final] Number of solutions in the terminal_pool = {terminal_count}")

        final_selected = self._diversify_and_select(terminal_pool)

        selected_count = len(final_selected)
        filtered_count = terminal_count - selected_count

        self.debug.log(f"[Final] Number of solutions retained after diversity filtering = {selected_count}")
        self.debug.log(f"[Final] Number of solutions filtered out by the diversity selection = {filtered_count}")

        return final_selected

    def _diversify_and_select(self, states: List[StrategyState]) -> List[StrategyState]:
        selected: List[StrategyState] = []
        for candidate in sorted(states, key=lambda s: s.score, reverse=True):
            if not selected:
                selected.append(candidate)
                continue
            is_diverse = all(
                batch_difference_count(candidate, chosen) >= self.cfg.diversity_min_batch_difference
                for chosen in selected
            )
            if is_diverse:
                selected.append(candidate)
            if len(selected) >= self.cfg.final_top_m:
                break
        return selected
