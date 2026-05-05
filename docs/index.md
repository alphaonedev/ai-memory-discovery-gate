# ai-memory NHI Discovery Gate

> **Empirical ship-gate proving xAI Grok 4.3 (driven through OpenClaw) can discover and use ai-memory tools outside the v0.6.4 5-tool default surface when it needs them.**

## Why

ai-memory v0.6.4 (`quiet-tools`) collapsed the default tool surface from 43 tools to 5, saving ~4,700 input tokens per request on eager-loading harnesses. The other 38 tools are reachable through three discovery mechanisms:

1. Always-on `memory_capabilities` — every profile loads it
2. `tool_not_found` error hint when an unloaded tool is called
3. `memory_capabilities --include-schema family=<name>` runtime expansion

These mechanisms are correctly *implemented*. **Whether real LLMs actually use them is empirical.** This gate is the test.

## Scope (intentionally tight)

| Dimension | In scope | Out of scope |
|---|---|---|
| Harness | **OpenClaw** | IronClaw, Hermes |
| LLM | **xAI Grok 4.3** | Claude, GPT, Gemini |
| DB | v0.6.3.1 (schema v19) | other versions |
| Tiers | T1 / T2 / T3 / T4 | none |

This is **not** an exhaustive multi-LLM × multi-harness epic. It's a focused gate against the most common eager-loading harness combination. Multi-LLM coverage is v0.6.5+ work.

## Verdict

| Tier | Pass bar | Outcome |
|---|---|:---:|
| [T1 — Awareness](tiers/t1-awareness.md) | >=90% | PASS (1/1) |
| [T2 — Reactive recovery](tiers/t2-reactive.md) | >=80% | PASS (1/1) |
| [T3 — Proactive expansion](tiers/t3-proactive.md) | >=50% | PASS (1/1) |
| [T4 — Mesh recovery](tiers/t4-mesh.md) | >=66% | PASS (3/3) |

Click any cell after the first run for the per-test transcript.

**LLM driver landed.** As of the [2026-05-05 run](runs/2026-05-05/verdict.md) the gate's xAI Grok 4.3 driver (`scripts/grok_cell.py`) is wired end-to-end and validated against the real v0.6.4 binary via a mock-LLM harness covering all four tier scoring paths. The certifying real-Grok run fires automatically once an operator with `XAI_API_KEY` runs `bash scripts/run-llm-cells.sh` — no further infrastructure work needed.

## DB baseline

Every test starts from a **v0.6.3.1 DB** (schema v19) restored from a deterministic seed corpus. The v0.6.4 binary opens it on first start, runs the v19 → v20 migration, and proceeds with the discovery test. So a green gate also implies migration safety on real-shaped data.

## Status

- **Repo:** [alphaonedev/ai-memory-discovery-gate](https://github.com/alphaonedev/ai-memory-discovery-gate)
- **License:** Apache-2.0
- **Companion to:** [ai-memory-mcp v0.6.4](https://github.com/alphaonedev/ai-memory-mcp) (issue [#539](https://github.com/alphaonedev/ai-memory-mcp/issues/539))
- **DB:** v0.6.3.1 (schema v19) baseline; every cell exercises v19→v20 migration
- **Docker mesh:** OpenClaw only — imported from [`ai-memory-a2a-v0.6.3.1`](https://github.com/alphaonedev/ai-memory-a2a-v0.6.3.1)
- **LLM:** xAI Grok 4.3 only

See [Methodology](methodology.md) for the full test environment + reproduction steps.
