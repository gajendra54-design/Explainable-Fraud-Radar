export interface User {
  id: number;
  username: string;
  role: string;
}
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
export interface Contribution {
  feature: string;
  description: string;
  value: number;
  baseline: number;
  contribution: number;
  reason?: string;
}
export interface Explanation {
  method: string;
  units: string;
  baseline: number;
  output_log_odds: number;
  probability: number;
  contributions: Contribution[];
  model_version: string;
  limitations: string;
}
export interface Prediction {
  risk_score: number;
  risk_band: string;
  fraud_probability: number;
  anomaly_score: number;
  rule_score: number;
  model_version: string;
  prediction_timestamp: string;
  triggered_rules: (string | { name?: string; rule?: string })[];
  explanation: Explanation;
}
export interface Transaction {
  transaction_id: string;
  account_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  channel: string;
  timestamp: string;
  merchant_category: string;
  transaction_type: string;
  country_code: string;
  merchant_id: string;
  device_id: string;
  risk_score: number | null;
  risk_band: string;
  model_version: string;
  status: string;
  prediction?: Prediction;
  alert?: Case;
  related_transactions: Transaction[];
}
export interface Audit {
  id: number;
  action: string;
  created_at: string;
  actor: string;
  username?: string;
  details: unknown;
}
export interface Case {
  id: number;
  transaction_id: string;
  risk_score: number;
  risk_band: string;
  status: string;
  assigned_to: string | null;
  created_at: string;
  disposition: string | null;
  notes: {
    id: number;
    author: string;
    username?: string;
    text: string;
    created_at: string;
  }[];
  history: Audit[];
}
export interface Dashboard {
  transactions: number;
  alerts: number;
  high_risk: number;
  open_cases: number;
  model_version: string | null;
  pipeline_health: string;
  drift_status: string;
  fraud_rate: number | null;
  false_positive_rate: number | null;
  trend: { date: string; transactions: number; alerts: number }[];
  risk_distribution: { band: string; count: number }[];
  recent_alerts: Case[];
}
export interface Metrics {
  precision: number;
  recall: number;
  f1: number;
  false_positive_rate: number;
  pr_auc: number;
  roc_auc: number | null;
  alert_volume: number;
  true_positives: number;
  false_positives: number;
  true_negatives: number;
  false_negatives: number;
  threshold: number;
  sample_count: number;
}
export interface Evaluation extends Metrics {
  models: (Metrics & { name: string })[];
  curves?: {
    available: boolean;
    precision_recall: {
      precision: number;
      recall: number;
      threshold: number | null;
    }[];
    roc: {
      false_positive_rate: number;
      true_positive_rate: number;
      threshold: number | null;
    }[];
  };
  by_scenario: {
    scenario: string;
    sample_count: number;
    detection_rate: number;
  }[];
}
export interface DriftFeature {
  feature: string;
  psi: number;
  ks_statistic: number;
  p_value: number;
  status: string;
  drift_detected?: boolean;
}
export interface Drift {
  status: string;
  reference_count: number;
  current_count: number;
  features: DriftFeature[];
  recommendation: string;
  limitations: string;
}
export interface Performance {
  label_coverage: number;
  label_source: string;
  window_maturity: string;
  investigator_decisions_used_as_truth: boolean;
  metrics: Evaluation;
}
export interface Model {
  version: string;
  model_version?: string;
  info?: { algorithm: string };
  algorithm?: string;
  status?: string;
  active: boolean;
  created_at: string;
}
export interface PipelineRun {
  id: number;
  status: string;
  processed: number;
  rejected: number;
  duration_seconds: number;
  started_at: string;
  created_at?: string;
  error?: string;
}
export interface LivePerformance {
  transaction_count: number;
  mature_count: number;
  immature_count: number;
  labeled_count: number;
  mature_labeled_count: number;
  label_coverage: number;
  mature_label_coverage: number;
  status: string;
  models: {
    model_version: string;
    labeled_count: number;
    mature_count: number;
    label_coverage: number;
    metrics: Metrics | null;
    status: string;
    baseline_f1: number | null;
    performance_degradation: boolean | null;
  }[];
  limitations: string;
}
export interface DriftIncident {
  id: number;
  title: string;
  summary: string;
  severity: string;
  status: string;
  report: Drift;
  created_at: string;
  created_by: string;
  updated_at: string;
  history?: {
    id: number;
    actor: string;
    note: string;
    previous_status: string;
    status: string;
    created_at: string;
  }[];
}
