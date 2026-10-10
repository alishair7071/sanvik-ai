// Data returned by Python through the Tauri bridge.
export type RiskLevel = "READ_ONLY" | "REVERSIBLE" | "SENSITIVE" | "DESTRUCTIVE";

export interface PlanStep {
  action: string;
  parameters: Record<string, string | number | boolean>;
  expected_result: string;
  risk_level: RiskLevel;
}

export interface Plan {
  goal: string;
  steps: PlanStep[];
}
export interface StepResult {
  action: string;
  success: boolean;
  message: string;
}

export interface Execution {
  completed: boolean;
  steps: StepResult[];
}

export interface RunResult {
  plan: Plan;
  execution: Execution;
}
