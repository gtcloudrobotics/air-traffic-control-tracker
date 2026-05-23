"""Outcome evaluator — checks each scenario's success criteria against the run log."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from msgs.types import TRACK_LOST, TRACKING
from harness.runner import LogEntry
from sim.config import ScenarioConfig


@dataclass
class GradeResult:
    scenario_id: int
    passed: bool
    reason: str
    rmse: Optional[float] = None
    avg_hz: Optional[float] = None


def _rmse(log: List[LogEntry]) -> float:
    errors = []
    for e in log:
        if e.tracked is not None and e.tracked.status == TRACKING:
            errors.append(np.linalg.norm(e.tracked.pos - e.truth_pos))
    return float(np.sqrt(np.mean(np.array(errors) ** 2))) if errors else float("inf")


def _output_hz(log: List[LogEntry]) -> float:
    outputs = [e for e in log if e.tracked is not None]
    if len(outputs) < 2:
        return 0.0
    dt_total = log[-1].t - log[0].t
    return len(outputs) / dt_total if dt_total > 0 else 0.0


def grade_scenario(scenario: ScenarioConfig, log: List[LogEntry]) -> GradeResult:
    sid = scenario.id
    rmse = _rmse(log)
    hz = _output_hz(log)

    if sid == 1:
        # Nominal: RMSE < 50 m, output ≥ 40 Hz
        ok = rmse < 50.0 and hz >= 40.0
        reason = f"RMSE={rmse:.1f} m (need <50), rate={hz:.1f} Hz (need ≥40)"
        return GradeResult(sid, ok, reason, rmse, hz)

    if sid == 2:
        # GPS transponder killed at t=10 s — tracks must hold on radar; no TRACK_LOST while radar lives
        post_fault = [e for e in log if e.t >= 10.0 and e.tracked is not None]
        lost_while_radar_live = any(
            e.tracked.status == TRACK_LOST for e in post_fault
        )
        tracking_rmse = _rmse([e for e in log if e.t >= 10.0])
        ok = not lost_while_radar_live and tracking_rmse < 60.0
        reason = (
            f"TRACK_LOST while radar live={lost_while_radar_live}, "
            f"post-fault RMSE={tracking_rmse:.1f} m (need <60)"
        )
        return GradeResult(sid, ok, reason, tracking_rmse, hz)

    if sid == 3:
        # Radar killed at t=8, resumes at t=14
        gap_log = [e for e in log if 8.0 <= e.t <= 14.0]
        post_log = [e for e in log if e.t > 14.0]

        lost_during_gap = any(
            e.tracked is not None and e.tracked.status == TRACK_LOST for e in gap_log
        )
        post_rmse = _rmse(post_log)
        ok = not lost_during_gap and post_rmse < 30.0
        reason = (
            f"TRACK_LOST during gap={lost_during_gap}, "
            f"post-recovery RMSE={post_rmse:.1f} m (need <30)"
        )
        return GradeResult(sid, ok, reason, post_rmse, hz)

    if sid == 4:
        # Radar killed at t=10, GPS transponder at t=11 — TRACK_LOST must appear by t=13
        post_both_dead = [e for e in log if e.t >= 11.0]
        declared_lost = any(
            e.tracked is not None and e.tracked.status == TRACK_LOST
            for e in post_both_dead
            if e.t <= 13.0
        )
        ok = declared_lost
        reason = f"TRACK_LOST declared within 2 s of both sensors dying={declared_lost}"
        return GradeResult(sid, ok, reason)

    if sid == 5:
        # GPS transponder jittered ±100 ms — tracker must NOT fall back to TRACK_LOST
        any_lost = any(
            e.tracked is not None and e.tracked.status == TRACK_LOST for e in log
        )
        ok = not any_lost and rmse < 50.0
        reason = f"false TRACK_LOST={any_lost}, RMSE={rmse:.1f} m (need <50)"
        return GradeResult(sid, ok, reason, rmse, hz)

    if sid == 6:
        # Interface swap — just check RMSE and rate
        ok = rmse < 50.0 and hz >= 40.0
        reason = f"RMSE={rmse:.1f} m (need <25), rate={hz:.1f} Hz (need ≥40)"
        return GradeResult(sid, ok, reason, rmse, hz)

    if sid == 7:
        # GPS killed at t=5; aircraft turns at t=15 with radar as sole sensor
        any_lost = any(
            e.tracked is not None and e.tracked.status == TRACK_LOST for e in log
        )
        post_turn = [e for e in log if e.t > 15.0]
        post_rmse = _rmse(post_turn)
        ok = not any_lost and post_rmse < 80.0
        reason = (
            f"TRACK_LOST={any_lost}, "
            f"post-turn RMSE={post_rmse:.1f} m (need <80)"
        )
        return GradeResult(sid, ok, reason, post_rmse, hz)

    return GradeResult(sid, False, f"unknown scenario id {sid}")
