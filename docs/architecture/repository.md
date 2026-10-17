# Repository map

```text
sanvik-ai/
|-- apps/desktop/
|   |-- src/
|   |   |-- App.tsx                    React chat interface
|   |   `-- bridge/
|   |       |-- runtime.ts             Typed Tauri calls
|   |       `-- types.ts               Lower-level task result types
|   `-- src-tauri/src/
|       |-- lib.rs                     Tauri commands and app lifecycle
|       |-- python_process_manager.rs  Python startup, pipes, and shutdown
|       `-- python_ipc_bridge.rs       JSON transport and response checks
|-- packages/agent/
|   |-- src/sanvik_agent/
|   |   |-- ipc/runtime.py             Python request loop
|   |   |-- agent/
|   |   |   |-- conversation.py       Chat and tool-calling LangGraph
|   |   |   |-- workflow.py           Plan then execute LangGraph
|   |   |   |-- planner.py            Structured LLM planning
|   |   |   `-- plan.py               Plan data models
|   |   |-- tools/
|   |   |   `-- computer_task_tool.py Tool wrapper around the task graph
|   |   |-- execution/
|   |   |   |-- plan_validator.py     Supported-plan checks
|   |   |   |-- executor.py           Action dispatch
|   |   |   `-- windows.py            Windows actions
|   |   `-- llm/provider.py           LangChain provider selection
|   `-- tests/                         Unit and IPC integration tests
|-- docs/architecture/                 Architecture and request flow
|-- docs/decisions/                    Architecture decisions
`-- config/                            Non-secret configuration notes
```

## Layer responsibilities

- **React:** displays the conversation and sends one message with a conversation ID.
- **Tauri/Rust:** owns the Python child process and transports validated JSON.
- **Python IPC:** validates and routes protocol operations.
- **Conversation agent:** answers directly or calls the controlled computer tool.
- **Computer tool:** exposes the existing task workflow to the conversation agent.
- **Task workflow:** plans first, then coordinates validated execution.
- **Execution:** checks allowed actions and parameters before touching Windows.
- **LLM provider:** supplies one configured LangChain chat model to both graphs.

The two LangGraphs have separate responsibilities. The conversation graph owns
the dialogue and tool choice. The task graph owns planning and execution of one
computer request.
