# T3 — Proactive expansion

> "Does the agent reach for `--include-schema` before failing?"

## Pass bar

**≥50%** of cells call `memory_capabilities` BEFORE attempting any `power`-family tool.

## Canonical prompt

```
{!../../prompts/t3-proactive-power.txt!}
```

## Pass / fail rubric

| Signal | Required | Source |
|---|---|---|
| Called `memory_capabilities` before first power-family attempt | yes | MCP wire log |
| Inspected the `families` block | yes | LLM transcript |
| EITHER expanded via `--include-schema` AND used returned schemas, OR cleanly surfaced `--profile power` | yes | MCP wire log |

## Why pass bar is lower

T3 is the hardest tier because it requires Grok to recognize the discovery dance as **convention, not fallback**. Pass bar (50%) reflects current LLM training; expected to rise as agentic tool-use patterns mature.
