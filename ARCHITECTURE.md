# OffGit — Architectural Specification

## Design Principles

1. **One Core, Many Triggers**: All real logic (`get_diff`, `summarize_with_llm`, `write_devlog`, `update_context_md`, `commit_and_push`, `maybe_scaffold_repo`) lives in `sync_engine.py`. Triggers are thin callers.
2. **Ground Truth is `git diff`**: `git diff HEAD` is the sole source of truth for what changed. Prompt logs serve strictly as supporting context.
3. **Autonomy is Scoped**: Commits, devlogs, and context snapshots are 100% automated. Brand new repository creation requires human confirmation via an LLM-phrased question.
4. **Private Thoughts Corpus**: The `thoughts` repository is private and auto-synced like any project repo.
5. **No Reverse-Engineered Internals**: Uses documented hook surfaces for Claude Code, Cursor, and Antigravity, with filesystem watchers for unhooked editors (Godot, Arduino IDE).
6. **Passive Cross-Tool Handoff**: No process spying. Incoming tools read `CONTEXT.md` via standard instruction pointers.
