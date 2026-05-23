#!/usr/bin/env python3
"""Batch runner — runs all visible scenarios and prints a grade summary.

    python run_tests.py            # visible scenarios only
    python run_tests.py --grade    # full autograder emulation (same scenarios, strict thresholds)
"""
import argparse
import multiprocessing as mp
import sys

from sim.config import load_scenario
from harness.runner import run_scenario
from harness.grader import grade_scenario
from tracker.node import Tracker

VISIBLE_SCENARIOS = [1, 2, 3, 4, 5, 6, 7]


def run_all(strict: bool = False):
    results = []
    for sid in VISIBLE_SCENARIOS:
        scenario = load_scenario(sid)
        print(f"  [{sid}] {scenario.name}… ", end="", flush=True)
        log = run_scenario(scenario, Tracker)
        result = grade_scenario(scenario, log)
        tag = "PASS" if result.passed else "FAIL"
        print(f"{tag}  —  {result.reason}")
        results.append(result)

    passed = sum(r.passed for r in results)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  {passed}/{total} scenarios passed", end="")
    if passed >= 6:
        print("  ← meets submission threshold (6/7)")
    else:
        print(f"  ← need at least 6/7 to pass")
    print(f"{'='*60}")
    return passed >= 6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grade", action="store_true",
                        help="Emulate autograder (strict mode)")
    args = parser.parse_args()

    print("Running all visible scenarios…\n")
    ok = run_all(strict=args.grade)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
