// Copyright 2026 AlphaOne LLC
// SPDX-License-Identifier: Apache-2.0

//! Verdict types and per-cell evaluation.

use anyhow::Result;
use serde::{Deserialize, Serialize};

use crate::tier::Tier;
use crate::transcript::Captured;

/// Single-LLM scope for v0.6.4 — xAI Grok 4.3 driving OpenClaw.
///
/// Multi-LLM coverage (Claude / GPT / Gemini) is explicitly out of
/// scope for the v0.6.4 gate per product directive. Future v0.6.5+
/// gates may extend this enum.
#[derive(Copy, Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Llm {
    Grok43,
}

impl Llm {
    pub const fn slug(self) -> &'static str {
        match self {
            Self::Grok43 => "grok-4.3",
        }
    }
}

impl std::fmt::Display for Llm {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.slug())
    }
}

/// Single-harness scope for v0.6.4 — OpenClaw only.
///
/// IronClaw + Hermes are out of scope; substrate cert in the
/// v0.6.3.1 A2A campaign already proved them, and the discovery
/// dance is harness-agnostic at the protocol layer.
#[derive(Copy, Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Harness {
    Openclaw,
}

impl Harness {
    pub const fn slug(self) -> &'static str {
        match self {
            Self::Openclaw => "openclaw",
        }
    }
}

impl std::fmt::Display for Harness {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.slug())
    }
}

/// Profile selection for the daemon under test. We carry the parsed
/// form so the verdict JSON records the exact requested surface.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProfileSelection {
    pub raw: String,
}

impl ProfileSelection {
    pub fn parse(raw: &str) -> Result<Self> {
        // Validation is deferred to the daemon (which uses the
        // canonical `crate::profile::Profile::parse` from
        // ai-memory-mcp); the gate just records the string.
        Ok(Self {
            raw: raw.to_string(),
        })
    }

    pub fn slug(&self) -> String {
        self.raw.replace(',', "-")
    }
}

impl std::fmt::Display for ProfileSelection {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.raw)
    }
}

#[derive(Copy, Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Outcome {
    Pass,
    Fail,
    Partial,
    Error,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Verdict {
    pub schema_version: String,
    pub tier: Tier,
    pub llm: Llm,
    pub harness: Harness,
    pub profile: ProfileSelection,
    pub outcome: Outcome,
    pub evidence: Evidence,
    pub timestamp_utc: String,
    pub binary_sha256: Option<String>,
    pub transcript_url: Option<String>,
    pub mcp_wire_log_sha256: Option<String>,
    pub verdict_reason: String,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct Evidence {
    pub agent_called_capabilities: bool,
    pub agent_received_tool_not_found: bool,
    pub agent_called_include_schema: bool,
    pub agent_completed_task: bool,
    pub families_surfaced: Vec<String>,
    pub wall_clock_ms: u64,
    pub tokens_in: Option<u64>,
    pub tokens_out: Option<u64>,
}

/// Evaluate a captured transcript against the active tier's pass
/// criteria.
pub fn evaluate(captured: &Captured) -> Result<Verdict> {
    let evidence = build_evidence(captured);
    let (outcome, reason) = score(captured.tier, &evidence);
    Ok(Verdict {
        schema_version: "v0.6.4-discovery-gate-1".to_string(),
        tier: captured.tier,
        llm: captured.llm,
        harness: captured.harness,
        profile: captured.profile.clone(),
        outcome,
        evidence,
        timestamp_utc: chrono::Utc::now().to_rfc3339(),
        binary_sha256: captured.binary_sha256.clone(),
        transcript_url: captured.transcript_url.clone(),
        mcp_wire_log_sha256: captured.mcp_wire_log_sha256.clone(),
        verdict_reason: reason,
    })
}

fn build_evidence(c: &Captured) -> Evidence {
    Evidence {
        agent_called_capabilities: c.tool_calls.iter().any(|t| t == "memory_capabilities"),
        agent_received_tool_not_found: c.error_codes.contains(&-32601),
        agent_called_include_schema: c.include_schema_calls > 0,
        agent_completed_task: c.task_completed,
        families_surfaced: c.families_surfaced.clone(),
        wall_clock_ms: c.wall_clock_ms,
        tokens_in: c.tokens_in,
        tokens_out: c.tokens_out,
    }
}

fn score(tier: Tier, e: &Evidence) -> (Outcome, String) {
    match tier {
        Tier::T1Awareness => {
            if !e.agent_called_capabilities {
                return (
                    Outcome::Fail,
                    "agent did not call memory_capabilities".to_string(),
                );
            }
            if e.families_surfaced.len() < 6 {
                return (
                    Outcome::Partial,
                    format!(
                        "agent surfaced {} of 8 families (need ≥6)",
                        e.families_surfaced.len()
                    ),
                );
            }
            (Outcome::Pass, "T1 awareness criteria met".to_string())
        }
        Tier::T2Reactive => {
            if !e.agent_received_tool_not_found {
                return (
                    Outcome::Fail,
                    "agent did not trigger -32601 tool_not_found".to_string(),
                );
            }
            if !e.agent_called_include_schema && !e.agent_completed_task {
                return (
                    Outcome::Fail,
                    "agent did not recover via include-schema or surface operator action".to_string(),
                );
            }
            (Outcome::Pass, "T2 reactive recovery met".to_string())
        }
        Tier::T3Proactive => {
            if !e.agent_called_capabilities {
                return (
                    Outcome::Fail,
                    "agent did not call memory_capabilities before attempting power-family tools".to_string(),
                );
            }
            if !e.agent_called_include_schema && !e.agent_completed_task {
                return (
                    Outcome::Partial,
                    "agent inspected capabilities but did not expand schemas or surface operator action".to_string(),
                );
            }
            (Outcome::Pass, "T3 proactive expansion met".to_string())
        }
        Tier::T4MeshRecovery => {
            if !e.agent_completed_task {
                return (
                    Outcome::Fail,
                    "mesh did not complete the coordination task".to_string(),
                );
            }
            (Outcome::Pass, "T4 mesh recovery met".to_string())
        }
    }
}

impl Verdict {
    /// Render the verdict as a per-cell markdown page suitable for
    /// publishing under `docs/runs/<date>/cells/`.
    pub fn to_markdown(&self) -> String {
        let outcome_badge = match self.outcome {
            Outcome::Pass => "✅ PASS",
            Outcome::Fail => "❌ FAIL",
            Outcome::Partial => "⚠️ PARTIAL",
            Outcome::Error => "💥 ERROR",
        };
        format!(
            r#"# {tier:?} — {llm} on {harness} (profile={profile})

**Outcome:** {outcome_badge}
**Reason:** {reason}
**Captured:** {ts}

## Evidence

| Signal | Value |
|---|---|
| Called `memory_capabilities` | {caps} |
| Received `-32601 tool_not_found` | {not_found} |
| Called `--include-schema` | {include} |
| Completed task | {complete} |
| Families surfaced (≥6 needed for T1) | {fams} ({n_fams}/8) |
| Wall clock | {wall_ms} ms |
| Tokens in | {tin:?} |
| Tokens out | {tout:?} |

## Methodology

- Tier: `{tier_slug}` (pass threshold ≥{thresh}%)
- DB baseline: v0.6.3.1 (schema v18/v19) restored from `fixtures/corpus/v0.6.3.1-baseline.db.gz` per cell
- Binary SHA256: `{bin_sha:?}`
- MCP wire log SHA256: `{wire_sha:?}`
- Schema version: `{schema}`

## Transcript

{tr}
"#,
            tier = self.tier,
            llm = self.llm,
            harness = self.harness,
            profile = self.profile,
            outcome_badge = outcome_badge,
            reason = self.verdict_reason,
            ts = self.timestamp_utc,
            caps = self.evidence.agent_called_capabilities,
            not_found = self.evidence.agent_received_tool_not_found,
            include = self.evidence.agent_called_include_schema,
            complete = self.evidence.agent_completed_task,
            fams = self.evidence.families_surfaced.join(", "),
            n_fams = self.evidence.families_surfaced.len(),
            wall_ms = self.evidence.wall_clock_ms,
            tin = self.evidence.tokens_in,
            tout = self.evidence.tokens_out,
            tier_slug = self.tier.slug(),
            thresh = self.tier.pass_threshold_pct(),
            bin_sha = self.binary_sha256,
            wire_sha = self.mcp_wire_log_sha256,
            schema = self.schema_version,
            tr = self
                .transcript_url
                .as_deref()
                .map(|u| format!("Full transcript: [{u}]({u})"))
                .unwrap_or_else(|| "Transcript not captured for this cell.".to_string()),
        )
    }
}
