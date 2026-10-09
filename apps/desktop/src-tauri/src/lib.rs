mod python_runtime;

use std::sync::Arc;

use python_runtime::{Plan, RuntimeState};
use tauri::Manager;

#[tauri::command]
async fn ping_runtime(state: tauri::State<'_, Arc<RuntimeState>>) -> Result<String, String> {
    let runtime = Arc::clone(state.inner());
    tauri::async_runtime::spawn_blocking(move || {
        runtime
            .exchange("ping", None)?
            .message
            .ok_or_else(|| "Python response has no message".into())
    })
    .await
    .map_err(|error| format!("Python bridge task failed: {error}"))?
}

#[tauri::command]
async fn send_message(
    message: String,
    state: tauri::State<'_, Arc<RuntimeState>>,
) -> Result<String, String> {
    if message.trim().is_empty() {
        return Err("Message must not be empty".into());
    }

    let runtime = Arc::clone(state.inner());
    tauri::async_runtime::spawn_blocking(move || {
        runtime
            .exchange("echo", Some(&message))?
            .message
            .ok_or_else(|| "Python response has no message".into())
    })
    .await
    .map_err(|error| format!("Python bridge task failed: {error}"))?
}

#[tauri::command]
async fn plan_task(
    task: String,
    state: tauri::State<'_, Arc<RuntimeState>>,
) -> Result<Plan, String> {
    if task.trim().is_empty() {
        return Err("Task must not be empty".into());
    }

    let runtime = Arc::clone(state.inner());
    tauri::async_runtime::spawn_blocking(move || {
        runtime
            .exchange("plan_task", Some(&task))?
            .plan
            .ok_or_else(|| "Python response has no plan".into())
    })
    .await
    .map_err(|error| format!("Python bridge task failed: {error}"))?
}

pub fn run() {
    let app = tauri::Builder::default()
        .setup(|app| {
            let runtime = Arc::new(RuntimeState::new());
            app.manage(Arc::clone(&runtime));
            std::thread::spawn(move || {
                if let Err(error) = runtime.start() {
                    eprintln!("Sanvik Python startup: {error}");
                }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            ping_runtime,
            send_message,
            plan_task
        ])
        .build(tauri::generate_context!())
        .expect("failed to build Sanvik desktop");

    app.run(|app_handle, event| {
        if matches!(event, tauri::RunEvent::Exit) {
            app_handle.state::<Arc<RuntimeState>>().shutdown();
        }
    });
}
