import { invoke } from "@tauri-apps/api/core";

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

export function pingRuntime(): Promise<string> {
  return invoke<string>("ping_runtime");
}

export function sendMessage(message: string): Promise<string> {
  return invoke<string>("send_message", { message });
}

export function planTask(task: string): Promise<Plan> {
  return invoke<Plan>("plan_task", { task });
}
