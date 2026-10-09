# Local IPC protocol, version 1

The Tauri shell writes one UTF-8 JSON request per line to Python stdin. Python
writes one UTF-8 JSON response per line to stdout and flushes immediately.
Python stderr is diagnostic output only. The shell must serialize requests to
this process and match each response to its request ID.

Request:

```json
{"version":1,"type":"request","id":"123-1","payload":{"operation":"echo","message":"Hello Sanvik"}}
```

`operation` is `ping`, `echo`, `plan_task`, or `shutdown`. `echo` and `plan_task` require a
non-empty `message`. For `plan_task`, `message` contains the natural-language task. Successful response:

```json
{"version":1,"type":"response","id":"123-1","success":true,"payload":{"message":"Sanvik Python received: Hello Sanvik"}}
```

Error response:

```json
{"version":1,"type":"response","id":"123-1","success":false,"error":{"code":"unknown_operation","message":"Unknown operation"}}
```

For malformed JSON or an unusable ID, the response ID is `null`. A
`shutdown` request receives an acknowledgement before Python exits. Closing
stdin also ends the Python loop. Tauri rejects invalid JSON, version, type,
and ID mismatches from Python, then drops that process and starts a new one on
the next request. Tauri waits up to ten seconds for ping/echo/shutdown and 65 seconds for planning. The Groq HTTP request has a 50-second timeout.

`plan_task` returns `payload.plan`, containing `goal` and a non-empty `steps` array. Each step has `action`, `parameters`, `expected_result`, and `risk_level`. The plan is validated intent data and is never executed by this protocol. Planning errors use `missing_api_key`, `provider_failure`, `provider_timeout`, `invalid_model_response`, `empty_task`, or `internal_error` in the existing error envelope.
