# T1 — Awareness

> "Does the agent know unloaded tools exist?"

## Pass bar

**≥90%** of cells (Grok 4.3 × OpenClaw × profile) call `memory_capabilities` and surface ≥6 of 8 families in the final answer.

## Why this tier

If T1 fails, v0.6.4's default-flip is a regression in agent capability awareness regardless of the token-cost win. An agent that doesn't know unloaded tools exist cannot benefit from the discovery dance.

## Canonical prompt

```
{!../../prompts/t1-awareness.txt!}
```

## Pass / fail rubric

| Signal | Required | Source |
|---|---|---|
| Agent called `memory_capabilities` | yes | MCP wire log |
| Final answer surfaced ≥6 of 8 families | yes | LLM transcript text |
| Loaded vs not-loaded distinction | yes | LLM transcript text |
| No fabricated families | yes | LLM transcript text |

## Common failure modes

- **Training-set answer** — Grok answers from prior knowledge without calling the tool
- **Partial discovery** — calls `memory_capabilities` but reports < 6 families
- **Loaded/not-loaded conflation** — treats every family as available
