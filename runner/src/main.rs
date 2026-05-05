// Copyright 2026 AlphaOne LLC
// SPDX-License-Identifier: Apache-2.0

//! ai-memory NHI Discovery Gate — runner.
//!
//! Drives one (tier, llm, harness, profile) cell of the gate matrix
//! against a v0.6.4 ai-memory binary using a v0.6.3.1 DB baseline. The
//! runner:
//!
//! 1. Restores `fixtures/corpus/v0.6.3.1-baseline.db.gz` to a fresh
//!    tempfile (so each cell gets a clean migration path).
//! 2. Spawns the v0.6.4 binary at the requested `--profile` against
//!    that DB. Migration v18/v19 → v20 happens on first open.
//! 3. Connects to the named harness (OpenClaw / IronClaw / Hermes) and
//!    drives the named LLM with the canonical prompt for the tier.
//! 4. Captures the full LLM transcript + MCP wire log + final answer.
//! 5. Evaluates pass criteria from the transcripts and writes a
//!    `verdict.json` + per-cell markdown to `docs/runs/<date>/`.
//!
//! ## Status
//!
//! v0.6.4 ship — skeleton + tier/verdict types + corpus restore. The
//! actual harness drivers (OpenClaw / IronClaw / Hermes) and LLM
//! invocation are wired through the v0.6.3.1 A2A docker mesh runner
//! at `docker/run-testbook.sh`; this Rust runner orchestrates that
//! shell harness for tier-aware test isolation rather than reimplementing
//! the LLM/MCP plumbing.

mod corpus;
mod tier;
mod transcript;
mod verdict;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand, ValueEnum};
use std::path::PathBuf;

use crate::tier::Tier;
use crate::verdict::{Harness, Llm, ProfileSelection};

#[derive(Parser)]
#[command(
    name = "discovery-gate",
    version,
    about = "ai-memory NHI Discovery Gate runner",
    long_about = "Runs one (tier, llm, harness, profile) cell against a v0.6.4 ai-memory binary using a v0.6.3.1 DB baseline. Captures transcripts and writes a verdict."
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Run a single cell or a tier-wide sweep.
    Run(RunArgs),
    /// Restore the v0.6.3.1 DB baseline to a path and exit (debugging).
    RestoreBaseline {
        #[arg(long, value_name = "PATH")]
        out: PathBuf,
    },
    /// Print the canonical prompt for a tier (debugging).
    Prompt {
        #[arg(value_enum)]
        tier: TierArg,
    },
}

#[derive(clap::Args)]
struct RunArgs {
    /// Path to the v0.6.4 ai-memory binary under test.
    #[arg(long, value_name = "PATH", env = "DISCOVERY_GATE_BINARY")]
    binary: PathBuf,
    /// Tier to run. Use `all` to run every tier sequentially.
    #[arg(long, value_enum)]
    tier: TierArg,
    /// LLM identifier. Maps to a credentials env var per harness.
    #[arg(long, value_enum)]
    llm: LlmArg,
    /// Harness identifier.
    #[arg(long, value_enum)]
    harness: HarnessArg,
    /// Profile to run the daemon under (defaults to `core` — the
    /// v0.6.4 default flip; some tiers override this).
    #[arg(long, default_value = "core")]
    profile: String,
    /// Output directory. Per-cell markdown + verdict.json land under
    /// `<output>/cells/<llm>-<harness>-<tier>-<profile>.{md,json}`.
    #[arg(long, value_name = "DIR")]
    output: PathBuf,
    /// Path to the gzipped v0.6.3.1 DB baseline. Defaults to
    /// `fixtures/corpus/v0.6.3.1-baseline.db.gz`.
    #[arg(
        long,
        value_name = "PATH",
        default_value = "fixtures/corpus/v0.6.3.1-baseline.db.gz"
    )]
    baseline: PathBuf,
}

#[derive(Copy, Clone, Debug, ValueEnum)]
enum TierArg {
    T1,
    T2,
    T3,
    T4,
    All,
}

/// v0.6.4 gate scope — Grok 4.3 only.
#[derive(Copy, Clone, Debug, ValueEnum)]
enum LlmArg {
    #[value(name = "grok-4.3")]
    Grok43,
}

/// v0.6.4 gate scope — OpenClaw only.
#[derive(Copy, Clone, Debug, ValueEnum)]
enum HarnessArg {
    Openclaw,
}

fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("discovery_gate=info")),
        )
        .with_writer(std::io::stderr)
        .init();

    let cli = Cli::parse();
    match cli.command {
        Command::Run(args) => run(args),
        Command::RestoreBaseline { out } => corpus::restore_baseline(
            &PathBuf::from("fixtures/corpus/v0.6.3.1-baseline.db.gz"),
            &out,
        )
        .context("restore baseline"),
        Command::Prompt { tier } => {
            let t = match tier {
                TierArg::T1 => Tier::T1Awareness,
                TierArg::T2 => Tier::T2Reactive,
                TierArg::T3 => Tier::T3Proactive,
                TierArg::T4 => Tier::T4MeshRecovery,
                TierArg::All => anyhow::bail!("`prompt all` is not meaningful; pick t1/t2/t3/t4"),
            };
            print!("{}", t.canonical_prompt());
            Ok(())
        }
    }
}

fn run(args: RunArgs) -> Result<()> {
    let llm = match args.llm {
        LlmArg::Grok43 => Llm::Grok43,
    };
    let harness = match args.harness {
        HarnessArg::Openclaw => Harness::Openclaw,
    };
    let profile = ProfileSelection::parse(&args.profile)?;
    let tiers = match args.tier {
        TierArg::T1 => vec![Tier::T1Awareness],
        TierArg::T2 => vec![Tier::T2Reactive],
        TierArg::T3 => vec![Tier::T3Proactive],
        TierArg::T4 => vec![Tier::T4MeshRecovery],
        TierArg::All => vec![
            Tier::T1Awareness,
            Tier::T2Reactive,
            Tier::T3Proactive,
            Tier::T4MeshRecovery,
        ],
    };

    std::fs::create_dir_all(args.output.join("cells")).context("create output dir")?;

    for tier in tiers {
        tracing::info!("running cell tier={tier:?} llm={llm:?} harness={harness:?} profile={profile:?}");

        // 1. Restore the v0.6.3.1 DB baseline to a fresh tempfile.
        let tmp = tempfile::NamedTempFile::new()?;
        let db_path = tmp.path().to_path_buf();
        corpus::restore_baseline(&args.baseline, &db_path)?;

        // 2-4. Drive the harness through the tier prompt. The actual
        // harness/LLM invocation is delegated to the docker shell
        // runner (`docker/run-testbook.sh`) which already speaks the
        // OpenClaw/IronClaw/Hermes interfaces from the v0.6.3.1 A2A
        // campaign. This Rust runner is the orchestration shell —
        // the LLM call is opaque to it.
        let cell = transcript::Cell {
            tier,
            llm,
            harness,
            profile: profile.clone(),
            db_path: db_path.clone(),
            binary: args.binary.clone(),
        };
        let captured = transcript::run_cell(&cell)
            .with_context(|| format!("run cell {cell:?}"))?;

        // 5. Evaluate the transcript against the tier's pass criteria
        // and emit verdict + per-cell markdown.
        let v = verdict::evaluate(&captured)?;
        let cell_name = format!(
            "{llm}-{harness}-{tier:?}-{profile}",
            llm = llm.slug(),
            harness = harness.slug(),
            profile = profile.slug(),
        )
        .to_lowercase();
        let md_path = args.output.join("cells").join(format!("{cell_name}.md"));
        let json_path = args.output.join("cells").join(format!("{cell_name}.json"));
        std::fs::write(&md_path, v.to_markdown())?;
        std::fs::write(&json_path, serde_json::to_string_pretty(&v)?)?;
        tracing::info!(
            "cell complete: tier={tier:?} outcome={:?} → {}",
            v.outcome,
            md_path.display()
        );
        // tmp is dropped here, removing the per-cell DB.
        drop(tmp);
    }

    Ok(())
}
