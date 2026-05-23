"""Scenario configuration loader."""
from __future__ import annotations
import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any

SCENARIOS_DIR = Path(__file__).parent.parent / "harness" / "scenarios"


def _load_jsonc(path: Path) -> dict:
    text = path.read_text()
    stripped = re.sub(r'//[^\n]*', '', text)   # strip // comments
    return json.loads(stripped)


@dataclass
class Fault:
    type: str          # "kill_sensor" | "resume_sensor"
    sensor: str        # "radar" | "gps"
    at_t: float        # sim time to apply


@dataclass
class ScenarioConfig:
    id: int
    name: str
    duration_s: float
    aircraft: List[Dict[str, Any]]
    faults: List[Fault]
    radar_hz: float = 50.0
    gps_hz: float = 5.0
    gps_jitter_s: float = 0.0


def load_scenario(scenario_id: int) -> ScenarioConfig:
    path = SCENARIOS_DIR / f"{scenario_id}.jsonc"
    d = _load_jsonc(path)
    faults = [
        Fault(type=fa["type"], sensor=fa["sensor"], at_t=float(fa["at_t"]))
        for fa in d.get("faults", [])
    ]
    return ScenarioConfig(
        id=d["id"],
        name=d["name"],
        duration_s=float(d["duration_s"]),
        aircraft=d["aircraft"],
        faults=faults,
        radar_hz=float(d.get("radar_hz", 50.0)),
        gps_hz=float(d.get("gps_hz", 5.0)),
        gps_jitter_s=float(d.get("gps_jitter_s", 0.0)),
    )
