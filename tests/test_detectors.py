"""Tests for driftglass detectors."""

import random

from driftglass.detectors import (
    AdwinLite,
    KLDivergenceDetector,
    PageHinkley,
    Severity,
    ZScoreSpike,
)


def test_page_hinkley_detects_shift():
    random.seed(42)
    ph = PageHinkley(threshold=30.0)
    severities = []
    for i in range(600):
        val = random.gauss(100, 3) if i < 300 else random.gauss(120, 3)
        result = ph.update(val)
        severities.append(result.severity)
    assert Severity.DRIFT in severities, "Page-Hinkley should detect the shift"


def test_zscore_detects_spike():
    random.seed(0)
    zs = ZScoreSpike(window_size=50, z_threshold=3.0)
    # Feed normal data
    for _ in range(60):
        zs.update(random.gauss(50, 2))
    # Inject spike
    result = zs.update(500.0)
    assert result.severity == Severity.DRIFT


def test_adwin_detects_shift():
    random.seed(7)
    adwin = AdwinLite(window_size=150, significance=0.05)
    severities = []
    for i in range(400):
        val = random.gauss(50, 2) if i < 200 else random.gauss(60, 2)
        result = adwin.update(val)
        severities.append(result.severity)
    assert Severity.DRIFT in severities, "ADWIN should detect the distribution shift"


def test_kl_divergence_stable():
    random.seed(99)
    kl = KLDivergenceDetector(window_size=200, kl_threshold=0.5)
    results = []
    for _ in range(200):
        r = kl.update(random.gauss(100, 5))
        results.append(r)
    # Stable data — should NOT trigger drift
    drift_count = sum(1 for r in results if r.severity == Severity.DRIFT)
    assert drift_count == 0, "KL should not fire on stable data"
