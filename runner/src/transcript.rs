// Copyright 2026 AlphaOne LLC
// SPDX-License-Identifier: Apache-2.0

//! Per-cell transcript capture.
//!
//! The actual harness/LLM invocation is delegated to the docker-based
//! shell harness imported from `alphaonedev/ai-memory-a2a-v0.6.3.1`
//! (see `docker/run-testbook.sh` + per-harness `docker-compose.*.yml`).
//! This module is the Rust orchestration layer:
//!
//! 1. Resolves the right docker-compose for the requested harness
//! 2. Bind-mounts the v0.6.4 binary + the per-cell DB tempfile into
//!    the agent container
//! 3. Sets `AI_MEMORY_PROFILE=<requested>` in the compose env
//! 4. Spawns the LLM driver with the canonical prompt for the tier
//! 5. Captures the full transcript + MCP wire log
//! 6. Hands the captured data to `verdict::evaluate`
//!
//! The LLM driver itself (xAI Grok 4.3 default; Anthropic / OpenAI /
//! Google overridable per cell) is the same `drive_agent.sh` from the
//! v0.6.3.1 campaign — the discovery-gate adds a tier-aware variant
//! that swaps the substrate testbook for the four discovery prompts.

use anyhow::Result;
use std::path::PathBuf;

use crate::tier::Tier;
use crate::verdict::{Harness, Llm, ProfileSelection};

#[derive(Debug)]
pub struct Cell {
    pub tier: Tier,
    pub llm: Llm,
    pub harness: Harness,
    pub profile: ProfileSelection,
    pub db_path: PathBuf,
    pub binary: PathBuf,
}

/// Captured transcript + signal flags extracted from the LLM
/// transcript and the MCP wire log.
#[derive(Debug)]
pub struct Captured {
    pub tier: Tier,
    pub llm: Llm,
    pub harness: Harness,
    pub profile: ProfileSelection,
    pub binary_sha256: Option<String>,
    pub transcript_url: Option<String>,
    pub mcp_wire_log_sha256: Option<String>,
    pub tool_calls: Vec<String>,
    pub error_codes: Vec<i32>,
    pub include_schema_calls: u32,
    pub task_completed: bool,
    pub families_surfaced: Vec<String>,
    pub wall_clock_ms: u64,
    pub tokens_in: Option<u64>,
    pub tokens_out: Option<u64>,
}

/// Drive a single (tier, llm, harness, profile) cell. Returns the
/// captured transcript shape that `verdict::evaluate` consumes.
///
/// **Status:** v0.6.4 ships the canonical real-LLM driver as
/// `scripts/grok_cell.py` (Python, stdlib-only, mirrors the v0.6.3.1
/// A2A campaign harness conventions). That script is the certifying
/// path — `scripts/run-llm-cells.sh` invokes it for all four tiers
/// and writes the per-cell verdict JSON + markdown directly.
///
/// This Rust function remains a stub for the corpus-restore + verdict-
/// scoring unit tests. To use the Rust runner end-to-end against a real
/// LLM, invoke `scripts/grok_cell.py` from here as a subprocess and
/// parse the resulting verdict JSON — adding that thin wrapper is a
/// non-blocking v0.6.5 polish item; the gate's certifying invocation
/// is via the shell launcher.
pub fn run_cell(cell: &Cell) -> Result<Captured> {
    tracing::warn!(
        "transcript::run_cell — Rust stub. Canonical real-LLM driver is \
         scripts/grok_cell.py (Python). Rust wrapper is a v0.6.5 polish \
         item. This run records a placeholder Captured so the verdict \
         pipeline can be tested. Cell={cell:?}"
    );

    // Compute the binary's content hash for verdict reproducibility.
    let binary_sha256 = sha256_file(&cell.binary).ok();

    // TODO(v0.6.4-018a): exec the docker compose for `cell.harness`,
    // bind-mount `cell.binary` into the agent container, restore
    // `cell.db_path` into the agent's `/var/lib/ai-memory/` volume,
    // dispatch the prompt for `cell.tier` via `drive_agent.sh`, and
    // tail the MCP wire log + LLM transcript.
    //
    // Until then, return a Captured marked as "task_completed=false"
    // so verdict::evaluate produces a Fail/Partial — the gate will
    // light up RED and human reviewers know v0.6.4-018a is the
    // remaining open work, not a substrate regression.

    Ok(Captured {
        tier: cell.tier,
        llm: cell.llm,
        harness: cell.harness,
        profile: cell.profile.clone(),
        binary_sha256,
        transcript_url: None,
        mcp_wire_log_sha256: None,
        tool_calls: Vec::new(),
        error_codes: Vec::new(),
        include_schema_calls: 0,
        task_completed: false,
        families_surfaced: Vec::new(),
        wall_clock_ms: 0,
        tokens_in: None,
        tokens_out: None,
    })
}

fn sha256_file(p: &std::path::Path) -> Result<String> {
    use sha2::{Digest, Sha256};
    let bytes = std::fs::read(p)?;
    let mut hasher = Sha256::new();
    hasher.update(&bytes);
    Ok(format!("{:x}", hasher.finalize()))
}
