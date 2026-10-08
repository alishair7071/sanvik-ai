# 0001: Local desktop-to-agent communication

Status: Day 1 request/response implemented; event streaming deferred

## Decision

Use a long-lived Python process launched and supervised by the Tauri Rust shell.
React calls narrow Tauri commands; the Rust bridge exchanges versioned,
newline-delimited JSON messages with Python over standard input and output.
Stream task events back to React through Tauri channels. Keep this transport
behind interfaces in `apps/desktop/src/bridge/` and
`packages/agent/src/sanvik_agent/ipc/`.

The wire contract should include protocol version, request/task IDs, message
type, payload, and explicit error/status values. Python standard output is
reserved for protocol messages; diagnostics go to standard error. The bridge
must eventually handle startup, cancellation, process exit, and restart.

## Reasoning

This supports a long-running local agent without exposing a localhost HTTP
port or adding an application server. Tauri documents bundled sidecars and
supports commands and channels for frontend communication. During development,
the process may run from the project Python environment; packaging the Python
runtime and Playwright browser assets is a separate implementation decision.

## Alternative

An authenticated loopback HTTP/WebSocket service is reasonable if multiple
local clients or independent agent lifecycle become requirements. It adds port
management and a local network attack surface, so it is not the V1 default.

The Day 1 transport is implemented in the Tauri shell and Python runtime. Production bundling remains out of scope.
