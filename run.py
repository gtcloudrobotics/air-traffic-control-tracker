#!/usr/bin/env python3
"""Run a single scenario.

Examples:
    python run.py --scenario 1
    python run.py --scenario 2 --visualize
    python run.py --scenario 3 --grade
"""
import argparse
import multiprocessing as mp
import sys

from sim.config import load_scenario
from harness.runner import run_scenario
from harness.grader import grade_scenario
from tracker.node import Tracker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", "-s", type=int, required=True, choices=range(1, 8),
                        help="Scenario number (1–7)")
    parser.add_argument("--visualize", "-v", action="store_true",
                        help="Open 3D visualization (requires websockets)")
    parser.add_argument("--grade", "-g", action="store_true",
                        help="Print pass/fail after the run")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    print(f"Running scenario {scenario.id}: {scenario.name}  ({scenario.duration_s} s)")

    viz_queue = None
    viz_proc = None
    run_event = None

    if args.visualize:
        import time
        viz_queue = mp.Queue(maxsize=500)
        run_event = mp.Event()  # starts unset = paused; browser S key sets/clears it
        from viz.server import run_server
        viz_proc = mp.Process(target=run_server, args=(viz_queue, run_event), daemon=True)
        viz_proc.start()
        time.sleep(0.5)  # let server bind
        print("Open this in your browser: http://localhost:8080")
        print("Press S in the browser to start. Ctrl+C here to quit.")

    log = run_scenario(scenario, Tracker, viz_queue=viz_queue, run_event=run_event)

    if args.visualize and viz_proc:
        print("\nScenario done. Keeping server alive — press Ctrl+C to exit.")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        viz_proc.terminate()

    if args.grade or True:  # always print a quick summary
        result = grade_scenario(scenario, log)
        status = "PASS ✓" if result.passed else "FAIL ✗"
        print(f"\n{status}  —  {result.reason}")
        sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
