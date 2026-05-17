# Tree-of-Thoughts Agent for Fuselage Riveting Strategy Design

This project implements a Tree-of-Thoughts (ToT) agent for generating diverse batch-combination strategies for aircraft fuselage riveting. It uses an OpenAI-compatible chat completion API to propose candidate batch actions, evaluate partial strategies, perform beam search, and return ranked, structurally diverse design alternatives.

The repository includes both a command-line workflow and a Gradio-based visual frontend with a live thought-tree viewer.

## Features

- Tree-of-Thoughts search for manufacturing-system strategy generation
- Planner and evaluator roles driven by an OpenAI-compatible LLM API
- Beam search with duplicate pruning, heuristic scoring, and final diversity filtering
- Mock LLM mode for local debugging without calling an external model
- CLI entry point for scripted runs
- Gradio frontend for interactive problem input, real-time backend logs, and thought-tree visualization
- JSON output containing ranked strategy candidates, batch plans, assignment details, and evaluation metadata

## Project Structure

```text
.
├── app_tot_frontend.py      # Gradio frontend and thought-tree visualization
├── main.py                  # CLI entry point
├── requirements.txt         # Project dependencies
├── logo.png                 # Frontend logo
└── tot_agent/
    ├── agent.py             # ToTAgent orchestration
    ├── config.py            # LLM and ToT configuration dataclasses
    ├── domain.py            # Strategy, batch, assignment, and validation models
    ├── evaluator.py         # LLM-based strategy-state evaluator
    ├── llm_client.py        # OpenAI-compatible chat completion client and mock mode
    ├── planner.py           # LLM-based candidate batch planner
    ├── prompts.py           # Planner and evaluator prompts
    ├── searcher.py          # Beam search, pruning, scoring, and diversity selection
    └── utils.py             # JSON parsing, score utilities, and debug printing
```

## Requirements

- Python 3.10 or later is recommended
- An OpenAI-compatible chat completion endpoint, unless using mock mode

Install the project dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=your_model_name
OPENAI_TIMEOUT=120
PLANNER_MAX_TOKENS=1200
EVALUATOR_MAX_TOKENS=800
TOT_USE_MOCK=false
```

For local testing without an API key, set:

```env
TOT_USE_MOCK=true
```

You can also pass `--mock` when running the CLI.

## Quick Start

Run with mock mode:

```bash
python main.py --mock
```

Run with a custom task:

```bash
python main.py ^
  --task "Generate diverse fuselage riveting batch strategies." ^
  --constraints "All four quarters must be completed exactly once." ^
  --tendency "Prefer high parallelism while keeping resource risk low." ^
  --resource-hint "Avoid excessive auto/manual resource conflicts."
```

On macOS or Linux, replace `^` with `\` for multi-line commands.

## CLI Options

| Option | Description |
| --- | --- |
| `--task` | Task description |
| `--constraints` | Engineering constraints |
| `--tendency` | Design preference |
| `--resource-hint` | Soft resource guidance |
| `--max-depth` | Maximum ToT search depth |
| `--planner-k` | Number of candidate batches proposed per state |
| `--beam-width` | Number of high-scoring states retained per depth |
| `--final-top-m` | Maximum number of final strategies returned |
| `--evaluator-repeat-n` | Number of repeated evaluator calls per state |
| `--temp-plan` | Planner LLM temperature |
| `--temp-eval` | Evaluator LLM temperature |
| `--mock` | Use local mock LLM outputs |
| `--no-debug` | Disable debug logs |

## Launch the Frontend

Start the app:

```bash
python app_tot_frontend.py
```

The app launches at:

```text
http://127.0.0.1:7860
```

The frontend provides preset design queries, streams backend logs, and renders the evolving thought tree while the ToT agent searches for strategies.

## Output Format

The agent returns a JSON array of strategy candidates:

```json
[
  {
    "strategy_id": "S1",
    "score": 8.25,
    "batches": [
      {
        "mode": "parallel",
        "assignments": [
          {"quarter": "upper_left", "method": "auto"},
          {"quarter": "lower_left", "method": "manual"}
        ]
      }
    ],
    "eval_detail": {
      "constraint_consistency": 10.0,
      "completion_potential": 8.0,
      "resource_risk": 7.5,
      "design_tendency": 8.0,
      "overall_score": 8.25,
      "reason": "Brief evaluator rationale."
    }
  }
]
```

Valid quarters are:

```text
upper_left, upper_right, lower_left, lower_right
```

Valid methods are:

```text
auto, manual
```

Valid execution modes are:

```text
serial, parallel
```

## Algorithm Overview

1. The root state starts with no completed fuselage quarters.
2. The planner proposes `k` candidate batch actions for each active state.
3. Candidate batches are deduplicated and validated against the remaining quarters.
4. Valid candidates are applied to create new partial strategy states.
5. The evaluator scores each new state on constraint consistency, completion potential, resource risk, and design tendency.
6. Beam search keeps the top-scoring states at each depth.
7. Complete terminal strategies are collected and ranked.
8. A final diversity filter returns high-quality strategies that differ structurally.

## Using as a Python Module

```python
from tot_agent import LLMConfig, ToTAgent, ToTConfig, UserProblem

agent = ToTAgent(
    llm_cfg=LLMConfig.from_env(),
    tot_cfg=ToTConfig(max_depth=4, planner_k=7, beam_width=5),
)

problem = UserProblem(
    task_description="Generate diverse fuselage riveting batch strategies.",
    engineering_constraints="All four quarters must be covered exactly once.",
    design_tendency="Prefer a mix of auto/manual and parallel/serial execution.",
    resource_hint="Avoid obvious resource conflicts.",
)

strategies = agent.run(problem)
print(strategies)
```

## Notes

- The backend reads configuration from `.env` through `python-dotenv`.
- `requirements.txt` contains the dependencies required by both the CLI workflow and the Gradio frontend.
- Mock mode is useful for validating the search pipeline and UI behavior, but it does not produce meaningful engineering recommendations.
- The LLM endpoint must be compatible with the `/chat/completions` API shape.
