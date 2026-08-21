# offGIT

> **offGIT is an agentic development harness that observes changes across your development environment and uses an LLM to understand, document, and preserve project context automatically.**

---

## Overview

**offGIT** is an ambient background harness engineered to bridge modern development environments into a unified, version-controlled workflow:

- **AI-Native Coding Environments**: Google Antigravity, Cursor, Claude Code
- **Embedded & Specialized Editors (Filesystem Observer)**: Arduino IDE, Thonny (MicroPython / Python), Godot Engine (GDScript)

By decoupling real-time local activity tracking from periodic remote synchronization, offGIT maintains complete technical context across tool transitions while eliminating manual Git overhead.

```
                         +-------------------------------+
                         |      CORE HARNESS ENGINE      |
                         |        sync_engine.py         |
                         +---------------+---------------+
                                         ^
                                         | Ingests state & triggers
        +----------------+---------------+---------------+----------------+
        |                |                               |                |
 +------+------+  +------+------+                 +------+------+  +------+------+
 | Claude Code |  |   Cursor    |                 | Antigravity |  | Filesystem  |
 | Hook        |  | Event Hook  |                 | Tool Hook   |  | Watcher     |
 |             |  |             |                 |             |  | Arduino IDE |
 |             |  |             |                 |             |  | Thonny      |
 |             |  |             |                 |             |  | Godot Engine|
 +-------------+  +-------------+                 +-------------+  +-------------+
```

---

## Core Capabilities

### 1. Cross-Tool Context Continuity (`CONTEXT.md`)
- Maintains an up-to-date snapshot of active implementation focus, directives, and technical reasoning directly in the repository root.
- Standardized configuration pointers (`CLAUDE.md`, `.cursorrules`, `.cursor/rules/context.mdc`) ensure that secondary IDEs ingest project context immediately upon session initialization, eliminating context loss during tool switching.

### 2. High-Performance Decoupled Synchronization (`DEVLOG.md`)
- **Zero-Latency Activity Logging (< 1ms)**: Appends prompts, directives, and architectural rationale to local workspace metadata instantaneously without blocking editor responsiveness or executing synchronous network operations.
- **Batched Git Synchronization**: Executes on a structured 10-minute cadence. Analyzes unified `git diff HEAD` snapshots, produces factual changelogs via LLM summarization, and commits changes with source attribution (`AI-assisted` vs. `Manual edit (Arduino IDE / Thonny / Godot)`).

### 3. How Non-AI Editors Work (Arduino IDE, Thonny, Godot)
For environments that lack native AI extension APIs, offGIT provides automated LLM-assisted Git operations completely out-of-the-box:

1. **Filesystem Change Detection**: `watcher.py` monitors file save events across `.ino`, `.py`, `.gd`, `.tscn`, `.c`, and `.cpp` files.
2. **Git Diff Extraction**: At the 10-minute batch mark, the engine extracts the real code modifications using `git diff HEAD`.
3. **Headless LLM Inspection**: The raw diff is sent to the configured LLM CLI (Claude / Antigravity / Cursor) to inspect the technical changes and produce a structured summary of what was implemented (e.g. pin configurations, interrupt handlers, logic loops).
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
|-- .cursorrules               # Configuration pointer for Cursor environments
|-- .cursor/rules/context.mdc  # Standardized Cursor Composer rule definition
|-- .gitignore                 # Automatically configured exclusion for internal harness data
`-- .offgit/
    |-- prompt-log.jsonl       # Structured telemetry and reasoning logs (local-only)
    `-- prompt-count           # Interval tracking counter
```

---

## Quick Start

### Installation & Initialization

```powershell
python install_and_launch.py
```

The installer verifies system dependencies (`git`, `gh`, `node`, `claude`), installs required Python modules (`pyyaml`, `watchdog`), validates GitHub CLI authentication, registers Windows Task Scheduler autostart on logon, and initializes the background daemon.

### Configuration (`~/.offgit/config.yaml`)

```yaml
llm_tool: claude                       # Headless CLI provider for automated summarization
devlog_interval_seconds: 600           # Cadence for batched repository synchronization (10 min)
context_push_debounce_seconds: 120     # Debounce threshold for context updates
diff_char_limit: 8000                  # Maximum character limit for diff evaluation
watched_extensions:                    # File patterns monitored by the filesystem observer
  - .ino
  - .gd
  - .py
  - .ts
  - .cpp
  - .h
  - .js
  - .c
  - .hpp
  - .tscn
  - .md
prompt_threshold:                      # Prompt intervals for repository inception checks
  - 5
  - 15
  - 30
  - 60
thoughts_repo_path: ~/.offgit/thoughts # Path to private architectural decision repository
notifications: windows_toast           # Desktop notification provider
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