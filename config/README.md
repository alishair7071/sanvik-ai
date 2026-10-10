# Configuration

Place versioned, non-secret configuration templates here when the runtime
settings schema exists. User settings, credentials, task history, and SQLite
databases belong in the user's application data directory, not this repository.

For local development only, the Python agent can read an ignored
`packages/agent/.env` file for the selected provider's API key. Change
`ACTIVE_PROVIDER` in `packages/agent/src/sanvik_agent/llm/provider.py` to
switch models. See `packages/agent/.env.example`. Product credential storage
will need a separate design before packaging.
