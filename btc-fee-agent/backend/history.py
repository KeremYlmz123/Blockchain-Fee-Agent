import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "history.csv"


def _ensure_file(headers: List[str]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not HISTORY_PATH.exists():
        with HISTORY_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()


def append_history(rows: Iterable[dict]) -> None:
    """Append iterable of rows to history CSV with a timestamp column."""
    headers = ["timestamp", "priority", "base_fee_sat_vb", "mempool_tx_count", "recommended_fee_sat_vb"]
    _ensure_file(headers)
    timestamp = datetime.now(timezone.utc).isoformat()
    with HISTORY_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        for row in rows:
            writer.writerow({"timestamp": timestamp, **row})


def read_recent(limit: int = 10) -> list[dict]:
    """Read the last `limit` records from history."""
    if not HISTORY_PATH.exists():
        return []
    with HISTORY_PATH.open("r", newline="", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    return reader[-limit:]
