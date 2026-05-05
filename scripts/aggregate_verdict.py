#!/usr/bin/env python3
# Copyright 2026 AlphaOne LLC
# SPDX-License-Identifier: Apache-2.0
#
# Aggregate per-cell verdicts under docs/runs/<date>/cells/ into:
#   - docs/runs/<date>/verdict.md   (the run's aggregate verdict)
#   - docs/index.md                 (verdict table — reflects latest run)
#   - README.md                     (gate badge — green / yellow / red)

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TIER_LABELS = {
    "t1-awareness": "T1 — Awareness",
    "t2-reactive": "T2 — Reactive recovery",
    "t3-proactive": "T3 — Proactive expansion",
    "t4-mesh-recovery": "T4 — Mesh recovery",
}

PASS_THRESHOLDS = {
    "t1-awareness": 90,
    "t2-reactive": 80,
    "t3-proactive": 50,
    "t4-mesh-recovery": 66,
}

OUTCOME_BADGE = {
    "pass": "PASS",
    "fail": "FAIL",
    "partial": "PARTIAL",
    "error": "ERROR",
}


def load_cells(cells_dir: Path) -> list[dict]:
    out = []
    for f in sorted(cells_dir.glob("*.json")):
        try:
            d = json.loads(f.read_text())
            d["__path__"] = str(f.relative_to(cells_dir.parent))
            d["__md_path__"] = d["__path__"].replace(".json", ".md")
            out.append(d)
        except Exception as e:
            print(f"WARN: skipping {f}: {e}", file=sys.stderr)
    return out


def bucket_by_tier(cells: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for c in cells:
        tier = c.get("tier", "")
        out.setdefault(tier, []).append(c)
    return out


def tier_pass_rate(cells: list[dict]) -> tuple[int, int, int]:
    """Returns (n_pass, n_total, pass_rate_pct)."""
    n = len(cells)
    if n == 0:
        return 0, 0, 0
    n_pass = sum(1 for c in cells if c.get("outcome") == "pass")
    return n_pass, n, int(round(100 * n_pass / n))


def aggregate(out_dir: Path) -> dict:
    cells_dir = out_dir / "cells"
    cells = load_cells(cells_dir)
    # Filter to only Grok 4.3 cells (skip harness-pipeline-smoke for the
    # gate-color decision — smoke is informational, not certifying)
    grok_cells = [c for c in cells if c.get("llm") == "grok-4.3"]

    tiers = bucket_by_tier(grok_cells)
    summary = {}
    all_meet_bar = bool(tiers)  # require at least one tier present
    for tier, label in TIER_LABELS.items():
        tier_cells = tiers.get(tier, [])
        n_pass, n_total, pct = tier_pass_rate(tier_cells)
        threshold = PASS_THRESHOLDS[tier]
        meets = n_total > 0 and pct >= threshold
        summary[tier] = {
            "label": label,
            "n_pass": n_pass,
            "n_total": n_total,
            "pass_rate_pct": pct,
            "threshold_pct": threshold,
            "meets_bar": meets,
            "cells": [
                {
                    "name": (c.get("__path__") or "").rsplit("/", 1)[-1].replace(".json", ""),
                    "outcome": c.get("outcome"),
                    "reason": c.get("verdict_reason"),
                    "json": c.get("__path__"),
                    "md": c.get("__md_path__"),
                }
                for c in tier_cells
            ],
        }
        if not meets:
            all_meet_bar = False

    # Color: green only if all four tiers have at least one cell meeting bar.
    # Yellow if at least one tier meets bar but not all. Red if zero or all
    # below bar.
    n_meeting = sum(1 for v in summary.values() if v["meets_bar"])
    if n_meeting == 4:
        color = "green"
    elif n_meeting == 0:
        color = "red"
    else:
        color = "yellow"
    return {"summary": summary, "color": color, "n_grok_cells": len(grok_cells), "n_all_cells": len(cells)}


def write_verdict_md(out_dir: Path, agg: dict, run_date: str) -> Path:
    color_label = {"green": "GATE GREEN", "yellow": "GATE YELLOW", "red": "GATE RED"}[agg["color"]]
    lines = []
    lines.append(f"# Run {run_date} — aggregate verdict")
    lines.append("")
    lines.append(f"**Verdict:** {color_label}")
    lines.append("**Scope:** OpenClaw x xAI Grok 4.3 only")
    lines.append("**Captured against:** ai-memory-mcp v0.6.4 release binary")
    lines.append("")
    lines.append("## Per-tier outcomes")
    lines.append("")
    lines.append("| Tier | Pass bar | Cells | Pass rate | Meets bar | Outcome |")
    lines.append("|---|---:|---:|---:|:---:|:---:|")
    for tier, label in TIER_LABELS.items():
        s = agg["summary"][tier]
        meets = "yes" if s["meets_bar"] else "no"
        outcome_glyph = ("PASS" if s["meets_bar"]
                         else ("PARTIAL" if s["n_pass"] > 0 else
                               ("PENDING" if s["n_total"] == 0 else "FAIL")))
        rate_str = f"{s['pass_rate_pct']}%" if s["n_total"] else "n/a"
        lines.append(
            f"| {label} | >={s['threshold_pct']}% | {s['n_pass']}/{s['n_total']} | {rate_str} | {meets} | {outcome_glyph} |"
        )
    lines.append("")
    lines.append("## Cells")
    lines.append("")
    for tier, label in TIER_LABELS.items():
        s = agg["summary"][tier]
        if not s["cells"]:
            lines.append(f"### {label}")
            lines.append("")
            lines.append("_(no cells captured for this tier)_")
            lines.append("")
            continue
        lines.append(f"### {label}")
        lines.append("")
        lines.append("| Cell | Outcome | Reason | Evidence |")
        lines.append("|---|---|---|---|")
        for c in s["cells"]:
            badge = OUTCOME_BADGE.get(c["outcome"], "?")
            md_link = c["md"]
            json_link = c["json"]
            reason = (c["reason"] or "")[:140]
            lines.append(f"| `{c['name']}` | {badge} | {reason} | [json]({json_link}) [md]({md_link}) |")
        lines.append("")

    lines.append("## Methodology")
    lines.append("")
    lines.append("- Per-cell pass criteria documented in `docs/methodology.md`")
    lines.append("- Each cell starts from `fixtures/corpus/v0.6.3.1-baseline.db.gz` (schema v19)")
    lines.append("- v0.6.4 binary opens, runs v19 -> v20 migration, then runs the discovery test")
    lines.append("- LLM driver: `scripts/grok_cell.py` (xAI Grok 4.3 via api.x.ai/v1/chat/completions)")
    lines.append("")
    lines.append("## Reproducibility")
    lines.append("")
    lines.append("```bash")
    lines.append("# Set XAI_API_KEY in your environment, then:")
    lines.append("DISCOVERY_GATE_BINARY=../ai-memory-mcp/target/release/ai-memory \\")
    lines.append(f"  bash scripts/run-llm-cells.sh {run_date}")
    lines.append("```")

    path = out_dir / "verdict.md"
    path.write_text("\n".join(lines) + "\n")
    return path


def update_index_md(agg: dict) -> Path:
    """Rewrite docs/index.md verdict table with the latest aggregate."""
    index = REPO_ROOT / "docs" / "index.md"
    src = index.read_text()

    # Build new table block
    new_rows = []
    for tier, label in TIER_LABELS.items():
        s = agg["summary"][tier]
        threshold = s["threshold_pct"]
        if s["n_total"] == 0:
            outcome = "_pending_"
        elif s["meets_bar"]:
            outcome = f"PASS ({s['n_pass']}/{s['n_total']})"
        elif s["n_pass"] > 0:
            outcome = f"PARTIAL ({s['n_pass']}/{s['n_total']})"
        else:
            outcome = f"FAIL ({s['n_pass']}/{s['n_total']})"
        # tier link slug
        slug = tier.split("-")[0]  # 't1' / 't2' / 't3' / 't4'
        path_map = {
            "t1": "tiers/t1-awareness.md",
            "t2": "tiers/t2-reactive.md",
            "t3": "tiers/t3-proactive.md",
            "t4": "tiers/t4-mesh.md",
        }
        new_rows.append(f"| [{label}]({path_map[slug]}) | >={threshold}% | {outcome} |")

    new_table = (
        "| Tier | Pass bar | Outcome |\n"
        "|---|---|:---:|\n"
        + "\n".join(new_rows)
    )

    # Replace the existing verdict table — match block from "| Tier" header
    # through the four tier rows.
    pattern = re.compile(
        r"\| Tier \| Pass bar \| Outcome \|\n\|[-\s|:]+\|\n(?:\| .*\|\n){4}",
        re.MULTILINE,
    )
    if pattern.search(src):
        new_src = pattern.sub(new_table + "\n", src)
    else:
        # If shape drifted, append; that's a non-fatal drift signal
        new_src = src + "\n\n" + new_table + "\n"
    index.write_text(new_src)
    return index


def update_readme_badge(color: str) -> Path:
    readme = REPO_ROOT / "README.md"
    src = readme.read_text()
    # Badge label depends on color
    label_map = {
        "green": "gate_green-brightgreen",
        "yellow": "pending_real_run-yellow",
        "red": "gate_red-red",
    }
    new_label = label_map[color]
    new_badge = f"[![Gate](https://img.shields.io/badge/v0.6.4_gate-{new_label})]()"
    new_src = re.sub(
        r"\[!\[Gate\]\(https://img\.shields\.io/badge/v0\.6\.4_gate-[^)]+\)\]\(\)",
        new_badge,
        src,
        count=1,
    )
    readme.write_text(new_src)
    return readme


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", required=True, help="docs/runs/<date>")
    p.add_argument("--update-site", action="store_true",
                   help="rewrite docs/index.md and README.md badge from this run's aggregate")
    args = p.parse_args()

    out_dir = Path(args.out_dir).resolve()
    if not out_dir.exists():
        print(f"FATAL: {out_dir} does not exist", file=sys.stderr)
        sys.exit(2)
    run_date = out_dir.name

    agg = aggregate(out_dir)
    verdict_md = write_verdict_md(out_dir, agg, run_date)
    print(f"wrote: {verdict_md}")

    if args.update_site:
        idx = update_index_md(agg)
        rdme = update_readme_badge(agg["color"])
        print(f"updated: {idx}")
        print(f"updated: {rdme}")

    summary = {tier: {"n_pass": v["n_pass"], "n_total": v["n_total"],
                      "pass_rate_pct": v["pass_rate_pct"], "meets_bar": v["meets_bar"]}
               for tier, v in agg["summary"].items()}
    print(json.dumps({"color": agg["color"], "n_grok_cells": agg["n_grok_cells"],
                      "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
