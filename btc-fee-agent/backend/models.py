from pydantic import BaseModel, Field


class FeeRecommendation(BaseModel):
    """Recommended fee details."""

    priority: str = Field(..., description="Requested transaction priority")
    mode: str = Field("recommend", description="recommend | estimate")
    base_fee_sat_vb: float = Field(..., description="Base fee before congestion multiplier")
    recommended_fee_sat_vb: float = Field(
        ..., description="Suggested sats/vByte fee for the given priority (may include decimals)"
    )
    input_fee_sat_vb: float | None = Field(
        None, description="User-supplied fee in estimate mode"
    )
    eta_blocks_min: int = Field(..., description="Lower bound of expected confirmation (blocks)")
    eta_blocks_max: int = Field(..., description="Upper bound of expected confirmation (blocks)")
    eta_minutes_min: float = Field(..., description="Lower bound of expected confirmation (minutes)")
    eta_minutes_max: float = Field(..., description="Upper bound of expected confirmation (minutes)")
    risk_level: str = Field(..., description="low | medium | high delay/overpay risk")
    mempool_tx_count: int = Field(..., description="Current mempool transaction count")
    explanation: list[str] = Field(
        ..., description="Bullet-point explanation of the recommendation"
    )
    agent_summary: str = Field(..., description="Deterministic agent summary")
    what_if_hint: str | None = Field(
        None, description="Optional deterministic hint for alternative fee"
    )
    signals_used: dict = Field(
        default_factory=dict,
        description="Observed signals such as mempool_tx_count, recommended fees, congestion_level",
    )
    rules_fired: list[str] = Field(
        default_factory=list, description="Rule identifiers/conditions that were applied"
    )
    confidence: str = Field(
        ..., description="low | medium | high confidence in the recommendation"
    )
    cache_used: bool = Field(
        False, description="True when data comes from local cache fallback"
    )
    source: str = Field("mempool.space", description="Upstream data source")
    llm_explanation: str | None = Field(
        None, description="Optional LLM-generated explanation (Turkish)"
    )


class CompareResponse(BaseModel):
    """Fee recommendations for predefined priority levels."""

    fast: FeeRecommendation
    medium: FeeRecommendation
    slow: FeeRecommendation
    overpay_percent_fast_vs_medium: float = Field(
        ..., description="Overpay percentage of fast vs medium recommendation"
    )
    overpay_delta_fast_vs_medium_sat_vb: float = Field(
        ..., description="Absolute fee delta (sat/vB) fast vs medium (may include decimals)"
    )
    note: str = Field(..., description="Context note about fee differences")
    verdict_title: str = Field(..., description="Verdict headline for comparison")
    verdict_text: str = Field(..., description="Verdict explanation for comparison")


class LiveStatus(BaseModel):
    """Latest observed mempool data snapshot."""

    updated_at_epoch: float | None = Field(None, description="Unix epoch seconds")
    timestamp: str | None = Field(None, description="ISO timestamp of last refresh")
    cache_used: bool = Field(False, description="True when latest data is from cache")
    fee_data: dict | None = Field(None, description="Raw fee data")
    mempool_data: dict | None = Field(None, description="Raw mempool data")
    error: str | None = Field(None, description="Last fetch error if any")
    source: str = Field("mempool.space", description="Upstream data source")
    network_state: str | None = Field(None, description="calm | moderate | congested")
    network_note: str | None = Field(None, description="Short human-readable note")


class HealthStatus(BaseModel):
    """Health check response."""

    status: str = "ok"


class MiningBlock(BaseModel):
    """Projected mempool block entry."""

    block_index: int
    minFee: float | None = None
    medianFee: float | None = None
    blockSize: int | None = None
    txCount: int | None = None


class MiningTargetEval(BaseModel):
    """Evaluation of a user-provided fee against projected blocks."""

    provided_fee_sat_vb: float
    fits_in_block_index: int | None = None
    meets_min_fee: bool = False
    note: str


class MiningTargetResponse(BaseModel):
    """Projected mempool blocks response."""

    timestamp: str
    cache_used: bool
    source: str
    blocks: list[MiningBlock]
    error: str | None = None
    user_fee_eval: MiningTargetEval | None = None
    target_blocks: int | None = None
    target_min_fee: float | None = None
    target_median_fee: float | None = None
    savings_vs_fast_sat_vb: float | None = None
    extra_delay_minutes: float | None = None
    target_note: str | None = None
