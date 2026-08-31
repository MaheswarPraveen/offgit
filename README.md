# offGIT

> An ambient development harness that observes local changes across development environments, automatically recording architectural reasoning into a private decision corpus while maintaining clean, version-controlled project repositories.

---

## Overview

offGIT runs as a lightweight ambient process that unifies modern AI coding tools and embedded editors into a cohesive, automated workflow:

- **AI-Native Environments**: Google Antigravity, Cursor, Claude Code, OpenAI Codex
- **Embedded & Specialized Editors**: Arduino IDE, Thonny, Godot Engine

By decoupling real-time local activity tracking (< 1ms) from periodic remote synchronization (10-minute cadence), offGIT preserves technical reasoning without introducing editor latency or manual Git overhead.

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

## Architecture & Dual-Channel Routing

On every 10-minute synchronization cycle, offGIT processes active workspaces through two independent channels:

1. **Channel A (Private Thoughts Repository)**:
   - Ingests developer directives and AI architectural reasoning.
   - Formats structured Architecture Decision Records (`YYYY-MM-DD_<project>_<slug>.md`).
   - Maintains a chronological index table in your private `thoughts` GitHub repository.

2. **Channel B (Project Code Repository)**:
   - Evaluates file diffs across monitored source files (`.ino`, `.gd`, `.py`, `.ts`, `.cpp`, `.h`, `.c`).
   - Generates a factual `DEVLOG.md` entry with tool attribution.
   - Refreshes the live implementation state in `CONTEXT.md`.
   - Executes rebase-safe commits and pushes upstream.

---

## Quick Start & Installation

### Windows

Open **PowerShell** and execute:

```powershell
irm https://raw.githubusercontent.com/MaheswarPraveen/offgit/main/install.ps1 | iex
```

---

### macOS & Linux

Open **Terminal** and execute:

```bash
curl -fsSL https://raw.githubusercontent.com/MaheswarPraveen/offgit/main/install.sh | bash
```

---

### Automated Setup Tasks

The one-line installer handles all setup automatically:

1. Resolves system dependencies (`git`, `gh`, `python3`).
2. Validates GitHub authentication (`gh auth login --web` if unauthenticated).
3. Installs runtime libraries (`pyyaml`, `watchdog`).
4. Deploys global AI integration rules (`Antigravity`, `Claude Code`, `Cursor`, `Codex`).
5. Initializes the private `thoughts` decision repository.
6. Registers and starts the background daemon (`Windows Startup VBS`, `macOS LaunchAgent`, or `Linux systemd`).

---

## Diagnostics & Self-Healing

Verify daemon health or resolve environment issues by running:

```bash
python ~/.offgit/sync_engine.py --fix
```

```text
===================================================
      offGIT Self-Healing Diagnostics & Fixes      
===================================================
[OK] GitHub CLI is installed and authenticated.
[OK] Background watcher daemon is running (PID: 15304).

--- Canonical Error Signatures & Fixes (FIXES.md) ---
```

---

## Configuration Reference (`~/.offgit/config.yaml`)

Paths are dynamically expanded relative to the user home directory (`~`):

```yaml
# Core offGIT Configuration
github_user: ""                      # Auto-detected automatically from GitHub CLI if left blank
default_repo_visibility: "private"   # Default visibility for new repositories: "private" or "public"
devlog_interval_seconds: 600         # Cadence for automated batch sweeps (600s = 10 minutes)
llm_tool: "claude"                   # Fallback CLI for headless diff summarization

# Directories dynamically monitored across all platforms
watched_directories:
  - "~/.gemini/antigravity/scratch"
  - "~/Documents/Arduino"
  - "~/Projects"
  - "~/workspace"
  - "~/dev"

# Monitored file extensions
watched_extensions:
  - ".ino"
  - ".gd"
  - ".py"
  - ".ts"
  - ".cpp"
  - ".h"
  - ".js"
  - ".c"
  - ".hpp"
  - ".tscn"
  - ".md"
  - ".json"
```

---

## Repository Structure

```text
<project-root>/
|-- CONTEXT.md                 # Live implementation state snapshot
|-- DEVLOG.md                  # Chronological changelog with tool attribution
|-- CLAUDE.md                  # Context pointer for Claude Code
|-- CODEX.md                   # Context pointer for Codex CLI
|-- .cursorrules               # Context pointer for Cursor
|-- .cursor/rules/context.mdc  # Context pointer for Cursor Composer
|-- .gitignore                 # Exclusion rules for local metadata
`-- .offgit/
    |-- prompt-log.jsonl       # Telemetry and reasoning log
    `-- prompt-count           # Milestone counter
```

---

## Production Hardening & Safety

- **Silent Windows Execution**: Enforces `subprocess.CREATE_NO_WINDOW` (`0x08000000`) across all child subprocesses.
- **Detached Daemon Persistence**: Windows daemon is spawned via detached WMI (`Win32_Process.Create`) to prevent termination on shell exit.
- **Subprocess Security**: Commands execute using strict argument lists (`shell=False`) with timeout bounds (15s on LLM calls, 30s on Git operations).
- **Rebase Conflict Protection**: Auto-runs `git pull --rebase --autostash` before pushing. Reverts cleanly via `git rebase --abort` if a merge conflict occurs.
- **Private by Default**: All scaffolded repositories and the `thoughts` repository default strictly to private visibility.
- **Non-Destructive Pointer Injection**: Integrations in `CLAUDE.md`, `.cursorrules`, and `thoughts/README.md` use comment markers (`<!-- OFFGIT_DECISIONS_START -->`) to preserve user hand-written notes.
- **Dynamic Path Expansion**: Resolves all user paths relative to home directory (`~`) with zero hardcoded usernames or machine-specific directories.

---

## Credits & Attribution

Created with and maintained with:
- Flash 3.7
- Opus 4.6
- Sonnet 5
- Antigravity

---

## License

GNU General Public License v3.0 (GPL-3.0)