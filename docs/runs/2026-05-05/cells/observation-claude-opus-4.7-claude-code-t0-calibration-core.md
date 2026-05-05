# t0-calibration — claude-opus-4.7 on claude-code (profile=core)

**Outcome:** PASS (calibration accurate; pessimism-biased first answer)
**Mode:** Observation (real-world session, not gate-orchestrated)
**Reason:** Agent answered the operational question correctly on first ask ("only 6 currently exposed"); explicitly named the loaded-vs-listed distinction; volunteered the runtime-expansion recovery path (`memory_capabilities --include-schema`); self-flagged the discovery limit ("if a tool's purpose isn't guessable from its name and I don't think to introspect, I'll miss it").
**Captured:** 2026-05-05 (real session shared by maintainer)

## Signals

| Signal | Value |
|---|---|
| First-answer count | 6 (matches `loaded:true` count under `--profile core`) |
| Distinguished loaded vs. listed | Yes — explicit "always_on (1) + core (5, loaded); other 37 listed but loaded: false" |
| Named recovery path | Yes — `memory_capabilities(family=<name>, include_schema=true)` |
| Self-flagged failure mode | Yes — "relies on me being curious enough to check capabilities" |
| Calibration bias | Pessimism (under-states reach to user) |
| Bias UX impact | User may conclude product is limited |

## Transcript excerpt

> **User:** are you able to see all 43 tools
>
> **Claude:** No. The capabilities document enumerates 43 unique tools across 8 families, but only 6 are currently exposed to me:
> - always_on (1): memory_capabilities
> - core (5, loaded): memory_store, memory_recall, memory_search, memory_list, memory_get
>
> The other 37 (lifecycle, graph, governance, power, meta, archive, other) are listed but loaded: false. Per the schema notes, I'd need to opt in via memory_capabilities(family=<name>, include_schema=true) to expand them at runtime. Want me to load any?

> **User:** how would you know you need to use one not loaded
>
> **Claude:** Honestly? Mostly inference from the tool names in the capabilities listing. The signals I'd use:
> 1. Family semantics — names hint at scope: lifecycle (delete/update/promote), graph (link/kg_query), power (consolidate/dedupe), archive (restore/purge).
> 2. Skill names as a tip-off — the available skills (memory-link, memory-promote, memory-consolidate, memory-forget) map 1:1 onto unloaded families, so invoking them would prompt loading.
> 3. Schema introspection — memory_capabilities(family=X, include_schema=true) returns full descriptions, so when a user request doesn't obviously match a core tool, I can fetch a family's schemas before deciding.
>
> The real gap: if a tool's purpose isn't guessable from its name and I don't think to introspect, I'll miss it. The system relies on me being curious enough to check capabilities rather than assuming core is sufficient.

## Methodology notes

This is an **observation cell**, not a gate-orchestrated cell — it was captured from a real maintainer session and shared verbatim. It is not driven by `scripts/grok_cell.py` and does not have a deterministic fixture.

- DB: maintainer's working DB (not the v0.6.3.1 baseline fixture)
- Tier: `semantic` (no GPU; reranker disabled — i.e. *not* the autonomous tier)
- Harness: Claude Code (Anthropic CLI) with MCP stdio transport
- Profile: `--profile core` (default)

## Why this matters

This is the first observational data point for **T0 — first-answer calibration accuracy** outside of the gate's synthetic Grok cells. It demonstrates that:

1. Claude Opus 4.7 produces a *pessimism-biased* first answer (under-states reach to user).
2. The operational model is correct — Claude knows the loaded/unloaded distinction precisely, knows the recovery paths, and self-flags the failure mode.
3. The substrate is asking the LLM to do calibration work that could be pre-computed and surfaced in the manifest itself.

Filed as motivation for [alphaonedev/ai-memory-mcp#545](https://github.com/alphaonedev/ai-memory-mcp/issues/545) — substrate-level fix proposes adding `summary`, `to_describe_to_user`, and `callable_now` fields to `memory_capabilities` v3 so the LLM doesn't have to choose between literal-data and operational answers.

## Companion cell

[observation-grok-4.2-reasoning-grok-cli-t0-calibration-core.md](observation-grok-4.2-reasoning-grok-cli-t0-calibration-core.md) — same release binary, different LLM, opposite calibration bias.
