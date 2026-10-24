# Synthetic data card

Source: seeded NumPy simulation, exclusively synthetic. No bank connection, customer financial record or personal identifier is required. `generate_transactions` accepts transaction/customer/merchant counts, period length, seed and fraud prevalence. The 100,000-row CLI and 3,000-row quick-start use the same implementation.

Normal spending uses customer-specific lognormal baselines with additional variability. Fraud scenarios include high relative amounts, repeated-customer transactions seconds after a previous event, small threshold-evasion amounts, first-seen devices, geographic anomalies, account-takeover-like combinations and unusual night activity. Nonfraud records sometimes receive overlapping anomalies. The fraud rate is a Bernoulli sampling probability, not a guaranteed exact proportion. Scenario signals are intentionally imperfect; some simulated fraud will look ordinary.

Generated history is sorted chronologically. Labels and scenario names are stored for supervised training and benchmark segmentation, never used as explanatory input features. Fraud prevalence affects precision and investigator load even when recall stays similar. Reports must state prevalence and review capacity alongside detection metrics.

Limitations: no realistic interbank network, device fingerprints, sustained fraud rings, demographic population or calibrated economic geography; velocity events are short pairs rather than a fully simulated attack campaign. Account opening ages are seeded once per account and increase consistently with elapsed days. Transactions use a fixed historical start of 2026-01-01 and a configurable number of days; choose a period ending before current time to pass validation. These records cannot support claims about fairness or real institutional fraud rates.

Retention: generated raw files and model binaries are local build outputs and should not be committed. Keep seed/config, feature version and model metadata for reproducibility. Regenerate rather than introducing real records into the demo.
