# offGIT

**A unified ambient developer harness for continuous Git sync, cross-tool context, and automated devlogs.**

---

## What is offGIT?

**offGIT** is a unified harness that runs silently underneath your coding environments (**Google Antigravity, Cursor, Claude Code, Godot Engine, Arduino IDE**).

It connects your tools through a single shared sync engine, keeping your repositories current, devlogs automated, and active context unified across sessions.

```
                         +-------------------------------+
                         |      UNIFIED CORE ENGINE      |
                         |        sync_engine.py         |
                         +---------------+---------------+
                                         ^
                                         | Calls engine
        +----------------+---------------+---------------+----------------+
        |                |                               |                |
 +------+------+  +------+------+                 +------+------+  +------+------+
 | Claude Code |  |   Cursor    |                 | Antigravity |  | Filesystem  |
 | Hook        |  | Hook        |                 | Hook        |  | Watcher     |
 +-------------+  +-------------+                 +-------------+  +-------------+
```

---

## What the Harness Does

1. **Unified Cross-Tool Context (`CONTEXT.md`)**
   - Writes a live snapshot of your current focus and reasoning on every prompt.
   - Claude Code, Cursor, and Antigravity automatically read `CONTEXT.md` on startup via standard pointers (`CLAUDE.md`, `.cursorrules`).
   - If you switch tools mid-project, the new tool picks up immediately where you left off.

2. **Automated Devlogs & Git Sync (`DEVLOG.md`)**
   - Evaluates real `git diff HEAD` every 10 minutes.
   - Writes factual changelog entries tagged with source attribution (`AI-assisted` vs `Manual edit`).
   - Automatically commits and pushes to your repository.

3. **Milestone Project Inception**
   - Tracks prompt milestones (`5, 15, 30, 60`).
   - At 5 prompts on a new project, offGIT generates a context-aware question and offers to scaffold and publish the GitHub repository.

4. **Private Thoughts Corpus**
   - Automatically records genuine architecture decisions into a private `thoughts` repository.

---

## Project Structure

```text
<project-root>/
├── CONTEXT.md                 # Live snapshot of current focus and state
├── DEVLOG.md                  # Chronological devlog with AI rationale
├── CLAUDE.md                  # "See CONTEXT.md for current project state."
├── .cursorrules               # "See CONTEXT.md for current project state."
├── .cursor/rules/context.mdc  # Cursor rule pointer
├── .gitignore                 # Automatically ignores .offgit/ internal logs
└── .offgit/
    ├── prompt-log.jsonl       # Prompt & reasoning log (local-only, gitignored)
    └── prompt-count           # Milestone counter (5, 15, 30, 60)
```

---

## Quick Start

```powershell
python install_and_launch.py
```

This verifies prerequisites, installs dependencies, verifies GitHub CLI authentication, registers Windows Task Scheduler for logon autostart, and starts the background harness.

---

## Credits & Attribution

Created and maintained by:
- **Flash 3.7**
- **Opus 4.6**
- **Sonnet 5**
- **Antigravity**

---

## License

MIT License
