import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from collections import Counter

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .agent import estimate_fee, recommend_fee
from .data_fetcher import get_fee_recommendations, get_mempool_stats, get_mining_targets
from .history import append_history, read_recent
from .llm import generate_llm_explanation
from .models import (
    CompareResponse,
    FeeRecommendation,
    HealthStatus,
    LiveStatus,
    MiningTargetResponse,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "cache.json"
LATEST_STATE = {
    "updated_at_epoch": None,
    "timestamp": None,
    "fee_data": None,
    "mempool_data": None,
    "cache_used": False,
    "error": None,
    "source": "mempool.space",
    "network_state": None,
    "network_note": None,
}


async def _refresh_live_state():
    while True:
        await asyncio.to_thread(refresh_once)
        await asyncio.sleep(10)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(_refresh_live_state())


def _load_cache_file() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        with CACHE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache_file(fee_data: dict, mempool: dict) -> None:
    payload = {"fees": fee_data, "mempool": mempool}
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def classify_network_state(fee_data: dict, mempool: dict) -> tuple[str, str]:
    mempool_tx = int((mempool or {}).get("count", 0) or 0)
    fastest = fee_data.get("fastestFee") or fee_data.get("halfHourFee") or 0
    economy = fee_data.get("economyFee") or fee_data.get("minimumFee") or 0
    fee_spread = max(0, fastest - economy)

    if mempool_tx < 120_000 and fee_spread <= 2:
        return "calm", "Network is calm; fee differences may have limited impact on speed."
    if mempool_tx < 250_000 and fee_spread <= 8:
        return "moderate", "Network is moderately congested; higher fees might gain speed."
    return "congested", "Network is congested; low fees may cause significant delays."


def _apply_agent_messages(rec: FeeRecommendation, network_state: str | None, fee_data: dict) -> FeeRecommendation:
    state_text = network_state or "unknown"
    summary = (
        f"Network state: {state_text}. ETA {rec.eta_blocks_min}-{rec.eta_blocks_max} blocks "
        f"(~{rec.eta_minutes_min}-{rec.eta_minutes_max} min). Risk: {rec.risk_level}."
    )
    what_if = None
    economy_fee = fee_data.get("economyFee") or fee_data.get("minimumFee")
    if rec.mode == "recommend":
        if network_state == "calm" and rec.priority == "fast":
            what_if = "Network is calm; medium fee might offer similar speed with cost savings."
        if network_state == "congested" and rec.priority == "slow":
            what_if = "Network is congested; choosing slow may cause severe delays, consider medium or fast."
    else:  # estimate
        if economy_fee and rec.input_fee_sat_vb and rec.input_fee_sat_vb < economy_fee:
            what_if = f"Fee is below economy level ({economy_fee} sat/vB); trying that or medium threshold will shorten confirmation time."

    rec.agent_summary = summary
    rec.what_if_hint = what_if
    return rec


def _build_compare_verdict(network_state: str | None, delta_sat: int, overpay_pct: float) -> tuple[str, str]:
    if network_state == "calm":
        return (
            "Network Calm",
            f"Fee difference is small (+{delta_sat} sat/vB, {overpay_pct}%) and speed gain might be limited.",
        )
    if network_state == "congested":
        return (
            "Network Congested",
            f"Fast fee (+{delta_sat} sat/vB, {overpay_pct}%) can reduce delay risk; slow choice may cause severe delays.",
        )
    return (
        "Network Moderate",
        f"Difference between Fast and Medium is +{delta_sat} sat/vB ({overpay_pct}%); higher fee might reduce wait time in moderate congestion.",
    )


def _history_insight(items: list[dict], network_state: str | None) -> str:
    if not items:
        return "No records yet."
    counts = Counter(i.get("priority", "unknown") for i in items)
    top = counts.most_common(1)[0][0]
    total = sum(counts.values())
    state = network_state or "unknown"
    if total >= 5:
        share_top = counts[top] / total
        if state == "calm" and top in ("slow", "medium") and share_top > 0.5:
            return "Recent records show a trend towards low/medium fees; logical since network is calm."
        if state == "calm" and top == "fast" and share_top > 0.5:
            return "Recent records show a trend towards fast fees; potential overpayment since network is calm."
        if state == "congested" and top == "slow" and share_top > 0.4:
            return "Recent records show a trend towards slow fees in a congested network; confirmation times may increase."
    return f"Records are mixed; network state: {state}."


def refresh_once():
    try:
        fee_data, fee_cache_used = get_fee_recommendations()
        mempool, mempool_cache_used = get_mempool_stats()
        cache_used = fee_cache_used or mempool_cache_used
        _save_cache_file(fee_data, mempool)
    except Exception as exc:
        cached = _load_cache_file()
        fee_data = cached.get("fees") or {}
        mempool = cached.get("mempool") or {}
        cache_used = True
        LATEST_STATE["error"] = str(exc)
    else:
        LATEST_STATE["error"] = None

    net_state, net_note = classify_network_state(fee_data, mempool)

    now = datetime.now(timezone.utc)
    LATEST_STATE.update(
        {
            "updated_at_epoch": now.timestamp(),
            "timestamp": now.isoformat(),
            "fee_data": fee_data,
            "mempool_data": mempool,
            "cache_used": cache_used,
            "source": "mempool.space",
            "network_state": net_state,
            "network_note": net_note,
        }
    )


def _get_live_data():
    if LATEST_STATE["fee_data"] is None or LATEST_STATE["mempool_data"] is None:
        refresh_once()
    return (
        LATEST_STATE["fee_data"],
        LATEST_STATE["mempool_data"],
        LATEST_STATE["cache_used"],
        LATEST_STATE.get("network_state"),
        LATEST_STATE.get("network_note"),
    )


@app.get("/health", response_model=HealthStatus)
def health() -> HealthStatus:
    """Simple health probe endpoint."""
    return HealthStatus()


@app.get("/recommend", response_model=FeeRecommendation)
def recommend(
    priority: Annotated[
        str,
        Query(
            enum=["fast", "medium", "slow"],
            description="Preset priority",
        ),
    ] = "medium",
    explain: Annotated[str | None, Query(enum=["none", "llm"], description="Explanation mode")] = "none",
) -> FeeRecommendation:
    """Suggest a transaction fee based on mempool stats and desired priority."""
    fee_data, mempool, cache_used, network_state, _ = _get_live_data()
    rec = recommend_fee(priority, fee_data, mempool, cache_used=cache_used)
    rec = _apply_agent_messages(rec, network_state, fee_data)
    if explain == "llm":
        rec.llm_explanation = generate_llm_explanation(rec.model_dump())
    append_history(
        [
            {
                "priority": rec.priority,
                "base_fee_sat_vb": rec.base_fee_sat_vb,
                "mempool_tx_count": rec.mempool_tx_count,
                "recommended_fee_sat_vb": rec.recommended_fee_sat_vb,
            }
        ]
    )
    return rec


@app.get("/compare", response_model=CompareResponse)
def compare(
    explain: Annotated[str | None, Query(enum=["none", "llm"], description="Explanation mode")] = "none",
) -> CompareResponse:
    """Return recommendations for presets in one response."""
    fee_data, mempool, cache_used, network_state, _ = _get_live_data()
    fast_rec = recommend_fee("fast", fee_data, mempool, cache_used=cache_used)
    medium_rec = recommend_fee("medium", fee_data, mempool, cache_used=cache_used)
    slow_rec = recommend_fee("slow", fee_data, mempool, cache_used=cache_used)
    fast_rec = _apply_agent_messages(fast_rec, network_state, fee_data)
    medium_rec = _apply_agent_messages(medium_rec, network_state, fee_data)
    slow_rec = _apply_agent_messages(slow_rec, network_state, fee_data)
    if explain == "llm":
        fast_rec.llm_explanation = generate_llm_explanation(fast_rec.model_dump())
        medium_rec.llm_explanation = generate_llm_explanation(medium_rec.model_dump())
        slow_rec.llm_explanation = generate_llm_explanation(slow_rec.model_dump())
    append_history(
        [
            {
                "priority": fast_rec.priority,
                "base_fee_sat_vb": fast_rec.base_fee_sat_vb,
                "mempool_tx_count": fast_rec.mempool_tx_count,
                "recommended_fee_sat_vb": fast_rec.recommended_fee_sat_vb,
            },
            {
                "priority": medium_rec.priority,
                "base_fee_sat_vb": medium_rec.base_fee_sat_vb,
                "mempool_tx_count": medium_rec.mempool_tx_count,
                "recommended_fee_sat_vb": medium_rec.recommended_fee_sat_vb,
            },
            {
                "priority": slow_rec.priority,
                "base_fee_sat_vb": slow_rec.base_fee_sat_vb,
                "mempool_tx_count": slow_rec.mempool_tx_count,
                "recommended_fee_sat_vb": slow_rec.recommended_fee_sat_vb,
            },
        ]
    )
    overpay_percent = 0.0
    overpay_delta = 0.0
    note = ""
    if medium_rec.recommended_fee_sat_vb:
        overpay_delta = max(0.0, fast_rec.recommended_fee_sat_vb - medium_rec.recommended_fee_sat_vb)
        overpay_percent = round((overpay_delta / medium_rec.recommended_fee_sat_vb) * 100, 2)
        overpay_delta = round(overpay_delta, 4)
    fee_spread = fast_rec.recommended_fee_sat_vb - slow_rec.recommended_fee_sat_vb
    if fee_spread <= 2:
        note = "Fee differences may have limited impact right now."
    else:
        note = "Fast pays more, slow delays more."
    verdict_title, verdict_text = _build_compare_verdict(network_state, overpay_delta, overpay_percent)
    return CompareResponse(
        fast=fast_rec,
        medium=medium_rec,
        slow=slow_rec,
        overpay_percent_fast_vs_medium=overpay_percent,
        overpay_delta_fast_vs_medium_sat_vb=overpay_delta,
        note=note,
        verdict_title=verdict_title,
        verdict_text=verdict_text,
    )


@app.get("/estimate", response_model=FeeRecommendation)
def estimate(
    fee: Annotated[float, Query(gt=0, description="Custom fee in sat/vB (decimals allowed)")],
    explain: Annotated[str | None, Query(enum=["none", "llm"], description="Explanation mode")] = "none",
) -> FeeRecommendation:
    """Estimate confirmation time for a custom fee."""
    fee_data, mempool, cache_used, network_state, _ = _get_live_data()
    rec = estimate_fee(fee, fee_data, mempool, cache_used=cache_used)
    rec = _apply_agent_messages(rec, network_state, fee_data)
    if explain == "llm":
        rec.llm_explanation = generate_llm_explanation(rec.model_dump())
    append_history(
        [
            {
                "priority": "estimate",
                "base_fee_sat_vb": rec.base_fee_sat_vb,
                "mempool_tx_count": rec.mempool_tx_count,
                "recommended_fee_sat_vb": rec.recommended_fee_sat_vb,
            }
        ]
    )
    return rec


@app.get("/history")
def history():
    """Return last 10 recommendation records."""
    items = read_recent(10)
    insight = _history_insight(items, LATEST_STATE.get("network_state"))
    return {"items": items, "insight": insight}


@app.get("/live/status", response_model=LiveStatus)
def live_status() -> LiveStatus:
    """Return latest periodically fetched mempool and fee data."""
    return LiveStatus(**LATEST_STATE)


@app.get("/mining-target", response_model=MiningTargetResponse)
def mining_target(
    fee: Annotated[float | None, Query(gt=0, description="Optional fee to test in sat/vB")] = None,
    target_blocks: Annotated[int | None, Query(ge=1, le=6, description="Desired confirmation within N blocks")] = None,
):
    """Return projected mempool blocks (top 3)."""
    try:
        data, cache_used = get_mining_targets()
    except Exception as exc:  # pragma: no cover - defensive
        now = datetime.now(timezone.utc).isoformat()
        return {
            "timestamp": now,
            "cache_used": True,
            "source": "mempool.space",
            "blocks": [],
            "error": str(exc),
        }

    blocks = []
    for idx, blk in enumerate((data or [])[:6], start=1):
        fee_range = blk.get("feeRange") or []
        min_fee = blk.get("minFee")
        if min_fee is None and fee_range:
            min_fee = min(fee_range)
        blocks.append(
            {
                "block_index": idx,
                "minFee": min_fee,
                "medianFee": blk.get("medianFee"),
                "blockSize": blk.get("blockSize"),
                "txCount": blk.get("nTx"),
            }
        )

    user_eval = None
    if fee is not None:
        fits_idx = None
        for b in blocks:
            min_req = b.get("minFee") or 0
            if fee >= min_req:
                fits_idx = b["block_index"]
                break
        meets = fits_idx is not None
        if meets:
            note = f"Your {fee} sat/vB fee looks sufficient to enter block {fits_idx}."
        else:
            note = f"Your {fee} sat/vB fee is below the minimum for the first {len(blocks)} blocks."
        user_eval = {
            "provided_fee_sat_vb": fee,
            "fits_in_block_index": fits_idx,
            "meets_min_fee": meets,
            "note": note,
        }

    # Target block summary (savings/delay)
    target_idx = target_blocks or 1
    target_idx = max(1, min(target_idx, len(blocks) if blocks else 1))
    target_block = blocks[target_idx - 1] if blocks else {}
    fastest_min = blocks[0].get("minFee") if blocks else None
    target_min = target_block.get("minFee")
    target_med = target_block.get("medianFee")
    savings = None
    if fastest_min is not None and target_min is not None:
        savings = round(max(0, fastest_min - target_min), 4)
    extra_delay_minutes = (target_idx - 1) * 10.0
    target_note = None
    if target_min is not None:
        target_note = (
            f"Target confirm within {target_idx} blocks: min ~{target_min:.4f} sat/vB, "
            f"savings vs fast ~{savings or 0} sat/vB, extra delay ~{extra_delay_minutes:.1f} min."
        )

    now = datetime.now(timezone.utc).isoformat()
    return {
        "timestamp": now,
        "cache_used": cache_used,
        "source": "mempool.space",
        "blocks": blocks,
        "error": None,
        "user_fee_eval": user_eval,
        "target_blocks": target_idx,
        "target_min_fee": target_min,
        "target_median_fee": target_med,
        "savings_vs_fast_sat_vb": savings,
        "extra_delay_minutes": extra_delay_minutes,
        "target_note": target_note,
    }
