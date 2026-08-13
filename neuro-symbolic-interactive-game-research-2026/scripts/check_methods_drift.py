#!/usr/bin/env python3
"""Drift check between OKF method atoms and the frozen experiment config.

The single source of numeric truth is configs/experiment-matrix.yaml. Method
prose lives in knowledge/ OKF atoms (and mirrors the paper/oracle plan). This
check fails when an atom quotes a number that no longer matches the frozen
config — the silent-drift failure mode that motivates the methods graph.
"""
import re
import sys

import yaml

CONFIG = "configs/experiment-matrix.yaml"
CHECKS = []


def check(atom_path, description, pattern):
    CHECKS.append((atom_path, description, pattern))


def main() -> int:
    config = yaml.safe_load(open(CONFIG))
    controls = config["controls"]
    design = config["design"]
    stage1 = design["stage_1_screening"]
    stage2 = design["stage_2_confirmatory"]
    budget = design["comparison_budget"]
    noninf = config["statistics"]["noninferiority"]

    seeds = controls["seeds"]
    seeds_regex = "·".join(str(seed) for seed in seeds)

    check(
        "knowledge/protocols/execution-controls.md",
        "decoding/seed/timeout controls",
        rf"temperature {controls['decoding']['temperature']}.*top_p {controls['decoding']['top_p']}"
        rf".*max_output_tokens {controls['decoding']['max_output_tokens']}"
        rf".*\[{', ?'.join(str(seed) for seed in seeds)}\]"
        rf".*K={controls['repair_budget_k']}.*timeout {controls['timeout_seconds']}s",
    )
    check(
        "knowledge/experiments/stage-1-screening.md",
        "stage 1 scale",
        rf"scenarios_per_track: {stage1['scenarios_per_track']}\b.*repetitions: {stage1['repetitions']}\b",
    )
    check(
        "knowledge/experiments/stage-2-confirmatory.md",
        "stage 2 scale",
        rf"scenarios_per_track: {stage2['scenarios_per_track']}\b.*repetitions: {stage2['repetitions']}\b",
    )
    check(
        "knowledge/experiments/stage-2-confirmatory.md",
        "stage 2 ablations",
        r".*".join(re.escape(name) for name in stage2["ablations"]),
    )
    check(
        "knowledge/experiments/controller-arms.md",
        "all six controller arms named",
        r".*".join(re.escape(arm) for arm in stage2["controller_arms"]),
    )
    check(
        "knowledge/experiments/controller-arms.md",
        "matched call budget",
        rf"최대 호출 {budget['proposal_or_repair_calls_max']}\(1\+K\), "
        rf"K={budget['invalid_followup_calls_max']}",
    )
    check(
        "knowledge/experiments/stage-2-confirmatory.md",
        "confirmatory seed list",
        seeds_regex,
    )
    margin_pp = int(round(float(noninf["margin_absolute"]) * 100))
    check(
        "knowledge/contrasts/h4-affect.md",
        "noninferiority margin and alpha",
        rf"한계 {margin_pp}pp.*α=\.0?25.*margin_absolute: {noninf['margin_absolute']}"
        rf".*alpha_one_sided: {noninf['alpha_one_sided']}",
    )

    failures = 0
    for atom_path, description, pattern in CHECKS:
        text = open(atom_path).read().replace("\n", " ")
        if re.search(pattern, text, re.DOTALL):
            print(f"PASS  {atom_path} :: {description}")
        else:
            print(f"DRIFT {atom_path} :: {description}")
            failures += 1
    if failures:
        print(f"\n{failures} drift(s) — reconcile atoms with {CONFIG} before preregistration.")
        return 1
    print(f"\nOK — {len(CHECKS)} method claims match the frozen config.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
