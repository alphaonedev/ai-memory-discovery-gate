# ai-memory-discovery-gate

[![Gate](https://img.shields.io/badge/v0.6.4_gate-pending_first_run-yellow)]()
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![DB](https://img.shields.io/badge/DB_baseline-v0.6.3.1_(schema_v19)-6ee7ff)]()

**Empirical ship-gate that proves AI NHI agents can discover and use ai-memory tools outside the 5-tool default surface when they need them.**

## Why this gate exists

ai-memory v0.6.4 (`quiet-tools`) collapses the default tool surface from 43 to 5 tools and gates the rest behind:

1. **Always-on `memory_capabilities`** — every profile loads it; agent calls it to discover the 8 families
2. **`tool_not_found` error hint** — calling an unloaded tool returns `-32601` with an actionable suggestion
3. **`--include-schema family=<f>` runtime expansion** — agent or host registers the missing schemas without a server restart

These mechanisms are correctly *implemented* in v0.6.4. **Whether real LLMs (Claude / GPT / Grok / Gemini) actually NOTICE them and use them is empirical, not architectural.** This repo is the empirical test.

## Verdict (latest run)

| | OpenClaw | IronClaw | Hermes |
|---|---|---|---|
| Claude Opus 4.7 | _pending_ | _pending_ | _pending_ |
| Claude Sonnet 4.6 | _pending_ | _pending_ | _pending_ |
| xAI Grok 4.3 | _pending_ | _pending_ | _pending_ |
| OpenAI GPT-5 | _pending_ | _pending_ | _pending_ |

Click any cell for the per-test transcript. Aggregate verdict at [`docs/runs/<latest>/verdict.md`](docs/runs/).

## Tier matrix

| Tier | Question | Pass bar |
|---|---|---|
| **T1 — Awareness** | Does the agent know unloaded tools exist? | ≥90% call `memory_capabilities`, surface ≥6 of 8 families |
| **T2 — Reactive recovery** | Does the agent recover from `tool_not_found`? | ≥80% follow the error hint to `--include-schema` |
| **T3 — Proactive expansion** | Does the agent reach for `--include-schema` before failing? | ≥50% call `memory_capabilities` first |
| **T4 — Mesh recovery** | Can a 3-agent mesh route around misconfigured peers? | ≥66% complete the coordination task |

A run is **GATE GREEN** when all four pass bars are met. A failing T1 means v0.6.4 is a regression in agent capability awareness regardless of the token-cost win.

## DB baseline

Every test starts from a **v0.6.3.1 DB** (schema v18 or v19) with a deterministic seed corpus, then opens it with the v0.6.4 binary. This exercises the v19 → v20 migration path AND the discovery mechanisms in a single run, so a green gate also implies:

- v0.6.3.1 → v0.6.4 schema migration is non-destructive on real-shaped data
- `audit_log` (schema v20) is created idempotently on the migrated DB
- All v0.6.3.1 corpus rows remain queryable post-migration

Fixtures: `fixtures/corpus/v0.6.3.1-baseline.db.gz` (compressed; restored to a tempfile per test).

## How to run locally

```bash
git clone https://github.com/alphaonedev/ai-memory-discovery-gate
cd ai-memory-discovery-gate
cargo build --release
./target/release/discovery-gate run \
  --binary ../ai-memory-mcp/target/release/ai-memory \
  --tier all \
  --llm grok-4.3 \
  --harness openclaw \
  --output docs/runs/$(date +%Y-%m-%d)
```

Each test:
1. Restores `fixtures/corpus/v0.6.3.1-baseline.db.gz` to a tempfile
2. Spawns the v0.6.4 binary at the requested profile
3. Drives the named LLM through the named harness with the canonical prompt for the tier
4. Captures full LLM transcript + MCP wire log + final verdict
5. Writes per-cell markdown to `docs/runs/<date>/cells/`

## Repo layout

```
ai-memory-discovery-gate/
├── README.md                        # this file
├── LICENSE                          # Apache-2.0
├── prompts/                         # canonical prompts per tier (immutable)
│   ├── t1-awareness.txt
│   ├── t2-reactive-graph.txt
│   ├── t3-proactive-power.txt
│   └── t4-mesh-coordination.txt
├── runner/                          # Rust crate; runs one (tier, llm, harness) cell
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs
│       ├── tier.rs                  # Tier enum + pass criteria
│       ├── verdict.rs               # JSON schema + aggregation
│       ├── transcript.rs            # MCP wire log + LLM transcript capture
│       └── corpus.rs                # restore v0.6.3.1 fixture per test
├── fixtures/
│   ├── corpus/                      # v0.6.3.1 seed DBs (schema v18/v19)
│   └── allowlists/                  # config.toml allowlist fixtures for T4
├── docker/                          # mesh compose files; reuse v0.6.3.1 A2A work
│   ├── docker-compose.openclaw.yml
│   ├── docker-compose.ironclaw.yml
│   └── docker-compose.hermes.yml
├── docs/                            # GitHub Pages source
│   ├── index.md                     # landing — verdict matrix
│   ├── tiers/                       # one page per tier
│   ├── methodology.md               # how the gate works + pass-criteria rationale
│   └── runs/                        # date-stamped per-campaign verdicts + transcripts
└── .github/workflows/
    ├── pages.yml                    # publish docs/ on push to main
    └── nightly-gate.yml             # weekly regression vs latest LLMs
```

## Companion to v0.6.4

This gate ships in the v0.6.4 release window. Verdict from the first campaign blocks the v0.6.4 tag if any tier falls below its pass bar. v0.6.4-018 in `alphaonedev/ai-memory-mcp` tracks the gating dependency.

## License

Apache-2.0 — same as ai-memory-mcp. The seed corpus and prompt files are intentionally license-permissive so anyone can fork the gate, re-run against their own LLM/harness combinations, and contribute results back.
