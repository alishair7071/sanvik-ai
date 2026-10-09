use std::{
    env,
    io::{BufRead, BufReader, Write},
    path::PathBuf,
    process::{Child, ChildStdin, Command, Stdio},
    sync::{
        atomic::{AtomicU64, Ordering},
        mpsc::{self, Receiver},
        Mutex,
    },
    thread,
    time::{Duration, Instant},
};

use serde::{Deserialize, Serialize};

const PROTOCOL_VERSION: u8 = 1;
const RESPONSE_TIMEOUT: Duration = Duration::from_secs(10);
const PLAN_TIMEOUT: Duration = Duration::from_secs(65);

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

struct PythonProcess {
    child: Child,
    stdin: ChildStdin,
    stdout_lines: Receiver<Result<String, String>>,
}

impl PythonProcess {
    fn start() -> Result<Self, String> {
        let package_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../../packages/agent")
            .canonicalize()
            .map_err(|error| format!("Cannot locate Python package: {error}"))?;
        let python = match env::var_os("SANVIK_PYTHON") {
            Some(path) => PathBuf::from(path),
            None => package_root.join(".venv/Scripts/python.exe"),
        };
        if !python.is_file() {
            return Err(format!(
                "Python executable not found at {}. Create packages/agent/.venv or set SANVIK_PYTHON.",
                python.display()
            ));
        }

        let mut command = Command::new(&python);
        command
            .args(["-u", "-m", "sanvik_agent.ipc.runtime"])
            .current_dir(&package_root)
            .env("PYTHONPATH", package_root.join("src"))
            .env("PYTHONIOENCODING", "utf-8")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
        }

        let mut child = command
            .spawn()
            .map_err(|error| format!("Failed to start Python: {error}"))?;
        let stdin = child.stdin.take().ok_or("Python stdin was not piped")?;
        let stdout = child.stdout.take().ok_or("Python stdout was not piped")?;
        let stderr = child.stderr.take().ok_or("Python stderr was not piped")?;

        let (sender, stdout_lines) = mpsc::channel();
        thread::spawn(move || {
            for line in BufReader::new(stdout).lines() {
                let item = line.map_err(|error| format!("Cannot read Python stdout: {error}"));
                if sender.send(item).is_err() {
                    break;
                }
            }
        });
        thread::spawn(move || {
            for line in BufReader::new(stderr).lines() {
                match line {
                    Ok(text) => eprintln!("[sanvik-python] {text}"),
                    Err(error) => {
                        eprintln!("[sanvik-python] stderr read failed: {error}");
                        break;
                    }
                }
            }
        });

        Ok(Self {
            child,
            stdin,
            stdout_lines,
        })
    }

    fn request(
        &mut self,
        id: &str,
        operation: &str,
        message: Option<&str>,
    ) -> Result<ResponsePayload, String> {
        let request = Request {
            version: PROTOCOL_VERSION,
            kind: "request",
            id,
            payload: RequestPayload { operation, message },
        };
        let encoded = serde_json::to_string(&request)
            .map_err(|error| format!("Cannot encode request: {error}"))?;
        writeln!(self.stdin, "{encoded}")
            .and_then(|_| self.stdin.flush())
            .map_err(|error| format!("Cannot write to Python: {error}"))?;

        let line = self
            .stdout_lines
            .recv_timeout(if operation == "plan_task" {
                PLAN_TIMEOUT
            } else {
                RESPONSE_TIMEOUT
            })
            .map_err(|error| match error {
                mpsc::RecvTimeoutError::Timeout => "Python response timed out".to_string(),
                mpsc::RecvTimeoutError::Disconnected => {
                    let status = self.child.try_wait().ok().flatten();
                    format!("Python exited before responding (status: {status:?})")
                }
            })?
            .map_err(|error| format!("Python output failed: {error}"))?;

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
        let _ = self.request(id, "shutdown", None);
        let deadline = Instant::now() + Duration::from_secs(2);
        while Instant::now() < deadline {
            if self.child.try_wait().ok().flatten().is_some() {
                return;
            }
            thread::sleep(Duration::from_millis(20));
        }
    }
}

impl Drop for PythonProcess {
    fn drop(&mut self) {
        if self.child.try_wait().ok().flatten().is_none() {
            let _ = self.child.kill();
            let _ = self.child.wait();
        }
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
