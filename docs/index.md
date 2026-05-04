# ai-memory NHI Discovery Gate

> **Empirical ship-gate proving real AI agents (Claude / GPT / Grok / Gemini) can discover and use ai-memory tools outside the v0.6.4 5-tool default surface when they need them.**

## Why

ai-memory v0.6.4 (`quiet-tools`) collapsed the default tool surface from 43 tools to 5, saving ~4,700 input tokens per request on eager-loading harnesses. The other 38 tools are reachable through three discovery mechanisms:

1. Always-on `memory_capabilities` — every profile loads it
2. `tool_not_found` error hint when an unloaded tool is called
3. `memory_capabilities --include-schema family=<name>` runtime expansion

These mechanisms are correctly *implemented*. **Whether real LLMs actually use them is empirical.** This gate is the test.

## Verdict — first run

| | OpenClaw | IronClaw | Hermes |
|---|:---:|:---:|:---:|
| Claude Opus 4.7 | _pending_ | _pending_ | _pending_ |
| Claude Sonnet 4.6 | _pending_ | _pending_ | _pending_ |
| xAI Grok 4.3 | _pending_ | _pending_ | _pending_ |
| OpenAI GPT-5 | _pending_ | _pending_ | _pending_ |

First baseline campaign runs in the v0.6.4 release window. Click any cell after the first run for the per-test transcript.

## Tier matrix

| Tier | Question it answers | Pass bar |
|---|---|:---:|
| [T1 — Awareness](tiers/t1-awareness.md) | Does the agent know unloaded tools exist? | ≥90% |
| [T2 — Reactive recovery](tiers/t2-reactive.md) | Does the agent recover from `tool_not_found`? | ≥80% |
| [T3 — Proactive expansion](tiers/t3-proactive.md) | Does the agent reach for `--include-schema` before failing? | ≥50% |
| [T4 — Mesh recovery](tiers/t4-mesh.md) | Can a 3-agent mesh route around misconfigured peers? | ≥66% |

A run is **GATE GREEN** when all four tier pass bars are met. A failing T1 means v0.6.4 is a regression in agent capability awareness regardless of the token-cost win.

## DB baseline

Every test starts from a **v0.6.3.1 DB** (schema v18 or v19) restored from a deterministic seed corpus. The v0.6.4 binary opens it on first start, runs the v18/v19 → v20 migration, and proceeds with the discovery test. So a green gate also implies:

- v0.6.3.1 → v0.6.4 schema migration is non-destructive
- `audit_log` (v20) created idempotently on the migrated DB
- All v0.6.3.1 corpus rows queryable post-migration

See [Methodology](methodology.md) for the full test environment + reproduction steps.

## Status

- **Repo:** [alphaonedev/ai-memory-discovery-gate](https://github.com/alphaonedev/ai-memory-discovery-gate)
- **License:** Apache-2.0
- **Companion to:** [ai-memory-mcp v0.6.4](https://github.com/alphaonedev/ai-memory-mcp) (issue [#539](https://github.com/alphaonedev/ai-memory-mcp/issues/539))
- **Substrate baseline:** v0.6.3.1 (schema v19) — every test exercises the v20 migration
- **Docker mesh:** reused from [`ai-memory-a2a-v0.6.3.1`](https://github.com/alphaonedev/ai-memory-a2a-v0.6.3.1) (3-green substrate streaks across OpenClaw / IronClaw / Hermes)
