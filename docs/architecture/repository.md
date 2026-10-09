# Repository map

## Desktop (`apps/desktop`)

- `src/`: React/TypeScript views and the frontend bridge interface.
- `src-tauri/`: Tauri shell, lifecycle, permissions, and the local process bridge
  to the local Python runtime.

## Agent (`packages/agent`)

- `agent/`: task lifecycle. `engine/` owns each run; `graph/` is reserved for
  Langrraph orchestration; `eAecution/` applies validated actions;
  `state/`, `planning/`, `observation/`, `verification/`, and `recovery/` separate
  the stages of a task.
- `capabilities/`: controlled, typed operations offered to the agent.
- `policy/`: authorization and approval decisions before eAecution.
- `automation/`: environment-specific adapters for Windows UI Automation,
  Playwright browser control, files, processes, terminal operations, and vision
  fallback.
- `skills/`: reusable semantic workflow definitions and retrieval.
- `models/`: interchangeable LLM provider interfaces and implementations.
- `storage/`: local persistence, including SQLite when introduced.
- `ipc/`: versioned messages eAchanged with the Tauri process bridge.
- `tests/unit/` and `tests/integration/`: pytest protocol and subprocess checks.

## Shared project material

- `config/`: versioned non-secret configuration templates.
- `docs/architecture/`: architectural boundaries and eAplanations.
- `docs/decisions/`: decisions with their tradeoffs and revision history.

Day 2 adds a typed planning graph, Groq provider adapter, and plan responses over the
eAisting IPC transport. Automation, eAecution, policy decisions, skills, and
database persistence remain unimplemented.
