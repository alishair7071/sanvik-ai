# One task through Sanvik

Example task: **Open Notepad and type Hello**. The model may phrase the plan
steps differently. The execution layer checks every step before acting.

```text
React form -> Tauri run_task command -> Rust stdin -> Python IPC
           -> LangGraph workflow -> planner -> checked plan -> execution
           -> Python stdout -> Rust response -> React result
```

## Outbound request

1. `apps/desktop/src/App.tsx`: submitting the form calls `runTask(task)` and
   shows a loading state.
2. `apps/desktop/src/bridge/runtime.ts`: `runTask()` invokes Tauri's `run_task`
   command. `bridge/types.ts` describes the returned plan and execution result.
3. `apps/desktop/src-tauri/src/lib.rs`: the command forwards the task through
   `RuntimeState.exchange("run_task", ...)`.
4. `apps/desktop/src-tauri/src/python_ipc_bridge.rs` builds a versioned JSON
   request. `python_process_manager.rs` writes it to the long-running Python
   process's stdin:

   ```json
   {"version":1,"type":"request","id":"example-1","payload":{"operation":"run_task","message":"Open Notepad and type Hello"}}
   ```

5. `packages/agent/src/sanvik_agent/ipc/runtime.py`: `serve()` reads the line;
   `handle_line()` validates it and calls `run_task(task)`.
6. `agent/workflow.py`: LangGraph calls its planning node, then its execution
   node. The planning node calls `agent/planner.py`; the execution node calls
   `execution/executor.py`.
7. `agent/planner.py` selects a LangChain model through `llm/provider.py` and
   asks it for a structured `Plan`. `agent/plan.py` validates that structure.
8. `execution/executor.py` checks the *entire* plan against supported actions
   and parameters before dispatching anything. `execution/windows.py` performs
   Windows actions and verifies their observable results.

## Return path

1. Python writes the plan and execution results as one JSON response line to
   stdout. Stdout is reserved for the protocol; diagnostics use stderr.
2. Rust checks the protocol version and request ID, deserializes the response,
   and returns it through the Tauri command.
3. React shows the task, planned steps, and each action's result.

A rejected plan returns an `unsupported_plan` error before desktop actions.
An action can still fail during execution; then `execution.completed` is false.
The response arrives after execution; this version does not stream progress.

## Why these boundaries exist

Tauri manages its window and the Python child process. Python owns planning,
policy checks, and computer operations. Stdin/stdout avoids a local HTTP server
and port management for this single-client desktop app. Vite's development URL
serves the React page; it is not the Tauri-to-Python channel.

The plan's `risk_level`, `action`, and parameters are untrusted model output.
Schema validation in `agent/plan.py` checks their shape; the executor checks
whether each action and parameter is actually supported before acting.
