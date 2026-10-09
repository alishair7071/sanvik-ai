# Desktop application

`src/` contains the minimal React/TypeScript communication test UI.
`src/bridge/` owns frontend calls to narrow Tauri commands. `src-tauri/`
owns the Python process lifecycle and line-delimited JSON transport.

## Development

From the repository root, create the Python environment:

```powershell
python -m venv packages/agent/.venv
packages/agent/.venv/Scripts/python.exe -m pip install -e "./packages/agent[test]"
```

From `apps/desktop`:

```powershell
npm.cmd install
npm.cmd run tauri dev
```

Rust, the MSVC C++ build tools, and WebView2 are required to launch Tauri on
Windows. The Rust bridge runs the repository's Python environment at
`packages/agent/.venv/Scripts/python.exe`; set `SANVIK_PYTHON` to another
Python 3.12 executable if needed. Python imports the local `src/` package,
and requires the dependencies declared in `packages/agent/pyproject.toml`.

Set `GROQ_API_KEY` in the environment that launches Tauri, or put it in the
ignored `packages/agent/.env` file, to enable Groq planning. Optionally set
`GROQ_MODEL` (default: `openai/gpt-oss-20b`). Never commit the key.
