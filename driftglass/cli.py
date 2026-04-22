"""
CLI entrypoint for driftglass.

Usage:
    driftglass run --scenario gradual --steps 800
    driftglass list-scenarios
"""

from __future__ import annotations

import time
from typing import Optional

import click
from rich.console import Console
from rich.live import Live

from driftglass import __version__
from driftglass.detectors import Severity
from driftglass.display import build_dashboard
from driftglass.generators import SCENARIOS
from driftglass.pipeline import Pipeline, PipelineConfig


console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="driftglass")
def main() -> None:
    """🔬 driftglass — real-time data drift detection from your terminal."""
    pass


@main.command()
def list_scenarios() -> None:
    """List available data scenarios."""
    console.print("\n[bold cyan]Available scenarios:[/]")
    for name, fn in SCENARIOS.items():
        doc = (fn.__doc__ or "").strip().split("\n")[0]
        console.print(f"  [green]{name:20s}[/] {doc}")
    console.print()


@main.command()
@click.option(
    "--scenario",
    "-s",
    type=click.Choice(list(SCENARIOS.keys())),
    default="gradual",
    help="Data scenario to simulate.",
)
@click.option("--steps", "-n", type=int, default=600, help="Number of data points to stream.")
@click.option("--delay", "-d", type=float, default=0.05, help="Seconds between steps.")
@click.option("--seed", type=int, default=None, help="Random seed for reproducibility.")
def run(scenario: str, steps: int, delay: float, seed: Optional[int]) -> None:
    """Run a drift detection simulation."""
    import random as _random

    if seed is not None:
        _random.seed(seed)

    gen_fn = SCENARIOS[scenario]
    stream = gen_fn()
    pipeline = Pipeline(config=PipelineConfig())

    history: list[float] = []
    drift_events = 0
    warning_events = 0

    console.print(f"\n[bold cyan]🔬 driftglass[/] v{__version__}")
    console.print(f"   scenario: [green]{scenario}[/]  steps: {steps}  delay: {delay}s\n")

    with Live(console=console, refresh_per_second=12) as live:
        for i, value, results in pipeline.feed_stream(stream):
            if i >= steps:
                break

            history.append(value)
            for r in results:
                if r.severity == Severity.DRIFT:
                    drift_events += 1
                elif r.severity == Severity.WARNING:
                    warning_events += 1

            dashboard = build_dashboard(i, value, results, history, drift_events, warning_events)
            live.update(dashboard)
            time.sleep(delay)

    console.print(f"\n[bold]Simulation complete.[/]")
    console.print(f"  Total drift events:   [red]{drift_events}[/]")
    console.print(f"  Total warnings:       [yellow]{warning_events}[/]")
    console.print(f"  Steps processed:      {min(i + 1, steps)}")
    console.print()


@main.command()
@click.option("--scenario", "-s", type=click.Choice(list(SCENARIOS.keys())), default="sudden")
@click.option("--steps", "-n", type=int, default=600)
@click.option("--seed", type=int, default=42)
def report(scenario: str, steps: int, seed: int) -> None:
    """Generate a static drift report (non-interactive)."""
    import random as _random

    _random.seed(seed)

    gen_fn = SCENARIOS[scenario]
    stream = gen_fn()
    pipeline = Pipeline(config=PipelineConfig())

    drift_log: list[dict] = []
    for i, value, results in pipeline.feed_stream(stream):
        if i >= steps:
            break
        for r in results:
            if r.severity in (Severity.DRIFT, Severity.WARNING):
                drift_log.append(
                    {"step": i, "value": round(value, 2), "detector": r.metric_name, "severity": r.severity.value, "detail": r.message}
                )

    console.print(f"\n[bold cyan]📊 Drift Report[/] — scenario=[green]{scenario}[/]  steps={steps}  seed={seed}\n")

    if not drift_log:
        console.print("  [green]No drift or warnings detected![/]\n")
        return

    from rich.table import Table

    table = Table(title="Detected Events", border_style="blue")
    table.add_column("Step", justify="right")
    table.add_column("Value", justify="right")
    table.add_column("Detector")
    table.add_column("Severity")
    table.add_column("Detail")

    for entry in drift_log:
        sev_style = "red" if entry["severity"] == "drift" else "yellow"
        table.add_row(
            str(entry["step"]),
            str(entry["value"]),
            entry["detector"],
            f"[{sev_style}]{entry['severity']}[/]",
            entry["detail"],
        )

    console.print(table)
    console.print(f"\n  Total events: {len(drift_log)}\n")


if __name__ == "__main__":
    main()
