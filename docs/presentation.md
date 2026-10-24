# Portfolio presentation

Open [the PowerPoint presentation](../reports/portfolio.pptx) for an eight-slide, approximately six-minute walkthrough.

1. **Explainable Fraud Radar:** introduce the synthetic transaction review application and decision-support scope.
2. **The investigator workspace:** describe the connected React and FastAPI workflow. The genuine screenshot shows the 3,000-record local demo, not the larger benchmark population.
3. **System architecture:** trace generation and validation through model training, API persistence and investigator review. PostgreSQL is the container deployment target, while SQLite supports local verification.
4. **Reproducible synthetic data:** explain the 100,000-record run and chronological 60,000/20,000/20,000 partitions. Highlight strict historical features and separate labels.
5. **Held-out synthetic performance:** discuss the actual 20,000-record test results from `reports/benchmark-100k/evaluation.json`. Logistic regression has 74.6% recall and 47.1% precision at the validation-selected 0.15 threshold. The model generates 1,808 alerts, including 957 false positives, and misses 289 positives. Compare PR-AUC across all four approaches. Explain why the deployed interpretable baseline remains useful even though the random forest comparator has higher PR-AUC.
6. **Explanations reproduce the score:** explain the exact additive log-odds calculation and sigmoid conversion. The genuine explanation screenshot uses the separate local demo model. Model attribution does not establish causation or fraud.
7. **Investigation and audit history:** describe assignment, notes, escalation and disposition, with transactional audit records. Predictions, investigator opinions and verified labels remain distinct.
8. **Validation and remaining limits:** state what local execution established and identify independent calibration, operational security and deployment work needed before real financial use.

The deck contains editable text and a native PowerPoint chart. Chart values derive from the benchmark report and round to four decimal places internally. Source references appear in speaker notes. The chart uses native literal data rather than an embedded Excel workbook, so cross-application chart editing is not verified. Screenshots remain raster evidence.

All eight slides were rendered and visually reviewed. Package, geometry, font and Artifact Tool import checks passed. Native Microsoft PowerPoint opening was not performed. The presentation makes no claim of public deployment or real-bank effectiveness.
