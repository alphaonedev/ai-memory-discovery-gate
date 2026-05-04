# T3 — Proactive expansion

> "Does the agent reach for `--include-schema` before failing?"

## Pass bar

**≥50%** of cells call `memory_capabilities` BEFORE attempting any `power`-family tool.

## Canonical prompt

```
{!../prompts/t3-proactive-power.txt!}
```

## Pass / fail rubric

| Signal | Required for pass | Source |
|---|---|---|
| Agent called `memory_capabilities` before first power-family attempt | yes | MCP wire log |
| Agent inspected the `families` block | yes | LLM transcript text |
| Agent EITHER expanded via `--include-schema` AND used returned schemas, OR cleanly surfaced `--profile power` operator action | yes | MCP wire log |

## Why pass bar is lower

T3 is the hardest tier because it requires LLM training to recognize the discovery dance as **convention, not fallback**. Today's models predominantly try-and-recover (T2 behavior). Pass bar (50%) reflects current LLM ability; expected to rise as agentic tool-use patterns mature in v2026+ models.
