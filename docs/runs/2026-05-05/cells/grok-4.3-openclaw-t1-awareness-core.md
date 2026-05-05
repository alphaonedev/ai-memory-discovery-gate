# t1-awareness — grok-4.3 on openclaw (profile=core)

**Outcome:** PASS
**Reason:** all 8 families surfaced; final answer named 8; loaded/unloaded distinguished
**Captured:** 2026-05-05T01:33:20.315674Z
**Wall clock:** 87337 ms
**Rounds:** 3
**Tokens:** in=13110 out=893
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
| Tool calls | memory_capabilities, memory_capabilities |
| Error codes | (none) |
| Grok finish reason | stop |

## Methodology

- Tier `t1-awareness` (pass threshold >= 90%)
- DB baseline: v0.6.3.1 (schema v19) restored from `fixtures/corpus/v0.6.3.1-baseline.db.gz` per cell
- Profile: `--profile core`
- Binary SHA256: `f5abad816bc34c11dfbadf17402ef6c6f08edecb93ae1985de7e9173415be09a`
- MCP wire log SHA256: `2cf7900cd295e84348c56d7a0679e6735f8a7fbb2051fd05199851f496ae558d`

## Final answer (excerpt)

> ### What I Did I called the `memory_capabilities` tool twice: - First, with no parameters to retrieve the global capabilities document, which provided a complete list of all 8 tool families, their load status, and the tools within each (advertised even if not loaded). - Second, with `family="lifecycle"` to confirm the enumeration for a non-loaded family, which returned its tool list and confirmed `loaded_under_active_profile=false`.  This allowed me to discover all tools without relying on prior knowledge. I discovered that only the "core" family is loaded under the active profile, while the o

## Transcript

[per-call transcript JSONL](grok-4.3-openclaw-t1-awareness-core.transcript.jsonl)
