export interface ServiceNode {
  id: string;
  name: string;
  kind: "edge" | "app" | "datastore" | "cache" | "external";
  tier: number;
  owner: string;
  replicas: number;
  slo_p95_ms: number;
  slo_error_pct: number;
  capacity_rps: number;
  timeout_ms: number;
}

export interface ServiceEdge {
  source: string;
  target: string;
  fanout: number;
}

export interface TopologyData {
  nodes: ServiceNode[];
  edges: ServiceEdge[];
}

export interface HealthState {
  score: number;
  status: "healthy" | "degraded" | "critical";
  services: Record<string, {
    score: number;
    status: string;
    metrics: Record<string, number>;
  }>;
}

export interface SystemInfo {
  state: string;
  tick: number;
  tick_seconds: number;
  wall_seconds: number;
  llm: {
    provider: string;
    model: string;
    mode: string;
  };
  ranker: {
    mode: string;
    model_path?: string;
  };
  detector: {
    fitted: boolean;
    threshold: number;
    harmonics: number;
    warmup_ticks: number;
    persistence: string;
    method: string;
  };
  knowledge_base: {
    documents: number;
    chunks: number;
    vocab_size: number;
  };
  stages: { id: string; label: string }[];
  scenarios: { id: string; title: string; blurb: string; severity: string }[];
  provenance: {
    real: string[];
    simulated: string[];
    production_gap: string[];
  };
}

export interface InvestigationStage {
  incident_id: string;
  stage: string;
  status: "running" | "done" | "waiting" | "failed";
  label: string;
  elapsed_ms: number;
  ts: number;
  detail?: string;
  provenance?: "REAL" | "SIMULATED" | "GAP";
  [key: string]: any;
}

export interface IncidentRecord {
  incident_id: string;
  record?: {
    id: string;
    scenario: string;
    status: string;
    created_at: number;
    root_class?: string;
    root_service?: string;
    confidence?: number;
    severity?: string;
    mttr_s?: number;
    ground_truth?: {
      root_service: string;
      root_class: string;
      gold_actions: string[];
    };
  };
  stages: InvestigationStage[];
  in_flight: boolean;
}

export interface EvalRun {
  run_id: string;
  created_at: number;
  config: Record<string, any>;
  detection: {
    f1: number;
    precision: number;
    recall: number;
    specificity: number;
    false_positive_rate_per_clean_episode: number;
    pr_auc: number;
    threshold: number;
    detection_delay_s: Record<string, any>;
    recall_ci95: [number, number];
  };
  localization: {
    top1_accuracy: number;
    top2_accuracy: number;
    top3_accuracy: number;
    top1_ci95: [number, number];
    per_scenario: Record<string, any>;
  };
  root_cause: {
    learned_accuracy?: number;
    learned_accuracy_ci95?: [number, number];
    rule_baseline_accuracy: number;
    rule_baseline_ci95: [number, number];
    macro_f1?: number;
    confusion_matrix?: number[][];
    calibration_bins?: { bin: string; empirical_accuracy: number }[];
  };
  retrieval: {
    predicted_class_query: {
      "recall@3": number;
      "precision@3": number;
      mrr: number;
      "ndcg@3": number;
    };
  };
  investigation: {
    remediation_action_accuracy: number;
    remediation_ci95: [number, number];
    joint_success_rate: number;
    joint_success_ci95: [number, number];
    definition: string;
  };
  latency: Record<string, any>;
  scenarios: Record<string, { title: string; root_service: string; root_class: string }>;
  honesty: string;
}
