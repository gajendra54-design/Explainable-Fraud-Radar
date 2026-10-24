# Portfolio walkthrough

## Five-minute demonstration

1. Explain the goal: help an investigator prioritize synthetic transactions, without declaring that model alerts are confirmed fraud.
2. Open the overview and show that totals come from the API and database.
3. Open a high-risk transaction. Compare supervised probability, anomaly priority, rule score and the blended operational score.
4. Read positive and mitigating contributions. Explain that additive logistic attribution is in log-odds and reconstructs only the supervised output.
5. Assign a case, record a note, escalate or resolve it, then inspect its audit history.
6. Change the evaluation threshold and show the workload/recall trade-off on held-out data.
7. Inspect drift and pipeline history, then explain the remaining deployment limitations.

## Technical questions to prepare

- Why chronological splitting? Future behavior must not influence earlier model decisions.
- Why are labels excluded from features? Ground truth and scenario names reveal the answer and cause target leakage.
- Why does precision fall when fraud is rare? Even a small false-positive rate can produce more false alerts than true alerts.
- Is an anomaly probability fraud probability? No; a rarity rank measures unusualness, and legitimate behavior can be unusual.
- Why retain model versions and feature values? Otherwise an explanation could silently refer to a different model than the stored prediction.
- Why transactional audit writes? A case state and the history that explains it must commit together.
- Why not automatically promote after drift? Drift may reflect benign changes or a broken pipeline; investigate and evaluate first.
- Why not add every suggested service? Operational complexity should solve a measured need. The local registry and synchronous batch workflow have explicit limitations.

## Presentation outline

Problem and boundaries → data lineage → leakage-safe features → model comparison → explanation demo → investigator workflow → monitoring → executed evidence → limitations and next steps.

Capture genuine screenshots of the running overview, explanation, case audit and evaluation screens. Do not substitute design mockups for execution evidence.
