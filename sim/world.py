"""Aircraft simulator — deterministic, waypoint-based trajectories."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
import numpy as np


@dataclass
class Waypoint:
    t: float
    pos: np.ndarray  # [x, y, z] metres


@dataclass
class Aircraft:
    id: str
    waypoints: List[Waypoint]

    def pos_at(self, t: float) -> np.ndarray:
        """Linearly interpolate position at sim time t."""
        wps = self.waypoints
        if t <= wps[0].t:
            return wps[0].pos.copy()
        if t >= wps[-1].t:
            return wps[-1].pos.copy()
        for i in range(len(wps) - 1):
            w0, w1 = wps[i], wps[i + 1]
            if w0.t <= t <= w1.t:
                alpha = (t - w0.t) / (w1.t - w0.t)
                return w0.pos + alpha * (w1.pos - w0.pos)
        return wps[-1].pos.copy()

    def vel_at(self, t: float) -> np.ndarray:
        """Velocity (m/s) from finite-difference of the waypoint segments."""
        wps = self.waypoints
        if t <= wps[0].t or t >= wps[-1].t:
            return np.zeros(3)
        for i in range(len(wps) - 1):
            w0, w1 = wps[i], wps[i + 1]
            if w0.t <= t <= w1.t:
                return (w1.pos - w0.pos) / (w1.t - w0.t)
        return np.zeros(3)


def build_aircraft(spec: dict) -> Aircraft:
    waypoints = [
        Waypoint(t=float(w["t"]), pos=np.array(w["pos"], dtype=float))
        for w in spec["waypoints"]
    ]
    return Aircraft(id=spec["id"], waypoints=waypoints)
