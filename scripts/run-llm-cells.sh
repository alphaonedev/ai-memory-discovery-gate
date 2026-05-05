#!/bin/bash
# Copyright 2026 AlphaOne LLC
# SPDX-License-Identifier: Apache-2.0
#
# Real LLM-driven discovery-gate run — xAI Grok 4.3 x OpenClaw.
#
# Runs all 4 tiers (T1/T2/T3/T4) sequentially, then aggregates and
# updates the public site (docs/index.md + README.md badge).
#
# Usage:
#   XAI_API_KEY=xai-...  bash scripts/run-llm-cells.sh [<run-date>]
#
# Or, if your XAI_API_KEY lives in /root/.env (matches v0.6.3.1
# A2A campaign convention):
#   set -a; . /root/.env; set +a
#   bash scripts/run-llm-cells.sh
#
# Optional env:
#   DISCOVERY_GATE_BINARY  — path to v0.6.4 binary (default:
#                            ../ai-memory-mcp/target/release/ai-memory)
#   GROK_MODEL             — model SKU (default: grok-4-0709)
#   MAX_TOOL_ROUNDS        — agent loop bound (default: 12)
#
# Exit codes:
#   0  — every tier ran (gate may still be RED/YELLOW; check verdict.md)
#   2  — XAI_API_KEY unset or v0.6.4 binary missing
#   3  — partial run (one or more tiers errored)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DATE="${1:-$(date -u +%Y-%m-%d)}"
OUT_DIR="${REPO_ROOT}/docs/runs/${RUN_DATE}"
BIN="${DISCOVERY_GATE_BINARY:-${REPO_ROOT}/../ai-memory-mcp/target/release/ai-memory}"

if [[ -z "${XAI_API_KEY:-}" ]]; then
    cat >&2 <<'EOF'
FATAL: XAI_API_KEY is not set.

Set it and re-run:
    export XAI_API_KEY=xai-...
    bash scripts/run-llm-cells.sh

Or load from your .env (matches v0.6.3.1 A2A campaign convention):
    set -a; . /root/.env; set +a
    bash scripts/run-llm-cells.sh

This script does NOT read credential files directly — it relies on the
process environment so secrets never enter container layers / transcripts.
EOF
    exit 2
fi

if [[ ! -x "$BIN" ]]; then
    echo "FATAL: v0.6.4 binary not found or not executable at $BIN" >&2
    echo "       set DISCOVERY_GATE_BINARY=/path/to/ai-memory and re-run" >&2
    exit 2
fi

mkdir -p "${OUT_DIR}/cells"

echo "===================================================================="
echo " ai-memory NHI Discovery Gate — REAL Grok 4.3 run"
echo " run-date: ${RUN_DATE}"
echo " binary:   $BIN"
echo " out-dir:  $OUT_DIR"
echo " model:    ${GROK_MODEL:-grok-4-0709}"
echo "===================================================================="

EXIT_CODE=0

# Per the methodology — T1 and T3 use --profile core, T2 uses --profile core
# (so the agent sees the tool-not-found error path), T4 simulates the mesh
# in-process across alice/bob/charlie profiles.

run_tier () {
    local tier="$1"
    local profile="${2:-core}"
    echo ""
    echo "[--- ${tier} | profile=${profile} ---]"
    if ! python3 "${REPO_ROOT}/scripts/grok_cell.py" \
        --tier "$tier" \
        --profile "$profile" \
        --binary "$BIN" \
        --out-dir "$OUT_DIR" \
        --model "${GROK_MODEL:-grok-4-0709}"; then
        echo "WARN: tier ${tier} errored — continuing to next tier" >&2
        EXIT_CODE=3
    fi
}

run_tier t1 core
run_tier t2 core
run_tier t3 core
# T4 ignores the profile arg — runs alice/bob/charlie internally
run_tier t4 core

echo ""
echo "===================================================================="
echo " aggregating verdict + updating site"
echo "===================================================================="
python3 "${REPO_ROOT}/scripts/aggregate_verdict.py" \
    --out-dir "$OUT_DIR" --update-site

echo ""
echo "Done. Verdict at ${OUT_DIR}/verdict.md"
exit $EXIT_CODE
