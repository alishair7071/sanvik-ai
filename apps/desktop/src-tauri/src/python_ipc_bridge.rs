//! JSON request/response bridge between Tauri commands and the local Python process.
//! python_process_manager.rs owns interpreter startup, pipes, and process cleanup.

use std::{
    sync::{
        atomic::{AtomicU64, Ordering},
        Mutex,
    },
    time::Duration,
};

use serde::{Deserialize, Serialize};

use crate::python_process_manager::PythonProcess;

const PROTOCOL_VERSION: u8 = 1;
const RESPONSE_TIMEOUT: Duration = Duration::from_secs(10);
const PLAN_TIMEOUT: Duration = Duration::from_secs(65);
const RUN_TIMEOUT: Duration = Duration::from_secs(90);

#[derive(Serialize)]
struct Request<'a> {
    version: u8,
    #[serde(rename = "type")]
    kind: &'static str,
    id: &'a str,
    payload: RequestPayload<'a>,
}

#[derive(Serialize)]
struct RequestPayload<'a> {
    operation: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    message: Option<&'a str>,
}

#[derive(Deserialize)]
struct Response {
    version: u8,
    #[serde(rename = "type")]
    kind: String,
    id: Option<String>,
    success: bool,
    payload: Option<ResponsePayload>,
    error: Option<ResponseError>,
}

#[derive(Deserialize)]
pub struct ResponsePayload {
    pub message: Option<String>,
    pub plan: Option<Plan>,
    pub execution: Option<Execution>,
}

#[derive(Deserialize, Serialize)]
pub struct Execution {
    pub completed: bool,
    pub steps: Vec<StepResult>,
}

#[derive(Deserialize, Serialize)]
pub struct StepResult {
    pub action: String,
    pub success: bool,
    pub message: String,
}
#[derive(Deserialize, Serialize)]
pub struct Plan {
    pub goal: String,
    pub steps: Vec<PlanStep>,
}

#[derive(Deserialize, Serialize)]
pub struct PlanStep {
    pub action: String,
    pub parameters: serde_json::Map<String, serde_json::Value>,
    pub expected_result: String,
    pub risk_level: String,
}

#[derive(Deserialize)]
struct ResponseError {
    code: String,
    message: String,
}

impl PythonProcess {
    fn request(
        &mut self,
        id: &str,
        operation: &str,
        message: Option<&str>,
    ) -> Result<ResponsePayload, String> {
        // Encode a versioned, correlated request for the Python IPC handler.
        let request = Request {
            version: PROTOCOL_VERSION,
            kind: "request",
            id,
            payload: RequestPayload { operation, message },
        };
        let encoded = serde_json::to_string(&request)
            .map_err(|error| format!("Cannot encode request: {error}"))?;
        // Send the encoded request to Python through its stdin pipe.
        self.write_line(&encoded)?;

        // Wait for one response from Python's stdout, with more time for planning.
        let timeout = if operation == "run_task" {
            RUN_TIMEOUT
        } else if operation == "plan_task" {
            PLAN_TIMEOUT
        } else {
            RESPONSE_TIMEOUT
        };
        let line = self.read_line(timeout)?;
        // Parse and validate the response before returning any result to a Tauri command.
        let response: Response = serde_json::from_str(&line)
            .map_err(|error| format!("Invalid JSON from Python: {error}"))?;
        if response.version != PROTOCOL_VERSION || response.kind != "response" {
            return Err("Invalid Python response version or type".into());
        }
        if response.id.as_deref() != Some(id) {
            return Err(format!("Python response ID mismatch for request {id}"));
        }
        if !response.success {
            return Err(match response.error {
                Some(error) => format!("Python error {}: {}", error.code, error.message),
                None => "Python returned an error without details".into(),
            });
        }
        response
            .payload
            .ok_or_else(|| "Python response has no payload".into())
    }

    fn shutdown(&mut self, id: &str) {
        // Ask Python to exit through the same protocol, then allow a short grace period.
        let _ = self.request(id, "shutdown", None);
        self.wait_for_exit();
    }
}

pub struct RuntimeState {
    process: Mutex<Option<PythonProcess>>,
    next_id: AtomicU64,
}

impl RuntimeState {
    pub fn new() -> Self {
        Self {
            process: Mutex::new(None),
            next_id: AtomicU64::new(1),
        }
    }

    fn request_id(&self) -> String {
        format!(
            "{}-{}",
            std::process::id(),
            self.next_id.fetch_add(1, Ordering::Relaxed)
        )
    }

    // Start once on app startup; exchange() also starts lazily if startup failed.
    pub fn start(&self) -> Result<(), String> {
        let mut guard = self
            .process
            .lock()
            .map_err(|_| "Python bridge lock failed")?;
        if guard.is_none() {
            *guard = Some(PythonProcess::start()?);
        }
        Ok(())
    }

    // Serialize access to the single Python process and reset it after any protocol error.
    pub fn exchange(
        &self,
        operation: &str,
        message: Option<&str>,
    ) -> Result<ResponsePayload, String> {
        let mut guard = self
            .process
            .lock()
            .map_err(|_| "Python bridge lock failed")?;
        if guard.is_none() {
            *guard = Some(PythonProcess::start()?);
        }
        let id = self.request_id();
        let result = guard
            .as_mut()
            .expect("Python process was started")
            .request(&id, operation, message);
        if result.is_err() {
            *guard = None;
        }
        result
    }

    pub fn shutdown(&self) {
        if let Ok(mut guard) = self.process.lock() {
            if let Some(process) = guard.as_mut() {
                process.shutdown(&self.request_id());
            }
            *guard = None;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::RuntimeState;

    #[test]
    fn python_ipc_bridge_handles_requests_errors_and_shutdown() {
        let runtime = RuntimeState::new();

        let ping = runtime.exchange("ping", None).expect("ping should succeed");
        assert_eq!(
            ping.message.as_deref(),
            Some("Sanvik Python runtime is running")
        );

        let echo = runtime
            .exchange("echo", Some("Hello"))
            .expect("echo should succeed");
        assert_eq!(
            echo.message.as_deref(),
            Some("Sanvik Python received: Hello")
        );

        let error = runtime
            .exchange("unknown", None)
            .err()
            .expect("unknown operation should fail");
        assert!(error.contains("unknown_operation"));

        // An error discards the process; the next request starts a new one.
        assert!(runtime.exchange("ping", None).is_ok());
        runtime.shutdown();
        assert!(runtime.process.lock().unwrap().is_none());
    }
}
