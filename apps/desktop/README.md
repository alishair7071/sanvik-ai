# Desktop application

`src/` is reserved for the React/TypeScript interface. `src/bridge/` will hold
the frontend-facing transport interface so UI code does not depend on the
Python IPC protocol.

`src-tauri/` is reserved for the Tauri shell. It will own the Python process
lifecycle and mediate communication between the webview and local runtime.
Tauri manifests, a frontend build, and the process bridge are not present yet.
