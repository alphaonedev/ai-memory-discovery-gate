# Run 2026-05-05 — LLM driver wired, gate ready for real campaign

**Verdict:** GATE YELLOW — harness-pipeline GREEN; LLM-driver infrastructure GREEN; **awaiting XAI_API_KEY in operator env to fire the certifying real-Grok run**.
**Scope:** OpenClaw × xAI Grok 4.3 only — per v0.6.4 product directive
**Captured against:** ai-memory-mcp v0.6.4 release binary @ `feat/v0.6.4` HEAD

## What changed in this run

The remaining gap from the prior 2026-05-05 capture (real LLM cells) was **infrastructure-side**: the runner's LLM call was stubbed. This run lands the real driver:

- New: `scripts/grok_cell.py` — full xAI Grok 4.3 (api.x.ai/v1/chat/completions, OpenAI-compatible) tool-calling loop against ai-memory MCP stdio. Discovers tools at session start, dispatches Grok's tool calls into the daemon, captures families surfaced + error codes + include_schema calls + tokens + wall clock + final answer. Honest scoring per tier — no fudging.
- New: `scripts/aggregate_verdict.py` — rewrites `docs/index.md` verdict table + `README.md` badge from per-cell JSON. Filters cells by `llm == "grok-4.3"` so the harness-pipeline-smoke cell is informational only and does not influence the gate color.
- New: `scripts/run-llm-cells.sh` — one-shot runner that fires T1 / T2 / T3 / T4 sequentially against Grok 4.3 and aggregates. Fails loud if `XAI_API_KEY` is unset; never reads credential files directly.
- New: `scripts/test_grok_cell_mock.py` — mock-LLM end-to-end test. Verifies all four tier scoring paths (perfect-T1 → pass, T2 reactive recovery → pass, T3 proactive expansion → pass, T4 mesh 3/3 sub-cells → pass) by patching `grok_chat` with deterministic fake responses. Drives the v0.6.4 binary for real (MCP stdio path is exercised end-to-end), only the LLM is mocked.

The mock harness validation makes one thing concrete: **the moment XAI_API_KEY hits the operator env, all four tiers fire deterministically**. The infrastructure is no longer the gating step.

## Cells in this run

| Cell | LLM | Outcome | Evidence |
|---|---|---|---|
| `harness-pipeline-openclaw-t1-awareness-core` | (smoke, no LLM) | PASS | [json](cells/harness-pipeline-openclaw-t1-awareness-core.json) · [md](cells/harness-pipeline-openclaw-t1-awareness-core.md) |
| `grok-4.3-openclaw-t1-awareness-core` | Grok 4.3 | _pending real run_ | (awaits `XAI_API_KEY`) |
| `grok-4.3-openclaw-t2-reactive-core` | Grok 4.3 | _pending real run_ | (awaits `XAI_API_KEY`) |
| `grok-4.3-openclaw-t3-proactive-core` | Grok 4.3 | _pending real run_ | (awaits `XAI_API_KEY`) |
| `grok-4.3-openclaw-t4-mesh-recovery-{alice,bob,charlie}` | Grok 4.3 | _pending real run_ | (awaits `XAI_API_KEY`) |

## Key signals (from smoke + mock validation)

- Real binary, real MCP stdio. All 8 families surfaced; 6 tools loaded under `--profile core` (5 core + always-on `memory_capabilities`). [smoke cell verifies]
- `memory_kg_query` from `--profile core` → `-32601` with the canonical error-hint message containing `Restart with --profile <name>` and `--include-schema family=`. [verified live against the v0.6.4 binary outside the gate]
- `memory_capabilities --include-schema family=graph` returns the 8 graph-family tool schemas (loaded_under_active_profile=false, schema_version=v0.6.4-family-schemas-1). [verified live]
- v19 → v20 migration non-destructive on the fixture: 17 memories preserved, 3 graph links preserved, `audit_log` table created.

## How to fire the real campaign (operator one-liner)

```bash
# In a shell where XAI_API_KEY is exported (e.g. via your usual .env loader):
cd /root/ai-memory-discovery-gate
DISCOVERY_GATE_BINARY=../ai-memory-mcp/target/release/ai-memory \
  bash scripts/run-llm-cells.sh
```

This:
1. Restores `fixtures/corpus/v0.6.3.1-baseline.db.gz` per cell
2. Spawns the v0.6.4 binary at `--profile core` (T1/T2/T3) and across alice/bob/charlie profiles (T4)
3. Drives Grok 4.3 with the canonical prompt for each tier
4. Captures per-cell wire log + LLM transcript
5. Scores against pass criteria from `docs/methodology.md`
6. Aggregates the run and rewrites `docs/index.md` table + `README.md` gate badge color

Total wall clock: ~3–6 minutes for the four tiers (T4 fires three sub-cells).

## Honesty discipline

- The harness-pipeline-smoke cell is `llm: "harness-pipeline-smoke"` — it's filtered OUT of the gate-color decision. Smoke alone cannot turn the badge green. Real-Grok cells are the only path to GREEN.
- `aggregate_verdict.py` colors:
  - **GREEN** — every tier has at least one Grok cell AND its pass rate meets the tier threshold (T1 ≥90%, T2 ≥80%, T3 ≥50%, T4 ≥66%)
  - **YELLOW** — at least one tier meets bar but not all (mixed result, transparent)
  - **RED** — zero tiers meet bar (gate emphatically not green)
- Per-cell verdict JSON includes the full Grok finish_reason + tool_call list + error_codes + tokens. No black-box "trust me" outcomes.

## What's unchanged from the prior run

- Methodology, prompts, pass criteria, DB baseline — all unchanged. The bar didn't move; only the path to the bar shortened.
- Scope still **OpenClaw × xAI Grok 4.3 only**. Multi-LLM coverage is v0.6.5+.
