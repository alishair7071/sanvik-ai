//! Owns the local Python process: locate it, start it, connect pipes, and stop it.
//! JSON encoding and validation live in python_ipc_bridge.rs.

use std::{
    env,
    io::{BufRead, BufReader, Write},
    path::PathBuf,
    process::{Child, ChildStdin, Command, Stdio},
    sync::mpsc::{self, Receiver},
    thread,
    time::{Duration, Instant},
};

pub(super) struct PythonProcess {
    child: Child,
    stdin: ChildStdin,
    stdout_lines: Receiver<Result<String, String>>,
}

impl PythonProcess {
    pub(super) fn start() -> Result<Self, String> {
        // Locate the agent package relative to this Tauri crate.
        let package_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../../packages/agent")
            .canonicalize()
            .map_err(|error| format!("Cannot locate Python package: {error}"))?;
        // Use an existing Python interpreter; this does not create a virtual environment.
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

        // Configure the local agent module and pipe JSON messages through stdin/stdout.
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

        // spawn() is the line that actually starts Python.
        let mut child = command
            .spawn()
            .map_err(|error| format!("Failed to start Python: {error}"))?;
        let stdin = child.stdin.take().ok_or("Python stdin was not piped")?;
        let stdout = child.stdout.take().ok_or("Python stdout was not piped")?;
        let stderr = child.stderr.take().ok_or("Python stderr was not piped")?;

        // Read stdout on a thread so requests can time out while Python runs.
        let (sender, stdout_lines) = mpsc::channel();
        thread::spawn(move || {
            for line in BufReader::new(stdout).lines() {
                let item = line.map_err(|error| format!("Cannot read Python stdout: {error}"));
                if sender.send(item).is_err() {
                    break;
                }
            }
        });
        // Python stdout is JSON only; stderr carries diagnostics.
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

    // Send one JSON line to Python's stdin.
    pub(super) fn write_line(&mut self, line: &str) -> Result<(), String> {
        writeln!(self.stdin, "{line}")
            .and_then(|_| self.stdin.flush())
            .map_err(|error| format!("Cannot write to Python: {error}"))
    }

    // Read one response from stdout; distinguish a timeout from a process exit.
    pub(super) fn read_line(&mut self, timeout: Duration) -> Result<String, String> {
        self.stdout_lines
            .recv_timeout(timeout)
            .map_err(|error| match error {
                mpsc::RecvTimeoutError::Timeout => "Python response timed out".to_string(),
                mpsc::RecvTimeoutError::Disconnected => {
                    let status = self.child.try_wait().ok().flatten();
                    format!("Python exited before responding (status: {status:?})")
                }
            })?
            .map_err(|error| format!("Python output failed: {error}"))
    }

    // Allow the agent to finish after receiving the shutdown request.
    pub(super) fn wait_for_exit(&mut self) {
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
        // A reset or app exit must not leave a Python child running.
        if self.child.try_wait().ok().flatten().is_none() {
            let _ = self.child.kill();
            let _ = self.child.wait();
        }
    }
}
