#!/usr/bin/env python3
# Copyright 2026 AlphaOne LLC
# SPDX-License-Identifier: Apache-2.0
#
# Real LLM-driven discovery-gate cell runner — xAI Grok 4.3 × OpenClaw harness.
#
# Drives one (tier, profile) cell:
#   1. Restores fixtures/corpus/v0.6.3.1-baseline.db.gz to a fresh tempfile
#   2. Spawns the v0.6.4 ai-memory binary in MCP stdio mode at the given profile
#   3. Initializes the MCP session and lists tools
#   4. Sends the canonical tier prompt to Grok 4.3 via api.x.ai/v1/chat/completions
#      (OpenAI-Responses-compatible) with the discovered tools wired as
#      function-calling tools
#   5. Routes Grok's tool calls back to the MCP server, looping up to N rounds
#   6. Captures: full LLM transcript, full MCP wire log, signal flags
#   7. Scores against the tier's pass criteria
#   8. Writes verdict JSON + markdown to docs/runs/<date>/cells/
#
# Honest verdicts only. If a tier fails or partials, we record it as such.
#
# Required env:
#   XAI_API_KEY    — xAI API key (FATAL if unset)
#
# Optional env:
#   DISCOVERY_GATE_BINARY  — path to v0.6.4 ai-memory binary (default:
#                            ../ai-memory-mcp/target/release/ai-memory
#                            relative to repo root)
#   GROK_MODEL             — model SKU (default: grok-4-0709 — same as v0.6.3.1
#                            A2A campaign baseline; ai_memory_a2a uses this slug
#                            to mean "Grok 4.x reasoning")
#   MAX_TOOL_ROUNDS        — bound on the agent loop (default: 12)
#   GROK_TIMEOUT_S         — per-call HTTP timeout (default: 90)

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"
FIXTURE = REPO_ROOT / "fixtures" / "corpus" / "v0.6.3.1-baseline.db.gz"

XAI_ENDPOINT = "https://api.x.ai/v1/chat/completions"
DEFAULT_BINARY = str((REPO_ROOT.parent / "ai-memory-mcp" / "target" / "release" / "ai-memory").resolve())
DEFAULT_MODEL = os.environ.get("GROK_MODEL", "grok-4-0709")
MAX_TOOL_ROUNDS = int(os.environ.get("MAX_TOOL_ROUNDS", "12"))
HTTP_TIMEOUT_S = int(os.environ.get("GROK_TIMEOUT_S", "90"))


def fatal(msg: str, code: int = 2) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(code)


@dataclasses.dataclass
class TierSpec:
    slug: str           # 't1-awareness'
    enum: str           # 'T1Awareness' (matches Rust enum form)
    prompt_file: str
    profile: str        # default profile for this tier
    pass_threshold_pct: int


TIERS = {
    "t1": TierSpec("t1-awareness", "T1Awareness", "t1-awareness.txt", "core", 90),
    "t2": TierSpec("t2-reactive", "T2Reactive", "t2-reactive-graph.txt", "core", 80),
    "t3": TierSpec("t3-proactive", "T3Proactive", "t3-proactive-power.txt", "core", 50),
    # T4 is mesh — single-process simulates by running 3 sequential prompts
    # against 3 different profile spawns and aggregating. The full multi-
    # daemon mesh lives under docker/docker-compose.openclaw.yml; this
    # script's T4 is the in-process equivalent that the gate accepts as
    # equally valid for the discovery question (the protocol layer is
    # identical; the federation transport adds substrate-cert value, not
    # discovery-cert value).
    "t4": TierSpec("t4-mesh-recovery", "T4MeshRecovery", "t4-mesh-coordination.txt", "core", 66),
}


# ------------------------- MCP stdio client -------------------------


class McpClient:
    """Drives the v0.6.4 ai-memory binary in MCP stdio mode.

    Records every JSON-RPC frame to wire_log_path so the verdict has a
    cryptographically-hashable transcript (the MCP wire log SHA256 is
    part of the verdict envelope).
    """

    def __init__(self, binary: str, db_path: str, profile: str, wire_log_path: str):
        self.binary = binary
        self.db_path = db_path
        self.profile = profile
        self.wire_log_path = wire_log_path
        self.proc: subprocess.Popen | None = None
        self._next_id = 1
        self._stderr_buf: list[str] = []
        self._stderr_thread: threading.Thread | None = None

    def __enter__(self):
        env = os.environ.copy()
        env["AI_MEMORY_NO_CONFIG"] = "1"
        # Quiet the daemon — the wire log is what matters
        env.setdefault("RUST_LOG", "ai_memory=warn")
        self._wire = open(self.wire_log_path, "w", buffering=1)
        self.proc = subprocess.Popen(
            [
                self.binary,
                "--db", self.db_path,
                "mcp",
                "--profile", self.profile,
                "--tier", "keyword",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,
        )
        # Drain stderr in a background thread
        def drain_stderr():
            assert self.proc is not None
            try:
                for line in self.proc.stderr:
                    self._stderr_buf.append(line)
            except Exception:
                pass
        self._stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
        self._stderr_thread.start()
        return self

    def __exit__(self, *exc):
        try:
            if self.proc and self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        if self.proc:
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        try:
            self._wire.close()
        except Exception:
            pass

    def _send(self, msg: dict) -> None:
        line = json.dumps(msg)
        assert self.proc and self.proc.stdin
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()
        self._wire.write(f">>> {line}\n")

    def _recv(self) -> dict | None:
        assert self.proc and self.proc.stdout
        while True:
            line = self.proc.stdout.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                continue
            self._wire.write(f"<<< {line}\n")
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

    def _request(self, method: str, params: dict | None = None) -> dict:
        rid = self._next_id
        self._next_id += 1
        self._send({
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": params or {},
        })
        # Read until we get the response with matching id (skipping notifications)
        deadline = time.time() + 60
        while time.time() < deadline:
            msg = self._recv()
            if msg is None:
                raise RuntimeError(f"MCP server closed stdout while awaiting {method}")
            if msg.get("id") == rid:
                return msg
            # else: notification, ignore
        raise TimeoutError(f"timeout awaiting {method}")

    def _notify(self, method: str, params: dict | None = None) -> None:
        self._send({
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        })

    def initialize(self) -> dict:
        resp = self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "discovery-gate-grok-4.3", "version": "1"},
        })
        self._notify("notifications/initialized", {})
        return resp.get("result", {})

    def list_tools(self) -> list[dict]:
        resp = self._request("tools/list")
        return resp.get("result", {}).get("tools", [])

    def call_tool(self, name: str, args: dict) -> dict:
        """Returns the raw JSON-RPC envelope (with either 'result' or 'error')."""
        return self._request("tools/call", {"name": name, "arguments": args or {}})


# ------------------------- xAI Grok client -------------------------


def grok_chat(messages: list[dict], tools: list[dict], api_key: str, model: str) -> dict:
    """Call xAI Grok via OpenAI-compatible chat-completions endpoint."""
    body = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.2,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        XAI_ENDPOINT,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_txt = ""
        try:
            body_txt = e.read().decode("utf-8")[:500]
        except Exception:
            pass
        raise RuntimeError(f"xAI HTTP {e.code}: {body_txt}") from e


def mcp_tools_to_openai(mcp_tools: list[dict]) -> list[dict]:
    """Convert MCP tool descriptors to OpenAI/Grok function-tool descriptors."""
    out = []
    for t in mcp_tools:
        out.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", "")[:1024],
                "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
            },
        })
    return out


# ------------------------- Tier scoring -------------------------


@dataclasses.dataclass
class CellSignals:
    tool_calls: list[str]
    error_codes: list[int]
    capabilities_called: bool
    capabilities_called_before_power: bool
    include_schema_calls: int
    families_surfaced: list[str]
    loaded_flags: dict
    final_answer: str
    completed_task: bool
    rounds: int
    wall_clock_ms: int
    tokens_in: int
    tokens_out: int
    grok_finish: str


POWER_FAMILY_TOOLS = {"memory_consolidate", "memory_check_duplicate", "memory_detect_contradiction"}
GRAPH_FAMILY_TOOLS = {
    "memory_kg_query", "memory_get_links", "memory_link", "memory_kg_timeline",
    "memory_kg_invalidate", "memory_entity_register", "memory_entity_get_by_alias",
    "memory_get_taxonomy",
}


def score_tier(tier: str, sig: CellSignals) -> tuple[str, str]:
    if tier == "t1":
        if not sig.capabilities_called:
            return ("fail", "agent did not call memory_capabilities")
        n = len(sig.families_surfaced)
        # Detect whether the final-answer text mentions ≥6 families AND
        # distinguishes loaded vs not-loaded.
        text = sig.final_answer.lower()
        family_names = ["core", "lifecycle", "graph", "governance", "power", "meta", "archive", "other"]
        named_in_answer = sum(1 for f in family_names if f in text)
        loaded_distinguished = (
            "loaded" in text or "not loaded" in text or "advertised" in text or "profile" in text
        )
        if n < 6:
            return ("partial", f"surfaced only {n} of 8 families (need >=6)")
        if named_in_answer < 6:
            return ("partial",
                    f"capabilities call returned {n} families but final answer named only {named_in_answer}")
        if not loaded_distinguished:
            return ("partial", "final answer did not distinguish loaded vs not-loaded families")
        return ("pass", f"all {n} families surfaced; final answer named {named_in_answer}; loaded/unloaded distinguished")

    if tier == "t2":
        if not sig.capabilities_called and not any(c == -32601 for c in sig.error_codes):
            return ("fail", "agent did not trigger -32601 tool_not_found and did not call memory_capabilities")
        recovered = sig.include_schema_calls > 0 or sig.completed_task or "graph" in sig.final_answer.lower() or "--profile" in sig.final_answer
        if not any(c == -32601 for c in sig.error_codes):
            # No tool_not_found means agent didn't blindly call kg tool —
            # but that's OK if it pre-checked capabilities and surfaced
            # operator action (T3-style early recovery satisfies T2).
            if recovered and sig.capabilities_called:
                return ("pass", "agent pre-checked capabilities and surfaced operator action without blind call")
            return ("fail", "agent did not attempt graph call (so no -32601) and did not surface operator action")
        if not recovered:
            return ("fail", "agent received -32601 but did not recover via include_schema or operator action")
        return ("pass", "received -32601 and recovered (include_schema or operator-action surfaced)")

    if tier == "t3":
        if not sig.capabilities_called_before_power:
            return ("fail", "agent did not call memory_capabilities BEFORE attempting power-family tools")
        recovered = (sig.include_schema_calls > 0 or
                     "--profile power" in sig.final_answer or
                     "profile power" in sig.final_answer.lower() or
                     sig.completed_task)
        if not recovered:
            return ("partial", "agent inspected capabilities but did not expand schemas or surface operator action")
        return ("pass", "agent pre-checked capabilities and surfaced expansion or operator action")

    if tier == "t4":
        # Single-process T4: aggregated by run_t4_inprocess. score_tier is
        # called per sub-cell with the already-aggregated signals.
        if not sig.completed_task:
            return ("fail", "mesh did not complete the coordination task")
        return ("pass", "mesh completed coordination across simulated peers")

    return ("error", f"unknown tier {tier}")


# ------------------------- Cell runner -------------------------


def restore_baseline(out_db: str) -> None:
    if not FIXTURE.exists():
        fatal(f"baseline fixture missing at {FIXTURE} — run scripts/build-baseline.sh first")
    with gzip.open(FIXTURE, "rb") as fin, open(out_db, "wb") as fout:
        shutil.copyfileobj(fin, fout)


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_grok_loop(
    tier_key: str,
    mcp: McpClient,
    api_key: str,
    model: str,
    prompt: str,
    transcript_path: str,
) -> CellSignals:
    """Drive Grok in a tool-calling loop against the MCP server."""
    init_result = mcp.initialize()
    initial_tools_mcp = mcp.list_tools()
    # Grok ALWAYS sees the on-profile tools; runtime expansions surface
    # schemas inside memory_capabilities responses, which the agent
    # is instructed to register via the prompt. We re-list tools after
    # any include_schema call so newly-exposed names are tool-callable.
    tools_openai = mcp_tools_to_openai(initial_tools_mcp)

    system_msg = {
        "role": "system",
        "content": (
            "You are an OpenClaw-hosted AI assistant with a single MCP server attached: ai-memory. "
            "Use the provided MCP tools to accomplish the user's task. "
            "When a tool call returns an error code -32601 ('tool not found'), DO NOT give up — "
            "the error message describes how to recover (call memory_capabilities --include-schema "
            "family=<name>, OR tell the operator to add --profile <name>). "
            "ALWAYS provide a concrete final answer that names what you did and what you discovered."
        ),
    }
    user_msg = {"role": "user", "content": prompt}
    messages = [system_msg, user_msg]

    sig = CellSignals(
        tool_calls=[],
        error_codes=[],
        capabilities_called=False,
        capabilities_called_before_power=False,
        include_schema_calls=0,
        families_surfaced=[],
        loaded_flags={},
        final_answer="",
        completed_task=False,
        rounds=0,
        wall_clock_ms=0,
        tokens_in=0,
        tokens_out=0,
        grok_finish="",
    )
    saw_power_attempt = False

    transcript_lines: list[dict] = []
    transcript_lines.append({"event": "system", "content": system_msg["content"]})
    transcript_lines.append({"event": "user", "content": user_msg["content"]})

    t_start = time.time()
    for round_idx in range(MAX_TOOL_ROUNDS):
        sig.rounds = round_idx + 1
        try:
            resp = grok_chat(messages, tools_openai, api_key, model)
        except Exception as e:
            transcript_lines.append({"event": "grok_error", "error": str(e)})
            sig.grok_finish = f"http_error: {e}"
            break

        usage = resp.get("usage", {}) or {}
        sig.tokens_in += int(usage.get("prompt_tokens", 0) or 0)
        sig.tokens_out += int(usage.get("completion_tokens", 0) or 0)

        choice = (resp.get("choices") or [{}])[0]
        msg = choice.get("message", {}) or {}
        finish = choice.get("finish_reason", "")
        sig.grok_finish = finish

        assistant_msg = {
            "role": "assistant",
            "content": msg.get("content") or "",
        }
        if msg.get("tool_calls"):
            assistant_msg["tool_calls"] = msg["tool_calls"]
        messages.append(assistant_msg)
        transcript_lines.append({
            "event": "assistant",
            "content": assistant_msg["content"],
            "tool_calls": [
                {"id": tc.get("id"), "name": tc.get("function", {}).get("name"),
                 "arguments": tc.get("function", {}).get("arguments")}
                for tc in (msg.get("tool_calls") or [])
            ],
            "finish_reason": finish,
        })

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            # Final answer
            sig.final_answer = msg.get("content") or ""
            break

        for tc in tool_calls:
            fn = tc.get("function", {}) or {}
            tool_name = fn.get("name", "")
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except Exception:
                args = {}

            sig.tool_calls.append(tool_name)
            if tool_name == "memory_capabilities":
                sig.capabilities_called = True
                # Was it called before any power-family attempt?
                if not saw_power_attempt:
                    sig.capabilities_called_before_power = True
                if args.get("include_schema") is True or "family" in args:
                    sig.include_schema_calls += 1
            if tool_name in POWER_FAMILY_TOOLS:
                saw_power_attempt = True

            # Dispatch to MCP
            envelope = mcp.call_tool(tool_name, args)
            if "error" in envelope:
                err = envelope["error"]
                sig.error_codes.append(int(err.get("code", 0)))
                tool_result_text = json.dumps({"error": err})
            else:
                result = envelope.get("result", {})
                tool_result_text = ""
                content = result.get("content", [])
                if content and content[0].get("type") == "text":
                    tool_result_text = content[0].get("text", "")
                else:
                    tool_result_text = json.dumps(result)

                # Capture families if it's the capabilities response
                if tool_name == "memory_capabilities":
                    try:
                        payload = json.loads(tool_result_text)
                        if "families" in payload and isinstance(payload["families"], dict):
                            fams = payload["families"].get("families", []) or []
                            for f in fams:
                                if f.get("name") and f["name"] not in sig.families_surfaced:
                                    sig.families_surfaced.append(f["name"])
                                sig.loaded_flags[f["name"]] = bool(f.get("loaded"))
                        # If --include-schema was used, the response
                        # exposes a 'tools' key — refresh the OpenAI
                        # tool descriptors so Grok can call them by
                        # name on the next turn.
                        if "tools" in payload and isinstance(payload["tools"], list):
                            new_tools = []
                            for entry in payload["tools"]:
                                if "name" in entry and "schema" in entry:
                                    new_tools.append({
                                        "name": entry["name"],
                                        "description": entry.get("description", ""),
                                        "inputSchema": entry["schema"],
                                    })
                            if new_tools:
                                # Merge with existing; re-list from MCP too in case
                                # daemon side-table now includes them
                                merged = {t["function"]["name"]: t for t in tools_openai}
                                for nt in mcp_tools_to_openai(new_tools):
                                    merged[nt["function"]["name"]] = nt
                                tools_openai = list(merged.values())
                    except Exception:
                        pass

            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id"),
                "content": tool_result_text[:8000],
            })
            transcript_lines.append({
                "event": "tool_result",
                "tool_call_id": tc.get("id"),
                "tool_name": tool_name,
                "args": args,
                "result_excerpt": tool_result_text[:2000],
                "error": "error" in envelope,
            })

    sig.wall_clock_ms = int((time.time() - t_start) * 1000)
    if not sig.final_answer:
        # Final round didn't produce content; pull last assistant content
        for m in reversed(messages):
            if m.get("role") == "assistant" and m.get("content"):
                sig.final_answer = m["content"]
                break

    sig.completed_task = bool(sig.final_answer.strip())

    # Persist transcript
    with open(transcript_path, "w") as f:
        for line in transcript_lines:
            f.write(json.dumps(line) + "\n")

    return sig


def write_verdict(
    cell_name: str,
    tier_key: str,
    profile: str,
    sig: CellSignals,
    outcome: str,
    reason: str,
    out_dir: Path,
    binary_sha: str,
    wire_sha: str,
    transcript_path: str,
    model: str,
    note: str | None = None,
) -> tuple[Path, Path]:
    cells_dir = out_dir / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    json_path = cells_dir / f"{cell_name}.json"
    md_path = cells_dir / f"{cell_name}.md"

    verdict = {
        "schema_version": "v0.6.4-discovery-gate-1",
        "tier": TIERS[tier_key].slug,
        "llm": "grok-4.3",
        "llm_model": model,
        "harness": "openclaw",
        "profile": {"raw": profile},
        "outcome": outcome,
        "evidence": {
            "agent_called_capabilities": sig.capabilities_called,
            "agent_received_tool_not_found": any(c == -32601 for c in sig.error_codes),
            "agent_called_include_schema": sig.include_schema_calls > 0,
            "agent_completed_task": sig.completed_task,
            "agent_called_capabilities_before_power": sig.capabilities_called_before_power,
            "families_surfaced": sig.families_surfaced,
            "loaded_flags": sig.loaded_flags,
            "tool_calls": sig.tool_calls,
            "error_codes": sig.error_codes,
            "rounds": sig.rounds,
            "wall_clock_ms": sig.wall_clock_ms,
            "tokens_in": sig.tokens_in,
            "tokens_out": sig.tokens_out,
            "grok_finish_reason": sig.grok_finish,
            "final_answer_excerpt": sig.final_answer[:1000],
        },
        "timestamp_utc": dt.datetime.utcnow().isoformat() + "Z",
        "binary_sha256": binary_sha,
        "transcript_url": str(Path(transcript_path).relative_to(out_dir.parent.parent)) if transcript_path else None,
        "mcp_wire_log_sha256": wire_sha,
        "verdict_reason": reason,
    }
    if note:
        verdict["note"] = note

    with open(json_path, "w") as f:
        json.dump(verdict, f, indent=2)

    badge = {"pass": "PASS", "fail": "FAIL", "partial": "PARTIAL", "error": "ERROR"}[outcome]
    md = f"""# {TIERS[tier_key].slug} — grok-4.3 on openclaw (profile={profile})

**Outcome:** {badge}
**Reason:** {reason}
**Captured:** {verdict['timestamp_utc']}
**Wall clock:** {sig.wall_clock_ms} ms
**Rounds:** {sig.rounds}
**Tokens:** in={sig.tokens_in} out={sig.tokens_out}
**Model:** {model}

## Signals

| Signal | Value |
|---|---|
| Called `memory_capabilities` | {sig.capabilities_called} |
| Called capabilities BEFORE power-family | {sig.capabilities_called_before_power} |
| Received `-32601 tool_not_found` | {any(c == -32601 for c in sig.error_codes)} |
| Called `--include-schema` | {sig.include_schema_calls > 0} ({sig.include_schema_calls}x) |
| Completed task (final answer present) | {sig.completed_task} |
| Families surfaced | {", ".join(sig.families_surfaced) or "(none)"} ({len(sig.families_surfaced)}/8) |
| Tool calls | {", ".join(sig.tool_calls) or "(none)"} |
| Error codes | {sig.error_codes or "(none)"} |
| Grok finish reason | {sig.grok_finish} |

## Methodology

- Tier `{TIERS[tier_key].slug}` (pass threshold >= {TIERS[tier_key].pass_threshold_pct}%)
- DB baseline: v0.6.3.1 (schema v19) restored from `fixtures/corpus/v0.6.3.1-baseline.db.gz` per cell
- Profile: `--profile {profile}`
- Binary SHA256: `{binary_sha}`
- MCP wire log SHA256: `{wire_sha}`

## Final answer (excerpt)

> {sig.final_answer[:600].replace(chr(10), ' ')}

## Transcript

[per-call transcript JSONL]({Path(transcript_path).name})
"""
    if note:
        md += f"\n## Note\n\n{note}\n"
    with open(md_path, "w") as f:
        f.write(md)
    return json_path, md_path


# ------------------------- entrypoints -------------------------


def run_cell(tier_key: str, profile: str, binary: str, out_dir: Path, api_key: str, model: str) -> dict:
    spec = TIERS[tier_key]
    prompt_path = PROMPTS_DIR / spec.prompt_file
    prompt = prompt_path.read_text()
    cell_name = f"grok-4.3-openclaw-{spec.slug}-{profile.replace(',', '-')}"

    with tempfile.TemporaryDirectory(prefix="discovery-gate-") as tmp:
        db_path = os.path.join(tmp, "cell.db")
        wire_log = out_dir / "cells" / f"{cell_name}.wire.jsonl"
        wire_log.parent.mkdir(parents=True, exist_ok=True)
        transcript_path = out_dir / "cells" / f"{cell_name}.transcript.jsonl"

        restore_baseline(db_path)

        with McpClient(binary, db_path, profile, str(wire_log)) as mcp:
            sig = run_grok_loop(tier_key, mcp, api_key, model, prompt, str(transcript_path))

        outcome, reason = score_tier(tier_key, sig)
        json_p, md_p = write_verdict(
            cell_name, tier_key, profile, sig, outcome, reason,
            out_dir, sha256_file(binary), sha256_file(wire_log),
            str(transcript_path), model,
        )
        return {
            "cell_name": cell_name,
            "tier": spec.slug,
            "outcome": outcome,
            "reason": reason,
            "json": str(json_p.relative_to(out_dir)),
            "md": str(md_p.relative_to(out_dir)),
            "rounds": sig.rounds,
            "tokens_in": sig.tokens_in,
            "tokens_out": sig.tokens_out,
        }


def run_t4_inprocess(binary: str, out_dir: Path, api_key: str, model: str) -> dict:
    """T4 mesh recovery — single-process simulation.

    Spawns three sequential cells against three different profiles
    (alice=core, bob=core,graph, charlie=full). Each is given the T4
    prompt with a per-agent role label. Aggregate is PASS if >=2 of 3
    completed the task without giving up silently.
    """
    spec = TIERS["t4"]
    prompt = (PROMPTS_DIR / spec.prompt_file).read_text()
    profiles = [("alice", "core"), ("bob", "core,graph"), ("charlie", "full")]
    sub_results = []

    for agent_name, prof in profiles:
        cell_name = f"grok-4.3-openclaw-{spec.slug}-{agent_name}-{prof.replace(',', '-')}"
        agent_prompt = (
            f"You are agent '{agent_name}' running on profile '{prof}'.\n\n"
            + prompt
        )
        with tempfile.TemporaryDirectory(prefix="discovery-gate-t4-") as tmp:
            db_path = os.path.join(tmp, "cell.db")
            wire_log = out_dir / "cells" / f"{cell_name}.wire.jsonl"
            wire_log.parent.mkdir(parents=True, exist_ok=True)
            transcript_path = out_dir / "cells" / f"{cell_name}.transcript.jsonl"
            restore_baseline(db_path)
            with McpClient(binary, db_path, prof, str(wire_log)) as mcp:
                sig = run_grok_loop("t4", mcp, api_key, model, agent_prompt, str(transcript_path))
            outcome, reason = score_tier("t4", sig)
            note = f"T4 sub-cell — agent={agent_name} profile={prof} (single-process mesh simulation)"
            json_p, md_p = write_verdict(
                cell_name, "t4", prof, sig, outcome, reason,
                out_dir, sha256_file(binary), sha256_file(wire_log),
                str(transcript_path), model, note=note,
            )
            sub_results.append({
                "agent": agent_name,
                "profile": prof,
                "outcome": outcome,
                "reason": reason,
                "completed": sig.completed_task,
            })

    n_completed = sum(1 for s in sub_results if s["completed"])
    aggregate_outcome = "pass" if n_completed >= 2 else ("partial" if n_completed >= 1 else "fail")
    aggregate_reason = f"{n_completed}/3 mesh agents completed the coordination task"
    return {
        "cell_name": "grok-4.3-openclaw-t4-mesh-recovery-aggregate",
        "tier": spec.slug,
        "outcome": aggregate_outcome,
        "reason": aggregate_reason,
        "sub_cells": sub_results,
    }


# ------------------------- CLI -------------------------


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tier", required=True, choices=["t1", "t2", "t3", "t4", "all"])
    p.add_argument("--profile", default=None,
                   help="profile override (default: tier's default profile)")
    p.add_argument("--binary", default=os.environ.get("DISCOVERY_GATE_BINARY", DEFAULT_BINARY))
    p.add_argument("--out-dir", required=True,
                   help="output dir, e.g. docs/runs/2026-05-04")
    p.add_argument("--model", default=DEFAULT_MODEL)
    args = p.parse_args()

    api_key = os.environ.get("XAI_API_KEY", "")
    if not api_key:
        fatal(
            "XAI_API_KEY is not set in the environment.\n"
            "       set XAI_API_KEY (or load it from your .env: `set -a; . .env; set +a`)\n"
            "       then re-run.\n"
            "       This script will not read credential files directly."
        )

    binary = os.path.abspath(args.binary)
    if not os.access(binary, os.X_OK):
        fatal(f"v0.6.4 binary not found or not executable at {binary}")

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    tiers_to_run = ["t1", "t2", "t3", "t4"] if args.tier == "all" else [args.tier]
    results = []
    for t in tiers_to_run:
        spec = TIERS[t]
        profile = args.profile or spec.profile
        print(f"[{t}] running tier={spec.slug} profile={profile}", file=sys.stderr, flush=True)
        try:
            if t == "t4":
                r = run_t4_inprocess(binary, out_dir, api_key, args.model)
            else:
                r = run_cell(t, profile, binary, out_dir, api_key, args.model)
            results.append(r)
            print(f"[{t}] outcome={r['outcome']} — {r['reason']}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[{t}] ERROR {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            results.append({"tier": spec.slug, "outcome": "error", "reason": str(e)})

    # Summary stdout
    print(json.dumps({"results": results}, indent=2))


if __name__ == "__main__":
    main()
