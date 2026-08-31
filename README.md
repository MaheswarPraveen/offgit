# offGIT

> **offGIT is an agentic development harness that observes changes across your development environment and uses an LLM to understand, document, and preserve project context automatically.**

---

## Overview

**offGIT** is an ambient background harness engineered to bridge modern development environments into a unified, version-controlled workflow:

- **AI-Native Coding Environments**: Google Antigravity, Cursor, Claude Code, OpenAI Codex / Copilot CLI
- **Embedded & Specialized Editors (Filesystem Observer)**: Arduino IDE, Thonny (MicroPython / Python), Godot Engine (GDScript)

By decoupling real-time local activity tracking from periodic remote synchronization, offGIT maintains complete technical context across tool transitions while eliminating manual Git overhead.

```
                                  +-------------------------------+
                                  |      CORE HARNESS ENGINE      |
                                  |        sync_engine.py         |
                                  +---------------+---------------+
                                                  ^
                                                  | Ingests state & triggers
        +----------------+---------------+--------+------+---------------+----------------+
        |                |                               |               |                |
 +------+------+  +------+------+                 +------+------+ +------+------+  +------+------+
 | Claude Code |  |   Cursor    |                 | Antigravity | |    Codex    |  | Filesystem  |
 | Hook        |  | Event Hook  |                 | Tool Hook   | | CLI / Hook  |  | Watcher     |
 |             |  |             |                 |             | |             |  | Arduino IDE |
 |             |  |             |                 |             | |             |  | Thonny      |
 |             |  |             |                 |             | |             |  | Godot Engine|
 +-------------+  +-------------+                 +-------------+ +-------------+  +-------------+
```

---

## Core Capabilities

### 1. Cross-Tool Context Continuity (`CONTEXT.md`)
- Maintains an up-to-date snapshot of active implementation focus, directives, and technical reasoning directly in the repository root.
- Standardized configuration pointers (`CLAUDE.md`, `CODEX.md`, `.cursorrules`, `.cursor/rules/context.mdc`) ensure that secondary IDEs and AI tools ingest project context immediately upon session initialization, eliminating context loss during tool switching.

### 2. High-Performance Decoupled Synchronization (`DEVLOG.md`)
- **Zero-Latency Activity Logging (< 1ms)**: Appends prompts, directives, and architectural rationale to local workspace metadata instantaneously without blocking editor responsiveness or executing synchronous network operations.
- **Batched Git Synchronization**: Executes on a structured 10-minute cadence. Analyzes unified `git diff HEAD` snapshots, produces factual changelogs via LLM summarization, and commits changes with source attribution (`AI-assisted (Claude Code)`, `AI-assisted (Cursor)`, `AI-assisted (Antigravity)`, `AI-assisted (Codex)`, `Manual edit (Arduino IDE / Thonny / Godot)`).

### 3. How Non-AI Editors Work (Arduino IDE, Thonny, Godot)
For environments that lack native AI extension APIs, offGIT provides automated LLM-assisted Git operations completely out-of-the-box:

1. **Filesystem Change Detection**: `watcher.py` monitors file save events across `.ino`, `.py`, `.gd`, `.tscn`, `.c`, and `.cpp` files.
2. **Git Diff Extraction**: At the 10-minute batch mark, the engine extracts the real code modifications using `git diff HEAD`.
3. **Headless LLM Inspection**: The raw diff is sent to the configured LLM CLI (Claude / Antigravity / Cursor / Codex) to inspect the technical changes and produce a structured summary of what was implemented (e.g. pin configurations, interrupt handlers, logic loops).
4. **Automated Commit & Remote Upload**: The LLM-generated changelog is appended to `DEVLOG.md` under `Manual edit (Arduino IDE / Thonny / Godot)`, `CONTEXT.md` is updated, and all code changes are committed and pushed to GitHub.

### 4. Automated Project Inception
- Analyzes interaction volume at defined conversational intervals (5, 15, 30, 60 prompts).
- Suggests structured kebab-case repository naming derived from conversational context and prompts the developer via a clean interactive interface prior to remote provisioning via GitHub CLI.

### 5. Technical Decision Archive
- Automatically identifies architectural design patterns, trade-offs, and decisions, recording them into a centralized private decision repository (`~/.offgit/thoughts/`).

---

## Repository Structure

Projects managed by offGIT adhere to a clean, standardized structure:

```text
<project-root>/
|-- CONTEXT.md                 # Live snapshot of active objectives and implementation state
|-- DEVLOG.md                  # Comprehensive chronological log with architectural rationale
|-- CLAUDE.md                  # Configuration pointer for Claude Code environments
|-- CODEX.md                   # Configuration pointer for Codex environments
|-- .cursorrules               # Configuration pointer for Cursor environments
|-- .cursor/rules/context.mdc  # Standardized Cursor Composer rule definition
|-- .gitignore                 # Automatically configured exclusion for internal harness data
`-- .offgit/
    |-- prompt-log.jsonl       # Structured telemetry and reasoning logs (local-only)
    `-- prompt-count           # Interval tracking counter
```

---

## Production Hardening & Safety

- **Safe Subprocess Execution**: All commands and headless LLM calls execute with strict argument lists (`shell=False`) and timeout protection (15s on LLM calls, 30s on git operations), preventing shell-injection vulnerabilities.
- **Divergence Prevention**: Auto-runs `git pull --rebase --autostash` before pushing to avoid rejected sync cycles if upstream moved.
- **Private by Default**: New repositories scaffold as **private** by default (`default_repo_visibility: private` in `config.yaml`), giving you full control over repository exposure.
- **Non-Destructive Pointer Injection**: AI editor rules (`CLAUDE.md`, `.cursorrules`, `CODEX.md`) are appended non-destructively without altering or overwriting existing hand-written user configurations.
- **Cross-Platform OS Architecture**: Native notification adapters and process management across **Windows** (Toast / Startup launcher), **macOS** (osascript / launchd), and **Linux** (notify-send / systemd).

## Quick Start

### One-Click Automated Setup

Double-click **`setup.bat`** (or execute via PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

```
===================================================
         offGIT - One-Click Setup & Launch
===================================================

[1/5] Verifying & Installing dependencies (git, gh, node via winget)...
[2/5] Setting up Python environment & libraries (pyyaml, watchdog)...
[3/5] Launching GitHub browser OAuth login (gh auth login)...
[4/5] Installing global IDE integration rules across Antigravity, Claude, Cursor...
[5/5] Registering background logon autostart and launching daemon...

[SUCCESS] offGIT is authenticated, running, and ready!
```

---
## Credits & Attribution

Created with and maintained with:
- **Flash 3.7**
- **Opus 4.6**
- **Sonnet 5**
- **Antigravity**

---

## License

GNU General Public License v3.0 (GPL-3.0)