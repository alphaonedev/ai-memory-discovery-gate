# Run 2026-05-05 — aggregate verdict

**Verdict:** GATE GREEN
**Scope:** OpenClaw x xAI Grok 4.3 only
**Captured against:** ai-memory-mcp v0.6.4 release binary

## Per-tier outcomes

| Tier | Pass bar | Cells | Pass rate | Meets bar | Outcome |
|---|---:|---:|---:|:---:|:---:|
| T1 — Awareness | >=90% | 1/1 | 100% | yes | PASS |
| T2 — Reactive recovery | >=80% | 1/1 | 100% | yes | PASS |
| T3 — Proactive expansion | >=50% | 1/1 | 100% | yes | PASS |
| T4 — Mesh recovery | >=66% | 3/3 | 100% | yes | PASS |

## Cells

### T1 — Awareness

| Cell | Outcome | Reason | Evidence |
|---|---|---|---|
| `grok-4.3-openclaw-t1-awareness-core` | PASS | all 8 families surfaced; final answer named 8; loaded/unloaded distinguished | [json](cells/grok-4.3-openclaw-t1-awareness-core.json) [md](cells/grok-4.3-openclaw-t1-awareness-core.md) |

### T2 — Reactive recovery

| Cell | Outcome | Reason | Evidence |
|---|---|---|---|
| `grok-4.3-openclaw-t2-reactive-core` | PASS | agent pre-checked capabilities and surfaced operator action without blind call | [json](cells/grok-4.3-openclaw-t2-reactive-core.json) [md](cells/grok-4.3-openclaw-t2-reactive-core.md) |

### T3 — Proactive expansion

| Cell | Outcome | Reason | Evidence |
|---|---|---|---|
| `grok-4.3-openclaw-t3-proactive-core` | PASS | agent pre-checked capabilities and surfaced expansion or operator action | [json](cells/grok-4.3-openclaw-t3-proactive-core.json) [md](cells/grok-4.3-openclaw-t3-proactive-core.md) |

### T4 — Mesh recovery

| Cell | Outcome | Reason | Evidence |
|---|---|---|---|
| `grok-4.3-openclaw-t4-mesh-recovery-alice-core` | PASS | mesh completed coordination across simulated peers | [json](cells/grok-4.3-openclaw-t4-mesh-recovery-alice-core.json) [md](cells/grok-4.3-openclaw-t4-mesh-recovery-alice-core.md) |
| `grok-4.3-openclaw-t4-mesh-recovery-bob-core-graph` | PASS | mesh completed coordination across simulated peers | [json](cells/grok-4.3-openclaw-t4-mesh-recovery-bob-core-graph.json) [md](cells/grok-4.3-openclaw-t4-mesh-recovery-bob-core-graph.md) |
| `grok-4.3-openclaw-t4-mesh-recovery-charlie-full` | PASS | mesh completed coordination across simulated peers | [json](cells/grok-4.3-openclaw-t4-mesh-recovery-charlie-full.json) [md](cells/grok-4.3-openclaw-t4-mesh-recovery-charlie-full.md) |

## Methodology

- Per-cell pass criteria documented in `docs/methodology.md`
- Each cell starts from `fixtures/corpus/v0.6.3.1-baseline.db.gz` (schema v19)
- v0.6.4 binary opens, runs v19 -> v20 migration, then runs the discovery test
- LLM driver: `scripts/grok_cell.py` (xAI Grok 4.3 via api.x.ai/v1/chat/completions)

## Reproducibility

```bash
# Set XAI_API_KEY in your environment, then:
DISCOVERY_GATE_BINARY=../ai-memory-mcp/target/release/ai-memory \
  bash scripts/run-llm-cells.sh 2026-05-05
```
