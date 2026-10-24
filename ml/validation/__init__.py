"""Schema checks and quarantine; does not discard large but valid amounts."""

from datetime import datetime, timezone
import math


def validate_records(records):
    accepted, rejected, seen = [], [], set()
    for index, row in enumerate(records):
        errors = []
        if not isinstance(row, dict):
            rejected.append(
                {
                    "row": index,
                    "transaction_id": None,
                    "reasons": ["record must be an object"],
                }
            )
            continue
        for key in (
            "transaction_id",
            "account_id",
            "customer_id",
            "timestamp",
            "amount",
            "currency",
            "merchant_id",
            "device_id",
        ):
            if row.get(key) is None or row.get(key) == "":
                errors.append(f"missing {key}")
            elif key not in ("amount",) and not isinstance(row[key], str):
                errors.append(f"{key} must be a string")
        if (
            isinstance(row.get("transaction_id"), str)
            and row.get("transaction_id") in seen
        ):
            errors.append("duplicate transaction_id")
        try:
            amount = float(row.get("amount"))
            if (
                isinstance(row.get("amount"), bool)
                or not math.isfinite(amount)
                or amount <= 0
            ):
                errors.append("amount must be finite and positive")
        except (ValueError, TypeError):
            errors.append("invalid amount")
        try:
            ts = datetime.fromisoformat(
                str(row.get("timestamp")).replace("Z", "+00:00")
            )
            if ts.tzinfo is None or ts.year < 2000 or ts > datetime.now(timezone.utc):
                errors.append(
                    "timestamp must be timezone-aware, after 2000 and not in future"
                )
        except ValueError:
            errors.append("invalid timestamp")
        if row.get("currency") != "LKR":
            errors.append(
                "unsupported currency: only LKR is supported; FX conversion is not implemented"
            )
        for key, lower, upper in [
            ("ip_risk_indicator", 0, 1),
            ("account_age_days", 0, 100000),
        ]:
            if key in row:
                try:
                    value = float(row[key])
                    if (
                        isinstance(row[key], bool)
                        or not math.isfinite(value)
                        or not lower <= value <= upper
                    ):
                        errors.append(
                            f"{key} must be finite between {lower} and {upper}"
                        )
                except (ValueError, TypeError):
                    errors.append(f"invalid {key}")
        if errors:
            rejected.append(
                {
                    "row": index,
                    "transaction_id": row.get("transaction_id"),
                    "reasons": errors,
                }
            )
        else:
            seen.add(row["transaction_id"])
            accepted.append(row.copy())
    return accepted, rejected
