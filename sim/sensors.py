"""Sensor processes — each runs as an independent subprocess.

The harness starts these; students do not call them directly.
"""
from __future__ import annotations
import time
import numpy as np
import multiprocessing as mp
from msgs.types import Observation, SharedSlot
from sim.world import Aircraft
from typing import List


def _sleep_precise(until: float) -> None:
    """Busy-wait the last 1 ms for sub-millisecond accuracy."""
    coarse = until - 0.001
    if time.monotonic() < coarse:
        time.sleep(coarse - time.monotonic())
    while time.monotonic() < until:
        pass


def radar_worker(
    aircraft_specs: list,
    slot: SharedSlot,
    stop_event: mp.Event,
    fault_event: mp.Event,
    hz: float = 50.0,
    rng_seed: int = 42,
) -> None:
    """σ = 15 m. Rate set by hz. Killed by fault_event; stopped by stop_event."""
    from sim.world import build_aircraft
    aircraft: List[Aircraft] = [build_aircraft(s) for s in aircraft_specs]
    rng = np.random.default_rng(rng_seed)
    dt = 1.0 / hz
    t = 0.0
    next_tick = time.monotonic()
    while not stop_event.is_set():
        next_tick += dt
        if not fault_event.is_set():
            for ac in aircraft:
                truth = ac.pos_at(t)
                noisy = truth + rng.normal(0.0, 15.0, 3)
                slot.write(Observation(t=t, pos=noisy, sensor="radar"))
        t += dt
        _sleep_precise(next_tick)


def gps_worker(
    aircraft_specs: list,
    slot: SharedSlot,
    stop_event: mp.Event,
    fault_event: mp.Event,
    hz: float = 5.0,
    jitter_s: float = 0.0,
    rng_seed: int = 99,
) -> None:
    """σ = 2 m. Rate set by hz. Killed by fault_event; stopped by stop_event."""
    from sim.world import build_aircraft
    aircraft: List[Aircraft] = [build_aircraft(s) for s in aircraft_specs]
    rng = np.random.default_rng(rng_seed)
    dt = 1.0 / hz
    t = 0.0
    next_tick = time.monotonic()
    while not stop_event.is_set():
        next_tick += dt
        if not fault_event.is_set():
            jitter = float(rng.uniform(-jitter_s, jitter_s)) if jitter_s > 0 else 0.0
            time.sleep(max(0.0, jitter))
            for ac in aircraft:
                truth = ac.pos_at(t)
                noisy = truth + rng.normal(0.0, 2.0, 3)
                slot.write(Observation(t=t, pos=noisy, sensor="gps"))
        t += dt
        _sleep_precise(next_tick)
