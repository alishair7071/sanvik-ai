# Desktop application

`src/` contains the minimal React/TypeScript communication test UI.
`src/bridge/` owns frontend calls to narrow Tauri commands. `src-tauri/`
owns the Python process lifecycle and line-delimited JSON transport.

## Development

From the repository root, create the Python environment:

```powershell
python -m venv packages/agent/.venv
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
so an editable install is not required for this communication test.
