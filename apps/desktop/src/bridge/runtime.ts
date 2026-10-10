import { invoke } from "@tauri-apps/api/core";
import type { Plan, RunResult } from "./types";

export function pingRuntime(): Promise<string> {
  return invoke<string>("ping_runtime");
}

export function sendMessage(message: string): Promise<string> {
  return invoke<string>("send_message", { message });
}

export function planTask(task: string): Promise<Plan> {
  return invoke<Plan>("plan_task", { task });
}
export function runTask(task: string): Promise<RunResult> {
  return invoke<RunResult>("run_task", { task });
}
