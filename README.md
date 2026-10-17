# Sanvik AI

Sanvik AI is a Windows-first AI computer operator. The current V1 has a chat
interface that can answer general messages and can run the supported Windows
tasks through a controlled tool.

Supported computer actions currently include:

- Open Notepad, File Explorer, or Google Chrome.
- Close one visible File Explorer or Google Chrome window gracefully.
- Type text into Notepad.
- Verify application opening, application closing, and Notepad text.

Closing Notepad remains unsupported because unsaved text requires save-dialog
handling. When several matching Chrome or File Explorer windows are open,
Sanvik refuses to choose one automatically but accepts an explicit request to
close all of them.

## Run locally

From the repository root, install the Python agent dependencies:

```powershell
python -m venv packages/agent/.venv
packages/agent/.venv/Scripts/python.exe -m pip install -e "./packages/agent[test]"
```

Set `ACTIVE_PROVIDER` in
`packages/agent/src/sanvik_agent/llm/provider.py` to `groq`, `openai`, or
`anthropic`. Copy `packages/agent/.env.example` to the ignored
`packages/agent/.env` and add the selected provider's API key.

Start the desktop app:

```powershell
cd apps/desktop
npm.cmd install
npm.cmd run tauri -- dev
```

Type a general question or a supported computer request such as
`Open Notepad and type Hello`. The chat keeps context while the desktop app
and its Python process remain open.

Rust, the MSVC C++ build tools, and WebView2 are required for Tauri on Windows.
Set `SANVIK_PYTHON` to override the Python executable used by the desktop app.

## Main files

| Responsibility | File |
| --- | --- |
| Chat interface | `apps/desktop/src/App.tsx` |
| React to Tauri calls | `apps/desktop/src/bridge/runtime.ts` |
| Tauri commands and startup | `apps/desktop/src-tauri/src/lib.rs` |
| Python process lifecycle | `apps/desktop/src-tauri/src/python_process_manager.rs` |
| Rust JSON bridge | `apps/desktop/src-tauri/src/python_ipc_bridge.rs` |
| Python request handling | `packages/agent/src/sanvik_agent/ipc/runtime.py` |
| Conversation LangGraph | `packages/agent/src/sanvik_agent/agent/conversation.py` |
| Computer task tool wrapper | `packages/agent/src/sanvik_agent/tools/computer_task_tool.py` |
| Plan and execute LangGraph | `packages/agent/src/sanvik_agent/agent/workflow.py` |
| Structured planner | `packages/agent/src/sanvik_agent/agent/planner.py` |
| Plan safety checks | `packages/agent/src/sanvik_agent/execution/plan_validator.py` |
| Action dispatch | `packages/agent/src/sanvik_agent/execution/executor.py` |
| Windows actions | `packages/agent/src/sanvik_agent/execution/windows.py` |

See [the request flow](docs/architecture/request-flow.md) and
[the IPC protocol](docs/architecture/ipc-protocol.md) for the end-to-end path.
