# 面向机身铆接策略设计的 Tree-of-Thoughts Agent

本项目实现了一个面向飞机机身铆接批次组合策略生成的 Tree-of-Thoughts（ToT）智能体。系统通过兼容 OpenAI Chat Completions 格式的大语言模型接口生成候选批次动作、评估中间策略状态、执行 beam search，并输出多样化的高分设计方案。

项目同时提供命令行运行方式和基于 Gradio 的可视化前端。前端支持输入设计问题、实时查看后端日志，并展示搜索过程中的思维树。

## 功能特性

- 基于 Tree-of-Thoughts 的制造系统策略生成
- 使用 Planner 和 Evaluator 两类 LLM 角色分别完成候选生成与状态评分
- 支持 beam search、重复候选剪枝、启发式评分和最终多样性筛选
- 支持 mock LLM 模式，便于无 API 环境下本地调试
- 提供命令行入口，适合脚本化运行和参数实验
- 提供 Gradio 前端，支持交互式输入、实时日志流和思维树可视化
- 输出 JSON 格式结果，包含策略编号、分数、批次安排、作业分配和评估细节

## 项目结构

```text
.
├── app_tot_frontend.py      # Gradio 前端与思维树可视化
├── main.py                  # 命令行入口
├── requirements.txt         # 项目依赖
├── logo.png                 # 前端 logo
└── tot_agent/
    ├── agent.py             # ToTAgent 总控逻辑
    ├── config.py            # LLM 与 ToT 配置数据类
    ├── domain.py            # 策略、批次、作业分配和校验模型
    ├── evaluator.py         # 基于 LLM 的策略状态评分器
    ├── llm_client.py        # OpenAI-compatible LLM 客户端与 mock 模式
    ├── planner.py           # 基于 LLM 的候选批次生成器
    ├── prompts.py           # Planner 和 Evaluator 提示词
    ├── searcher.py          # Beam search、剪枝、评分和多样性选择
    └── utils.py             # JSON 解析、分数处理和调试输出工具
```

## 环境要求

- 推荐使用 Python 3.10 或更高版本
- 如果不使用 mock 模式，需要一个兼容 OpenAI Chat Completions 的模型接口

安装项目依赖：

```bash
pip install -r requirements.txt
```

## 环境变量配置

在项目根目录创建 `.env` 文件：

```env
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=your_model_name
OPENAI_TIMEOUT=120
PLANNER_MAX_TOKENS=1200
EVALUATOR_MAX_TOKENS=800
TOT_USE_MOCK=false
```

如果只想本地调试、不调用真实模型，可以设置：

```env
TOT_USE_MOCK=true
```

也可以在运行命令行时添加 `--mock` 参数。

## 快速开始

使用 mock 模式运行：

```bash
python main.py --mock
```

指定自定义任务运行：

```bash
python main.py ^
  --task "Generate diverse fuselage riveting batch strategies." ^
  --constraints "All four quarters must be completed exactly once." ^
  --tendency "Prefer high parallelism while keeping resource risk low." ^
  --resource-hint "Avoid excessive auto/manual resource conflicts."
```

在 macOS 或 Linux 中，可以将多行命令里的 `^` 替换为 `\`。

## 命令行参数

| 参数 | 说明 |
| --- | --- |
| `--task` | 任务描述 |
| `--constraints` | 工程约束 |
| `--tendency` | 设计倾向 |
| `--resource-hint` | 资源使用提示或软约束 |
| `--max-depth` | ToT 搜索最大深度 |
| `--planner-k` | 每个状态下 Planner 生成的候选批次数量 |
| `--beam-width` | 每一层保留的高分状态数量 |
| `--final-top-m` | 最多返回的最终策略数量 |
| `--evaluator-repeat-n` | 每个状态重复调用 Evaluator 的次数 |
| `--temp-plan` | Planner 的 LLM temperature |
| `--temp-eval` | Evaluator 的 LLM temperature |
| `--mock` | 使用本地 mock LLM 输出 |
| `--no-debug` | 关闭调试日志 |

## 启动可视化前端

启动前端：

```bash
python app_tot_frontend.py
```

默认访问地址为：

```text
http://127.0.0.1:7860
```

前端提供预设问题按钮，可以实时显示后端搜索日志，并在左侧绘制 ToT 搜索过程中的思维树。

## 输出格式

智能体返回一个 JSON 数组，每个元素代表一个候选策略：

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

合法的机身区域取值为：

```text
upper_left, upper_right, lower_left, lower_right
```

合法的执行方式为：

```text
auto, manual
```

合法的批次模式为：

```text
serial, parallel
```

## 算法流程

1. 根状态从尚未完成任何机身区域开始。
2. Planner 根据当前状态为每个节点生成 `k` 个候选批次动作。
3. 系统对候选批次去重，并根据剩余机身区域进行合法性校验。
4. 合法候选被应用到当前状态，形成新的部分策略状态。
5. Evaluator 从约束一致性、完成潜力、资源风险和设计倾向四个维度对新状态评分。
6. Beam search 在每一层保留得分最高的一批状态继续扩展。
7. 完整终止策略会进入 terminal pool，并按得分排序。
8. 最终通过多样性筛选返回结构上具有差异的高质量策略。

## 作为 Python 模块使用

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

## 注意事项

- 后端通过 `python-dotenv` 从 `.env` 中读取模型配置。
- 当前 `requirements.txt` 已包含命令行流程和 Gradio 前端所需依赖。
- mock 模式适合验证搜索流程和前端交互，但不代表真实工程推荐结果。
- 模型服务需要兼容 `/chat/completions` 接口格式。
