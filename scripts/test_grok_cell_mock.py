#!/usr/bin/env python3
# Copyright 2026 AlphaOne LLC
# SPDX-License-Identifier: Apache-2.0
#
# Validate grok_cell.py's MCP loop and scoring with a mock LLM. No
# network. Drives the script end-to-end against the v0.6.4 binary.

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Required by entrypoint
os.environ.setdefault("XAI_API_KEY", "test-mock-key")

import grok_cell  # noqa: E402

BINARY = os.environ.get("DISCOVERY_GATE_BINARY",
                        str((REPO_ROOT.parent / "ai-memory-mcp" / "target" / "release" / "ai-memory").resolve()))
OUT_BASE = Path("/tmp/discovery-mock-test")


def _fake_chat(scenario):
    """Return a function matching grok_chat's signature that yields a
    deterministic sequence of LLM responses keyed by `scenario`.
    """
    rounds = iter(scenario)

    def fake_grok_chat(messages, tools, api_key, model):
        try:
            return next(rounds)
        except StopIteration:
            return {
                "choices": [{"message": {"content": "(no more mock rounds)"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }

    return fake_grok_chat


def msg(content="", tool_calls=None):
    m = {"role": "assistant", "content": content}
    if tool_calls:
        m["tool_calls"] = tool_calls
    return {"choices": [{"message": m, "finish_reason": "stop" if not tool_calls else "tool_calls"}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}}


def tc(name, args, call_id="c1"):
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}


# ---------- Scenario A: T1 perfect — call capabilities, name 6+ families ----------

scenarioA = [
    msg(tool_calls=[tc("memory_capabilities", {})]),
    msg(content=("I called memory_capabilities. Eight families are advertised: "
                 "core, lifecycle, graph, governance, power, meta, archive, and other. "
                 "Currently only the core family is loaded under --profile core; the "
                 "other families are advertised but not loaded. "
                 "Total tools: 43; loaded under active profile: 6 "
                 "(5 core tools + memory_capabilities). To load others, the operator "
                 "would restart with --profile graph (or full).")),
]

# ---------- Scenario B: T2 reactive — try kg, get -32601, recover with include_schema ----------

scenarioB = [
    msg(tool_calls=[tc("memory_kg_query", {"entity": "Project Alpha"}, "c-kg")]),
    msg(tool_calls=[tc("memory_capabilities", {"include_schema": True, "family": "graph"}, "c-cap")]),
    msg(content="I received -32601 'tool_not_found'. Per the error hint I called "
                "memory_capabilities with include_schema=true family=graph. The graph "
                "family is not loaded under --profile core; the operator should restart "
                "with --profile core,graph (or --profile full) to enable memory_kg_query "
                "and the other graph-family tools."),
]

# ---------- Scenario C: T3 proactive — capabilities first, surface --profile power ----------

scenarioC = [
    msg(tool_calls=[tc("memory_capabilities", {})]),
    msg(content="I checked memory_capabilities first. The power family (which contains "
                "memory_consolidate, memory_check_duplicate, memory_detect_contradiction) "
                "is not loaded under --profile core. To consolidate Project Aurora "
                "memories, the operator should restart with --profile power (or "
                "--profile full)."),
]

# ---------- Scenario D: T4 mesh — alice surfaces operator action, bob does graph, charlie consolidates ----------

# T4 runs three sub-cells. Each sub-cell needs its own scenario.
scenarioD_alice = [
    msg(tool_calls=[tc("memory_capabilities", {})]),
    msg(content="As alice (--profile core), I cannot natively call memory_kg_query "
                "or memory_consolidate. I delegate the graph build to bob (--profile graph) "
                "and consolidation to charlie (--profile full). Coordination plan recorded."),
]
scenarioD_bob = [
    msg(tool_calls=[tc("memory_capabilities", {})]),
    msg(content="As bob (--profile core,graph), I built the mesh-coordination-test graph: "
                "3 nodes (test-a, test-b, test-c) with related_to edges. Delegating "
                "consolidation to charlie."),
]
scenarioD_charlie = [
    msg(tool_calls=[tc("memory_capabilities", {})]),
    msg(content="As charlie (--profile full), I have all 43 tools. I would call "
                "memory_consolidate on the duplicates. Mesh task complete: 3 nodes, "
                "1 consolidation."),
]


def run_scenario(name, tier, profile, scenario):
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    out_dir = OUT_BASE / name
    out_dir.mkdir(parents=True, exist_ok=True)
    fake = _fake_chat(scenario)
    with mock.patch.object(grok_cell, "grok_chat", fake):
        result = grok_cell.run_cell(tier, profile, BINARY, out_dir, "mock-key", "mock-model")
    print(f"[{name}] tier={tier} profile={profile} outcome={result['outcome']} reason={result['reason']}")
    return result


def main():
    if not os.access(BINARY, os.X_OK):
        print(f"FATAL: binary missing at {BINARY}", file=sys.stderr)
        sys.exit(2)

    rA = run_scenario("scenarioA-t1", "t1", "core", scenarioA)
    assert rA["outcome"] == "pass", f"T1 should pass: {rA}"

    rB = run_scenario("scenarioB-t2", "t2", "core", scenarioB)
    assert rB["outcome"] == "pass", f"T2 should pass: {rB}"

    rC = run_scenario("scenarioC-t3", "t3", "core", scenarioC)
    assert rC["outcome"] == "pass", f"T3 should pass: {rC}"

    # T4: simulate the in-process mesh by patching run_cell's per-agent
    # scenarios. Easier to test the per-sub-cell flow directly since the
    # 3 different scenarios need 3 different mocks.
    print("[scenarioD-t4] running 3 sub-cells with per-agent scenarios...")
    out_dir = OUT_BASE / "scenarioD-t4"
    out_dir.mkdir(parents=True, exist_ok=True)
    sub_results = []
    for agent, prof, scen in [
        ("alice", "core", scenarioD_alice),
        ("bob", "core,graph", scenarioD_bob),
        ("charlie", "full", scenarioD_charlie),
    ]:
        fake = _fake_chat(scen)
        with mock.patch.object(grok_cell, "grok_chat", fake):
            sub = run_scenario(f"D-{agent}", "t4", prof, scen)
            sub_results.append(sub)

    n_pass = sum(1 for s in sub_results if s["outcome"] == "pass")
    print(f"[scenarioD-t4] aggregate: {n_pass}/3 sub-cells passed")
    assert n_pass >= 2, "T4 mock should have >=2 sub-cells passing"

    print("\nAll mock scenarios behaved as expected. Scoring + MCP loop verified.")


if __name__ == "__main__":
    main()
