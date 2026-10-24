# Technical glossary

This guide follows the code paths in `backend/app`, `ml`, and `frontend/src`. The examples describe synthetic records only. “Positive” means the generator's fraud label is 1, not a criminal finding.

## Web and storage

**API** — A defined interface through which programs communicate. It keeps the UI independent of database internals. FastAPI routes in `backend/app/api` accept validated requests and return JSON; for example, the explorer asks for a page of transactions. A common mistake is treating an endpoint's existence as permission to use it. Related: REST, authorization.

**REST** — A resource-oriented style of HTTP API. Routes represent things such as transactions and cases, and verbs represent operations. The versioned routes in `backend/app/api` let the React client fetch and change resources. For example, GET reads a transaction while POST records a note. REST is an architectural style, not a security protocol. Related: API, HTTP.

**HTTP** — The request/response protocol used between browser and API. Methods, headers and status codes carry intent and outcome. FastAPI returns success or error statuses; the frontend API client checks them. A 401 means authentication is needed, while 403 means the authenticated role lacks permission. Do not display a success toast for every completed network request. Related: REST, JSON.

**JSON** — A text format for objects, arrays, numbers, strings, booleans and null. It allows Python and TypeScript to exchange structured data. API responses contain transaction IDs and risk values. `backend/app/schemas` validates incoming structures. JSON itself does not enforce a schema, and NaN is not valid JSON. Related: schema, API.

**ORM** — An object-relational mapper translates Python expressions into SQL. SQLAlchemy in `backend/app/db` and `backend/app/models` maps persistent entities and binds query parameters. A case object becomes a database row. An ORM does not remove the need for indexes, transactions or query review. Related: SQL, migration.

**SQL** — A language for selecting and changing relational data. PostgreSQL executes SQL produced by SQLAlchemy, including filtered transaction queries. Parameter binding keeps a search term separate from executable query syntax. Never concatenate user input into SQL. Related: ORM, PostgreSQL.

**PostgreSQL** — The relational database used by Docker Compose. It enforces keys and transactions, stores application state durably, and supports concurrent clients. The `postgres` service persists data in a named volume. Stopping a container differs from deleting its volume. SQLite is only the lightweight local/test alternative. Related: SQL, transaction, migration.

**Migration** — A versioned change to database structure. Alembic scripts in `backend/migrations` move the schema to a known revision. Running upgrade creates the tables required by the current application. Editing a model class alone does not update an existing database. Related: schema, rollback.

**Schema** — A formal definition of fields, types and constraints. Pydantic schemas validate API requests; SQLAlchemy models define persistence. A positive transaction amount and a valid timestamp are schema rules. Matching field names is insufficient if units or meaning differ. Related: validation, JSON.

## Data engineering

**ETL** — Extract, transform, load: clean data before placing it in its curated destination. `ml/validation` and backend ingestion reject invalid input before persisting usable transactions. A negative amount goes to quarantine. ETL differs from ELT in where transformation occurs. Related: curated data, quarantine.

**ELT** — Extract, load, transform: retain source data first and transform it later. Retaining raw request payloads or generated JSON makes later reconstruction possible. This application primarily validates before curated ingestion; it is not a distributed ELT warehouse. Never assume raw records are safe to train on. Related: ETL, lineage.

**Raw and curated data** — Raw records preserve source fields; curated records have passed validation and consistent definitions. Generated records originate in `ml/data_generation`, while ingestion stores valid transactions and separates rejected ones. A raw duplicate is not a second valid transaction. Related: ETL, schema.

**Data lineage** — The trace from input to output. Pipeline IDs, transaction IDs, feature version and model version explain how a score was produced. `backend/app/services` and `ml/inference` connect these references. A score without its model and feature context is not reproducible. Related: audit, model registry.

**Batch processing** — Processing a bounded set of records together. The seed CLI generates and scores a dataset and records a pipeline run. A batch of 3,000 records provides quick-start data. Training jobs use a durable database queue with bounded retries and lease recovery; direct transaction batch ingestion remains synchronous and clients can safely replay transaction IDs. Related: streaming, idempotency.

**Streaming** — Processing events incrementally as they arrive. Single-transaction ingestion offers incremental scoring, but the repository does not implement Kafka-style delivery semantics. Real streaming needs ordering, deduplication and late-event policy. Calling an HTTP endpoint repeatedly is not a full streaming architecture. Related: batch, event time.

**Idempotency** — Repeating an operation has the same intended durable result as doing it once. Unique transaction IDs prevent replayed ingestion from duplicating records. Backend ingestion checks existing IDs and database constraints provide the final guard. A retry must not create a second alert or overwrite investigation history. Related: transaction, batch.

**Feature engineering** — Turning raw observations into numerical model inputs. `ml/features.engineer` calculates amount ratios, historical counts and first-seen indicators. An amount ratio compares a transaction with that customer's past spending. A useful feature must be available at prediction time. Related: rolling window, leakage.

**Rolling window** — A moving interval relative to each transaction time. `ml/features.engineer` maintains preceding one-hour and 24-hour activity. Three earlier events in one hour create a velocity signal. Including the current event twice or later events changes the definition and causes train/serve inconsistency. Related: feature engineering, event time.

**Data leakage** — Information crosses a boundary it should not cross during model development. Fitting preprocessing on held-out test data leaks its distribution. `ml/training.train_models` fits preprocessing on the training split only. Good test scores obtained through leakage will not generalize. Related: target leakage, chronological split.

**Target leakage** — A special case of leakage where predictors reveal the answer or post-outcome information. Fraud labels, scenario names and investigator decisions are excluded by `ml/features.FEATURE_NAMES`. Using a confirmed-fraud flag to predict fraud would be circular. Related: data leakage, ground truth.

**Chronological split** — Dividing records in time order so training precedes validation and testing. `ml/training` uses 60/20/20 partitions. Validation selects a threshold; the final period estimates out-of-time performance. Random splits can hide temporal failures. Related: leakage, holdout.

## Models and evaluation

**Class imbalance** — One outcome is much rarer than another. Synthetic prevalence is configurable in `ml/data_generation`; most records are legitimate. Predicting every transaction as legitimate can yield high accuracy but zero fraud recall. Related: precision, PR-AUC.

**Supervised learning** — Learning from examples paired with known labels. `ml/training` trains Logistic Regression and Random Forest using synthetic ground truth. The model learns associations between historical features and labels. Investigator opinions should not silently become verified training labels. Related: classification, unsupervised learning.

**Unsupervised learning** — Learning structure without predicting a supplied outcome label. Isolation Forest models unusual feature patterns in `ml/training`. The reference training subset consists of synthetic legitimate examples, so the selection itself uses known training labels. Unusualness is not proof of fraud. Related: anomaly detection, supervised learning.

**Classification** — Assigning observations to categories, often via a probability and threshold. Logistic Regression in `ml/training` estimates the synthetic positive class. Comparing its output with a chosen threshold determines review priority. A classification decision is not an enforcement decision. Related: probability, threshold.

**Anomaly detection** — Finding observations unlike a reference population. Isolation Forest isolates rare patterns; `ml/inference` converts its scores into a reference percentile. A percentile of 0.99 means unusually high anomaly rank, not 99% fraud probability. Related: unsupervised learning, calibration.

**Probability calibration** — Agreement between predicted probabilities and observed frequencies. Among many genuinely calibrated 0.2 predictions, approximately 20% would be positive in a comparable population. This repository exposes logistic probabilities but does not establish real-world calibration. Synthetic prevalence shifts can invalidate them. Related: threshold, class imbalance.

**Threshold** — A cutoff converting a continuous score into an action category. `ml/training` chooses the logistic decision threshold using validation F1 and an alert-capacity constraint; `ml/evaluation` measures alternatives. Lower cutoffs usually increase alerts and recall. Never optimize a production threshold on the final test set. Related: precision, recall.

**Confusion matrix** — Counts of true positives, false positives, false negatives and true negatives at one threshold. `ml/evaluation.evaluate` compares predictions with labels. It distinguishes a missed positive from an unnecessary alert. Always specify the positive class and matrix layout. Related: precision, specificity.

**Precision** — TP/(TP+FP): the share of alerts that are labelled positive. `ml/evaluation` returns zero when no positives are predicted. If 10 alerts include 3 true positives, precision is 0.3. Precision is not the share of all fraud found. Related: recall, false positive.

**Recall** — TP/(TP+FN): the share of labelled positives detected. `ml/evaluation` computes it safely when no positives exist. Finding 3 of 5 positives gives recall 0.6. High recall can coexist with an overwhelming false-alert workload. Related: precision, false negative.

**F1-score** — The harmonic mean of precision and recall, 2PR/(P+R). `ml/evaluation` computes it for threshold comparison. It penalizes a very low value of either component. F1 does not express staffing cost or financial loss directly. Related: threshold, alert workload.

**Specificity** — TN/(TN+FP): the share of legitimate examples correctly not alerted. `ml/evaluation` reports this alongside false-positive rate. Specificity of 0.98 corresponds to a false-positive rate of 0.02. It is not precision. Related: confusion matrix, false-positive rate.

**False-positive rate** — FP/(FP+TN): the share of negatives incorrectly alerted. `ml/evaluation` handles empty denominators. A small rate can still create many alerts when legitimate transactions dominate. Do not divide FP by the number of alerts; that measures a different quantity. Related: precision, imbalance.

**PR-AUC** — A summary of the precision-recall trade-off as thresholds vary. The implementation uses scikit-learn average precision, a step-weighted PR summary, and labels it accordingly in methodology. `ml/evaluation` emphasizes it for rare positives. It depends strongly on prevalence and is not interchangeable with ROC-AUC. Related: recall, class imbalance.

**ROC-AUC** — Area under the true-positive-rate versus false-positive-rate curve. `ml/evaluation` reports it only when both classes exist. It measures ranking discrimination across thresholds. A strong ROC-AUC can coexist with low operational precision in a rare-event setting. Related: PR-AUC, threshold.

**False positive** — A legitimate labelled example that triggers an alert. It consumes investigation time; `ml/evaluation` counts it and the case UI permits a legitimate disposition. An analyst's opinion does not alter the synthetic label. Related: precision, verified ground truth.

**False negative** — A labelled positive below the review threshold. `ml/evaluation` counts missed synthetic cases. Raising the threshold can reduce workload but increase misses. A dashboard showing only alerts cannot reveal false negatives without labels. Related: recall, label coverage.

**Alert workload** — The number of cases a threshold sends for review and the estimated time required. `ml/evaluation` exposes alert counts and capacity metrics. A ten-minute review assumption converts counts to staff time. Such an estimate is an assumption, not measured human productivity. Related: threshold, precision at capacity.

## Explainability and monitoring

**SHAP** — A family of model-attribution methods based on distributing an output difference across features. The project uses a model-appropriate exact linear additive decomposition in `ml/explainability`, rather than claiming to run SHAP. Both approaches require explicit units and a baseline. Attribution does not prove causation. Related: feature contribution, baseline.

**Baseline** — The reference output or behavior used for comparison. In `ml/explainability`, a reference linear-model output plus contributions reconstructs the prediction in log-odds. In feature engineering, a past spending median is a different kind of baseline. Do not confuse these two uses. Related: contribution, log-odds.

**Feature contribution** — A signed amount by which a feature changes an explained model output relative to its reference. `ml/explainability.explain` uses logistic coefficients and standardized inputs. Positive bars increase log-odds; negative bars mitigate them. They are not percentage-point changes in the operational score. Related: baseline, SHAP.

**Log-odds** — The natural logarithm of p/(1-p). Logistic Regression adds coefficients in this space; the sigmoid converts the result to probability. `ml/explainability` checks baseline plus contributions. Adding a contribution directly to a percentage would be mathematically wrong. Related: probability, contribution.

**Data drift** — A change in the distribution of inputs relative to a reference window. `ml/monitoring` uses numerical PSI/KS and categorical comparisons. A shifted amount distribution may warn of a pipeline problem or changed activity. A statistical warning alone does not establish fraud or model failure. Related: concept drift, prediction drift.

**Concept drift** — A change in the relationship between features and outcomes. A pattern that used to predict fraud might become normal. Monitoring cannot establish this from feature distributions alone; mature verified labels are needed. The API labels this uncertainty. Related: performance degradation, data drift.

**Prediction drift** — A change in score distributions or predicted-positive rate. `ml/inference.drift_report` compares outputs across windows. More high scores could arise from changed inputs without reduced accuracy. Do not substitute prediction drift for verified performance analysis. Related: data drift, label coverage.

**Model registry** — A catalogue connecting model versions, artifacts and evaluation metadata. The local implementation uses database metadata plus trusted persisted joblib artifacts in `ml/inference`. A version makes historical explanations reproducible. A filename alone is not an approval process; this is a local substitute for an MLflow service. Related: inference, rollback.

**Inference** — Applying a trained model to features to obtain a prediction. `ml/inference.FraudEngine` shares feature definitions with training and returns score, version and explanation. It must not refit preprocessing for each transaction. Related: training, feature engineering.

**Retraining** — Fitting a new model on a deliberately selected dataset. The pipeline can produce a new version; monitoring recommends investigation before promotion. Retraining is not automatically safe merely because it uses newer data. Compare approved and candidate models on a meaningful holdout. Related: registry, drift.

**Label coverage** — The share of evaluated records with usable verified outcomes. Synthetic generated datasets have immediate labels; arbitrary incoming transactions may not. Monitoring distinguishes missing labels from negatives. Never interpret low-coverage performance as a mature population estimate. Related: concept drift, recall.

## Security and operations

**Authentication** — Establishing identity, implemented in `backend/app/security` through password verification and signed tokens. A successful login identifies the user. A valid identity does not imply administrator authority. Related: authorization, hashing.

**Authorization** — Checking whether an identity may perform an operation. Backend role guards protect case mutations and pipeline administration. For example, analysts can read but should not resolve cases. Hiding a button is not an authorization control. Related: authentication, least privilege.

**JWT** — A signed JSON Web Token carrying identity and expiration claims. Backend security signs and verifies tokens using an environment-provided secret. A signature prevents undetected modification; it does not encrypt the payload. Never place passwords inside a JWT or log it. Related: authentication, encryption.

**Hashing** — A one-way transformation used with a salt and work factor to verify passwords. `backend/app/security` compares a derived hash instead of retaining plaintext. Fast general-purpose hashes alone are inappropriate for passwords. Hashing differs from encryption because there is no decryption key. Related: authentication, encryption.

**Encryption** — Reversible protection using a secret key. HTTPS is required in production to protect browser/API traffic; managed database and artifact storage should enable encryption at rest. Local HTTP is a development setting. A hashed password does not encrypt the database. Related: hashing, TLS.

**Docker** — Tooling for building and running isolated container images. Dockerfiles and `docker-compose.yml` describe application dependencies and services. A clean build reproduces runtime installation. Containers are not a replacement for patching, least privilege or backups. Related: container, CI/CD.

**Container** — A running isolated process environment created from an image. Compose runs PostgreSQL, backend and frontend containers with private service networking. Persistent volumes retain state independently of container replacement. Do not store the only model copy in an ephemeral container layer. Related: Docker, volume.

**CI/CD** — Continuous integration automates checks on changes; continuous delivery prepares deployable artifacts. `.github/workflows/ci.yml` runs tests and frontend build. Passing CI is evidence for those checks, not proof that a deployment has happened. Related: tests, deployment.

**Health check** — A probe of service condition. `/health` confirms the process responds; `/ready` checks whether it can serve useful work. Compose uses probes for startup coordination. A responding web server with a missing model should not be called fully ready. Related: observability, SRE.

**Observability** — Inferring internal behavior from outputs such as logs, metrics and traces. Request IDs, pipeline records and metrics expose application state. A failed ingestion can be linked to its run and error. Collecting data without actionable review is not sufficient monitoring. Related: logging, metrics, tracing.

**Logging** — Recording discrete events. Backend middleware emits structured request information and failures. A request ID helps correlate an error with a user report. Avoid credentials, tokens and unnecessary payloads in logs. Related: observability, auditing.

**Metrics** — Numeric measurements aggregated over time or a dataset. `/metrics` exposes operational counters while `ml/evaluation` reports model performance. A request count and precision measure different things. Keep units and denominators explicit. Related: monitoring, logging.

**Tracing** — Following one operation across components using correlated identifiers and spans. This project provides request IDs but not a complete distributed OpenTelemetry tracing deployment. A request ID can locate associated logs. Do not claim distributed tracing simply because IDs exist. Related: observability, logging.

**Unit test** — A focused test of a function or small component. `backend/tests/test_ml.py` checks feature chronology, metrics and attribution. A test should validate behavior with an independent expectation, not repeat the same implementation. Related: integration test, end-to-end test.

**Integration test** — A test of connected components. Backend API tests exercise authentication, database writes and audit events; PostgreSQL migration verification checks the deployed storage path. SQLite tests alone cannot prove PostgreSQL compatibility. Related: unit test, migration.

**End-to-end test** — A test of a user's full workflow through the browser and server. Frontend tests cover login, browsing, investigation and evaluation when the application is running. A successful build does not replace browser execution. Record which environment and flow were actually tested. Related: integration test, acceptance evidence.
