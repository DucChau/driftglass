"""
Rich-powered terminal display for driftglass pipeline output.
"""

from __future__ import annotations

from typing import List

from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from driftglass.detectors import DetectorResult, Severity


SEVERITY_COLORS = {
    Severity.OK: "green",
    Severity.WARNING: "yellow",
    Severity.DRIFT: "bold red",
}

SEVERITY_ICONS = {
    Severity.OK: "✓",
    Severity.WARNING: "⚠",
    Severity.DRIFT: "🔴",
}


def build_dashboard(
    step: int,
    value: float,
    results: List[DetectorResult],
    history: List[float],
    drift_events: int,
    warning_events: int,
) -> Table:
    """Build the main dashboard table."""
    outer = Table.grid(padding=1)

    # Header
    header = Text()
    header.append("🔬 driftglass", style="bold cyan")
    header.append(f"  step={step}  value={value:.2f}", style="dim")
    outer.add_row(header)

    # Detector table
    det_table = Table(title="Detectors", expand=True, border_style="blue")
    det_table.add_column("Detector", style="cyan", min_width=16)
    det_table.add_column("Status", min_width=8)
    det_table.add_column("Value", justify="right", min_width=10)
    det_table.add_column("Threshold", justify="right", min_width=10)
    det_table.add_column("Message", min_width=30)

    for r in results:
        icon = SEVERITY_ICONS[r.severity]
        color = SEVERITY_COLORS[r.severity]
        det_table.add_row(
            r.metric_name,
            Text(f"{icon} {r.severity.value}", style=color),
            f"{r.value:.4f}",
            f"{r.threshold:.4f}",
            r.message,
        )

    outer.add_row(det_table)

    # Sparkline (last 60 values)
    spark = _sparkline(history[-60:])
    outer.add_row(Panel(spark, title="Recent Values", border_style="dim"))

    # Stats
    stats_text = Text()
    stats_text.append(f"  Drift events: {drift_events}", style="red")
    stats_text.append(f"  │  Warnings: {warning_events}", style="yellow")
    stats_text.append(f"  │  Total steps: {step}", style="dim")
    outer.add_row(stats_text)

    return outer


def _sparkline(values: List[float], width: int = 60) -> Text:
    """Render a tiny unicode sparkline."""
    if not values:
        return Text("(waiting for data)")
    blocks = " ▁▂▃▄▅▆▇█"
    lo, hi = min(values), max(values)
    spread = hi - lo if hi != lo else 1.0
    chars = []
    for v in values[-width:]:
        idx = int((v - lo) / spread * (len(blocks) - 1))
        idx = max(0, min(idx, len(blocks) - 1))
        chars.append(blocks[idx])
    return Text("".join(chars), style="green")
