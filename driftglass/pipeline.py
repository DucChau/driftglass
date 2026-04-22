"""
Pipeline: orchestrates multiple detectors over a data stream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generator, List, Tuple

from driftglass.detectors import (
    AdwinLite,
    DetectorResult,
    KLDivergenceDetector,
    PageHinkley,
    Severity,
    ZScoreSpike,
)


@dataclass
class PipelineConfig:
    enable_page_hinkley: bool = True
    enable_adwin: bool = True
    enable_zscore: bool = True
    enable_kl: bool = True


@dataclass
class Pipeline:
    """Runs a battery of drift detectors on each incoming data point."""

    config: PipelineConfig = field(default_factory=PipelineConfig)
    _detectors: list = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.config.enable_page_hinkley:
            self._detectors.append(PageHinkley())
        if self.config.enable_adwin:
            self._detectors.append(AdwinLite())
        if self.config.enable_zscore:
            self._detectors.append(ZScoreSpike())
        if self.config.enable_kl:
            self._detectors.append(KLDivergenceDetector())

    def reset(self) -> None:
        for d in self._detectors:
            d.reset()

    def feed(self, value: float) -> List[DetectorResult]:
        """Feed a single value and return results from all detectors."""
        return [d.update(value) for d in self._detectors]

    def feed_stream(
        self, stream: Generator[float, None, None]
    ) -> Generator[Tuple[int, float, List[DetectorResult]], None, None]:
        """Iterate through a stream, yielding (index, value, results) tuples."""
        for i, value in enumerate(stream):
            results = self.feed(value)
            yield i, value, results

    @property
    def detector_names(self) -> List[str]:
        return [d.name for d in self._detectors]
