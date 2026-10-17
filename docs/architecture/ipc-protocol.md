# Local IPC protocol, version 1

Tauri starts one long-running Python process. Rust writes one UTF-8 JSON request
per line to Python stdin. Python writes one JSON response per line to stdout and
flushes immediately. Requests are serialized and matched by ID.

## Chat request

```json
{"version":1,"type":"request","id":"123-1","payload":{"operation":"chat_message","message":"Open Chrome","conversation_id":"chat-abc"}}
```

A successful response contains the assistant's final text:

```json
{"version":1,"type":"response","id":"123-1","success":true,"payload":{"message":"Chrome opened successfully."}}
```

The conversation ID must contain 1 to 128 characters. Reusing it lets the
conversation LangGraph remember earlier messages while the Python process is
running.

For a computer request, the conversation graph calls the
`run_computer_task` tool. The tool uses the existing task graph to plan,
validate, execute, and verify supported actions. The task result is returned to
the conversation graph before it creates the final response.

The execution layer can gracefully close one visible Chrome or File Explorer
window. It reports an already-closed application as successful and refuses to
choose when multiple matching windows exist unless the user explicitly requests
that all matching windows close. Notepad closing and forceful process
termination are not supported.

## Other operations

- `ping` checks whether Python is ready.
- `echo` is a development diagnostic.
- `run_task` remains available as the lower-level plan-and-execute operation.
- `shutdown` acknowledges the request and stops the Python loop.

## Errors and validation

Errors use the same envelope:

```json
{"version":1,"type":"response","id":"123-1","success":false,"error":{"code":"invalid_message","message":"Message must not be empty"}}
```

Python validates JSON, protocol version, message type, request ID, payload,
operation, message, and conversation ID. Rust validates the response version,
type, and matching request ID. A transport or protocol failure causes Rust to
discard the child process and start a new one on the next request.

Rust waits 10 seconds for simple operations, 90 seconds for `run_task`, and
180 seconds for `chat_message`. Chat can involve an initial model call, a task
planning call, computer execution, and a final model call.
