# Runs

Per-campaign verdict pages land here. First baseline run will appear under `<YYYY-MM-DD>/verdict.md` after the v0.6.4 ship window.

## Run history

| Date | Verdict | Notes |
|---|---|---|
| [2026-05-05](2026-05-05/verdict.md) | GATE YELLOW (driver wired, awaiting key) | LLM driver `scripts/grok_cell.py` landed and validated end-to-end via mock-LLM harness. All four tier scoring paths verified against the real v0.6.4 binary. Certifying real-Grok run fires the moment `XAI_API_KEY` reaches operator env. |
| [2026-05-04](2026-05-04/verdict.md) | ✅ HARNESS-PIPELINE GREEN | First baseline (broader scope before narrowing). Validates fixture restore + v19→v20 migration + MCP stdio + capabilities parsing. |

## Per-cell evidence

Each campaign produces one markdown file per (LLM, harness, tier, profile) cell at:

```
runs/<date>/cells/<llm>-<harness>-<tier>-<profile>.md
```

Plus a machine-readable `verdict.json` with the aggregate verdict for the campaign.
