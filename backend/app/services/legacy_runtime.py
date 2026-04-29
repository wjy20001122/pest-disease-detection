from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ml import config
from app.ml.mypredictor import ONNXPredictor
from app.ml.tracker_predictor import TrackerPredictor
from app.ml import tracker_config


@dataclass(frozen=True)
class LegacyRuntime:
    config: Any
    ONNXPredictor: Any
    TrackerPredictor: Any
    tracker_config: Any


_runtime: LegacyRuntime | None = None


def load_legacy_runtime() -> LegacyRuntime:
    global _runtime
    if _runtime is not None:
        return _runtime

    _runtime = LegacyRuntime(
        config=config,
        ONNXPredictor=ONNXPredictor,
        TrackerPredictor=TrackerPredictor,
        tracker_config=tracker_config,
    )
    return _runtime