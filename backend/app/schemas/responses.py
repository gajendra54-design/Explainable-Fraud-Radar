"""Stable public API envelopes with explicit core fields and extensible ML metadata."""

from typing import Any, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field


class ExtensibleResponse(BaseModel):
    model_config = ConfigDict(extra="allow")


class UserResponse(BaseModel):
    id: int
    username: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class ContributionResponse(BaseModel):
    feature: str
    description: str
    value: float
    baseline: float
    contribution: float
    direction: str


class ExplanationResponse(ExtensibleResponse):
    method: str
    units: str
    baseline: float
    output_log_odds: float
    probability: float = Field(ge=0, le=1)
    contributions: list[ContributionResponse]
    model_version: str
    limitations: str


class PredictionResponse(ExtensibleResponse):
    risk_score: float = Field(ge=0, le=100)
    risk_band: str
    model_version: str
    prediction_timestamp: str
    fraud_probability: float = Field(ge=0, le=1)
    anomaly_score: float = Field(ge=0, le=1)
    rule_score: float = Field(ge=0, le=100)
    features: dict[str, float]
    explanation: ExplanationResponse


class CaseResponse(ExtensibleResponse):
    id: int
    transaction_id: str
    status: str
    assigned_to: str | None
    disposition: str | None
    created_at: str
    risk_score: float
    risk_band: str
    model_version: str


class TransactionResponse(ExtensibleResponse):
    transaction_id: str
    account_id: str
    customer_id: str
    timestamp: str
    amount: float
    currency: str
    channel: str
    risk_score: float | None
    risk_band: str | None
    model_version: str | None
    status: str


class TransactionDetailResponse(TransactionResponse):
    prediction: PredictionResponse | None
    alert: CaseResponse | None
    related_transactions: list[TransactionResponse]


class AuditResponse(BaseModel):
    id: int
    case_id: int | None
    actor: str
    action: str
    details: dict[str, Any]
    created_at: str


class CaseDetailResponse(CaseResponse):
    transaction: dict[str, Any]
    prediction: PredictionResponse
    notes: list[dict[str, Any]]
    history: list[AuditResponse]


T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class MetricsResponse(ExtensibleResponse):
    threshold: float
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    pr_auc: float
    roc_auc: float | None
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    confusion_matrix: list[list[int]]
    alert_volume: int
    sample_count: int


class ModelResponse(BaseModel):
    version: str
    created_at: str
    info: dict[str, Any]
    metrics: MetricsResponse
    artifact_path: str
    active: bool


class PipelineResponse(BaseModel):
    id: str
    status: str
    started_at: str
    completed_at: str | None
    processed: int
    rejected: int
    duplicates: int
    duration_seconds: float
    config: dict[str, Any]
    error: str | None
    job_type: str
    attempts: int
    max_attempts: int
    lease_owner: str | None
    lease_expires_at: str | None
    heartbeat_at: str | None
    next_attempt_at: str | None


class DashboardResponse(BaseModel):
    transactions: int
    alerts: int
    high_risk: int
    open_cases: int
    model_version: str | None
    pipeline_health: str
    drift_status: str
    fraud_rate: float | None
    false_positive_rate: float | None
    trend: list[dict[str, Any]]
    risk_distribution: list[dict[str, Any]]
    recent_alerts: list[CaseResponse]


class SystemResponse(BaseModel):
    status: str
    synthetic_only: bool
    model_version: str | None
    database: str


class DriftResponse(ExtensibleResponse):
    status: str
    features: list[dict[str, Any]]
    reference_count: int
    current_count: int
    label_coverage: float | None
    recommendation: str
    limitations: str


class PerformanceResponse(BaseModel):
    metrics: MetricsResponse
    label_source: str
    label_coverage: float
    window_maturity: str
    investigator_decisions_used_as_truth: bool


class LogoutResponse(BaseModel):
    status: str


class RevocationResponse(BaseModel):
    revoked: int


class PasswordResponse(BaseModel):
    status: str
    reauthentication_required: bool
