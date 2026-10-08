# Local IPC protocol, version 1

The Tauri shell writes one UTF-8 JSON request per line to Python stdin. Python
writes one UTF-8 JSON response per line to stdout and flushes immediately.
Python stderr is diagnostic output only. The shell must serialize requests to
this process and match each response to its request ID.

Request:

```json
{"version":1,"type":"request","id":"123-1","payload":{"operation":"echo","message":"Hello Sanvik"}}
```

`operation` is `ping`, `echo`, or `shutdown`. Only `echo` requires a
non-empty `message`. Successful response:

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
the next request. The command times out after ten seconds without a response.

This contract is for the Day 1 communication test and carries no agent actions.
