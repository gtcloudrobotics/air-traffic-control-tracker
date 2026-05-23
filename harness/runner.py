"""Scenario runner — starts sensor processes, runs tracker tick loop, records output."""
from __future__ import annotations
import time
import multiprocessing as mp
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import numpy as np

from msgs.types import SharedSlot, TrackedState, TRACK_LOST
from sim.config import ScenarioConfig, Fault
from sim.sensors import radar_worker, gps_worker
from sim.world import build_aircraft
from kalman.reference import KalmanFilter


@dataclass
class TrackerConfig:
    radar_slot: SharedSlot
    gps_slot: SharedSlot
    output_slot: SharedSlot
    kalman: KalmanFilter
    radar_hz: float = 50.0
    gps_hz: float = 5.0


@dataclass
class LogEntry:
    t: float
    truth_pos: np.ndarray   # ground-truth position of first aircraft
    tracked: Optional[TrackedState]


def run_scenario(
    scenario: ScenarioConfig,
    tracker_cls,
    viz_queue: Optional[mp.Queue] = None,
    run_event: Optional[mp.Event] = None,
) -> List[LogEntry]:
    """
    Orchestrate a full scenario run.

    Returns a list of LogEntry objects that the grader evaluates.
    """
    manager = mp.Manager()

    radar_slot = SharedSlot(manager)
    gps_slot   = SharedSlot(manager)
    output_slot = SharedSlot(manager)
    kalman = KalmanFilter()

    config = TrackerConfig(
        radar_slot=radar_slot,
        gps_slot=gps_slot,
        output_slot=output_slot,
        kalman=kalman,
        radar_hz=scenario.radar_hz,
        gps_hz=scenario.gps_hz,
    )
    tracker = tracker_cls(config)

    # fault control events — set = sensor is dead
    radar_fault = manager.Event()
    gps_fault   = manager.Event()
    stop_event  = manager.Event()

    aircraft_specs = scenario.aircraft

    radar_proc = mp.Process(
        target=radar_worker,
        args=(aircraft_specs, radar_slot, stop_event, radar_fault),
        kwargs={"hz": scenario.radar_hz},
        daemon=True,
    )
    gps_proc = mp.Process(
        target=gps_worker,
        args=(aircraft_specs, gps_slot, stop_event, gps_fault),
        kwargs={"hz": scenario.gps_hz, "jitter_s": scenario.gps_jitter_s},
        daemon=True,
    )

    aircraft = [build_aircraft(s) for s in aircraft_specs]

    log: List[LogEntry] = []
    dt = 1.0 / 50.0
    t = 0.0
    next_tick = time.monotonic()
    sensors_started = False

    pending_faults: List[Fault] = list(scenario.faults)

    try:
        while t < scenario.duration_s:
            # pause support: block until browser sends start (S key)
            if run_event is not None and not run_event.is_set():
                run_event.wait()
                next_tick = time.monotonic()  # reset timing so we don't rush to catch up

            # Start sensors on the first tick (after any S-press wait) so their
            # internal t counter is aligned with the harness t counter.
            if not sensors_started:
                radar_proc.start()
                gps_proc.start()
                sensors_started = True

            next_tick += dt

            # apply any faults that are due
            due = [f for f in pending_faults if f.at_t <= t]
            for fault in due:
                pending_faults.remove(fault)
                target = radar_fault if fault.sensor == "radar" else gps_fault
                if fault.type == "kill_sensor":
                    target.set()
                elif fault.type == "resume_sensor":
                    target.clear()

            tracker.tick(t)
            state: Optional[TrackedState] = output_slot.read()

            truth = aircraft[0].pos_at(t)
            log.append(LogEntry(t=t, truth_pos=truth, tracked=state))

            if viz_queue is not None:
                has_state = state is not None and state.status != TRACK_LOST
                r_obs = radar_slot.read()
                g_obs = gps_slot.read()
                viz_queue.put({
                    "t": t,
                    "scenario": scenario.name,
                    "truth": truth.tolist(),
                    "pos": state.pos.tolist() if has_state else None,
                    "cov_diag": np.diag(state.cov[:3, :3]).tolist() if has_state else None,
                    "status": state.status if state is not None else "no_output",
                    "radar_age_s": round(t - r_obs.t, 4) if r_obs is not None else None,
                    "gps_age_s":   round(t - g_obs.t, 4) if g_obs is not None else None,
                })

            t += dt
            now = time.monotonic()
            if now < next_tick:
                time.sleep(next_tick - now)
    finally:
        stop_event.set()
        for proc in (radar_proc, gps_proc):
            proc.join(timeout=2)
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=1)
        manager.shutdown()

    return log
