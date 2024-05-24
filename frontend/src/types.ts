export type User = { tenant: string; subject: string; roles: string[] };
export type Observation = {
  reference: string;
  kind: "metric" | "log";
  name?: string;
  value?: number;
  text?: string;
};
export type Evidence = {
  version: number;
  generation: number;
  digest: string;
  healthy: boolean;
  observations: Observation[];
};
export type Step = {
  action: string;
  target: string;
  arguments: Record<string, string | number>;
};
export type Plan = {
  version: number;
  digest: string;
  evidence_version: number;
  evidence_digest: string;
  steps: Step[];
  author: string;
  rationale: string;
};
export type IncidentSummary = {
  id: string;
  title: string;
  service: string;
  status: string;
  revision: number;
  created_at: number;
};
export type Incident = IncidentSummary & {
  tenant: string;
  created_by: string;
  mode?: string;
  evidence: Evidence | null;
  evidence_history: Evidence[];
  hypotheses: {
    label: string;
    references: string[];
    reason: string;
    source: string;
  }[];
  plan: Plan | null;
  review_request?: {
    subject: string;
    reason: string;
    plan_digest: string;
  } | null;
  approval: { subject: string; expires_at: number } | null;
  trace: {
    id: string;
    kind: string;
    actor: string;
    message: string;
    time: number;
    references: string[];
  }[];
  receipts: {
    key: string;
    action: string;
    changed: boolean;
    effect_number: number;
  }[];
  budget: {
    steps: number;
    seconds: number;
    model_calls: number;
    effects: number;
  };
  error: string | null;
};
export const readable = (value: string) => value.replace(/_/g, " ");
