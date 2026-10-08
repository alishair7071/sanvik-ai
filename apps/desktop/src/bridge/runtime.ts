import { invoke } from "@tauri-apps/api/core";

export function pingRuntime(): Promise<string> {
  return invoke<string>("ping_runtime");
}

export function sendMessage(message: string): Promise<string> {
  return invoke<string>("send_message", { message });
}
