"""Shared chronological feature definitions for training and serving."""

from datetime import datetime
from collections import defaultdict, deque
import numpy as np

FEATURE_NAMES = [
    "log_amount",
    "amount_ratio",
    "count_1h",
    "count_24h",
    "log_spend_24h",
    "minutes_since_previous",
    "new_device",
    "new_merchant",
    "foreign_country",
    "night_time",
    "ip_risk",
    "log_account_age",
]
FEATURE_DESCRIPTIONS = [
    "Transaction amount (natural log of 1 + LKR)",
    "Amount divided by prior account median",
    "Prior transactions in one hour",
    "Prior transactions in 24 hours",
    "Prior 24-hour spend (natural log)",
    "Minutes since prior transaction (capped at one day)",
    "Device not previously seen for account",
    "Merchant not previously seen for account",
    "Country differs from customer home",
    "Transaction between midnight and 05:00 UTC",
    "Synthetic IP risk indicator",
    "Account age (natural log days)",
]


def stamp(row):
    return datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")).timestamp()


def engineer(records):
    """Stable chronological sort, strict past only, never inspect labels/scenarios."""
    histories = defaultdict(
        lambda: {
            "recent": deque(),
            "amounts": deque(maxlen=100),
            "devices": set(),
            "merchants": set(),
            "last": None,
        }
    )
    result = [None] * len(records)
    ordered = sorted(enumerate(records), key=lambda pair: stamp(pair[1]))
    # Equal timestamp transactions share a snapshot and are added only after scoring.
    from itertools import groupby

    for time, group in groupby(ordered, key=lambda pair: stamp(pair[1])):
        batch = list(group)
        for index, row in batch:
            h = histories[row["account_id"]]
            while h["recent"] and h["recent"][0][0] < time - 86400:
                h["recent"].popleft()
            baseline = float(np.median(h["amounts"])) if h["amounts"] else 3000.0
            amount = float(row["amount"])
            dt = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            result[index] = [
                np.log1p(amount),
                min(amount / max(baseline, 1), 100),
                sum(t >= time - 3600 for t, a in h["recent"]),
                len(h["recent"]),
                np.log1p(sum(a for t, a in h["recent"])),
                min((time - h["last"]) / 60, 1440) if h["last"] is not None else 1440,
                int(row.get("device_id") not in h["devices"]),
                int(row.get("merchant_id") not in h["merchants"]),
                int(row.get("country_code", "LK") != row.get("customer_country", "LK")),
                int(dt.hour < 5),
                float(row.get("ip_risk_indicator", 0)),
                np.log1p(float(row.get("account_age_days", 365))),
            ]
        for _, row in batch:
            h = histories[row["account_id"]]
            h["recent"].append((time, float(row["amount"])))
            h["amounts"].append(float(row["amount"]))
            h["devices"].add(row.get("device_id"))
            h["merchants"].add(row.get("merchant_id"))
            h["last"] = time
    return np.asarray(result, dtype=float)
