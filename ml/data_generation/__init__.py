"""Reproducible synthetic records. No external financial data is used."""

from datetime import datetime, timedelta, timezone
import numpy as np


def generate_transactions(
    n=3000, seed=42, customers=180, fraud_rate=0.06, days=90, merchants=80
):
    if n < 50 or customers < 1 or days < 1 or merchants < 1 or not 0 < fraud_rate < 0.5:
        raise ValueError("n >= 50, positive counts, and 0 < fraud_rate < 0.5 required")
    rng = np.random.default_rng(seed)
    baselines = rng.lognormal(7.8, 0.7, customers)
    opening_ages = rng.integers(2, 3000, customers)
    offsets = np.sort(rng.uniform(0, days * 86400, n))
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    records = []
    scenarios = [
        "large_amount",
        "velocity",
        "threshold_evasion",
        "new_device",
        "geographic",
        "account_takeover",
        "unusual_time",
    ]
    for i, seconds in enumerate(offsets):
        c = int(rng.integers(customers))
        fraud = bool(rng.random() < fraud_rate)
        scenario = str(rng.choice(scenarios)) if fraud else "legitimate"
        amount = float(rng.lognormal(np.log(baselines[c]), 0.8))
        # Overlapping anomalies deliberately create legitimate hard negatives.
        unusual = fraud or rng.random() < 0.09
        if unusual and scenario in ("large_amount", "account_takeover", "legitimate"):
            amount *= float(rng.uniform(2, 7))
        if scenario == "threshold_evasion":
            amount *= 0.35
        if scenario == "velocity" and records:
            c = int(records[-1]["customer_id"].split("-")[1])
            seconds = (
                datetime.fromisoformat(records[-1]["timestamp"]) - start
            ).total_seconds() + float(rng.uniform(0.1, 5))
        if scenario == "unusual_time":
            seconds = int(seconds // 86400) * 86400 + float(rng.uniform(0, 4 * 3600))
        foreign = unusual and rng.random() < 0.55
        new_device = unusual and rng.random() < 0.65
        records.append(
            dict(
                transaction_id=f"TXN-{seed:03d}-{i + 1:07d}",
                account_id=f"ACC-{c:05d}",
                customer_id=f"CUS-{c:05d}",
                timestamp=(start + timedelta(seconds=float(seconds))).isoformat(),
                amount=round(amount, 2),
                currency="LKR",
                merchant_id=f"MER-{int(rng.integers(merchants)):04d}",
                merchant_category=str(
                    rng.choice(
                        [
                            "Retail",
                            "Travel",
                            "Groceries",
                            "Electronics",
                            "Transfer",
                            "Dining",
                        ]
                    )
                ),
                channel=str(
                    rng.choice(
                        ["Online", "POS", "Mobile", "ATM"], p=[0.4, 0.3, 0.2, 0.1]
                    )
                ),
                country_code=str(rng.choice(["US", "GB", "SG"])) if foreign else "LK",
                customer_country="LK",
                device_id=f"DEV-{c:05d}-{i if new_device else 0}",
                ip_risk_indicator=round(
                    float(rng.beta(3, 3) if unusual else rng.beta(1, 9)), 4
                ),
                account_age_days=int(opening_ages[c] + seconds // 86400),
                ground_truth_fraud_label=int(fraud),
                fraud_scenario_type=scenario,
            )
        )
    return sorted(records, key=lambda row: row["timestamp"])
