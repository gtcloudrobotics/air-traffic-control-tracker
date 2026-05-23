"""Air-traffic-control tracker — YOUR file to implement.
"""
from msgs.types import TRACK_LOST, TrackedState


class Tracker:
    def __init__(self, config):
        self.radar_slot = config.radar_slot
        self.gps_slot = config.gps_slot
        self.output_slot = config.output_slot
        self.kalman = config.kalman

        self.track_estimated_state = None 
        self.last_radar_t = None
        self.last_gps_t = None

        # 10 missed radar pings / 5 missed GPS fixes before declaring stale.
        # The multiplier is intentionally generous: fault injection goes through
        # the multiprocessing Manager, which briefly backs up IPC and can prevent
        # the sensor worker from writing for several ticks even though the sensor
        # is still alive. A tight threshold (e.g. 5 pings) produces false TRACK_LOST
        # events at the exact moment a fault fires.
        self.stale_radar_after_s = 10 / config.radar_hz
        self.stale_gps_after_s = 5 / config.gps_hz

    def tick(self, now_s: float):
        """Called at 50 Hz by the harness. now_s is the current sim time.

        Fuse any new observations (sort by timestamp if both sensors have one),
        then check staleness: bail with TRACK_LOST if nothing's been heard from
        either sensor, otherwise predict forward to now_s and publish.
        """
         
        # Non-blocking: always returns immediately with the latest observation the sensor wrote,
        # or None if the sensor hasn't written anything yet. GPS runs at 5 Hz but this loop runs
        # at 50 Hz. So 9 out of 10 ticks, gps_slot.read() returns the exact same observation as
        # last tick. You must check obs.t against the last timestamp you saw to know whether the
        # sensor actually produced something new, or you're just seeing the previous write again.
        radar_obs = self.radar_slot.read()
        gps_obs = self.gps_slot.read()

        # TODO: implement this method.
        pass


# --- Part 2: interface design ---
#
# You just implemented inside a fixed architecture. Now reason about extending it.
#
# Suppose you need to add a barometric altimeter: 10 Hz, ±5 m vertical accuracy.
# Answer the questions below in a comment block directly beneath each one:
#
#   1. Where does the new slot live? (look at harness/runner.py — that's where
#      radar_slot and gps_slot are created and handed to the tracker via config)
#   2. What change to the config object or __init__ signature does adding it require?
#      Is that change localized, or does it ripple into other files?
#   3. What staleness threshold makes sense for 10 Hz relative to the existing ones?
#   4. If the altimeter goes stale but radar and GPS are healthy, should the tracker
#      degrade silently or surface it in the output? What are the tradeoffs?
#
# The point is not the altimeter itself. It's what adding any new sensor forces you
# to decide about ownership, interfaces, and how failures propagate across boundaries.