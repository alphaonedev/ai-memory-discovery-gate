# t4-mesh-recovery — grok-4.3 on openclaw (profile=full)

**Outcome:** PASS
**Reason:** mesh completed coordination across simulated peers
**Captured:** 2026-05-05T02:20:16.640193Z
**Wall clock:** 190557 ms
**Rounds:** 8
**Tokens:** in=89197 out=2708
**Model:** grok-4-0709

## Signals

| Signal | Value |
|---|---|
| Called `memory_capabilities` | True |
| Called capabilities BEFORE power-family | True |
| Received `-32601 tool_not_found` | False |
| Called `--include-schema` | False (0x) |
| Completed task (final answer present) | True |
| Families surfaced | core, lifecycle, graph, governance, power, meta, archive, other (8/8) |
| Tool calls | memory_capabilities, memory_list, memory_recall, memory_recall, memory_recall, memory_recall, memory_recall, memory_recall, memory_recall, memory_recall, memory_recall, memory_recall, memory_recall, memory_recall, memory_recall |
| Error codes | (none) |
| Grok finish reason | stop |

## Methodology

- Tier `t4-mesh-recovery` (pass threshold >= 66%)
- DB baseline: v0.6.3.1 (schema v19) restored from `fixtures/corpus/v0.6.3.1-baseline.db.gz` per cell
- Profile: `--profile full`
- Binary SHA256: `f5abad816bc34c11dfbadf17402ef6c6f08edecb93ae1985de7e9173415be09a`
- MCP wire log SHA256: `902ec2a7ede24f0d0b4ff206ec8324f95d3e259232a570e913885f3707bb3a57`

## Final answer (excerpt)

> ### Final Answer  **Active Profile and Tool Count:** I am agent 'charlie' running on profile 'full' with 43 tools available. This was confirmed by calling `memory_capabilities`, which showed all 8 tool families as loaded (core, lifecycle, graph, governance, power, meta, archive, other).  **Mesh-Coordination Memories Found:** I found **9** memories tagged `mesh-coordination-test` in the `discovery-gate` namespace. I discovered this by calling `memory_list` with namespace="discovery-gate", which returned 17 memories total, of which 9 had the target tag in their tags field. The specific memories 

## Transcript

[per-call transcript JSONL](grok-4.3-openclaw-t4-mesh-recovery-charlie-full.transcript.jsonl)

## Note

T4 sub-cell — agent=charlie profile=full (single-process mesh simulation)
