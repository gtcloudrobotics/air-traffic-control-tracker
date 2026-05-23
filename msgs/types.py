from __future__ import annotations
from dataclasses import dataclass
import multiprocessing as mp
import numpy as np
from typing import Optional

TRACK_LOST = "track_lost"
TRACKING = "tracking"


@dataclass
class Observation:
    t: float          # sim time in seconds
    pos: np.ndarray   # shape (3,) — [x, y, z] metres
    sensor: str       # "radar" or "gps"


@dataclass
class TrackedState:
    t: float
    pos: np.ndarray   # shape (3,)
    vel: np.ndarray   # shape (3,)
    cov: np.ndarray   # shape (6, 6)
    status: str = TRACKING


class SharedSlot:
    """Latest-value slot — non-blocking read, writer always overwrites.

    Backed by a multiprocessing Manager so it is safe across processes.
    The student never constructs this directly; the harness passes it in.
    """

    def __init__(self, manager: "mp.managers.SyncManager"):
        self._d = manager.dict({"v": None})
        self._lock = manager.Lock()

    def write(self, value) -> None:
        with self._lock:
            self._d["v"] = value

    def read(self) -> Optional[object]:
        with self._lock:
            return self._d["v"]
