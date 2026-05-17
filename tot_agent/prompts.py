from __future__ import annotations

import json
from typing import Any, Dict, List


PLANNER_SYSTEM_PROMPT = """
You are a planner for aircraft fuselage riveting system design.
Your goal is NOT to generate a complete solution or detailed operational procedures, but to propose k candidate design actions based on the current state.

You must strictly follow these rules:
1. Output ONLY a JSON array. Do not include explanations, markdown, or any extra text before or after.
2. The length of the array must be exactly k.
3. Each element must strictly follow this format:
   {
     "mode": "serial | parallel",
     "assignments": [
       {"quarter": "upper_left | upper_right | lower_left | lower_right", "method": "auto | manual"}
     ]
   }
4. When mode = "serial", assignments must contain exactly ONE element.
5. When mode = "parallel", assignments are required to contain two or more elements.
6. The quarter values in assignments must be selected from the user-provided remaining_quarters.
7. Do not assign the same quarter more than once within the same batch.
8. You must prioritize the user-provided engineering_constraints, design_tendency, and resource_hint when generating candidates.
9. The generated candidates must NOT violate engineering_constraints.
10. resource_hint is a soft constraint—precise resource accounting is not required, but obviously unreasonable resource conflicts should be avoided.
11. Ensure structural diversity among candidates to increase strategy variety; avoid generating duplicate or overly similar candidates.

""".strip()


EVALUATOR_SYSTEM_PROMPT = """
You are an evaluator for aircraft fuselage riveting system design.
Your role is to heuristically score a new action, not to prove whether it is fully executable.

You must strictly follow these rules:
1. Output ONLY a single JSON object. Do not include markdown, explanations, or any extra text.
2. Assign scores from 0 to 10 (floating-point values allowed) for the following four dimensions, and follow the format below:
{
  "constraint_consistency": 10,
  "completion_potential": 7.0,
  "resource_risk": 6.5,
  "design_tendency": 7.5,
  "reason": "Briefly explain the rationale for the scores in no more than two sentences."
}
constraint_consistency must be either 0 or 10 only.
3. If the branch clearly violates the user-provided engineering constraints, you must significantly lower constraint_consistency.
4. resource_risk means “the lower the resource risk, the higher the score.” This is a heuristic judgment, not an exact resource validation.
5. Do NOT output overall_score; the total score will be computed externally with weighted aggregation.

""".strip()


def planner_user_prompt(
    task_description: str,
    engineering_constraints: str,
    design_tendency: str,
    resource_hint: str | None,
    current_batches: List[Dict[str, Any]],
    remaining_quarters: List[str],
    k: int,
) -> str:
    payload = {
        "task_description": task_description,
        "engineering_constraints": engineering_constraints,
        "design_tendency": design_tendency,
        "resource_hint": resource_hint,
        "current_partial_strategy": current_batches,
        "remaining_quarters": remaining_quarters,
        "k": k,
        "field_explanations": {
            "task_description": "Task Background and Objectives",
            "engineering_constraints": "User-specified engineering constraints must be prioritized; do not use any implicit or unspecified rules.",
            "design_tendency": "User-preferred design direction",
            "resource_hint": "Soft constraints related to resource usage—no precise calculation is required, but obviously unreasonable resource conflicts should be avoided.",
            "current_partial_strategy": "Previously determined batch decisions are fixed and must not be modified; you need to continue expanding the next steps based on them.",
            "remaining_quarters": "The set of quarters that remain incomplete and are available for selection in the current candidate batch.",
            "k": "The number of candidate batches to generate in this iteration."
        }
    }
    return (
        "Based on the following context, please generate the next set of candidate batches."
        "Please focus on task_description, engineering_constraints, design_tendency, and resource_hint as the primary references."
        "Output JSON array only; do not include any explanation.\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )



def evaluator_user_prompt(
    task_description: str,
    engineering_constraints: str,
    design_tendency: str,
    new_state: Dict[str, Any],
    resource_hint: str | None,
) -> str:
    payload = {
        "task_description": task_description,
        "engineering_constraints": engineering_constraints,
        "design_tendency": design_tendency,
        "resource_hint": resource_hint,
        "new_state": new_state,
        "scoring_guide": {
            "constraint_consistency": "Whether it satisfies the engineering constraints and the user’s additional constraints: assign 10 points if it does, and 0 points if it does not.",
            "completion_potential": "The extent to which the current action advances overall progress: the more quarters a single batch covers, the more it reduces the number of subsequent batches, and the more it helps shorten the total processing time, the higher the score.",
            "resource_risk": "Whether the parallel/auto combination may introduce higher resource usage and conflict risk; a higher score indicates lower risk.",
            "design_tendency": "Whether it aligns with the user’s design preference.",
        },
    }
    return (
        "Please assign a heuristic score to the following new_state. Output a JSON object only.\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )
