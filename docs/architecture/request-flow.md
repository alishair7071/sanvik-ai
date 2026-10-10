# One task through Sanvik

Example task: **Open Notepad and type Hello**. The plan wording can vary because
the model generates it. No step is executed.

```text
React form → Tauri command → Rust stdin → Python IPC
          → LangGraph planner → selected LangChain model → validated Plan
          → Python stdout → Rust response → React display
```

## Outbound request

1. `apps/desktop/src/App.tsx`: `submit()` takes the task from the input,
   shows a loading state, and calls `planTask(task)`.
2. `apps/desktop/src/bridge/runtime.ts`: `planTask()` invokes Tauri's
   `plan_task` command. `bridge/types.ts` describes the returned `Plan`.
3. `apps/desktop/src-tauri/src/lib.rs`: the `plan_task` command forwards the
   task through `RuntimeState.exchange("plan_task", ...)`.
4. `apps/desktop/src-tauri/src/python_ipc_bridge.rs`: `PythonProcess::request()`
   encodes a versioned JSON request. `python_process_manager.rs` writes that
   line to the long-running Python process's stdin:

   ```json
   {"version":1,"type":"request","id":"example-1","payload":{"operation":"plan_task","message":"Open Notepad and type Hello"}}
   ```

5. `packages/agent/src/sanvik_agent/ipc/runtime.py`: `serve()` reads the line;
   `handle_line()` validates its envelope and calls `plan_task(task)`.
6. `agent/planner.py`: `plan_task()` trims and checks the request, then runs
   the graph: `START -> create_plan -> END`. The node asks the selected model
   for a structured plan and validates it with `agent/plan.py`.
7. `llm/provider.py`: `get_chat_model()` selects Groq, OpenAI, or Anthropic from
   `ACTIVE_PROVIDER` in code and initializes only that LangChain integration. The graph
   requests structured output with the same prompt for every provider.
   `agent/plan.py` validates the returned data as a typed `Plan`.

## Return path

1. Python IPC converts the validated `Plan` to JSON and writes one response line
   to stdout. Stdout is reserved for this protocol; diagnostics use stderr.
2. Rust reads that line, checks the protocol version and request ID, and
   deserializes the plan. It returns the plan through the Tauri command.
3. The React `submit()` call receives the plan and renders its goal and steps.

If planning fails, Python returns an error code and safe message. Rust forwards
that failure to the Tauri command, and React displays it. The graph does not yet
persist state or recover automatically.

## Why these boundaries exist

Tauri needs Rust to manage its window and the Python child process. The Python
agent owns planning and the Groq call. Stdin/stdout avoids a separate local HTTP
server, port management, and a second server lifecycle for this single-client
desktop app. Vite's development URL serves the React page; it is not the
Tauri-to-Python channel.

The plan's `risk_level` and `action` fields are still untrusted model output
after schema validation. A later policy and capability layer must decide whether
an action is allowed and available before any computer operation happens.
Python `agent/plan.py` validates the plan at runtime. Rust and TypeScript have
matching transport types so those languages can pass and display it; those types
do not replace Python validation.
