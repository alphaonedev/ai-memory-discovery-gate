# Runs

Per-campaign verdict pages land here. First baseline run will appear under `<YYYY-MM-DD>/verdict.md` after the v0.6.4 ship window.

## Run history

| Date | Verdict | Notes |
|---|---|---|
| [2026-05-04](2026-05-04/verdict.md) | ✅ HARNESS-PIPELINE GREEN | First baseline run. Validates fixture restore + v19→v20 migration + MCP stdio + capabilities parsing + verdict scoring. LLM cells pending API credentials. |

## Per-cell evidence

Each campaign produces one markdown file per (LLM, harness, tier, profile) cell at:

```
runs/<date>/cells/<llm>-<harness>-<tier>-<profile>.md
```

Plus a machine-readable `verdict.json` with the aggregate verdict for the campaign.
