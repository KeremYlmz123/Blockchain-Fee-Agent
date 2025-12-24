from .models import FeeRecommendation

# Congestion thresholds for mapping mempool count to low/medium/high
CONGESTION_THRESHOLDS = (50_000, 200_000)
# Maximum additional multiplier (30%) applied under heavy congestion
MAX_CONGESTION_BONUS = 0.30
CONFIDENCE_ORDER = ["low", "medium", "high"]

PRESETS = {
    "fast": {"blocks_min": 1, "blocks_max": 2, "risk": "low"},
    "medium": {"blocks_min": 3, "blocks_max": 6, "risk": "medium"},
    "slow": {"blocks_min": 6, "blocks_max": 12, "risk": "high"},
}


def _pick_base_fee(priority: str, fee_data: dict) -> int:
    if priority == "fast":
        return float(fee_data.get("fastestFee") or fee_data.get("halfHourFee") or fee_data.get("minimumFee", 1))
    if priority == "medium":
        return float(fee_data.get("hourFee") or fee_data.get("halfHourFee") or fee_data.get("minimumFee", 1))
    # slow
    return float(fee_data.get("economyFee") or fee_data.get("minimumFee", 1))


def observe(priority: str, fee_data: dict, mempool: dict, cache_used: bool):
    degraded = False
    preset = PRESETS.get(priority, PRESETS["medium"])
    try:
        base_fee = _pick_base_fee(priority, fee_data)
    except Exception:
        base_fee = int(fee_data.get("minimumFee", 1))
        degraded = True

    try:
        mempool_tx_count = int(mempool.get("count", 0) or 0)
    except Exception:
        mempool_tx_count = 0
        degraded = True

    congestion_level = _congestion_level(mempool_tx_count)
    ratio = _congestion_ratio(mempool_tx_count)

    signals = {
        "mempool_tx_count": mempool_tx_count,
        "congestion_level": congestion_level,
        "recommended_fees": {
            "fastest": fee_data.get("fastestFee"),
            "halfHour": fee_data.get("halfHourFee"),
            "hour": fee_data.get("hourFee"),
            "economy": fee_data.get("economyFee"),
            "minimum": fee_data.get("minimumFee"),
        },
    }

    return {
        "mode": "recommend",
        "priority": priority,
        "base_fee": float(base_fee),
        "blocks_min": preset["blocks_min"],
        "blocks_max": preset["blocks_max"],
        "risk_level": preset["risk"],
        "mempool_tx_count": mempool_tx_count,
        "congestion_ratio": ratio,
        "congestion_level": congestion_level,
        "cache_used": cache_used,
        "signals": signals,
        "degraded": degraded or cache_used,
    }


def observe_estimate(fee: float, mempool: dict, cache_used: bool, fee_data: dict):
    degraded = False
    try:
        mempool_tx_count = int(mempool.get("count", 0) or 0)
    except Exception:
        mempool_tx_count = 0
        degraded = True

    congestion_level = _congestion_level(mempool_tx_count)
    ratio = _congestion_ratio(mempool_tx_count)

    fast_base = _pick_base_fee("fast", fee_data)
    medium_base = _pick_base_fee("medium", fee_data)
    slow_base = _pick_base_fee("slow", fee_data)

    # classify user fee
    if fee >= fast_base:
        preset = PRESETS["fast"]
        priority = "fast"
        rule = "R_ESTIMATE_FAST"
    elif fee >= medium_base:
        preset = PRESETS["medium"]
        priority = "medium"
        rule = "R_ESTIMATE_MEDIUM"
    elif fee >= slow_base:
        preset = PRESETS["slow"]
        priority = "slow"
        rule = "R_ESTIMATE_SLOW"
    else:
        preset = {"blocks_min": PRESETS["slow"]["blocks_min"] + 2, "blocks_max": PRESETS["slow"]["blocks_max"] + 4, "risk": "high"}
        priority = "slow"
        rule = "R_ESTIMATE_BELOW_SLOW"

    signals = {
        "mempool_tx_count": mempool_tx_count,
        "congestion_level": congestion_level,
        "input_fee_sat_vb": fee,
        "reference_fee_fast": fast_base,
        "reference_fee_medium": medium_base,
        "reference_fee_slow": slow_base,
    }

    return {
        "mode": "estimate",
        "priority": priority,
        "input_fee": float(fee),
        "blocks_min": preset["blocks_min"],
        "blocks_max": preset["blocks_max"],
        "risk_level": preset["risk"],
        "mempool_tx_count": mempool_tx_count,
        "congestion_ratio": ratio,
        "congestion_level": congestion_level,
        "cache_used": cache_used,
        "signals": signals,
        "degraded": degraded or cache_used,
        "classification_rule": rule,
        "base_fee_ref": medium_base,
    }


def decide(obs: dict):
    ratio = obs["congestion_ratio"]
    congestion_multiplier = 1 + (MAX_CONGESTION_BONUS * ratio)

    if obs["mode"] == "recommend":
        recommended_fee = max(1.0, round(obs["base_fee"] * congestion_multiplier, 3))
        rules_fired = [
            _priority_rule(obs["priority"]),
            _congestion_rule(obs["congestion_level"]),
        ]
        blocks_min, blocks_max = _scale_eta(obs["blocks_min"], obs["blocks_max"], ratio)
        risk_level = obs["risk_level"]
    else:
        # Apply congestion to user input, keep decimals
        recommended_fee = max(0.1, round(obs["input_fee"] * congestion_multiplier, 3))
        rules_fired = [
            obs.get("classification_rule", "R_ESTIMATE_UNKNOWN"),
            _congestion_rule(obs["congestion_level"]),
        ]
        blocks_min, blocks_max = _scale_eta(obs["blocks_min"], obs["blocks_max"], ratio)
        risk_level = obs["risk_level"]

    if obs["cache_used"]:
        rules_fired.append("R_CACHE_USED")
    if obs["degraded"]:
        rules_fired.append("R_DEGRADED_INPUT")

    confidence = _confidence_from_ratio(ratio)
    if obs["degraded"]:
        confidence = _downgrade_confidence(confidence)

    minutes_min = blocks_min * 10
    minutes_max = blocks_max * 10

    return {
        "recommended_fee": recommended_fee,
        "rules_fired": rules_fired,
        "confidence": confidence,
        "congestion_multiplier": congestion_multiplier,
        "risk_level": risk_level,
        "eta_blocks_min": blocks_min,
        "eta_blocks_max": blocks_max,
        "eta_minutes_min": minutes_min,
        "eta_minutes_max": minutes_max,
    }


def explain(obs: dict, decision: dict):
    base_line = (
        f"Base fee for {obs['priority']} priority: {obs.get('base_fee', obs.get('input_fee'))} sat/vB."
        if obs["mode"] == "recommend"
        else f"User fee: {obs['input_fee']} sat/vB classified as {obs['priority']}."
    )
    return [
        base_line,
        f"Mempool tx count {obs['mempool_tx_count']} gives congestion multiplier {decision['congestion_multiplier']:.2f}.",
        f"ETA range: {decision['eta_blocks_min']}-{decision['eta_blocks_max']} blocks (~{decision['eta_minutes_min']}-{decision['eta_minutes_max']} minutes).",
        f"Cache used: {obs['cache_used']}. Degraded inputs: {obs['degraded']}.",
    ]


def _priority_rule(priority: str) -> str:
    mapping = {
        "fast": "R_PRIORITY_FAST",
        "medium": "R_PRIORITY_MEDIUM",
        "slow": "R_PRIORITY_SLOW",
    }
    return mapping.get(priority, "R_PRIORITY_MEDIUM")


def _congestion_rule(level: str) -> str:
    mapping = {"low": "R_CONGESTION_LOW", "medium": "R_CONGESTION_MEDIUM", "high": "R_CONGESTION_HIGH"}
    return mapping.get(level, "R_CONGESTION_MEDIUM")


def _scale_eta(blocks_min: int, blocks_max: int, ratio: float) -> tuple[int, int]:
    if ratio <= 0.33:
        factor = 1.0
    elif ratio <= 0.66:
        factor = 1.5
    else:
        factor = 2.0
    bmin = max(1, round(blocks_min * factor))
    bmax = max(bmin, round(blocks_max * factor))
    return bmin, bmax


def _congestion_ratio(mempool_count: int) -> float:
    low, high = CONGESTION_THRESHOLDS
    if mempool_count <= low:
        return 0.0
    if mempool_count >= high:
        return 1.0
    return (mempool_count - low) / (high - low)


def _congestion_level(mempool_count: int) -> str:
    low, high = CONGESTION_THRESHOLDS
    if mempool_count <= low:
        return "low"
    if mempool_count <= high:
        return "medium"
    return "high"


def _confidence_from_ratio(ratio: float) -> str:
    if ratio < 0.33:
        return "high"
    if ratio < 0.66:
        return "medium"
    return "low"


def _downgrade_confidence(level: str) -> str:
    try:
        idx = CONFIDENCE_ORDER.index(level)
    except ValueError:
        return "low"
    return CONFIDENCE_ORDER[max(0, idx - 1)]


def recommend_fee(
    priority: str, fee_data: dict, mempool: dict, cache_used: bool = False
) -> FeeRecommendation:
    obs = observe(priority, fee_data, mempool, cache_used)
    decision = decide(obs)
    explanation = explain(obs, decision)

    return FeeRecommendation(
        mode="recommend",
        priority=priority,
        base_fee_sat_vb=obs["base_fee"],
        recommended_fee_sat_vb=decision["recommended_fee"],
        eta_blocks_min=decision["eta_blocks_min"],
        eta_blocks_max=decision["eta_blocks_max"],
        eta_minutes_min=decision["eta_minutes_min"],
        eta_minutes_max=decision["eta_minutes_max"],
        risk_level=decision["risk_level"],
        mempool_tx_count=obs["mempool_tx_count"],
        explanation=explanation,
        agent_summary="",
        what_if_hint=None,
        signals_used=obs["signals"],
        rules_fired=decision["rules_fired"],
        confidence=decision["confidence"],
        cache_used=obs["cache_used"],
        source="mempool.space",
    )


def estimate_fee(
    user_fee_sat_vb: int, fee_data: dict, mempool: dict, cache_used: bool = False
) -> FeeRecommendation:
    obs = observe_estimate(user_fee_sat_vb, mempool, cache_used, fee_data)
    decision = decide(obs)
    explanation = explain(obs, decision)

    return FeeRecommendation(
        mode="estimate",
        priority=obs["priority"],
        base_fee_sat_vb=obs.get("base_fee_ref", obs["input_fee"]),
        recommended_fee_sat_vb=decision["recommended_fee"],
        input_fee_sat_vb=user_fee_sat_vb,
        eta_blocks_min=decision["eta_blocks_min"],
        eta_blocks_max=decision["eta_blocks_max"],
        eta_minutes_min=decision["eta_minutes_min"],
        eta_minutes_max=decision["eta_minutes_max"],
        risk_level=decision["risk_level"],
        mempool_tx_count=obs["mempool_tx_count"],
        explanation=explanation,
        agent_summary="",
        what_if_hint=None,
        signals_used=obs["signals"],
        rules_fired=decision["rules_fired"],
        confidence=decision["confidence"],
        cache_used=obs["cache_used"],
        source="mempool.space",
    )
