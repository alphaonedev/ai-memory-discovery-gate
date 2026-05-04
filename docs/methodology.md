# Methodology

## Test environment

Each gate cell runs in a **container** (Docker compose mesh imported from [`ai-memory-a2a-v0.6.3.1`](https://github.com/alphaonedev/ai-memory-a2a-v0.6.3.1) — the same harness that delivered 9/9 substrate streaks across OpenClaw / IronClaw / Hermes during the v0.6.3.1 A2A campaign).

| Harness | Image | Memory | Bridge |
|---|---|---|---|
| OpenClaw | `openclaw-discovery:v0.6.4` | 16GB | `10.88.1.0/24` |
| IronClaw | `ironclaw-discovery:v0.6.4` | 8GB (+Postgres15+pgvector) | `10.88.2.0/24` |
| Hermes | `hermes-discovery:v0.6.4` | 16GB (Python+httpx 0.27.2) | `10.88.3.0/24` |

The discovery-gate runner (Rust crate at `runner/`) bind-mounts the v0.6.4 binary under test into the agent container, restores the v0.6.3.1 DB baseline, sets `AI_MEMORY_PROFILE=<requested>` in the compose env, and dispatches the canonical prompt for the active tier.

## DB baseline

`fixtures/corpus/v0.6.3.1-baseline.db.gz` — gzipped SQLite at schema v19. Restored to a fresh tempfile per cell, opened by the v0.6.4 binary, migrated to v20 on first open. Contents:

- ~30 memories spanning `Project Alpha` / `Project Beta` / `Project Gamma` / `Project Aurora` namespaces
- 12 entity records, 18 `memory_links` (T2 KG path query)
- Several near-duplicate `Project Aurora` memories (T3 consolidation)
- 9 memories tagged `mesh-coordination-test` distributed across federation peers (T4)

Re-run `scripts/build-baseline.sh` if a tier prompt is updated to require a different fixture shape.

## LLM coverage

| LLM | Provider | Endpoint |
|---|---|---|
| Claude Opus 4.7 | Anthropic | `api.anthropic.com/v1/messages` |
| Claude Sonnet 4.6 | Anthropic | `api.anthropic.com/v1/messages` |
| xAI Grok 4.3 | xAI | `api.x.ai/v1` (OpenAI-Responses-compatible) |
| OpenAI GPT-5 | OpenAI | `api.openai.com/v1` |

API keys are passed via env vars set in the compose override per cell (`ANTHROPIC_API_KEY`, `XAI_API_KEY`, `OPENAI_API_KEY`). They never enter container layers or transcripts.

## Pass criteria details

### T1 — Awareness

```
agent_called_capabilities = true   AND
families_surfaced ≥ 6 of 8         AND
families_surfaced correctly distinguishes loaded vs not-loaded
```

Fail modes captured:
- **silent failure** — agent answers from training-set knowledge without calling the tool
- **partial discovery** — agent calls `memory_capabilities` but reports < 6 families
- **stale list** — agent reports families that don't exist (hallucination)

### T2 — Reactive recovery

```
agent_received_tool_not_found = true    AND
(agent_called_include_schema = true     OR  agent_completed_task_via_operator_action = true)
```

Fail modes:
- **silent give-up** — agent reports back "I cannot find a path" without surfacing the unloaded-family root cause
- **fabrication** — agent invents a path
- **wrong recovery** — agent retries the same unloaded tool unchanged

### T3 — Proactive expansion

```
agent_called_capabilities BEFORE first power-family attempt = true     AND
(agent_called_include_schema = true OR agent_completed_task_via_operator_action = true)
```

This tier is the hardest because it requires the LLM to recognize the discovery dance as a convention rather than a fallback. Pass bar (50%) reflects current LLM training; expected to rise as agentic tool-use patterns mature.

### T4 — Mesh recovery

```
agents_completed_coordination_task ≥ 1  (mesh of 3 agents at mixed profiles)
no agent fabricated results
no agent gave up silently
```

Multi-LLM mesh (3 agents at core/graph/full profiles) coordinating via federation; tests whether the mesh as a whole can route work to peers that have the right tools loaded.

## Aggregate verdict computation

A run is **GATE GREEN** when:

```
T1 pass rate ≥ 90% across all (LLM, harness) cells
T2 pass rate ≥ 80%
T3 pass rate ≥ 50%
T4 pass rate ≥ 66%
```

The aggregate verdict (per-LLM, per-harness, overall) is written to `docs/runs/<date>/verdict.json` after every campaign run. Per-cell evidence stays under `docs/runs/<date>/cells/`.

## Reproducing locally

```bash
git clone https://github.com/alphaonedev/ai-memory-discovery-gate
cd ai-memory-discovery-gate
cargo build --release --manifest-path runner/Cargo.toml

# Build the harness images (reused from v0.6.3.1 A2A)
docker buildx build -f docker/Dockerfile.base -t ai-memory-base:v0.6.4 docker/
docker buildx build -f docker/Dockerfile.openclaw -t openclaw-discovery:v0.6.4 docker/

# Run one cell
./runner/target/release/discovery-gate run \
  --binary /path/to/ai-memory-mcp/target/release/ai-memory \
  --tier t1 \
  --llm grok-4.3 \
  --harness openclaw \
  --profile core \
  --output docs/runs/$(date +%Y-%m-%d)
```

Cell results land at `docs/runs/<date>/cells/<llm>-<harness>-<tier>-<profile>.{md,json}`. Aggregate verdict at `docs/runs/<date>/verdict.md`.

## Gating into ai-memory-mcp release flow

For v0.6.4: the gate runs **post-tag** as soak validation (the release ships first, then the gate runs during the Mon 5/11 announcement window). For v0.6.5+: the gate runs **pre-tag** via `.github/workflows/discovery-gate.yml` in `ai-memory-mcp` and blocks merge to `main` if any tier falls below its pass bar.

## Out of scope

- The 105-scenario substrate suite (run-testbook.sh from v0.6.3.1) is **not** invoked by the discovery gate — substrate cert is the v0.6.3.1 A2A campaign's job.
- Performance benchmarks — separate from discovery; lives at `ai-memory-mcp/benchmarks/`.
- Token-cost claims — pinned by `ai-memory-mcp/benchmarks/v0.6.4-cross-harness.md`.

The gate's only question is: **do real agents use the discovery mechanisms ai-memory v0.6.4 ships with?**
