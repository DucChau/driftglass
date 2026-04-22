"""
Synthetic data generators that simulate realistic data pipeline scenarios.
Each generator yields floats and optionally injects anomalies / drift.
"""

from __future__ import annotations

import math
import random
from typing import Generator


def stable_gaussian(mean: float = 100.0, std: float = 5.0) -> Generator[float, None, None]:
    """Infinite stream of Gaussian noise — the 'normal' baseline."""
    while True:
        yield random.gauss(mean, std)


def gradual_drift(
    start_mean: float = 100.0,
    end_mean: float = 130.0,
    std: float = 5.0,
    drift_start: int = 300,
    drift_duration: int = 200,
) -> Generator[float, None, None]:
    """Mean drifts linearly from start_mean to end_mean over drift_duration steps."""
    i = 0
    while True:
        if i < drift_start:
            mean = start_mean
        elif i < drift_start + drift_duration:
            progress = (i - drift_start) / drift_duration
            mean = start_mean + (end_mean - start_mean) * progress
        else:
            mean = end_mean
        yield random.gauss(mean, std)
        i += 1


def sudden_shift(
    normal_mean: float = 100.0,
    shifted_mean: float = 120.0,
    std: float = 5.0,
    shift_at: int = 400,
) -> Generator[float, None, None]:
    """Abrupt mean shift at a specific step."""
    i = 0
    while True:
        mean = normal_mean if i < shift_at else shifted_mean
        yield random.gauss(mean, std)
        i += 1


def periodic_with_spikes(
    base: float = 100.0,
    amplitude: float = 15.0,
    period: int = 50,
    spike_prob: float = 0.02,
    spike_magnitude: float = 60.0,
) -> Generator[float, None, None]:
    """Sinusoidal signal with random spikes injected."""
    i = 0
    while True:
        val = base + amplitude * math.sin(2 * math.pi * i / period) + random.gauss(0, 2)
        if random.random() < spike_prob:
            val += spike_magnitude * random.choice([-1, 1])
        yield val
        i += 1


def variance_explosion(
    mean: float = 100.0,
    normal_std: float = 3.0,
    exploded_std: float = 25.0,
    explode_at: int = 350,
) -> Generator[float, None, None]:
    """Variance suddenly increases at a given step — same mean, wider spread."""
    i = 0
    while True:
        std = normal_std if i < explode_at else exploded_std
        yield random.gauss(mean, std)
        i += 1


SCENARIOS = {
    "stable": stable_gaussian,
    "gradual": gradual_drift,
    "sudden": sudden_shift,
    "periodic-spikes": periodic_with_spikes,
    "variance-explosion": variance_explosion,
}
