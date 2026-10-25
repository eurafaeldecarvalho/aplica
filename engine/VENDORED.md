# engine/ — vendored

Copy of the [aplica-claude-plugin](https://github.com/eurafaeldecarvalho/aplica-claude-plugin) engine,
bundled with the app for local database reads (`jobdb.py`). Agentic runs use the plugin via `claude -p`.
Keep it in sync; `jobdb.py check` warns if the database `schema_version` drifts from the engine.
