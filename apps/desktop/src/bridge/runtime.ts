import { invoke } from "@tauri-apps/api/core";
import type { RunResult } from "./types";

export function pingRuntime(): Promise<string> {
  return invoke<string>("ping_runtime");
}

export function sendMessage(message: string): Promise<string> {
  return invoke<string>("send_message", { message });
}

export function sendChatMessage(
  message: string,
  conversationId: string,
): Promise<string> {
  return invoke<string>("chat_message", { message, conversationId });
}

export function runTask(task: string): Promise<RunResult> {
  return invoke<RunResult>("run_task", { task });
}
