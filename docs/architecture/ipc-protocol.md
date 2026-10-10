# Local IPC protocol, version 1

Tauri starts one long-running Python process. It writes one UTF-8 JSON request per
line to Python's stdin. Python writes one JSON response per line to stdout and
flushes immediately. Stdout is reserved for protocol messages; stderr is for
diagnostics. Requests are serialized and matched by ID.

A planning request:

```json
{"version":1,"type":"request","id":"123-1","payload":{"operation":"plan_task","message":"Open Notepad and type Hello"}}
```

`message` carries the user's task for `plan_task`. The same field carries text
for the Day 1 `echo` operation. Other operations are `ping` and `shutdown`.
The successful planning response contains a structured plan:

```json
{"version":1,"type":"response","id":"123-1","success":true,"payload":{"plan":{"goal":"Open Notepad and type Hello","steps":[{"action":"launch_app","parameters":{"app":"Notepad"},"expected_result":"Notepad is open","risk_level":"READ_ONLY"}]}}}
```

Errors use the same envelope:

```json
{"version":1,"type":"response","id":"123-1","success":false,"error":{"code":"missing_api_key","message":"GROQ_API_KEY is not set in the Python environment or packages/agent/.env"}}
```

The Python handler checks the version, type, ID, and payload. Malformed JSON or
an unusable ID gets a response with `id: null`. Planning errors use codes such
as `empty_task`, `provider_failure`, `provider_timeout`,
`invalid_model_response`, and `internal_error`.

Rust checks the response version, type, and matching ID. A bad response or
transport failure causes Rust to discard the Python process and start a new one
on the next request. The bridge waits up to 10 seconds for ping, echo, and
shutdown, and 65 seconds for planning. The LangChain model request has a 50-second
timeout. A `shutdown` request receives an acknowledgement before Python exits;
closing stdin also ends the Python loop.

The plan is data returned to the UI. This protocol performs no computer actions.
See [the request flow](request-flow.md) for how the layers use it.