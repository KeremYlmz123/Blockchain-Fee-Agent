from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HISTORY_PATH = DATA_DIR / "history.csv"
OUTPUT_PATH = DATA_DIR / "plot.png"


def read_history() -> List[Dict[str, str]]:
    if not HISTORY_PATH.exists():
        print("history.csv not found; nothing to plot.")
        return []
    with HISTORY_PATH.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_rows(rows: List[Dict[str, str]]) -> Dict[str, List[tuple]]:
    series: Dict[str, List[tuple]] = {"fast": [], "normal": [], "cheap": []}
    for row in rows:
        ts = row.get("timestamp")
        priority = row.get("priority")
        fee = row.get("recommended_fee_sat_vb")
        if not ts or not priority or not fee:
            continue
        try:
            dt = datetime.fromisoformat(ts)
            fee_val = float(fee)
        except ValueError:
            continue
        series.setdefault(priority, []).append((dt, fee_val))

    # sort by timestamp per series
    for key, values in series.items():
        series[key] = sorted(values, key=lambda x: x[0])
    return series


def plot_history(series: Dict[str, List[tuple]]) -> None:
    plt.figure(figsize=(8, 4))
    colors = {"fast": "#ff7f50", "normal": "#1e90ff", "cheap": "#32cd32"}

    has_data = False
    for priority, points in series.items():
        if not points:
            continue
        has_data = True
        xs, ys = zip(*points)
        plt.plot(xs, ys, label=priority.capitalize(), color=colors.get(priority, None))

    if not has_data:
        print("No data to plot.")
        return

    plt.title("Recommended Fee Over Time")
    plt.xlabel("Timestamp")
    plt.ylabel("Recommended Fee (sat/vB)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PATH, dpi=150)
    print(f"Saved plot to {OUTPUT_PATH}")


def main() -> None:
    rows = read_history()
    series = parse_rows(rows)
    plot_history(series)


if __name__ == "__main__":
    main()
