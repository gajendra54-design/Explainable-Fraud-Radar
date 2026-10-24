"""Export small, genuine evidence from the configured synthetic application DB."""

import json
from pathlib import Path

from sqlalchemy import select

from backend.app.api.routes import case_detail, serialized
from backend.app.db.session import SessionLocal
from backend.app.main import app
from backend.app.models.entities import Alert, PipelineRun
from backend.app.services.pipeline import load_engine


def main():
    destination = Path("reports/application")
    destination.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        engine = load_engine(db)
        if engine is None:
            raise SystemExit("Seed the application before exporting reports.")
        outputs = {
            "evaluation": engine.metrics(),
            "thresholds": engine.thresholds(),
            "model": engine.model_info(),
            "pipeline_runs": [serialized(r) for r in db.scalars(select(PipelineRun))],
        }
        case = db.scalar(select(Alert).where(Alert.status == "Resolved").order_by(Alert.id.desc()))
        if case:
            outputs["sample_incident"] = {
                "synthetic_only": True,
                "source": "Executed application investigation; actual persisted audit events",
                "disposition_is_verified_ground_truth": False,
                **case_detail(db, case),
            }
            incident = outputs["sample_incident"]
            explanation = incident["prediction"]["explanation"]
            lines = [
                "# Executed synthetic investigation",
                "",
                f"Case {case.id} / transaction {case.transaction_id} was reviewed in the running application.",
                f"Final status: **{case.status}**. Investigator disposition: **{case.disposition}**.",
                "This opinion is separate from the generator label and is not an independent finding of fraud.",
                "",
                f"Stored model: `{incident['model_version']}`; operational score: {incident['risk_score']}/100.",
                f"Transaction: {incident['transaction']['currency']} {incident['transaction']['amount']:,.2f}.",
                "",
                "## Model evidence",
                "",
                f"Method: {explanation['method']}; units: {explanation['units']}.",
                f"Reference log-odds: {explanation['baseline']:.6f}; output log-odds: {explanation['output_log_odds']:.6f}.",
                "",
            ]
            for contribution in explanation["contributions"][:5]:
                lines.append(f"- {contribution['feature']}: observed {contribution['value']:.4f}, contribution {contribution['contribution']:+.4f}. {contribution['description']}")
            lines += ["", "## Actual audit timeline", ""]
            for event in incident["history"]:
                lines.append(f"- {event['created_at']} — {event['actor']} — {event['action']}: {json.dumps(event['details'])}")
            lines += ["", "The complete raw evidence is retained in `sample_incident.json`. No account was frozen and no real banking operation occurred.", ""]
            (destination / "sample_incident.md").write_text("\n".join(lines), encoding="utf-8")
        for name, data in outputs.items():
            (destination / f"{name}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        Path("docs/openapi.json").write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
        print(f"Exported {len(outputs)} reports and OpenAPI schema; resolved incident available: {bool(case)}")


if __name__ == "__main__":
    main()
