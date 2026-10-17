# Local IPC protocol, version 1

Tauri starts one long-running Python process. It writes one UTF-8 JSON request
per line to Python's stdin. Python writes one JSON response per line to stdout
and flushes immediately. Stdout is reserved for protocol messages; stderr is
for diagnostics. Requests are serialized and matched by ID.

A task request:

```json
{"version":1,"type":"request","id":"123-1","payload":{"operation":"run_task","message":"Open Notepad and type Hello"}}
```

`run_task` plans, validates, and executes supported steps. The successful
response contains both the plan and execution results:

```json
{"version":1,"type":"response","id":"123-1","success":true,"payload":{"plan":{"goal":"Open Notepad and type Hello","steps":[{"action":"open_application","parameters":{"application":"notepad"},"expected_result":"Notepad is visible","risk_level":"REVERSIBLE"},{"action":"type_text","parameters":{"text":"Hello"},"expected_result":"Hello appears in Notepad","risk_level":"REVERSIBLE"},{"action":"verify_text","parameters":{"text":"Hello"},"expected_result":"Notepad contains Hello","risk_level":"READ_ONLY"}]},"execution":{"completed":true,"steps":[{"action":"open_application","success":true,"message":"Completed"},{"action":"type_text","success":true,"message":"Completed"},{"action":"verify_text","success":true,"message":"Verified"}]}}}
```

The execution milestone accepts open-and-verify plans for Notepad, File
Explorer, and Google Chrome. It also accepts Notepad plans that type and verify the same text.
The execution result has one entry per attempted step. If an action
fails, `execution.completed` is false. A plan with an unsupported action or
parameter returns `unsupported_plan` before any desktop action. This protocol
does not stream step results yet; Rust allows up to 90 seconds for `run_task`.

Errors use the same envelope:

```json
{"version":1,"type":"response","id":"123-1","success":false,"error":{"code":"unsupported_plan","message":"Application must be one of: notepad, file_explorer, chrome"}}
```

The Python handler checks the version, type, ID, and payload. Malformed JSON or
an unusable ID gets a response with `id: null`. Planning errors can use codes
such as `empty_task`, `missing_api_key`, `provider_failure`, `provider_timeout`,
`invalid_model_response`, and `internal_error`.

Rust checks the response version, type, and matching ID. A bad response or
transport failure causes Rust to discard the Python process and start a new one
on the next request. The bridge waits up to 10 seconds for `ping`, `echo`, and
`shutdown`. The LangChain model request has a 50-second timeout. A `shutdown`
request receives an acknowledgement before Python exits; closing stdin also
ends the Python loop.

`ping` checks runtime readiness. `echo` is a development diagnostic. The
plan-only `plan_task` operation is no longer exposed. See [the request
flow](request-flow.md) for how the layers use `run_task`.
