"""Tests for the driftglass pipeline."""

from driftglass.generators import stable_gaussian
from driftglass.pipeline import Pipeline, PipelineConfig


def test_pipeline_feed():
    pipe = Pipeline(config=PipelineConfig())
    results = pipe.feed(42.0)
    assert len(results) == 4  # all four detectors


def test_pipeline_stream():
    pipe = Pipeline(config=PipelineConfig())
    gen = stable_gaussian(mean=100, std=1)
    items = list(zip(range(10), pipe.feed_stream(gen)))
    assert len(items) == 10
