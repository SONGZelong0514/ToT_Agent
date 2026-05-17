from __future__ import annotations

import ast
import html
import os
import queue
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import gradio as gr


BASE_DIR = Path(__file__).resolve().parent
MAIN_FILE = BASE_DIR / "main.py"
LOGO_FILE = BASE_DIR / "logo.png"

DEFAULT_CONSTRAINTS = (
    "1. Aircraft riveting is divided into two sub-processes: upper fuselage riveting and lower fuselage riveting. Each half-body riveting process is further divided into a left quarter and a right quarter."
    "2. The upper-left and upper-right quarters belong to the upper fuselage, while the lower-left and lower-right quarters belong to the lower fuselage."
    "3. Aircraft riveting operations are categorized into auto and manual; each execution of either an auto or a manual operation corresponds to the completion of one quarter."
    "4. All four quarters must be covered, and each must be covered exactly once."
    "5. Within the same parallel batch, if one quarter of a given half-body is processed using auto, then the other quarter of that half-body must not appear in that batch."
    "However, one or both quarters of the other half-body may still appear in the same batch."
)

DEFAULT_TENDENCY = (
    "1. Maximize resource utilization as much as possible (the solution should include both automated and manual operations)."
    "2. Minimize the total processing time as much as possible (aim to execute two or three operations in parallel within each batch)."
    "3. Generate a set of clearly differentiated and interpretable solution alternatives."
)

DEFAULT_RESOURCE_HINT = (
    "Due to resource constraints, within the parallel operations of a single batch, the number of auto and manual operations must not exceed three each."
    "However, there is no limit on the total number of auto and manual operations combined."
)

PRESET_QUERIES = {
    "Question 1": "Please generate a diverse set of batch combination strategies for the aircraft fuselage riveting system, with a primary focus on minimizing total processing time, while ensuring that all four quarters are covered and that each quarter is executed exactly once.",
    "Question 2": "Please generate a diverse set of aircraft fuselage riveting batch strategies, with emphasis on maximizing the use of both auto and manual resources while keeping all engineering constraints satisfied.",
    "Question 3": "Please generate several interpretable aircraft fuselage riveting strategies that intentionally differ in automation preference, parallelism level, and resource utilization style.",
    "Question 4": "Please generate candidate aircraft fuselage riveting strategies that prioritize conservative feasibility first, then improve efficiency as much as possible under the given constraints.",
}


THEME_CSS = r'''
:root {
  --brand-blue: #0B3D91;
  --brand-blue-light: #2B7CE9;
}

.gradio-container,
.gradio-container * {
  font-family: "Times New Roman", Times, serif !important;
}

.header-wrap {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 8px 16px 0 16px;
  padding: 8px 16px;
  background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
  border: 1px solid #e5e7eb;
  border-radius: 10px;
}

.header-right {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.header-right > div {
  margin: 0 !important;
  padding: 0 !important;
}

.header-right .prose {
  margin: 0 !important;
}

.header-right .prose * {
  margin-top: 0 !important;
  margin-bottom: 0 !important;
}

.header-sub {
  margin-top: 4px !important;
}

.logo {
  height: 70px;
}

.main-wrap {
  display: flex !important;
  flex-direction: column !important;
  gap: 12px;
  margin: 8px 16px 0 16px;
  padding: 8px 0 12px 0;
}
.main-wrap > * {
  width: 100%;
}

.grid-2 {
  display: grid !important;
  grid-template-columns: 1.0fr 1.5fr;
  gap: 12px;
  align-items: stretch;
}

.card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 600px;
}

.card .title {
  padding: 6px 12px;
  font-weight: 700;
  color: var(--brand-blue);
  border-bottom: 1px solid #e5e7eb;
  background: #f9fbff;
}
.card .title * {
  margin: 0 !important;
}

.graphBox {
  flex: 1 1 auto !important;
  min-height: 0;
  overflow: hidden;
}

.graphBox > div,
.graphBox iframe,
.graphBox .prose,
.graphBox .overflow-y-auto,
.graphBox .prose > div,
.graphBox .overflow-y-auto > div {
  height: 100% !important;
  max-height: none !important;
}

.graphBox .prose,
.graphBox .overflow-y-auto {
  overflow: hidden !important;
}

.chatBox {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.submit-row {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 8px 12px 12px 12px;
  border-top: 1px solid #e5e7eb;
  background: #ffffff;
}

.submit-row button {
  padding: 6px 14px;
  line-height: 1.2;
  min-height: 45px;
}

.footer-preset {
  display: flex !important;
  flex-direction: column !important;
  align-items: stretch !important;
  justify-content: flex-start !important;
  width: 100%;
  gap: 0 !important;
}

.footer-preset > * {
  width: 100% !important;
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}

.preset-wrap {
  display: flex !important;
  flex-wrap: nowrap !important;
  justify-content: space-between !important;
  align-items: center;
  gap: 0 !important;
  width: 100%;
}

.preset-wrap button {
  flex: 0 0 auto !important;
  min-width: 0 !important;
  padding: 6px 36px !important;
  white-space: nowrap;
}

.header-title,
.header-title * {
  font-size: 20px !important;
  line-height: 1.25 !important;
}

.header-sub,
.header-sub * {
  font-size: 14px !important;
  line-height: 1.25 !important;
}

.card .title,
.card .title * {
  font-size: 20px !important;
  line-height: 1.25 !important;
}

button,
.preset-wrap button,
.submit-row button {
  font-size: 20px !important;
}

.submit-row input,
.submit-row textarea,
.gr-textbox textarea {
  font-size: 20px !important;
}

.chatBox * {
  font-size: 20px !important;
  line-height: 1.25 !important;
}

.footer-preset .prose p,
.footer-preset .markdown-text p {
  font-size: 20px !important;
  font-weight: 700 !important;
  line-height: 1.25 !important;
}

.graphBox p {
  font-size: 20px !important;
  line-height: 1.25 !important;
}

.header-wrap {
  margin-top: 0px !important;
  padding-top: 0px !important;
  margin-bottom: 2px !important;
  padding-bottom: 2px !important;
}

.main-wrap {
  margin-top: 0px !important;
  padding-top: 0px !important;
  padding-bottom: 0px !important;
  gap: 0px !important;
}

.footer-preset {
  margin-top: 0px !important;
}

.footer-preset .prose p,
.footer-preset .markdown-text p {
  margin-top: 2px !important;
  margin-bottom: 2px !important;
}

.preset-wrap {
  margin-top: 0 !important;
}

.card * {
  font-size: 20px !important;
}
'''


PLACEHOLDER_TREE_HTML = """
<div style='width:100%; height:100%; box-sizing:border-box; padding:10px; display:flex; align-items:center; justify-content:center;'>
  <div style='text-align:center; color:#555; line-height:1.5;'>
    <div style='font-weight:700; color:#0B3D91; margin-bottom:10px;'>Thought tree output will appear here.</div>
    <div>Enter a design problem or click one of the preset questions below, then click Send.</div>
  </div>
</div>
"""


@dataclass
class TreeNode:
    node_id: str
    label: str
    depth: int
    parent_id: str | None = None
    kind: str = "candidate"
    status: str = "running"
    ref: str | None = None
    score: float | None = None
    tooltip: list[str] = field(default_factory=list)


class ToTTreeState:
    def __init__(self) -> None:
        self.nodes: dict[str, TreeNode] = {}
        self.children: dict[str, list[str]] = {}
        self.counter = 0
        self.root_id: str | None = None
        self.current_depth: int = 0
        self.current_state_id: str | None = None
        self.current_state_from_ref: str | None = None
        self.current_candidate_id: str | None = None
        self.candidate_by_ref: dict[str, str] = {}
        self.state_by_from_ref: dict[str, str] = {}
        self.terminal_count = 0

    def add_node(self, label: str, depth: int, parent_id: str | None, *, kind: str, status: str = "running", ref: str | None = None) -> str:
        self.counter += 1
        node_id = f"n{self.counter}"
        self.nodes[node_id] = TreeNode(node_id=node_id, label=label, depth=max(depth, 0), parent_id=parent_id, kind=kind, status=status, ref=ref)
        self.children.setdefault(node_id, [])
        if parent_id:
            self.children.setdefault(parent_id, []).append(node_id)
        if self.root_id is None:
            self.root_id = node_id
        return node_id

    def ensure_root(self, question: str) -> str:
        if self.root_id is None:
            short = question.strip().replace("\n", " ")
            if len(short) > 72:
                short = short[:69] + "..."
            rid = self.add_node("Root", 0, None, kind="root", status="accepted", ref="ROOT")
            self.nodes[rid].tooltip.extend(["User problem", short])
            self.root_id = rid
        return self.root_id

    def begin_state(self, depth: int, state_idx: int, from_ref: str, completed: list[str], remaining: list[str]) -> None:
        self.current_depth = depth
        self.current_candidate_id = None
        self.current_state_from_ref = from_ref

        if from_ref == "ROOT":
            self.current_state_id = self.ensure_root("User problem")
            return

        existing = self.state_by_from_ref.get(from_ref)
        if existing:
            self.current_state_id = existing
            node = self.nodes[existing]
            node.tooltip.extend([
                f"completed={completed}",
                f"remaining={remaining}",
                f"depth={depth}",
            ])
            return

        parent = self.candidate_by_ref.get(from_ref, self.root_id)
        state_id = self.add_node(f"State {state_idx}", max(1, depth * 2), parent, kind="state", status="accepted", ref=f"STATE-D{depth}-S{state_idx}")
        self.nodes[state_id].tooltip.extend([
            f"from={from_ref}",
            f"completed={completed}",
            f"remaining={remaining}",
            f"depth={depth}",
        ])
        self.state_by_from_ref[from_ref] = state_id
        self.current_state_id = state_id
        if parent and parent in self.nodes:
            self.nodes[parent].status = "accepted"

    def add_candidate(self, candidate_idx: int, ref: str, batch_text: str) -> None:
        parent_id = self.root_id if self.current_state_from_ref == "ROOT" else self.current_state_id
        if not parent_id:
            return
        candidate_id = self.add_node(
            f"Candidate {candidate_idx}\n[{ref}]",
            max(1, self.current_depth * 2 + 1),
            parent_id,
            kind="candidate",
            status="running",
            ref=ref,
        )
        self.candidate_by_ref[ref] = candidate_id
        self.current_candidate_id = candidate_id
        self.nodes[candidate_id].tooltip.append(batch_text)

    def update_current_candidate_score(self, score: float | None, line: str) -> None:
        if not self.current_candidate_id:
            return
        node = self.nodes[self.current_candidate_id]
        node.score = score
        node.tooltip.append(line)

    def append_current_candidate_detail(self, line: str) -> None:
        if self.current_candidate_id:
            self.nodes[self.current_candidate_id].tooltip.append(line)

    def mark_candidate_pruned(self, ref: str, detail: str) -> None:
        nid = self.candidate_by_ref.get(ref)
        if not nid:
            return
        self.nodes[nid].status = "pruned"
        self.nodes[nid].tooltip.append(detail)

    def add_next_state_from_candidate(self, state_idx: int, candidate_ref: str, score: float | None, batch_text: str) -> None:
        nid = self.candidate_by_ref.get(candidate_ref)
        if not nid:
            return
        self.nodes[nid].status = "accepted"
        if score is not None:
            self.nodes[nid].score = score
        self.nodes[nid].tooltip.append(f"retained_for_next_state score={score}")
        self.nodes[nid].tooltip.append(batch_text)
        depth = self.current_depth + 1
        if candidate_ref not in self.state_by_from_ref:
            state_id = self.add_node(f"State {state_idx}", max(1, depth * 2), nid, kind="state", status="accepted", ref=f"STATE-D{depth}-S{state_idx}")
            self.nodes[state_id].tooltip.append(f"from={candidate_ref}")
            self.state_by_from_ref[candidate_ref] = state_id

    def add_terminal_from_current_candidate(self) -> None:
        if not self.current_candidate_id:
            return
        self.terminal_count += 1
        parent_id = self.current_candidate_id
        node = self.nodes[parent_id]
        node.status = "accepted"
        term_id = self.add_node("terminal_pool", node.depth + 1, parent_id, kind="terminal", status="terminal", ref=f"TP-{self.terminal_count}")
        self.nodes[term_id].tooltip.append(f"added_from={node.ref}")


def try_parse_batch_dict(text: str) -> dict[str, Any] | None:
    try:
        return ast.literal_eval(text)
    except Exception:
        return None


class LogTreeParser:
    depth_header_re = re.compile(r"=+\s*Depth\s+(\d+)\s*\|\s*Beam Size\s*=\s*(\d+)\s*=+", re.I)
    state_re = re.compile(r"\[State\s+(\d+)\s*\|\s*from\s+([^\]]+)\]\s*completed=(\[.*?\])\s*,\s*remaining=(\[.*?\])\s*,\s*depth=(\d+)", re.I)
    candidate_re = re.compile(r"-\s*Candidate\s+(\d+)\s*\[([^\]]+)\]\s*:\s*(\{.*\})")
    score_re = re.compile(r"overall=([0-9]+(?:\.[0-9]+)?)", re.I)
    next_state_re = re.compile(r"-\s*Next State\s+(\d+)\s*<=\s*([^|]+?)\s*\|\s*score=([0-9]+(?:\.[0-9]+)?)\s*\|\s*batch=(\{.*\})", re.I)
    pruned_re = re.compile(r"-\s*PRUNED\s+([^|]+?)\s*\|\s*score=([0-9]+(?:\.[0-9]+)?)\s*\|\s*batch=(\{.*\})", re.I)

    def __init__(self, tree: ToTTreeState) -> None:
        self.tree = tree

    def ingest(self, line: str) -> None:
        stripped = line.strip()
        if not stripped:
            return

        m = self.depth_header_re.search(stripped)
        if m:
            self.tree.current_depth = int(m.group(1))
            self.tree.current_candidate_id = None
            return

        m = self.state_re.search(stripped)
        if m:
            state_idx = int(m.group(1))
            from_ref = m.group(2).strip()
            completed = ast.literal_eval(m.group(3))
            remaining = ast.literal_eval(m.group(4))
            depth = int(m.group(5))
            self.tree.begin_state(depth, state_idx, from_ref, completed, remaining)
            return

        m = self.candidate_re.search(stripped)
        if m:
            candidate_idx = int(m.group(1))
            ref = m.group(2).strip()
            batch_text = m.group(3)
            self.tree.add_candidate(candidate_idx, ref, batch_text)
            return

        if stripped.startswith("-> Score:"):
            sm = self.score_re.search(stripped)
            score = float(sm.group(1)) if sm else None
            self.tree.update_current_candidate_score(score, stripped)
            return

        if stripped.startswith("reason:") or stripped.startswith("reason："):
            self.tree.append_current_candidate_detail(stripped)
            return

        if "Terminal strategy" in stripped:
            self.tree.append_current_candidate_detail(stripped)
            self.tree.add_terminal_from_current_candidate()
            return

        m = self.next_state_re.search(stripped)
        if m:
            state_idx = int(m.group(1))
            ref = m.group(2).strip()
            score = float(m.group(3))
            batch_text = m.group(4)
            self.tree.add_next_state_from_candidate(state_idx, ref, score, batch_text)
            return

        m = self.pruned_re.search(stripped)
        if m:
            ref = m.group(1).strip()
            score = float(m.group(2))
            batch_text = m.group(3)
            self.tree.mark_candidate_pruned(ref, f"PRUNED score={score} | batch={batch_text}")
            return


def wrap_text(s: str, n: int = 18) -> list[str]:
    s = s.replace("\n", " ")
    return [s[i:i+n] for i in range(0, len(s), n)][:4]


def node_style(node: TreeNode) -> tuple[str, str, str]:
    if node.kind == "root":
        return "#E8F1FF", "#3558A8", "#3558A8"
    if node.kind == "state":
        return "#EEF9F1", "#2E8B57", "#2E8B57"
    if node.kind == "terminal":
        return "#F1E9FF", "#7A4CE0", "#7A4CE0"
    if node.status == "pruned":
        return "#FFE8E8", "#D63C3C", "#C53030"
    return "#EDF2FF", "#5577E6", "#5577E6"


def _render_svg_document(tree: ToTTreeState) -> str:
    if not tree.root_id:
        return PLACEHOLDER_TREE_HTML

    levels: dict[int, list[TreeNode]] = {}
    for node in tree.nodes.values():
        levels.setdefault(node.depth, []).append(node)
    for depth in levels:
        levels[depth].sort(key=lambda x: (x.kind, x.ref or x.node_id, x.node_id))

    max_depth = max(levels) if levels else 0
    max_count = max((len(v) for v in levels.values()), default=1)
    col_gap = 240
    row_gap = 90
    width = max(1400, 260 + col_gap * (max_depth + 1))
    height = max(560, 110 + row_gap * max_count)

    positions: dict[str, tuple[float, float]] = {}
    for depth in range(max_depth + 1):
        nodes = levels.get(depth, [])
        count = max(1, len(nodes))
        for idx, node in enumerate(nodes, start=1):
            x = 120 + depth * col_gap
            y = (height / (count + 1)) * idx
            positions[node.node_id] = (x, y)

    edge_parts: list[str] = []
    node_parts: list[str] = []

    for node in tree.nodes.values():
        if node.parent_id and node.parent_id in positions and node.node_id in positions:
            x1, y1 = positions[node.parent_id]
            x2, y2 = positions[node.node_id]
            mx = (x1 + x2) / 2
            edge_color = "#E39A9A" if node.kind == "candidate" and node.status == "pruned" else "#B8C4FF"
            edge_parts.append(
                f"<path d='M {x1+95} {y1} C {mx} {y1}, {mx} {y2}, {x2-95} {y2}' "
                f"stroke='{edge_color}' stroke-width='2.0' fill='none' />"
            )

    for node in tree.nodes.values():
        x, y = positions[node.node_id]
        fill, stroke, text_color = node_style(node)
        text_lines = wrap_text(node.label)
        h = max(64, 28 + 18 * len(text_lines))
        w = 188
        tip = html.escape("\n".join([node.label] + node.tooltip[-10:]))
        texts = []
        for i, line in enumerate(text_lines):
            yy = y - (len(text_lines) - 1) * 9 + i * 18
            texts.append(
                f"<text x='{x}' y='{yy}' text-anchor='middle' font-size='13' "
                f"fill='{text_color}' font-weight='600'>{html.escape(line)}</text>"
            )
        badge = ""
        if node.score is not None and node.kind == "candidate":
            badge = (
                f"<rect x='{x+42}' y='{y-h/2-11}' rx='10' ry='10' width='50' height='20' "
                f"fill='white' stroke='{stroke}' stroke-width='1.4' />"
                f"<text x='{x+67}' y='{y-h/2+2}' text-anchor='middle' font-size='11' "
                f"fill='{stroke}'>{node.score:.2f}</text>"
            )

        node_parts.append(
            f"<g><title>{tip}</title>"
            f"<rect x='{x-w/2}' y='{y-h/2}' rx='14' ry='14' width='{w}' height='{h}' "
            f"fill='{fill}' stroke='{stroke}' stroke-width='2' />"
            f"{''.join(texts)}{badge}</g>"
        )

    return f"""
    <html>
      <head>
        <meta charset='utf-8'>
        <style>
          html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            background: #fbfdff;
            overflow: hidden;
          }}

          .viewer-wrap {{
            width: 100%;
            height: 100%;
            position: relative;
            overflow: hidden;
            background: #fbfdff;
            cursor: grab;
            user-select: none;
          }}

          .viewer-wrap.dragging {{
            cursor: grabbing;
          }}

          #treeSvg {{
            width: 100%;
            height: 100%;
            display: block;
            background: #fbfdff;
          }}

          .toolbar {{
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 10;
            display: flex;
            gap: 6px;
          }}

          .toolbar button {{
            border: 1px solid #d1d5db;
            background: white;
            border-radius: 8px;
            padding: 4px 10px;
            font-size: 14px;
            cursor: pointer;
          }}

          .toolbar button:hover {{
            background: #f3f4f6;
          }}
        </style>
      </head>
      <body>
        <div class='viewer-wrap' id='viewerWrap'>
          <div class='toolbar'>
            <button id='zoomInBtn' type='button'>+</button>
            <button id='zoomOutBtn' type='button'>-</button>
            <button id='resetBtn' type='button'>Reset</button>
          </div>

          <svg id='treeSvg' viewBox='0 0 {width} {height}' preserveAspectRatio='xMinYMin meet'>
            {''.join(edge_parts)}
            {''.join(node_parts)}
          </svg>
        </div>

        <script>
          (function() {{
            const svg = document.getElementById('treeSvg');
            const wrap = document.getElementById('viewerWrap');
            const zoomInBtn = document.getElementById('zoomInBtn');
            const zoomOutBtn = document.getElementById('zoomOutBtn');
            const resetBtn = document.getElementById('resetBtn');

            const baseWidth = {width};
            const baseHeight = {height};

            let scale = 1.0;
            let minScale = 0.2;
            let maxScale = 4.0;
            let viewX = 0;
            let viewY = 0;

            let isDragging = false;
            let dragStartX = 0;
            let dragStartY = 0;
            let dragStartViewX = 0;
            let dragStartViewY = 0;

            function clamp(val, min, max) {{
              return Math.max(min, Math.min(max, val));
            }}

            function applyViewBox() {{
              const w = baseWidth / scale;
              const h = baseHeight / scale;
              svg.setAttribute('viewBox', `${{viewX}} ${{viewY}} ${{w}} ${{h}}`);
            }}

            function zoomAt(clientX, clientY, zoomFactor) {{
              const rect = svg.getBoundingClientRect();
              if (!rect.width || !rect.height) return;

              const oldScale = scale;
              const newScale = clamp(scale * zoomFactor, minScale, maxScale);
              if (newScale === oldScale) return;

              const oldW = baseWidth / oldScale;
              const oldH = baseHeight / oldScale;
              const newW = baseWidth / newScale;
              const newH = baseHeight / newScale;

              const px = (clientX - rect.left) / rect.width;
              const py = (clientY - rect.top) / rect.height;

              const worldX = viewX + px * oldW;
              const worldY = viewY + py * oldH;

              scale = newScale;
              viewX = worldX - px * newW;
              viewY = worldY - py * newH;

              applyViewBox();
            }}

            wrap.addEventListener('wheel', function(e) {{
              e.preventDefault();
              const factor = e.deltaY < 0 ? 1.12 : 0.88;
              zoomAt(e.clientX, e.clientY, factor);
            }}, {{ passive: false }});

            wrap.addEventListener('mousedown', function(e) {{
              if (e.button !== 0) return;
              isDragging = true;
              wrap.classList.add('dragging');
              dragStartX = e.clientX;
              dragStartY = e.clientY;
              dragStartViewX = viewX;
              dragStartViewY = viewY;
            }});

            window.addEventListener('mousemove', function(e) {{
              if (!isDragging) return;

              const rect = svg.getBoundingClientRect();
              if (!rect.width || !rect.height) return;

              const w = baseWidth / scale;
              const h = baseHeight / scale;

              const dx = e.clientX - dragStartX;
              const dy = e.clientY - dragStartY;

              viewX = dragStartViewX - (dx / rect.width) * w;
              viewY = dragStartViewY - (dy / rect.height) * h;
              applyViewBox();
            }});

            window.addEventListener('mouseup', function() {{
              isDragging = false;
              wrap.classList.remove('dragging');
            }});

            zoomInBtn.addEventListener('click', function() {{
              const rect = svg.getBoundingClientRect();
              zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, 1.2);
            }});

            zoomOutBtn.addEventListener('click', function() {{
              const rect = svg.getBoundingClientRect();
              zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, 0.8);
            }});

            resetBtn.addEventListener('click', function() {{
              scale = 1.0;
              viewX = 0;
              viewY = 0;
              applyViewBox();
            }});

            applyViewBox();
          }})();
        </script>
      </body>
    </html>
    """


def render_tree_html(tree: ToTTreeState) -> str:
    if not tree.root_id:
        return PLACEHOLDER_TREE_HTML
    inner = _render_svg_document(tree).replace("&", "&amp;").replace('"', "&quot;")
    return (
        "<div style='width:100%; height:100%; box-sizing:border-box; overflow:hidden;'>"
        f"<iframe srcdoc=\"{inner}\" style='width:100%; height:100%; border:none;'></iframe>"
        "</div>"
    )


def build_backend_command(question: str) -> list[str]:
    return [
        sys.executable,
        "-u",
        str(MAIN_FILE),
        "--task", question.strip(),
        "--constraints", DEFAULT_CONSTRAINTS,
        "--tendency", DEFAULT_TENDENCY,
        "--resource-hint", DEFAULT_RESOURCE_HINT,
    ]


def run_backend(question: str, q: queue.Queue[str], result_holder: dict[str, Any]) -> None:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    cmd = build_backend_command(question)
    proc = subprocess.Popen(
        cmd,
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
        errors="ignore",
    )

    lines: list[str] = []
    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip("\n")
            lines.append(line)
            q.put(line)
        proc.wait()
    finally:
        result_holder["returncode"] = proc.returncode
        result_holder["all_text"] = "\n".join(lines)
        q.put("__PROCESS_DONE__")


def extract_final_json_blob(text: str) -> str:
    marker = "================ Final Strategies ================"
    if marker not in text:
        return ""
    tail = text.split(marker, 1)[-1]
    end_marker = "=================================================="
    if end_marker in tail:
        tail = tail.split(end_marker, 1)[0]
    first = tail.find("{")
    last = tail.rfind("}")
    if first == -1 or last == -1 or last <= first:
        return ""
    return tail[first:last+1].strip()


def format_assistant_text(log_text: str, final_json: str = "") -> str:
    parts = ["Backend real-time output:", f"```text\n{log_text[-30000:]}\n```"]
    if final_json:
        parts += ["Final result:", f"```json\n{final_json}\n```"]
    return "\n\n".join(parts)


def set_preset(text: str):
    return gr.update(value=text)


def stream_tot(user_input: str, chat_history: list[tuple[str, str]] | None):
    history = list(chat_history or [])
    question = (user_input or "").strip()
    if not question:
        history = history + [("System", "Please enter a design problem, or click one of the preset question buttons below first.")]
        yield PLACEHOLDER_TREE_HTML, history, history, gr.update()
        return

    if not MAIN_FILE.exists():
        history = history + [(question, f"Backend entry file not found: {MAIN_FILE}")]
        yield PLACEHOLDER_TREE_HTML, history, history, gr.update(value="")
        return

    tree = ToTTreeState()
    tree.ensure_root(question)
    parser = LogTreeParser(tree)

    q: queue.Queue[str] = queue.Queue()
    result_holder: dict[str, Any] = {}
    worker = threading.Thread(target=run_backend, args=(question, q, result_holder), daemon=True)
    worker.start()

    history = history + [(question, "The ToT agent has started and is waiting for backend output...")]
    yield render_tree_html(tree), history, history, gr.update(value="")

    all_lines: list[str] = []
    done = False
    last_emit = 0.0

    while True:
        got = False
        try:
            item = q.get(timeout=0.25)
            got = True
        except queue.Empty:
            item = None

        if item == "__PROCESS_DONE__":
            done = True
        elif isinstance(item, str):
            all_lines.append(item)
            parser.ingest(item)

        now = time.time()
        if got or (now - last_emit > 0.5):
            log_text = "\n".join(all_lines)
            history[-1] = (question, format_assistant_text(log_text))
            yield render_tree_html(tree), history, history, gr.update(value="")
            last_emit = now

        if done and q.empty():
            break

    worker.join(timeout=0.1)
    full_text = result_holder.get("all_text", "\n".join(all_lines))
    final_json = extract_final_json_blob(full_text)
    history[-1] = (question, format_assistant_text(full_text, final_json))
    yield render_tree_html(tree), history, history, gr.update(value="")


with gr.Blocks(css=THEME_CSS, theme=gr.themes.Soft()) as demo:
    with gr.Row(elem_classes=["header-wrap"]):
        with gr.Column(scale=1.35):
            gr.Image(
                value=str(LOGO_FILE) if LOGO_FILE.exists() else None,
                elem_classes=["logo"],
                show_label=False,
                container=False,
                interactive=False,
                show_download_button=False,
                show_fullscreen_button=False,
            )
        with gr.Column(scale=2, elem_classes=["header-right"]):
            gr.Markdown(
                "### Design-on-Graph 2.0: Tree of Thoughts-Based AI Agent for Diversified Design Plan Generation of Manufacturing Systems",
                elem_classes=["header-title"],
            )
            gr.Markdown(
                "Supported by the **AI4DESE Lab**, **SUSTech**, Shenzhen, China.",
                elem_classes=["header-sub"],
            )

    with gr.Row(elem_classes=["main-wrap"]):
        with gr.Row(elem_classes=["grid-2"]):
            with gr.Column(elem_classes=["card"]):
                gr.Markdown("#### Thought Tree Viewer", elem_classes=["title"])
                tree_html = gr.HTML(value=PLACEHOLDER_TREE_HTML, elem_classes=["graphBox"])

            with gr.Column(elem_classes=["card"]):
                gr.Markdown("#### Generative Design Assistant", elem_classes=["title"])
                chat = gr.Chatbot(
                    elem_classes=["chatBox"],
                    bubble_full_width=False,
                    avatar_images=(None, None),
                    show_label=False,
                    value=[],
                )
                with gr.Row(elem_classes=["submit-row"]):
                    user_inp = gr.Textbox(
                        placeholder="Please enter a design problem directly, or click one of the preset question buttons below and then click Send.",
                        scale=8,
                        show_label=False,
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)

        with gr.Row(elem_classes=["footer-preset"]):
            gr.Markdown("**Preset queries**")
            with gr.Row(elem_classes=["preset-wrap"]):
                for title, value in PRESET_QUERIES.items():
                    gr.Button(title).click(lambda v=value: set_preset(v), outputs=user_inp)

    state_chat = gr.State([])

    send_btn.click(
        stream_tot,
        inputs=[user_inp, state_chat],
        outputs=[tree_html, chat, state_chat, user_inp],
    )
    user_inp.submit(
        stream_tot,
        inputs=[user_inp, state_chat],
        outputs=[tree_html, chat, state_chat, user_inp],
    )


demo.queue(default_concurrency_limit=1)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
