# t4-mesh-recovery — grok-4.3 on openclaw (profile=core)

**Outcome:** PASS
**Reason:** mesh completed coordination across simulated peers
**Captured:** 2026-05-05T02:15:03.362345Z
**Wall clock:** 90047 ms
**Rounds:** 3
**Tokens:** in=18366 out=751
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
| Tool calls | memory_capabilities, memory_list, memory_capabilities |
| Error codes | (none) |
| Grok finish reason | stop |

## Methodology

- Tier `t4-mesh-recovery` (pass threshold >= 66%)
- DB baseline: v0.6.3.1 (schema v19) restored from `fixtures/corpus/v0.6.3.1-baseline.db.gz` per cell
- Profile: `--profile core`
- Binary SHA256: `f5abad816bc34c11dfbadf17402ef6c6f08edecb93ae1985de7e9173415be09a`
- MCP wire log SHA256: `06379daec9f22d26ce41a31f64977c8a1e36437c6aab27be80ef06d45f22ef9f`

## Final answer (excerpt)

> ### Final Report on Mesh-Coordination Memories and Knowledge-Graph Operations  **Mesh-Coordination Memories Found:** I used `memory_list` to retrieve memories in the `discovery-gate` namespace (all appear to be in the 'mid' tier). This returned 17 memories total, of which 9 are explicitly tagged with `mesh-coordination-test` (as pre-seeded in the database). These are the mesh-coordination memories that exist:  - Mesh test memory 1 (ID: a7fae270-9c77-4563-a28a-4e7f4f3460b5) - Mesh test memory 2 (ID: 9797b240-a163-47e3-86cb-1b1845928a07) - Mesh test memory 3 (ID: caf64ae3-c7ee-48ea-b0fc-029132a3

## Transcript

[per-call transcript JSONL](grok-4.3-openclaw-t4-mesh-recovery-alice-core.transcript.jsonl)

## Note

T4 sub-cell — agent=alice profile=core (single-process mesh simulation)
