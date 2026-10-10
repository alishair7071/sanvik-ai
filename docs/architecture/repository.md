# Repository map

Only implemented code appears in the active source tree. Add separate execution,
policy, automation, verification, recovery, storage, and skill modules when those
features are built.

```text
sanvik-ai/
├── apps/desktop/
│   ├── src/
│   │   ├── App.tsx                 Task input and plan display
│   │   └── bridge/
│   │       ├── runtime.ts          React calls to Tauri
│   │       └── types.ts            Plan type at the frontend boundary
│   └── src-tauri/src/
│       ├── lib.rs                  Tauri setup and commands
│       ├── python_process_manager.rs  Start/stop Python and own its pipes
│       └── python_ipc_bridge.rs       JSON requests and response validation
├── packages/agent/
│   ├── src/sanvik_agent/
│   │   ├── ipc/runtime.py          Python request loop and responses
│   │   ├── agent/
│   │   │   ├── planner.py          LangGraph and task state
│   │   │   └── plan.py             Validated plan data
│   │   └── llm/
│   │       └── provider.py         Model selection, keys, and errors
│   └── tests/                      Unit and subprocess tests
├── docs/architecture/             How the layers communicate
├── docs/decisions/                Why the transport was chosen
└── config/                        Non-secret configuration notes
```

## Layer responsibilities

- **Frontend:** accepts a task, calls a narrow Tauri command, and displays a plan
  or error. It cannot call the Python process or Groq directly.
- **Desktop shell:** opens and closes the Python process, forwards JSON requests,
  checks response IDs and timeouts, and returns results to React. It does not plan.
- **Python IPC:** parses and routes requests, then writes one response per request.
  It does not contain the planning prompt or API protocol.
- **Agent:** validates the task and plan and runs the small LangGraph flow.
- **LLM:** selects one LangChain chat integration and loads only its API key from
  the Python environment or an ignored local file.

The current plan is data only. There are no actions or policy decisions yet.
