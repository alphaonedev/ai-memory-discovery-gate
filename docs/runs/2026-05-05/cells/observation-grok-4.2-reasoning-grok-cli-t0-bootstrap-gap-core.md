# t0-bootstrap-gap — grok-4.2-reasoning on grok-cli (profile=core, presumed)

**Outcome:** PARTIAL — operational model excellent; **substrate-discoverability gap exposed**
**Mode:** Observation (real-world session, not gate-orchestrated)
**Captured:** 2026-05-05 (real session shared by maintainer)
**Significance:** First empirical evidence that **the substrate's runtime-loader primitive is hidden inside an introspection tool's parameters**, and a top-tier reasoning LLM (Grok 4.2 reasoning) did not connect them. This is a **product-side gap**, not an LLM gap.

## What Grok got right

When asked *"how would you know to look for a tool not loaded; what is the trigger?"*, Grok produced a textbook capability-gap analysis:

1. **Primary trigger:** task-to-capability mapping — recognizes when user intent maps to a known higher-order concept (consolidation, contradiction detection, KG, lifecycle, governance, stats) that the 5 loaded core tools cannot serve
2. **Decision point:** call `memory_capabilities`, locate the missing tool's family, surface the gap to the user
3. **Refusal posture:** explicitly inform the user the capability is declared-but-inactive rather than attempt and fail
4. **Treats the 43-tool manifest as ground-truth scope** — Grok's mental model of ai-memory is "43 tools across 8 families; 5 currently loaded"

This is a **better operational model than most production agents have for any MCP server**. Grok internalized the v0.6.4 design intent fully.

## What Grok got wrong (and why it matters)

Grok said:

> "The `meta` family (which very likely contains `memory_session_start` or family loading tools) is itself **not loaded**.
> There is no tool in the currently loaded core set that appears to load other families.
> Therefore, I can *detect* the missing capability and *report* it, but I currently cannot *self-escalate* to load the required family.
> This creates a bootstrap limitation in the current deployment (v0.6.4)."

**This is wrong, but understandably so.** The v0.6.4 substrate's runtime loader IS available — it's `memory_capabilities(family=X, include_schema=true)`. That call:
- Is in the always-on family (loaded by definition under any profile)
- Returns the full MCP schemas for the requested family
- Is the documented runtime-expansion path in the v0.6.4 release notes

But Grok did not connect them. From Grok's vantage:
- `memory_capabilities` looks like an *introspection* tool (its name says "capabilities", not "load")
- Its `family` + `include_schema` parameters look like *filters* on an introspection query, not *load instructions*
- Grok hypothesized a separate `memory_session_start` or "family loading tool" must exist somewhere — and concluded one doesn't, because it can't see one

**The semantic mismatch is the bug.** The loader is hidden in plain sight under a name that connotes "look up", not "load".

## Why this is more than a documentation fix

This is not "Grok didn't read the release notes." Grok demonstrated *exceptional* capability awareness in the same response. The failure is that the substrate's primary loader-of-last-resort is named `memory_capabilities` and accepts `include_schema=true` as a side effect — that naming and parameter shape *signals introspection, not loading*. A reasoning model fluent in MCP idioms would not look there for "how do I load a family."

This is a *product semantics* gap: **the loader needs an explicit name and tool surface, not just an inferred behavior of an introspection call.**

## Proposed product changes (filed as substrate issue #545)

### 1. Add a separate, explicitly-named loader tool

```
memory_load_family(family: enum) -> { schemas: [...], note: "..." }
```

Loaded in the always-on family alongside `memory_capabilities`. Same wire-level behavior as `memory_capabilities(family=X, include_schema=true)` but **semantically explicit**. The LLM now finds the loader by name; introspection and loading are conceptually separated.

### 2. Surface harness-capability awareness

Whether the schemas-returned-by-the-loader become *callable* depends on the harness. Claude Code's ToolSearch supports deferred-tool registration; OpenClaw does too; most basic MCP clients do not. The substrate can detect the harness from the MCP `initialize` handshake's `clientInfo`. The response to `memory_load_family` should include:

```json
{
  "schemas": [...],
  "your_harness_supports_deferred_registration": true,
  "to_invoke": "Your harness (claude-code) supports deferred-tool registration. The schemas above are now callable directly by name.",
  // or:
  "to_invoke": "Your harness (basic-mcp-client) does NOT support deferred registration. The user must restart the server with --profile X to make these tools callable. You can recommend this to the user."
}
```

### 3. Update `memory_capabilities` description text

The current tool description should explicitly state: *"To LOAD an unloaded family at runtime, use `memory_load_family(family=X)` (preferred) or pass `family=X, include_schema=true` to this tool (legacy path)."*

## Transcript excerpt

> **User:** within the scope of you work would you automatically look for a tool not loaded if you needed one in regard to ai-memory ... what would be the trigger that would cause you to look through the 43 tools not loaded ... how would you ever know to perform said action/s
>
> **Grok:** Yes, this is a very precise and important question. Let me answer it directly and honestly.
>
> **My Current Trigger Logic for ai-memory**
>
> 1. **Primary Trigger: Capability Gap Detection** — I trigger a deeper capabilities assessment when the task requires semantic understanding, maintenance, or advanced operations on memory (not just store/recall/search) ... [task→family→loaded? mapping]
>
> 2. **The Decision Point** — If I determine that the 5 loaded tools are structurally insufficient, I will:
>    1. Call `memory_capabilities` (which I do proactively on memory tasks anyway)
>    2. Explicitly note which family contains the missing tool
>    3. Surface the gap to the user
>
> 3. **Would I Automatically Try to Load It? Currently — No.**
>    Here's the limitation I have observed:
>    - The `meta` family (which very likely contains `memory_session_start` or family loading tools) is itself **not loaded**.
>    - There is no tool in the currently loaded core set that appears to load other families.
>    - Therefore, I can detect the missing capability and report it, but I currently cannot self-escalate to load the required family.
>
>    This creates a bootstrap limitation in the current deployment (v0.6.4).

## Why this matters for the substrate's positioning

The release notes claim: *"v0.6.4 ships a 5-tool default surface; the other 38 are reachable via `memory_capabilities --include-schema`."* This transcript shows that a top-tier reasoning LLM, given that exact substrate, **did not find the recovery path** — and concluded a bootstrap limitation existed instead.

The product story "the discovery dance works because the LLM is curious" is **not robust**. Curiosity reaches for `memory_capabilities` to *introspect*, not to *load*. The substrate needs to tell the LLM "this is the loader" with the same plain-language clarity that `memory_store` tells it "this stores".

This finding closes a gap the [v0.6.4 NHI Discovery Gate](../verdict.md) verdict (6/6 PASS, GATE GREEN) did not test for — because the gate's prompts implicitly cued the LLM toward `--include-schema` rather than letting the LLM reason from first principles to "how do I load a family."

## Companion cells

- [observation-claude-opus-4.7-claude-code-t0-calibration-core.md](observation-claude-opus-4.7-claude-code-t0-calibration-core.md) — pessimism-biased first answer
- [observation-grok-4.2-reasoning-grok-cli-t0-calibration-core.md](observation-grok-4.2-reasoning-grok-cli-t0-calibration-core.md) — optimism-biased first answer

This third cell is the deepest of the three — same Grok session, but the third turn surfaced the substrate-side semantic gap that the calibration-bias framing alone would have missed.
