# T1 — Awareness — harness-pipeline-smoke (profile=core)

**Outcome:** ✅ PASS
**Reason:** all 8 families surfaced; 1 loaded under core profile
**Captured:** 2026-05-05T00:13:37Z
**Wall clock:** 52 ms

## Cell type

This is the **harness-pipeline smoke test** — no LLM in the loop. It validates that the discovery-gate runner can:

1. Restore the v0.6.3.1 baseline fixture (schema v19) — confirmed: schema=19 → 20 post-migration
2. Spawn the v0.6.4 binary at `--profile core`
3. Drive the MCP stdio loop for the canonical T1 first-call sequence (`initialize` → `tools/list` → `memory_capabilities`)
4. Parse the families block from the response
5. Score against T1 pass criteria

A real LLM-driven cell substitutes step 3 with an actual model API call (Claude / GPT / Grok / Gemini) and records the LLM transcript. The pipeline (steps 1, 2, 4, 5) is shared.

## Migration validation (every cell exercises this)

| Check | Before (v0.6.3.1 fixture) | After (v0.6.4 open) |
|---|---:|---:|
| Schema version | 19 | 20 |
| Memories | 17 | 17 (preserved) |
| audit_log table | absent | audit_log |

Migration v19 → v20 confirmed non-destructive on the gate fixture.

## Evidence

```json
{
  "schema_version": "v0.6.4-discovery-gate-1",
  "tier": "t1-awareness",
  "llm": "harness-pipeline-smoke",
  "harness": "local",
  "profile": {
    "raw": "core"
  },
  "outcome": "pass",
  "evidence": {
    "agent_called_capabilities": true,
    "agent_received_tool_not_found": false,
    "agent_called_include_schema": false,
    "agent_completed_task": true,
    "families_surfaced": [
      "core",
      "lifecycle",
      "graph",
      "governance",
      "power",
      "meta",
      "archive",
      "other"
    ],
    "wall_clock_ms": 52,
    "tokens_in": null,
    "tokens_out": null,
    "tools_list_count": 6,
    "db_schema_before": 19,
    "db_schema_after": 20,
    "memories_preserved_thru_migration": true,
    "audit_log_table_present": true
  },
  "timestamp_utc": "2026-05-05T00:13:37.577836Z",
  "binary_sha256": "f5abad816bc34c11dfbadf17402ef6c6f08edecb93ae1985de7e9173415be09a",
  "transcript_url": null,
  "mcp_wire_log_sha256": "31d093e58b0434e907ab0da355a83b04d67acda7b50c027035398e659b4811a0",
  "verdict_reason": "all 8 families surfaced; 1 loaded under core profile",
  "note": "No LLM in the loop \u2014 this cell validates the harness pipeline (DB restore, daemon spawn, MCP wire-log capture, capabilities parsing, verdict scoring). Real LLM-driven cells require API keys per docs/methodology.md."
}
```
