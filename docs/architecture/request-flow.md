# One chat turn through Sanvik

Example message: **Open Notepad and type Hello**.

```text
React chat -> Tauri chat_message -> Rust stdin -> Python IPC
           -> conversation LangGraph
              -> direct answer, or computer tool
                 -> task LangGraph -> planner -> validator -> execution
              -> final assistant answer
           -> Python stdout -> Rust -> React chat
```

## Request path

1. `apps/desktop/src/App.tsx` adds the user's message to the chat and calls
   `sendChatMessage(message, conversationId)`.
2. `apps/desktop/src/bridge/runtime.ts` invokes Tauri's `chat_message` command.
3. `apps/desktop/src-tauri/src/lib.rs` validates the values and calls the local
   Python bridge.
4. `python_ipc_bridge.rs` writes a versioned JSON line to Python:

   ```json
   {"version":1,"type":"request","id":"123-1","payload":{"operation":"chat_message","message":"Open Notepad and type Hello","conversation_id":"example-chat"}}
   ```

5. `packages/agent/src/sanvik_agent/ipc/runtime.py` validates the request and
   calls `agent/conversation.py`.
6. The conversation graph asks the model whether it can answer directly or
   should call `run_computer_task`.
7. For a computer request, `tools/computer_task_tool.py` calls the existing
   `agent/workflow.py`. That graph creates a validated plan and passes it to
   the execution layer.
8. The tool result returns to the conversation graph. The model uses that real
   result to write the assistant reply.

## Response path

Python writes one JSON response line to stdout. Rust checks the version and
request ID, extracts `payload.message`, and returns it to React. React adds the
text as an assistant message.

The same `conversation_id` is reused for every message in the open UI session,
so LangGraph can include earlier messages. This memory currently lives only in
the Python process and is cleared when the desktop app exits.

## Boundaries

- React owns chat display and input.
- Rust owns the desktop process boundary and request transport.
- The conversation graph decides between a direct answer and the computer tool.
- The task graph plans and coordinates execution.
- The execution layer validates model output and performs supported Windows actions.
- Stdout is reserved for JSON protocol messages; diagnostics use stderr.
