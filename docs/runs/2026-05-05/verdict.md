# Run 2026-05-05 — scope-narrowed baseline

**Verdict:** ✅ HARNESS-PIPELINE GREEN (LLM cell pending xAI API key)
**Scope:** OpenClaw × xAI Grok 4.3 only — per v0.6.4 product directive
**Captured against:** ai-memory-mcp v0.6.4 release binary @ `feat/v0.6.4` HEAD

## What changed from 2026-05-04 run

- Scope narrowed from "4 LLMs × 3 harnesses" to **"xAI Grok 4.3 × OpenClaw"** — no Claude / GPT / Gemini, no IronClaw / Hermes
- Runner enums (`Llm`, `Harness`) reduced to single variants
- Docker assets pruned to OpenClaw only (Dockerfile.ironclaw / .hermes + their composes removed)
- Tier docs + methodology rewritten for the tight scope
- Verdict shape unchanged — same per-cell JSON, same pass criteria

## Cells

| Cell | Outcome | Evidence |
|---|---|---|
| `harness-pipeline-openclaw-t1-awareness-core` | ✅ PASS | [json](cells/harness-pipeline-openclaw-t1-awareness-core.json) · [md](cells/harness-pipeline-openclaw-t1-awareness-core.md) |

## Key signals

- All **8 families** surfaced by `memory_capabilities` (target ≥6)
- `tools/list` returns **6 tools** under `--profile core` (5 core + always-on `memory_capabilities`)
- Schema migration v19 → v20 non-destructive on the fixture (17 memories preserved, 3 graph links preserved, `audit_log` table created)
- `loaded_flags` correctly reports only `core` family loaded under `--profile core`

## What's still pending

The first **real LLM-driven** cell requires:

1. xAI API key in `.env` (matches v0.6.3.1 A2A campaign secrets pattern)
2. Run via `runner/target/release/discovery-gate run --tier all --llm grok-4.3 --harness openclaw --profile core`

Pipeline is wired end-to-end; only credential plumbing is left.

## Reproducibility

```bash
# Smoke (no LLM — what this run captured):
DISCOVERY_GATE_BINARY=../ai-memory-mcp/target/release/ai-memory \
    bash scripts/smoke-t1-local.sh

# Real LLM-driven cell (requires xAI key):
echo "XAI_API_KEY=xai-..." > .env
./runner/target/release/discovery-gate run \
    --binary ../ai-memory-mcp/target/release/ai-memory \
    --tier all \
    --llm grok-4.3 \
    --harness openclaw \
    --profile core \
    --output docs/runs/$(date +%Y-%m-%d)
```
