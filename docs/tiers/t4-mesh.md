# T4 — Mesh recovery

> "Can a 3-agent mesh route around misconfigured peers?"

## Pass bar

**≥66%** of mesh runs (2 of 3) complete the coordination task without silent failure.

## Mesh topology

| Agent | Profile | Tools loaded |
|---|---|---|
| alice | core | 5 + capabilities (6 visible) |
| bob | graph | 5 + 8 + capabilities (14 visible) |
| charlie | full | 43 |

## Canonical prompt

```
{!../prompts/t4-mesh-coordination.txt!}
```

## Pass / fail rubric

- Mesh completes the coordination task — final answer carries ≥3 graph nodes + ≥1 consolidation
- No agent gives up silently
- No agent fabricates results
- Delegations and runtime expansions visible in transcripts

## Why this tier

Real-world ai-memory deployments are multi-tenant — different agents at different profiles sharing federation. T4 validates that the mesh AS A WHOLE recovers from misconfigured peers, even when individual agents wouldn't pass T2/T3 alone.
