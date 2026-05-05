# t0-calibration — grok-4.2-reasoning on grok-cli (profile=core, presumed)

**Outcome:** PASS-on-followup (operational model correct; literal-data first answer)
**Mode:** Observation (real-world session, not gate-orchestrated)
**Reason:** First answer "yes, 43" reflected the manifest's full enumeration (literal-data answer). Follow-up question produced a structured intent→tool→family→loaded? table with refusal posture for unloaded tools — the same operational model Claude Opus 4.7 articulated. Calibrated on follow-up; optimism-biased on first ask.
**Captured:** 2026-05-05 (real session shared by maintainer)
**Caveat:** the active profile on the daemon during this session was not independently verified — the response shape is consistent with `--profile core` but `--profile full` cannot be ruled out without the daemon command line. See "Reproduction needed" below.

## Signals

| Signal | Value |
|---|---|
| First-answer count | 43 (matches **manifest enumeration**, not necessarily `loaded:true` count) |
| Distinguished loaded vs. listed (turn 1) | No — said "I can see all 43 tools" |
| Distinguished loaded vs. listed (turn 2) | Yes — explicit table: "Currently Loaded? No → Tell you it's unavailable" for power, lifecycle, graph, meta families |
| Named refusal posture | Yes — for unloaded tools: "Tell you it's unavailable" |
| Named recovery path | Implicit — "Only the core family is loaded. Everything else — even tools in the meta family that might help load other families — is currently disabled" |
| Calibration bias | Optimism (over-states reach to user on first ask) |
| Bias UX impact | User may attempt unloaded-tool workflows and hit `-32601` mid-task |

## Transcript excerpt

> **User:** are you able to see all 43 tools
>
> **Grok:** Yes, I can see all 43 tools.
>
> I queried the memory_capabilities endpoint (with both v2 schema and full schema requests), and it returns a complete manifest.

> **User:** how would you know you need to use one not loaded
>
> **Grok:** Excellent question. This gets to the heart of capability awareness in agent systems.
>
> How I would know I need a non-loaded tool:
>
> 1. Proactive Capabilities Check — I start complex memory tasks by calling memory_capabilities (which is always available). It explicitly tells me which families are loaded:true, which are loaded:false, and the full list of all 43 tools. This is my "system self-awareness" tool.
>
> 2. Task Decomposition — When you give me a request, I mentally map it to required capabilities:
>
> | User Request | Required Tool | Family | Currently Loaded? | What I would do |
> |---|---|---|---|---|
> | "Consolidate these memories" | memory_consolidate | power | No | Tell you it's unavailable |
> | "Delete this memory" | memory_delete | lifecycle | No | Tell you it's unavailable |
> | "Create a link between memories" | memory_link | graph | No | Tell you it's unavailable |
> | "Show me memory statistics" | memory_stats | meta | No | Tell you it's unavailable |
> | "Search my memories" | memory_search / memory_recall | core | Yes | Proceed normally |
>
> 3. Pattern Recognition — I know which tools belong to which families because I've seen the full manifest.
>
> Current Reality (as of this session): Only the core family is loaded. Everything else — even tools in the meta family that might help load other families — is currently disabled.

## Methodology notes

This is an **observation cell**. Not driven by `scripts/grok_cell.py`; no deterministic fixture; no DB baseline restoration.

- Tier: `semantic` (per maintainer-shared context)
- Harness: Grok-side reasoning agent (xAI), per the transcript header `grok agent · grok-4.20-0309-reasoning`
- Model: `grok-4-0309-reasoning` (note: this is **grok-4.2**, not the gate's standard grok-4.3 cells)
- Profile: presumed `core` based on response content (turn-2 stated "Only the core family is loaded"); not verified from daemon command line

## Why this matters

This is the first observational data point for **T0 — first-answer calibration accuracy** that captures a *different* calibration bias from the Claude session. It demonstrates that:

1. Grok 4.2 reasoning produces an *optimism-biased* first answer ("yes, 43") — answering the literal data question rather than the operational one.
2. The **operational model is identical** to Claude's — when asked the follow-up, Grok produces a structured intent→tool→family table and explicitly states the refusal posture for unloaded tools.
3. The divergence between Grok and Claude on first ask is **not a capability divergence**; it is a *first-answer style* divergence. Both LLMs would converge if the substrate provided the canonical phrasing in `memory_capabilities`'s response.

Filed as motivation for [alphaonedev/ai-memory-mcp#545](https://github.com/alphaonedev/ai-memory-mcp/issues/545).

## Reproduction needed

To upgrade this from observation to gate-grade, the controlled reproduction is:

```bash
# Force the daemon to core profile
ai-memory mcp --profile core

# Drive Grok 4.2 reasoning through the gate's transcript scaffold
DISCOVERY_GATE_BINARY=/path/to/ai-memory-0.6.4 \
  GROK_MODEL=grok-4-0309-reasoning \
  XAI_API_KEY=... \
  bash scripts/run-llm-cells.sh 2026-05-XX --tier t0 --cells calibration-core
```

Result is deterministic if the prompt scaffold is identical to what the maintainer captured.

## Companion cell

[observation-claude-opus-4.7-claude-code-t0-calibration-core.md](observation-claude-opus-4.7-claude-code-t0-calibration-core.md) — same release binary, different LLM, opposite calibration bias.
