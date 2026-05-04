# Run 2026-05-04 — first baseline campaign

**Verdict:** ✅ HARNESS-PIPELINE GREEN (LLM cells pending API credentials)
**Captured against:** ai-memory-mcp v0.6.4 release binary @ `feat/v0.6.4` HEAD
**Repo:** [alphaonedev/ai-memory-discovery-gate](https://github.com/alphaonedev/ai-memory-discovery-gate)

## What this run covers

The 2026-05-04 baseline run is the **harness-pipeline smoke test** — it validates every step of the discovery-gate runner except the LLM call itself. Cells with `llm=harness-pipeline-smoke` substitute a deterministic MCP-stdio simulation for the model API call, then score the result against the same pass criteria a real LLM run would.

A green smoke run proves:

- The v0.6.3.1 baseline fixture restores cleanly
- The v0.6.4 binary opens it, migrates schema v19 → v20, populates `audit_log`, preserves all rows
- MCP stdio loop drives the canonical T1 first-call sequence (`initialize` → `tools/list` → `memory_capabilities`)
- The capabilities response contains the v0.6.4 `families` block with all 8 families
- The runner's verdict scoring + per-cell markdown emission work

A green smoke run does NOT prove that real LLMs (Claude / GPT / Grok / Gemini) will make those calls. That's what the next run (with API keys) tests.

## Cells

| Cell | Outcome | Wall clock | Evidence |
|---|---|---|---|
| `harness-pipeline-openclaw-t1-awareness-core` | ✅ PASS | see cell | [json](cells/harness-pipeline-openclaw-t1-awareness-core.json) · [md](cells/harness-pipeline-openclaw-t1-awareness-core.md) |

## Key signals

- All **8 families** surfaced by `memory_capabilities` (target ≥6)
- `tools/list` returns **6 tools** under `--profile core` (5 core + always-on `memory_capabilities`) — matches the v0.6.4 contract
- Schema migration v19 → v20 non-destructive on the fixture (17 memories preserved, `audit_log` table created)
- `loaded_flags` correctly reports only `core` family loaded under the `--profile core` profile

## Pending

The first **LLM-driven** baseline campaign requires:

1. xAI API key (for Grok 4.3 — simplest to wire; matches v0.6.3.1 A2A campaign)
2. Anthropic API key (for Claude Opus 4.7 + Claude Sonnet 4.6)
3. OpenAI API key (for GPT-5)

Set these in `.env` and re-run `scripts/smoke-t1-local.sh` with the `--llm` override to fan out into real cells. Multi-LLM × multi-harness × all-tier matrix runs land at `docs/runs/<future-date>/`.

## Reproducibility

```bash
cd ai-memory-discovery-gate
DISCOVERY_GATE_BINARY=../ai-memory-mcp/target/release/ai-memory \
    bash scripts/smoke-t1-local.sh
```

The smoke script is fully self-contained — needs only the v0.6.4 binary and the gate's own fixture. No Docker, no API keys, no daemon stand-up.

## Cell verdict (full)

See `cells/harness-pipeline-openclaw-t1-awareness-core.json` for the structured verdict and `cells/harness-pipeline-openclaw-t1-awareness-core.md` for the human-readable per-cell page.
