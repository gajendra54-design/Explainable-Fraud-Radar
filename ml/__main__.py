"""Reproducible offline pipeline: python -m ml --transactions 100000."""

import argparse
import json
import csv
import time
from pathlib import Path
from ml import FraudEngine, generate_transactions
from ml.validation import validate_records
from ml.features import FEATURE_NAMES
from ml.evaluation.reports import analytical_reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transactions", type=int, default=100000)
    parser.add_argument("--customers", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--fraud-rate", type=float, default=0.06)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--output", default="reports/generated")
    args = parser.parse_args()
    started = time.perf_counter()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    data = generate_transactions(
        args.transactions, args.seed, args.customers, args.fraud_rate, args.days
    )
    accepted, rejected = validate_records(data)
    engine = FraudEngine(accepted, args.seed)
    engine.save(out / "model.joblib")
    reports = {
        "evaluation": engine.metrics(),
        "thresholds": engine.thresholds(),
        "drift": engine.drift_report(),
        "model": engine.model_info(),
        "data_summary": engine.dataset_summary(),
        "quality": {
            "accepted": len(accepted),
            "rejected": len(rejected),
            "quarantine": rejected,
        },
        "config": vars(args),
        **analytical_reports(engine),
    }
    for name, report in reports.items():
        (out / f"{name}.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
    with (out / "raw_transactions.jsonl").open("w", encoding="utf-8") as handle:
        for row in data:
            handle.write(json.dumps(row) + "\n")
    with (out / "curated_transactions.jsonl").open("w", encoding="utf-8") as handle:
        for row in engine.data:
            handle.write(
                json.dumps(
                    {
                        k: v
                        for k, v in row.items()
                        if k not in ("ground_truth_fraud_label", "fraud_scenario_type")
                    }
                )
                + "\n"
            )
    with (out / "features.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["transaction_id", *FEATURE_NAMES])
        for row, features in zip(engine.data, engine.x):
            writer.writerow([row["transaction_id"], *features])
    with (out / "labels.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["transaction_id", "ground_truth_fraud_label", "fraud_scenario_type"]
        )
        for row in engine.data:
            writer.writerow(
                [
                    row["transaction_id"],
                    row["ground_truth_fraud_label"],
                    row["fraud_scenario_type"],
                ]
            )
    (out / "pipeline_performance.json").write_text(
        json.dumps(
            {
                "records": len(data),
                "duration_seconds": time.perf_counter() - started,
                "status": "completed",
                "model_version": engine.version,
                "raw": "raw_transactions.jsonl",
                "curated": "curated_transactions.jsonl",
                "features": "features.csv",
                "labels": "labels.csv",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps({"output": str(out), "records": len(data), "model": engine.version})
    )


if __name__ == "__main__":
    main()
