# Executed synthetic investigation

Case 293 / transaction TXN-042-0002963 was reviewed in the running application.
Final status: **Resolved**. Investigator disposition: **Inconclusive**.
This opinion is separate from the generator label and is not an independent finding of fraud.

Stored model: `lr-v1-b725bf7e38`; operational score: 21.57/100.
Transaction: LKR 2,192.65.

## Model evidence

Method: Exact logistic linear attribution; units: log-odds.
Reference log-odds: -4.276093; output log-odds: -1.291153.

- ip_risk: observed 0.4679, contribution +1.9358. Synthetic IP risk indicator
- new_device: observed 1.0000, contribution +0.9349. Device not previously seen for customer
- log_spend_24h: observed 0.0000, contribution +0.1687. Prior 24-hour spend (natural log)
- night_time: observed 1.0000, contribution +0.1672. Transaction between midnight and 05:00 UTC
- log_amount: observed 7.6933, contribution +0.1323. Transaction amount (natural log of 1 + LKR)

## Actual audit timeline

- 2026-10-23T10:46:02.525095+00:00 — admin — assigned: {"previous": null, "assigned_to": "admin"}
- 2026-10-23T10:46:02.690802+00:00 — admin — status_changed: {"previous": "Assigned", "status": "Under Review"}
- 2026-10-23T10:46:02.787486+00:00 — admin — note_added: {"text": "Automated E2E review: synthetic evidence inspected; no enforcement action."}
- 2026-10-23T10:46:03.066031+00:00 — admin — disposition_recorded: {"disposition": "Inconclusive", "verified_ground_truth_changed": false}

The complete raw evidence is retained in `sample_incident.json`. No account was frozen and no real banking operation occurred.
