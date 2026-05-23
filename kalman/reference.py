"""Reference Kalman filter — 3-D constant-velocity model.

Students call predict() and update(); they do not modify this file.
"""
from __future__ import annotations
import numpy as np
from msgs.types import Observation, TrackedState, TRACKING

# Observation matrix: we observe [x, y, z] from state [x, y, z, vx, vy, vz]
_H = np.zeros((3, 6))
_H[0, 0] = _H[1, 1] = _H[2, 2] = 1.0

_R_RADAR = (15.0 ** 2) * np.eye(3)   # radar noise variance (σ = 15 m)
_R_GPS   = (2.0 ** 2) * np.eye(3)    # GPS transponder noise variance (σ = 2 m)

_PROCESS_ACCEL_STD = 2.0  # m/s² — models aircraft manoeuvres


def _F(dt: float) -> np.ndarray:
    """State-transition matrix for constant-velocity model.

    No acceleration state. The filter assumes straight-line flight between updates.
    Sharp manoeuvres produce systematic lag: the model is wrong, not the implementation.
    """
    F = np.eye(6)
    F[0, 3] = F[1, 4] = F[2, 5] = dt
    return F


def _Q(dt: float) -> np.ndarray:
    """Discrete-time process-noise covariance (piecewise-constant accel model)."""
    q = _PROCESS_ACCEL_STD ** 2
    Q = np.zeros((6, 6))
    for i in range(3):
        Q[i, i]     = (dt ** 4 / 4) * q
        Q[i, i + 3] = (dt ** 3 / 2) * q
        Q[i + 3, i] = (dt ** 3 / 2) * q
        Q[i+3, i+3] = (dt ** 2)     * q
    return Q


class KalmanFilter:
    """Provided Kalman filter. Call predict() and update() — do not subclass."""

    def init_from_obs(self, obs: Observation) -> TrackedState:
        """Bootstrap a new track from the first observation."""
        return TrackedState(
            t=obs.t,
            pos=obs.pos.copy(),
            vel=np.zeros(3),
            cov=np.diag([500.0, 500.0, 500.0, 100.0, 100.0, 100.0]),
        )

    def predict(self, state: TrackedState, dt: float) -> TrackedState:
        """Propagate state forward by dt seconds with no new observation."""
        x = np.concatenate([state.pos, state.vel])
        F = _F(dt)
        Q = _Q(dt)
        x_new = F @ x
        P_new = F @ state.cov @ F.T + Q
        return TrackedState(
            t=state.t + dt,
            pos=x_new[:3],
            vel=x_new[3:],
            cov=P_new,
            status=state.status,
        )

    def update(self, state: TrackedState, obs: Observation) -> TrackedState:
        """Fuse a fresh observation into the current state."""
        R = _R_RADAR if obs.sensor == "radar" else _R_GPS
        x = np.concatenate([state.pos, state.vel])
        P = state.cov
        y = obs.pos - _H @ x
        S = _H @ P @ _H.T + R
        K = P @ _H.T @ np.linalg.solve(S.T, np.eye(3)).T
        x_new = x + K @ y
        P_new = (np.eye(6) - K @ _H) @ P
        return TrackedState(
            t=obs.t,
            pos=x_new[:3],
            vel=x_new[3:],
            cov=P_new,
            status=TRACKING,
        )
