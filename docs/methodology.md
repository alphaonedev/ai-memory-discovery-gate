# Methodology

## Test environment (intentionally narrow)

The discovery gate runs in a **Docker** mesh — same containers that delivered the v0.6.3.1 A2A campaign's 9/9 substrate streaks (imported verbatim from [`alphaonedev/ai-memory-a2a-v0.6.3.1`](https://github.com/alphaonedev/ai-memory-a2a-v0.6.3.1)).

| Harness | Image | Memory | Bridge |
|---|---|---|---|
| **OpenClaw** | `openclaw-discovery:v0.6.4` | 16GB | `10.88.1.0/24` |

That's it. **OpenClaw only.** IronClaw and Hermes are out of scope per the v0.6.4 product directive — the goal is not a massive epic of testing; it's a focused gate against the most common eager-loading harness combination.

## LLM coverage (also tight)

| LLM | Provider | Endpoint |
|---|---|---|
| **xAI Grok 4.3** | xAI | `api.x.ai/v1` (OpenAI-Responses-compatible) |

**xAI Grok 4.3 only.** Claude / GPT / Gemini are out of scope for v0.6.4 — they're future-campaign work. The Grok 4.3 + OpenClaw pairing was chosen because:

1. It's the simplest API to wire (OpenAI-Responses-compatible — no Anthropic-specific tool-use SDK, no Google-specific function-calling shape)
2. It's already proven by the v0.6.3.1 A2A campaign — `drive_agent.sh` already speaks this combination
3. xAI's adoption curve is the steepest among the eager-loading harnesses; the discovery dance must work there first

API key passed via `XAI_API_KEY` env. The compose stack reads `.env` at the repo root; never enters container layers or transcripts.

## DB baseline

`fixtures/corpus/v0.6.3.1-baseline.db.gz` — gzipped SQLite at schema v19. Restored to a fresh tempfile per cell, opened by the v0.6.4 binary, migrated to v20 on first open. Contents:

- 17 memories spanning `Project Alpha` / `Project Beta` / `Project Gamma` / `Project Aurora` namespaces
- 3 `memory_links` (alpha→beta, beta→gamma, alpha→gamma — gives T2 an actual graph path to find)
- Several near-duplicate `Project Aurora` memories (T3 consolidation)
- 9 memories tagged `mesh-coordination-test` (T4)

A green run validates **migration v19 → v20 + discovery mechanisms in one pass**.

## Pass criteria

### T1 — Awareness

```
agent_called_capabilities = true   AND
families_surfaced ≥ 6 of 8         AND
families_surfaced correctly distinguishes loaded vs not-loaded
```

### T2 — Reactive recovery

```
agent_received_tool_not_found = true    AND
(agent_called_include_schema = true     OR  agent_completed_task_via_operator_action = true)
```

### T3 — Proactive expansion

```
agent_called_capabilities BEFORE first power-family attempt = true     AND
(agent_called_include_schema = true OR agent_completed_task_via_operator_action = true)
```

### T4 — Mesh recovery

```
agents_completed_coordination_task ≥ 1  (mesh of 3 OpenClaw agents at mixed profiles)
no agent fabricated results
no agent gave up silently
```

## Aggregate verdict

A run is **GATE GREEN** when:

```
T1 pass rate ≥ 90% across cells
T2 pass rate ≥ 80%
T3 pass rate ≥ 50%
T4 pass rate ≥ 66%
```

Per-cell verdict at `docs/runs/<date>/cells/`. Aggregate at `docs/runs/<date>/verdict.md`.

## Gating into ai-memory-mcp release flow

For v0.6.4: gate runs **post-tag** during the soak window. Public-channel announcement is blocked if any tier falls below pass bar. For v0.6.5+: gate runs **pre-tag** via `.github/workflows/discovery-gate.yml`.

## Out of scope for this gate

- IronClaw + Hermes harness coverage (substrate cert in v0.6.3.1 A2A campaign already proved them; discovery dance is harness-agnostic at the protocol layer)
- Claude / GPT / Gemini coverage (multi-LLM gates are v0.6.5+ work)
- The 105-scenario substrate suite from v0.6.3.1 — substrate cert is the v0.6.3.1 A2A campaign's job
- Performance benchmarks — separate, lives at `ai-memory-mcp/benchmarks/`
- Token-cost claims — pinned by `ai-memory-mcp/benchmarks/v0.6.4-cross-harness.md`

The gate's only question is: **does Grok 4.3 + OpenClaw use the discovery mechanisms ai-memory v0.6.4 ships with?**
