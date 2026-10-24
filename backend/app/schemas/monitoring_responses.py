"""Validated output contracts for delayed outcomes and drift investigations."""

from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, JsonValue

Fraction = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Count = Annotated[int, Field(ge=0)]
IncidentStatus = Literal["Open", "Investigating", "Resolved"]
ModelStatus = Literal["insufficient_labels", "provisional", "ready"]


class Response(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class VerifiedLabelsResponse(Response):
    accepted: Count
    duplicates: Count
    source: Literal["verified_labels"]
    investigator_dispositions_used: Literal[False]


class LiveMetrics(Response):
    threshold: Fraction
    true_positives: Count
    true_negatives: Count
    false_positives: Count
    false_negatives: Count
    precision: Fraction
    recall: Fraction
    f1: Fraction
    specificity: Fraction
    false_positive_rate: Fraction
    pr_auc: Fraction
    roc_auc: Fraction | None
    confusion_matrix: tuple[tuple[Count, Count], tuple[Count, Count]]
    alert_volume: Count
    alert_rate_per_1000: Annotated[float, Field(ge=0, le=1000, allow_inf_nan=False)]
    investigation_hours: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    precision_at_capacity: Fraction
    review_capacity: Count
    sample_count: Count
    fraud_prevalence: Fraction


class LiveModelPerformance(Response):
    model_version: str
    labeled_count: Count
    mature_count: Count
    label_coverage: Fraction
    metrics: LiveMetrics | None
    status: ModelStatus
    baseline_f1: Fraction | None
    performance_degradation: bool
    comparison_note: str


class LivePerformanceResponse(Response):
    source: Literal["independently submitted verified labels"]
    window_start: datetime
    window_end: datetime
    maturity_cutoff: datetime
    maturity_days: Count
    minimum_labels: Annotated[int, Field(ge=2)]
    transaction_count: Count
    mature_count: Count
    immature_count: Count
    labeled_count: Count
    mature_labeled_count: Count
    label_coverage: Fraction
    mature_label_coverage: Fraction
    status: Literal["no_transactions", "awaiting_maturity", "insufficient_labels", "provisional", "ready"]
    models: list[LiveModelPerformance]
    performance_degradation: bool
    limitations: str


class MonitoringIncidentResponse(Response):
    id: Annotated[int, Field(ge=1)]
    title: str
    summary: str
    severity: Literal["warning", "critical"]
    status: IncidentStatus
    report: dict[str, JsonValue]
    created_at: datetime
    created_by: str
    updated_at: datetime


class MonitoringEventResponse(Response):
    id: Annotated[int, Field(ge=1)]
    incident_id: Annotated[int, Field(ge=1)]
    actor: str
    note: str
    previous_status: IncidentStatus | None
    status: IncidentStatus
    created_at: datetime


class MonitoringDetailResponse(MonitoringIncidentResponse):
    history: list[MonitoringEventResponse]


class MonitoringListResponse(Response):
    items: list[MonitoringIncidentResponse]
    total: Count
    page: Annotated[int, Field(ge=1)]
    page_size: Annotated[int, Field(ge=1, le=100)]
