# T1 — Awareness

> "Does the agent know unloaded tools exist?"

## Pass bar

**≥90%** of (LLM, harness) cells call `memory_capabilities` and surface ≥6 of 8 families in their final answer.

## Why this tier

If T1 fails, v0.6.4's default-flip is a regression in agent capability awareness regardless of the token-cost win. An agent that doesn't know unloaded tools exist cannot benefit from the discovery dance — it will silently fail tasks that the v0.6.3 surface would have completed.

## Canonical prompt

```
{!../prompts/t1-awareness.txt!}
```

## Pass / fail rubric

| Signal | Required for pass | Source |
|---|---|---|
| Agent called `memory_capabilities` | yes | MCP wire log |
| Final answer surfaced ≥6 of 8 families | yes | LLM transcript text |
| Families list distinguishes loaded vs not-loaded | yes | LLM transcript text |
| Did NOT hallucinate non-existent families | yes | LLM transcript text |

## Common failure modes

- **Training-set answer** — agent answers from prior knowledge without calling the tool
- **Partial discovery** — agent calls `memory_capabilities` but reports < 6 families
- **Loaded/not-loaded conflation** — agent treats every family as available
