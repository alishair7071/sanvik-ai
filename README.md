# Sanvik AI

Sanvik AI is a Windows desktop application that turns a task into a structured plan.
The current execution milestone opens Notepad, File Explorer, or Google Chrome. It can also type text into Notepad and verify the result.

## Run it locally

From the repository root, install the Python agent dependencies:

```powershell
python -m venv packages/agent/.venv
packages/agent/.venv/Scripts/python.exe -m pip install -e "./packages/agent[test]"
```

Choose the provider by changing `ACTIVE_PROVIDER` near the top of
`packages/agent/src/sanvik_agent/llm/provider.py` to `groq`, `openai`, or
`anthropic`. The same file lists the model used for each provider. Copy
`packages/agent/.env.example` to the ignored `packages/agent/.env`, and set
only the selected provider's API key. Restart the desktop app after changing
the provider.

Then start the desktop app:

```powershell
cd apps/desktop
npm.cmd install
npm.cmd run tauri -- dev
```

Enter a request such as `Open Notepad and type Hello`, then select **Run task**.
Sanvik plans the task, checks the plan, executes supported steps, and shows the results.
Execution currently supports opening Notepad, File Explorer, or Google Chrome, and opening
Notepad to type text. The accepted application identifiers are `notepad`,
`file_explorer`, and `chrome`. The accepted actions are `open_application`, `type_text`,
`verify_application`, and `verify_text`. The entire plan is checked
before acting. Text is not saved to a file, and step results appear after the
task finishes.

Rust, the MSVC C++ build tools, and WebView2 are needed to run Tauri on Windows.
The Python executable can be overridden with `SANVIK_PYTHON`.

## Where to look

| Change you want to make | File |
| --- | --- |
| Task form, loading state, plan display | `apps/desktop/src/App.tsx` |
| React calls into Tauri | `apps/desktop/src/bridge/runtime.ts` |
| Plan data type used by React | `apps/desktop/src/bridge/types.ts` |
| Tauri commands and app startup | `apps/desktop/src-tauri/src/lib.rs` |
| Start, stop, and connect to Python | `apps/desktop/src-tauri/src/python_process_manager.rs` |
| JSON messages and response validation | `apps/desktop/src-tauri/src/python_ipc_bridge.rs` |
| Python request handling | `packages/agent/src/sanvik_agent/ipc/runtime.py` |
| Plan validation | `packages/agent/src/sanvik_agent/agent/plan.py` |
| Provider selection and LangChain setup | `packages/agent/src/sanvik_agent/llm/provider.py` |
| Shared planning prompt and model call | `packages/agent/src/sanvik_agent/agent/planner.py` |
| Plan then execute graph | `packages/agent/src/sanvik_agent/agent/workflow.py` |
| Plan safety checks | `packages/agent/src/sanvik_agent/execution/plan_validator.py` |
| Supported action execution | `packages/agent/src/sanvik_agent/execution/executor.py` |
| Windows UI Automation actions | `packages/agent/src/sanvik_agent/execution/windows.py` |

Read [the request flow](docs/architecture/request-flow.md) for one complete
example and [the repository map](docs/architecture/repository.md) for the layers.
