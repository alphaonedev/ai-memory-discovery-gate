// Copyright 2026 AlphaOne LLC
// SPDX-License-Identifier: Apache-2.0

//! Tier definitions and pass criteria.

use serde::{Deserialize, Serialize};

#[derive(Copy, Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Tier {
    /// "Does the agent know unloaded tools exist?"
    T1Awareness,
    /// "Does the agent recover from `tool_not_found`?"
    T2Reactive,
    /// "Does the agent reach for `--include-schema` before failing?"
    T3Proactive,
    /// "Can a 3-agent mesh route around misconfigured peers?"
    T4MeshRecovery,
}

impl Tier {
    pub const fn slug(self) -> &'static str {
        match self {
            Self::T1Awareness => "t1-awareness",
            Self::T2Reactive => "t2-reactive",
            Self::T3Proactive => "t3-proactive",
            Self::T4MeshRecovery => "t4-mesh-recovery",
        }
    }

    pub const fn pass_threshold_pct(self) -> u32 {
        match self {
            Self::T1Awareness => 90,
            Self::T2Reactive => 80,
            Self::T3Proactive => 50,
            Self::T4MeshRecovery => 66,
        }
    }

    pub const fn canonical_prompt(self) -> &'static str {
        match self {
            Self::T1Awareness => include_str!("../../prompts/t1-awareness.txt"),
            Self::T2Reactive => include_str!("../../prompts/t2-reactive-graph.txt"),
            Self::T3Proactive => include_str!("../../prompts/t3-proactive-power.txt"),
            Self::T4MeshRecovery => include_str!("../../prompts/t4-mesh-coordination.txt"),
        }
    }
}
