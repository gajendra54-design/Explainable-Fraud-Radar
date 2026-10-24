# Model card

Intended use: synthetic fraud-review prioritization and software demonstration. Not suitable for autonomous enforcement, account freezing, legal accusations or real financial deployment without independent assessment.

Primary estimator: StandardScaler plus unweighted logistic regression. Comparators: balanced random forest, isolation forest and transparent rules. Exact installed versions are pinned in backend requirements. Model version, seed, feature schema, chronological boundaries, counts and validation threshold are exported in `reports/generated/model.json` after an actual run.

Evaluation uses a chronological final 20% holdout. Exported metrics include precision, recall, F1, specificity, false-positive rate, average precision (PR-AUC convention), ROC-AUC when both classes exist, confusion matrix, review volume, workload, capacity precision and channel/scenario breakdowns. No benchmark numbers are asserted here without an executed report.

Limitations: synthetic patterns and prevalence do not establish real-bank effectiveness. Sparse histories, customer cold starts, geographic simplification, currency differences and temporal distribution changes can degrade predictions. Account-group generalization and external validation are not implemented. Logistic probabilities are model outputs and have not undergone independent calibration assessment. Investigator labels are opinions until separately verified.

Approval: local synthetic demo only. No automatic promotion on drift. A versioned artifact can be restored for rollback; trusted local artifacts only. Explanation baseline and coefficients are stored with the artifact.
