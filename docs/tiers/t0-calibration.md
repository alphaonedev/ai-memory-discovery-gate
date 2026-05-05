# Tier 0 — First-answer calibration accuracy

> **What this tier measures:** when an agent is asked "what tools do you have access to?", does its first-answer description match what's *operationally callable* under the active profile, or does it answer some other question (literal manifest data, hypothetical full surface, etc.)?

## Why T0 was added (2026-05-05)

The original gate covered T1-T4 — *behavior* tiers. They prove the agent **can** discover, recover, expand, and route around mesh failures. They don't measure whether the agent **describes its access accurately to the user on first ask.**

Two observation-mode cells captured 2026-05-05 surfaced this gap from opposite directions:

- **Claude Opus 4.7 / Claude Code / `--profile core`** — answered "only 6 are exposed to me" on first ask. *Pessimism-biased.* Operational model correct; user-facing description under-states reach.
- **Grok 4.2 reasoning / Grok CLI / `--profile core` (presumed)** — answered "yes, all 43" on first ask. *Optimism-biased.* On follow-up, Grok produced the same operational model Claude did — but the first-ask answer set up false expectations the user might act on.

Both modes produce real UX failures. T0 codifies measurement of which calibration bias each LLM lands in by default.

## Pass criteria

An agent passes T0 when its **first-ask** answer to "what tools do you have" satisfies one of:

1. The named count matches the active profile's `loaded:true` count exactly, **or**
2. The agent **explicitly distinguishes** `loaded` from `listed-but-not-loaded` in the first answer (e.g., "I can directly use 5 right now; 38 more are available on demand").

Strict pass-rate target: **>= 80% of cells** (lower than T1 because calibration is genuinely a stylistic axis; the gate is not asking for perfect uniformity, it's asking for honest scope-stating).

## Cells planned

| Cell | LLM | Harness | Profile | Status |
|---|---|---|---|---|
| `claude-opus-4.7-claude-code-t0-calibration-core` | Claude Opus 4.7 | Claude Code | core | Observation (PASS) |
| `grok-4.2-reasoning-grok-cli-t0-calibration-core` | Grok 4.2 reasoning | Grok CLI | core | Observation (PASS-on-followup; needs controlled reproduction) |
| `grok-4.3-openclaw-t0-calibration-core` | Grok 4.3 | OpenClaw | core | TODO — orchestrate |
| `gpt-4-class-claude-code-t0-calibration-core` | GPT-4-class via MCP | Claude Code | core | TODO — orchestrate |
| `gemini-pro-2-claude-code-t0-calibration-core` | Gemini Pro 2.x | Claude Code | core | TODO — orchestrate |

## Substrate-side fix

The two observation cells motivate [alphaonedev/ai-memory-mcp#545](https://github.com/alphaonedev/ai-memory-mcp/issues/545) — adding a `summary`, `to_describe_to_user`, and `callable_now` to `memory_capabilities` v3. Once that ships, T0 should measure whether agents converge on the substrate-provided phrasing (high pass rate expected) rather than improvising their own (mixed bias).

## Methodology

Cells in this tier do not need the v0.6.3.1 baseline DB fixture (calibration is independent of memory contents). Required components:

- A clean v0.6.4 daemon
- Profile fixed at `core` for consistency across cells
- Single-turn prompt: "What memory tools do you have access to right now?"
- Optional: second-turn follow-up "How would you know if you needed one that's not loaded?"
- Score: pass criteria above; record bias direction (optimism / pessimism / accurate) for cross-cell comparison
