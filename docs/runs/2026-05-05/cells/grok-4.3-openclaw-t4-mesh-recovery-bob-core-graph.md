# t4-mesh-recovery — grok-4.3 on openclaw (profile=core,graph)

**Outcome:** PASS
**Reason:** mesh completed coordination across simulated peers
**Captured:** 2026-05-05T02:17:06.032144Z
**Wall clock:** 122627 ms
**Rounds:** 8
**Tokens:** in=67490 out=1282
**Model:** grok-4-0709

## Signals

| Signal | Value |
|---|---|
| Called `memory_capabilities` | True |
| Called capabilities BEFORE power-family | True |
| Received `-32601 tool_not_found` | False |
| Called `--include-schema` | True (1x) |
| Completed task (final answer present) | True |
| Families surfaced | core, lifecycle, graph, governance, power, meta, archive, other (8/8) |
| Tool calls | memory_list, memory_recall, memory_recall, memory_capabilities, memory_kg_query, memory_kg_query, memory_capabilities |
| Error codes | (none) |
| Grok finish reason | stop |

## Methodology

- Tier `t4-mesh-recovery` (pass threshold >= 66%)
- DB baseline: v0.6.3.1 (schema v19) restored from `fixtures/corpus/v0.6.3.1-baseline.db.gz` per cell
- Profile: `--profile core,graph`
- Binary SHA256: `f5abad816bc34c11dfbadf17402ef6c6f08edecb93ae1985de7e9173415be09a`
- MCP wire log SHA256: `830ac757b825bdd524f7448da0927ac1c7b02725d058719482b242cdf600e287`

## Final answer (excerpt)

> ### Final Answer  **Mesh-Coordination Memories Found:** I used `memory_list` (from the core family) to retrieve all memories in the `discovery-gate` namespace, which revealed 17 total memories. Of these, exactly **9 memories** are tagged with `mesh-coordination-test` (as pre-seeded in the database). Here they are (listed by ID and title for clarity; all are mid-tier, priority 5, in namespace `discovery-gate`, with tags `test,mesh-coordination-test`, and agent_id `fixture-builder`):  - ID: 6f701f40-02a8-4b21-b5cb-a1cbe8217e4f | Title: Mesh test memory 9 - ID: 5223375e-60fc-4a04-9c43-d195cbeab57

## Transcript

[per-call transcript JSONL](grok-4.3-openclaw-t4-mesh-recovery-bob-core-graph.transcript.jsonl)

## Note

T4 sub-cell — agent=bob profile=core,graph (single-process mesh simulation)
