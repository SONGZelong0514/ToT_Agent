from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from tot_agent.agent import ToTAgent
from tot_agent.config import LLMConfig, ToTConfig, UserProblem


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Tree-of-Thoughts agent for fuselage riveting strategy design")
    p.add_argument("--task", type=str, help="Task description")
    p.add_argument("--constraints", type=str, help="Engineering constraints")
    p.add_argument("--tendency", type=str, help="Design preference")
    p.add_argument("--resource-hint", type=str, help="Resource hint")
    p.add_argument("--max-depth", type=int)
    p.add_argument("--planner-k", type=int)
    p.add_argument("--beam-width", type=int)
    p.add_argument("--final-top-m", type=int)
    p.add_argument("--evaluator-repeat-n", type=int)
    p.add_argument("--temp-plan", type=float)
    p.add_argument("--temp-eval", type=float)
    p.add_argument("--mock", action="store_true", help="Use the mock LLM for local debugging")
    p.add_argument("--no-debug", action="store_true", help="Disable debug logs")
    return p


def main() -> None:
    load_dotenv()
    parser = build_arg_parser()
    args = parser.parse_args()

    task = args.task or ask(
        "Please enter a task description.",
        "Please generate a diverse set of batch combination strategies for the aircraft fuselage riveting system.",
    )
    constraints = args.constraints or ask(
        "Please enter the engineering constraints.",
        "1. Aircraft riveting is divided into two sub-processes: upper fuselage riveting and lower fuselage riveting. Each half-body riveting process is further divided into a left quarter and a right quarter."
        "2. The upper-left and upper-right quarters belong to the upper fuselage, while the lower-left and lower-right quarters belong to the lower fuselage."
        "3. Aircraft riveting operations are categorized into auto and manual; each execution of either an auto or a manual operation corresponds to the completion of one quarter."
        "4. All four quarters must be covered, and each must be covered exactly once."
        "5. Within the same parallel batch, if one quarter of a given half-body is processed using auto, then the other quarter of that half-body must not appear in that batch."
        "However, one or both quarters of the other half-body may still appear in the same batch."
    )
    tendency = args.tendency or ask("Please enter the design preference.",
                                    "Incorporate auto and manual operations, as well as both parallel and serial execution, as much as possible."
    )
    resource_hint = args.resource_hint or ask("Please enter the resource hints.",
                                              "Due to resource constraints, within the parallel operations of a single batch, the number of auto and manual operations must not exceed three each."
                                              "However, there is no limit on the total number of auto and manual operations combined."
    )

    llm_cfg = LLMConfig.from_env()
    llm_cfg.use_mock = args.mock or llm_cfg.use_mock

    tot_cfg = ToTConfig()  # Start with the defaults from config.py

    # Override values only when CLI arguments are provided
    if args.max_depth is not None:
        tot_cfg.max_depth = args.max_depth
    if args.planner_k is not None:
        tot_cfg.planner_k = args.planner_k
    if args.beam_width is not None:
        tot_cfg.beam_width = args.beam_width
    if args.final_top_m is not None:
        tot_cfg.final_top_m = args.final_top_m
    if args.evaluator_repeat_n is not None:
        tot_cfg.evaluator_repeat_n = args.evaluator_repeat_n
    if args.temp_plan is not None:
        tot_cfg.temp_plan = args.temp_plan
    if args.temp_eval is not None:
        tot_cfg.temp_eval = args.temp_eval

    tot_cfg.debug = not args.no_debug

    agent = ToTAgent(llm_cfg=llm_cfg, tot_cfg=tot_cfg)
    problem = UserProblem(
        task_description=task,
        engineering_constraints=constraints,
        design_tendency=tendency,
        resource_hint=resource_hint or None,
    )

    print("\n================ ToT Agent Started ================")
    print(f"Model      : {llm_cfg.model}")
    print(f"Base URL   : {llm_cfg.base_url}")
    print(f"Mock Mode  : {llm_cfg.use_mock}")
    print(f"Beam Width : {tot_cfg.beam_width}")
    print(f"Planner k  : {tot_cfg.planner_k}")
    print(f"Max Depth  : {tot_cfg.max_depth}")
    print("===================================================\n")

    result = agent.run(problem)

    print("\n================ Final Strategies ================")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("==================================================")


if __name__ == "__main__":
    main()
