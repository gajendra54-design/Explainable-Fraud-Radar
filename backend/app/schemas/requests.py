from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class TransactionInput(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    transaction_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    account_id: str = Field(min_length=1, max_length=80)
    customer_id: str = Field(min_length=1, max_length=80)
    timestamp: datetime
    amount: float = Field(gt=0, le=1e12)
    currency: Literal["LKR"]
    merchant_id: str = Field(min_length=1, max_length=80)
    merchant_category: str = Field(min_length=1, max_length=80)
    channel: str = Field(min_length=1, max_length=40)
    country_code: str = Field(pattern=r"^[A-Z]{2}$")
    customer_country: str = Field(default="LK", pattern=r"^[A-Z]{2}$")
    device_id: str = Field(min_length=1, max_length=80)
    ip_risk_indicator: float = Field(default=0, ge=0, le=1)
    account_age_days: int = Field(default=365, ge=0)
    ground_truth_fraud_label: Literal[0, 1] | None = None
    fraud_scenario_type: str | None = Field(default=None, max_length=80)

    @field_validator("timestamp")
    @classmethod
    def timestamp_valid(cls, value):
        if value.tzinfo is None:
            raise ValueError("Timezone-aware timestamp required")
        if value > datetime.now(timezone.utc) or value.year < 2000:
            raise ValueError("Timestamp outside supported historical range")
        return value.astimezone(timezone.utc)

    @field_serializer("timestamp")
    def serialize_timestamp(self, value):
        return value.isoformat(timespec="microseconds")


class Batch(BaseModel):
    records: list[dict] = Field(min_length=1, max_length=10000)


class PipelineConfig(BaseModel):
    transactions: int = Field(default=3000, ge=500, le=100000)
    seed: int = Field(default=42, ge=0, le=2147483647)
    customers: int = Field(default=180, ge=10, le=10000)
    fraud_rate: float = Field(default=0.06, ge=0.005, le=0.3)


class Assignment(BaseModel):
    username: str = Field(min_length=1, max_length=80)


class NoteInput(BaseModel):
    text: str = Field(min_length=1, max_length=10000)


class Escalation(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class Disposition(BaseModel):
    disposition: Literal["Confirmed suspicious activity", "Legitimate activity / false positive", "Inconclusive", "Requires further review"]
    confirmed: bool


class StatusInput(BaseModel):
    status: Literal["Under Review"]
