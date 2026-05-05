# ai-memory-discovery-gate

[![Gate](https://img.shields.io/badge/v0.6.4_gate-pending_real_run-yellow)]()
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![DB](https://img.shields.io/badge/DB_baseline-v0.6.3.1_(schema_v19)-6ee7ff)]()
[![Scope](https://img.shields.io/badge/scope-OpenClaw_×_xAI_Grok_4.3-deep--purple)]()

**Empirical ship-gate that proves AI NHI agents (xAI Grok 4.3 driven through OpenClaw) can discover and use ai-memory tools outside the v0.6.4 5-tool default surface when they need them.**

## Why this gate exists

ai-memory v0.6.4 (`quiet-tools`) collapses the default tool surface from 43 to 5 tools and gates the rest behind:

1. **Always-on `memory_capabilities`** — every profile loads it; agent calls it to discover the 8 families
2. **`tool_not_found` error hint** — calling an unloaded tool returns `-32601` with an actionable suggestion
3. **`memory_capabilities --include-schema family=<f>` runtime expansion** — agent or host registers the missing schemas without a server restart

These mechanisms are correctly *implemented* in v0.6.4. **Whether xAI Grok 4.3 actually NOTICES them and uses them is empirical, not architectural.** This repo is the empirical test.

## Scope (intentionally tight)

| Dimension | In scope | Out of scope |
|---|---|---|
| **Harness** | OpenClaw only | IronClaw, Hermes |
| **LLM** | xAI Grok 4.3 only | Claude Opus / Sonnet, OpenAI GPT-5, Gemini |
| **DB baseline** | v0.6.3.1 (schema v19) | other versions |
| **Tiers** | T1 awareness, T2 reactive, T3 proactive, T4 mesh | none |
| **Profiles** | core (default), graph, full, custom | admin, power (covered transitively) |

This is **not** a "massive epic of testing" — it's a focused gate that answers one question: *can a Grok-driven OpenClaw agent use the v0.6.4 discovery dance?* If yes, the v0.6.4 ship is empirically validated for the most common eager-loading harness combination. If no, v0.6.4 needs sharper system-prompt education before public announcement.

## Verdict (latest run)

| Tier | Pass bar | Outcome |
|---|---|---|
| T1 — Awareness | ≥90% calls succeed | _pending_ |
| T2 — Reactive recovery | ≥80% recover | _pending_ |
| T3 — Proactive expansion | ≥50% pre-check | _pending_ |
| T4 — Mesh recovery | ≥66% mesh complete | _pending_ |

A run is **GATE GREEN** when all four pass bars are met. Click any cell after the first run for the per-test transcript.

## DB baseline

Every test starts from a **v0.6.3.1 DB** (schema v19) restored from a deterministic seed corpus (17 memories spanning Project Alpha/Beta/Gamma + Aurora consolidation candidates + 9 mesh-coordination memories; 3 graph links). The v0.6.4 binary opens it on first start, runs the v19 → v20 migration, and proceeds with the discovery test.

So a green gate also implies:

- v0.6.3.1 → v0.6.4 schema migration is non-destructive
- `audit_log` (v20) created idempotently on the migrated DB
- All v0.6.3.1 corpus rows queryable post-migration

Fixture: `fixtures/corpus/v0.6.3.1-baseline.db.gz` (7,601 bytes).

## How to run

The runner is Docker-based (per user directive — reuses the OpenClaw harness from `alphaonedev/ai-memory-a2a-v0.6.3.1` that delivered 9/9 substrate streaks).

```bash
# 1. Build the OpenClaw image with v0.6.4 binary baked in
docker buildx build -f docker/Dockerfile.base -t ai-memory-base:v0.6.4 .
docker buildx build -f docker/Dockerfile.openclaw -t openclaw-discovery:v0.6.4 docker/

# 2. Drop your xAI API key into .env
echo "XAI_API_KEY=xai-..." > .env

# 3. Run the gate
./runner/target/release/discovery-gate run \
  --binary ../ai-memory-mcp/target/release/ai-memory \
  --tier all \
  --llm grok-4.3 \
  --harness openclaw \
  --output docs/runs/$(date +%Y-%m-%d)
```

Or for the no-LLM-credentials harness-pipeline smoke test:

```bash
DISCOVERY_GATE_BINARY=../ai-memory-mcp/target/release/ai-memory \
    bash scripts/smoke-t1-local.sh
```

## Repo layout

```
ai-memory-discovery-gate/
├── README.md                        # this file
├── LICENSE                          # Apache-2.0
├── prompts/                         # 4 canonical immutable tier prompts
├── runner/                          # Rust crate; orchestrates Docker mesh
├── fixtures/
│   ├── corpus/                      # v0.6.3.1 seed DBs
│   └── allowlists/                  # config.toml allowlist fixtures (T4)
├── docker/                          # OpenClaw mesh (imported from
│   │                                # ai-memory-a2a-v0.6.3.1)
│   ├── Dockerfile.base
│   ├── Dockerfile.openclaw
│   ├── docker-compose.openclaw.yml  # 4-node mesh, bridge 10.88.1.0/24
│   ├── entrypoint.sh
│   ├── drive_agent.sh               # xAI Grok 4.3 driver
│   ├── gen-tls.sh
│   ├── healthcheck.sh
│   └── run-testbook.sh
├── docs/                            # GitHub Pages source
├── scripts/
│   └── smoke-t1-local.sh            # no-LLM smoke test (no Docker, no key)
└── .github/workflows/pages.yml      # Pages publish on push to main
```

## Companion to v0.6.4

- Ships in the v0.6.4 release window
- Verdict from the first **real LLM-driven** campaign blocks the v0.6.4 public-channel announcement if any tier falls below pass bar
- The harness-pipeline smoke run already validates the non-LLM portion of the pipeline (DB restore + v19→v20 migration + MCP stdio + capabilities parsing + verdict scoring)
- Tracked in [`alphaonedev/ai-memory-mcp` issue #539](https://github.com/alphaonedev/ai-memory-mcp/issues/539)

## License

Apache-2.0 — same as ai-memory-mcp.
