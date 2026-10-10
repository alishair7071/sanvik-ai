# Desktop app

`src/` is the React interface and `src/bridge/` contains the frontend's
Tauri calls and the data types returned through them.

`src-tauri/` is the desktop shell. It owns the Python process and exchanges
JSON lines with the local agent through stdin and stdout.

See the [root README](../../README.md) for setup and
[request flow](../../docs/architecture/request-flow.md) for the full path of a task.