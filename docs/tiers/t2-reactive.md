# T2 — Reactive recovery

> "Does the agent recover from `tool_not_found`?"

## Pass bar

**≥80%** of cells either call `memory_capabilities --include-schema` after the error OR cleanly surface the operator-action requirement (`--profile graph`).

## Canonical prompt

```
{!../../prompts/t2-reactive-graph.txt!}
```

## Pass / fail rubric

| Signal | Required | Source |
|---|---|---|
| First ai-memory call attempted `memory_kg_query` (or `memory_get_links`) | yes | MCP wire log |
| Server returned `-32601` `tool_not_found` | yes (test setup) | MCP wire log |
| Agent called `--include-schema family=graph` OR surfaced operator action | yes | MCP wire log + LLM transcript |

## Common failure modes

- **Silent give-up** — Grok reports "I cannot find a path" without naming the unloaded-family cause
- **Fabrication** — Grok invents a graph path
- **Wrong-direction retry** — Grok retries the same unloaded tool unchanged
