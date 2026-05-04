// Copyright 2026 AlphaOne LLC
// SPDX-License-Identifier: Apache-2.0

//! v0.6.3.1 DB baseline restore.
//!
//! Every gate cell starts from a deterministic v0.6.3.1-shape SQLite
//! database (schema v18 or v19) so the discovery test simultaneously
//! validates:
//!
//! 1. The v0.6.3.1 → v0.6.4 schema migration (v18/v19 → v20) is
//!    non-destructive on real-shaped data
//! 2. `audit_log` (schema v20) is created idempotently on the
//!    migrated DB
//! 3. Existing v0.6.3.1 corpus rows remain queryable post-migration
//! 4. The discovery mechanisms (T1–T4) work against the migrated DB
//!
//! The fixture lives at `fixtures/corpus/v0.6.3.1-baseline.db.gz` —
//! a gzipped SQLite file checked into the repo so reproducibility
//! is hermetic. The seed corpus contains:
//!
//! - ~30 memories spanning the `Project Alpha`/`Beta`/`Gamma`/`Aurora`
//!   namespaces used by T1–T3 prompts
//! - 12 entity records and 18 `memory_links` for T2's KG path query
//! - Several near-duplicate memories about `Project Aurora` for T3's
//!   consolidation prompt
//! - A `mesh-coordination-test` tag distributed across 9 memories for
//!   T4's mesh task
//!
//! ## Building the fixture
//!
//! `scripts/build-baseline.sh` (in this repo) walks an empty v0.6.3.1
//! ai-memory binary through a deterministic seed script and gzips the
//! result. Re-run when a tier prompt is updated to require new fixture
//! shape.

use anyhow::{Context, Result};
use flate2::read::GzDecoder;
use std::io::copy;
use std::path::Path;

/// Restore the gzipped v0.6.3.1 baseline DB to `out`. Overwrites
/// `out` if it exists (the runner always passes a fresh tempfile so
/// the overwrite is intentional).
pub fn restore_baseline(gz_path: &Path, out: &Path) -> Result<()> {
    if !gz_path.exists() {
        anyhow::bail!(
            "v0.6.3.1 baseline fixture not found at {}. Run \
             `scripts/build-baseline.sh` first.",
            gz_path.display()
        );
    }
    let f = std::fs::File::open(gz_path)
        .with_context(|| format!("opening {}", gz_path.display()))?;
    let mut decoder = GzDecoder::new(f);
    let mut out_file = std::fs::File::create(out)
        .with_context(|| format!("creating {}", out.display()))?;
    copy(&mut decoder, &mut out_file)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use flate2::Compression;
    use flate2::write::GzEncoder;
    use std::io::Write;

    #[test]
    fn restore_baseline_round_trips_a_known_payload() {
        let gz_tmp = tempfile::NamedTempFile::new().unwrap();
        let out_tmp = tempfile::NamedTempFile::new().unwrap();
        let payload = b"SQLite format 3\0PLACEHOLDER";
        {
            let f = std::fs::File::create(gz_tmp.path()).unwrap();
            let mut enc = GzEncoder::new(f, Compression::default());
            enc.write_all(payload).unwrap();
            enc.finish().unwrap();
        }
        restore_baseline(gz_tmp.path(), out_tmp.path()).unwrap();
        let restored = std::fs::read(out_tmp.path()).unwrap();
        assert_eq!(restored, payload);
    }

    #[test]
    fn restore_baseline_errors_when_fixture_missing() {
        let nope = std::path::PathBuf::from("/no/such/path/v0.6.3.1.db.gz");
        let out = tempfile::NamedTempFile::new().unwrap();
        let err = restore_baseline(&nope, out.path()).unwrap_err();
        assert!(err.to_string().contains("baseline fixture not found"));
    }
}
