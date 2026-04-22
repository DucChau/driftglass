"""
Statistical detectors for concept drift and distribution shift.

Each detector implements a simple protocol:
    .update(value) -> DetectorResult
    .reset()
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List

import numpy as np
from scipy import stats


class Severity(str, Enum):
    OK = "ok"
    WARNING = "warning"
    DRIFT = "drift"


@dataclass
class DetectorResult:
    severity: Severity
    metric_name: str
    value: float
    threshold: float
    message: str


# ─── Page-Hinkley Test ────────────────────────────────────────────────────
# Detects abrupt changes in the mean of a Gaussian signal.

@dataclass
class PageHinkley:
    """Page-Hinkley change-point detector."""

    delta: float = 0.005
    threshold: float = 50.0
    alpha: float = 1 - 0.0001
    _sum: float = field(default=0.0, init=False)
    _x_mean: float = field(default=0.0, init=False)
    _n: int = field(default=0, init=False)
    _min_sum: float = field(default=float("inf"), init=False)
    name: str = "page_hinkley"

    def reset(self) -> None:
        self._sum = 0.0
        self._x_mean = 0.0
        self._n = 0
        self._min_sum = float("inf")

    def update(self, value: float) -> DetectorResult:
        self._n += 1
        self._x_mean = self._x_mean * self.alpha + value * (1 - self.alpha)
        self._sum += value - self._x_mean - self.delta
        self._min_sum = min(self._min_sum, self._sum)
        ph_value = self._sum - self._min_sum

        if ph_value > self.threshold:
            severity = Severity.DRIFT
            msg = f"Page-Hinkley detected drift (PH={ph_value:.2f} > {self.threshold})"
        elif ph_value > self.threshold * 0.7:
            severity = Severity.WARNING
            msg = f"Page-Hinkley approaching threshold (PH={ph_value:.2f})"
        else:
            severity = Severity.OK
            msg = "No drift detected"

        return DetectorResult(
            severity=severity,
            metric_name=self.name,
            value=ph_value,
            threshold=self.threshold,
            message=msg,
        )


# ─── ADWIN-lite (simplified) ──────────────────────────────────────────────
# Adaptive windowing: keeps a sliding window and splits it to find mean shifts.

@dataclass
class AdwinLite:
    """Simplified ADWIN-style drift detector using a two-window t-test."""

    window_size: int = 200
    significance: float = 0.01
    name: str = "adwin_lite"
    _buffer: List[float] = field(default_factory=list, init=False)

    def reset(self) -> None:
        self._buffer = []

    def update(self, value: float) -> DetectorResult:
        self._buffer.append(value)
        if len(self._buffer) > self.window_size:
            self._buffer.pop(0)

        if len(self._buffer) < 40:
            return DetectorResult(Severity.OK, self.name, 0.0, self.significance, "Warming up")

        mid = len(self._buffer) // 2
        left = np.array(self._buffer[:mid])
        right = np.array(self._buffer[mid:])
        t_stat, p_val = stats.ttest_ind(left, right, equal_var=False)

        if math.isnan(p_val):
            p_val = 1.0

        if p_val < self.significance:
            severity = Severity.DRIFT
            msg = f"ADWIN detected distribution shift (p={p_val:.4f})"
        elif p_val < self.significance * 5:
            severity = Severity.WARNING
            msg = f"ADWIN warning — possible shift (p={p_val:.4f})"
        else:
            severity = Severity.OK
            msg = "No shift detected"

        return DetectorResult(
            severity=severity,
            metric_name=self.name,
            value=p_val,
            threshold=self.significance,
            message=msg,
        )


# ─── Z-Score Spike Detector ───────────────────────────────────────────────

@dataclass
class ZScoreSpike:
    """Rolling z-score based spike/outlier detector."""

    window_size: int = 100
    z_threshold: float = 3.5
    name: str = "zscore_spike"
    _buffer: List[float] = field(default_factory=list, init=False)

    def reset(self) -> None:
        self._buffer = []

    def update(self, value: float) -> DetectorResult:
        self._buffer.append(value)
        if len(self._buffer) > self.window_size:
            self._buffer.pop(0)

        if len(self._buffer) < 10:
            return DetectorResult(Severity.OK, self.name, 0.0, self.z_threshold, "Warming up")

        arr = np.array(self._buffer)
        mean = arr.mean()
        std = arr.std()
        if std == 0:
            z = 0.0
        else:
            z = abs(value - mean) / std

        if z > self.z_threshold:
            severity = Severity.DRIFT
            msg = f"Z-Score spike detected (z={z:.2f})"
        elif z > self.z_threshold * 0.7:
            severity = Severity.WARNING
            msg = f"Z-Score elevated (z={z:.2f})"
        else:
            severity = Severity.OK
            msg = "Normal"

        return DetectorResult(
            severity=severity,
            metric_name=self.name,
            value=z,
            threshold=self.z_threshold,
            message=msg,
        )


# ─── KL Divergence Window Detector ────────────────────────────────────────

@dataclass
class KLDivergenceDetector:
    """Detects drift via KL divergence between reference and recent histograms."""

    window_size: int = 200
    n_bins: int = 20
    kl_threshold: float = 0.3
    name: str = "kl_divergence"
    _buffer: List[float] = field(default_factory=list, init=False)

    def reset(self) -> None:
        self._buffer = []

    def _histogram(self, data: np.ndarray, bins: np.ndarray) -> np.ndarray:
        hist, _ = np.histogram(data, bins=bins, density=True)
        hist = hist + 1e-10  # smoothing
        return hist / hist.sum()

    def update(self, value: float) -> DetectorResult:
        self._buffer.append(value)
        if len(self._buffer) > self.window_size:
            self._buffer.pop(0)

        if len(self._buffer) < 60:
            return DetectorResult(Severity.OK, self.name, 0.0, self.kl_threshold, "Warming up")

        mid = len(self._buffer) // 2
        all_data = np.array(self._buffer)
        bins = np.linspace(all_data.min(), all_data.max(), self.n_bins + 1)

        ref = self._histogram(all_data[:mid], bins)
        cur = self._histogram(all_data[mid:], bins)
        kl = float(stats.entropy(cur, ref))

        if kl > self.kl_threshold:
            severity = Severity.DRIFT
            msg = f"KL divergence drift (KL={kl:.4f})"
        elif kl > self.kl_threshold * 0.6:
            severity = Severity.WARNING
            msg = f"KL divergence elevated (KL={kl:.4f})"
        else:
            severity = Severity.OK
            msg = "Distributions aligned"

        return DetectorResult(
            severity=severity,
            metric_name=self.name,
            value=kl,
            threshold=self.kl_threshold,
            message=msg,
        )
