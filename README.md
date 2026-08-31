# offGIT

> **offGIT is an ambient agentic development harness that observes changes across your development environment, automatically extracting technical reasoning into private thoughts while version-controlling clean, professional code repositories.**

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

### 1. Dual-Channel Ambient Routing
- **Channel A (Private Thoughts Repository)**: Evaluates conversation streams and AI architectural rationale, formatting them into standardized Architecture Decision Records (`YYYY-MM-DD_<project>_<slug>.md`) indexed in your private **`thoughts`** GitHub repository.
- **Channel B (Project Code Repositories)**: Evaluates file changes and code diffs on a 10-minute cadence, generating factual, zero-emoji **`DEVLOG.md`** entries, live **`CONTEXT.md`** snapshots, and rebase-safe Git commits pushed upstream.

### 2. Cross-Tool Context Continuity (`CONTEXT.md`)
- Maintains an up-to-date snapshot of active implementation focus, directives, and technical reasoning directly in the repository root.
- Standardized configuration pointers (`CLAUDE.md`, `CODEX.md`, `.cursorrules`, `.cursor/rules/context.mdc`) ensure that secondary IDEs and AI tools ingest project context immediately upon session initialization, eliminating context loss during tool switching.

### 3. Non-AI Editor Autonomy (Arduino IDE, Thonny, Godot)
For environments that lack native AI extension APIs, offGIT provides automated Git operations completely out-of-the-box:
1. **Filesystem Change Detection**: `watcher.py` monitors file save events across `.ino`, `.py`, `.gd`, `.tscn`, `.c`, and `.cpp` files.
2. **Git Diff Extraction**: At the 10-minute batch mark, the engine extracts the real code modifications using `git diff HEAD`.
3. **Headless LLM Inspection**: The raw diff is sent to the configured LLM CLI (Claude / Antigravity / Cursor / Codex) to inspect the technical changes and produce a structured summary of what was implemented.
4. **Automated Commit & Remote Upload**: The LLM-generated changelog is appended to `DEVLOG.md` under `Manual edit (Arduino IDE / Thonny / Godot)`, `CONTEXT.md` is updated, and all code changes are committed and pushed to GitHub.

### 4. Automated Milestone Inception (In-Chat)
- Analyzes interaction volume at defined conversational intervals (5, 15, 30, 60 prompts).
- If the project is not yet a GitHub repository, offGIT prompts the developer in-chat with a suggested kebab-case repository name.
- If the repository is already created on GitHub, all subsequent milestone creation prompts are automatically suppressed.

---

## Installation Guide (Windows, macOS, Linux)

### 🪟 Windows Installation

Choose **any one** of the three methods below:

#### Method 1: One-Line PowerShell Command (Fastest — No Git Clone Required)
Open **PowerShell** and paste:

```powershell
irm https://raw.githubusercontent.com/MaheswarPraveen/offgit/main/install.ps1 | iex
```

---

#### Method 2: Git Clone & Double-Click Setup
If you prefer cloning the repository manually:

1. Open PowerShell or Terminal and clone the repository:
   ```powershell
   git clone https://github.com/MaheswarPraveen/offgit.git
   cd offgit
   ```
2. Double-click **`setup.bat`** (or run `.\setup.bat` in PowerShell).

---

#### Method 3: Download ZIP (No Git or Terminal Required)
1. Click the green **`< > Code`** button at the top of this GitHub page $\rightarrow$ select **`Download ZIP`**.
2. Extract the ZIP file anywhere on your computer.
3. Open the extracted folder and double-click **`setup.bat`**.

---

### 🍎 macOS & 🐧 Linux Installation

Open your terminal and run the one-line installer:

```bash
curl -fsSL https://raw.githubusercontent.com/MaheswarPraveen/offgit/main/install.sh | bash
```

*Or from a local clone:*
```bash
git clone https://github.com/MaheswarPraveen/offgit.git
cd offgit
chmod +x install.sh && ./install.sh
```

---

## What the One-Click Installer Automates

Regardless of your operating system, the installer handles all setup automatically:

1. **Dependency Resolution**: Installs missing prerequisites (`git`, `gh`, `python3`) via `winget` (Windows), `brew` (macOS), `apt` (Ubuntu/Debian), `dnf` (Fedora), or `pacman` (Arch).
2. **Browser OAuth Login**: Checks `gh auth status` and opens your default browser for one-click authorization if needed.
3. **Python Runtime Libraries**: Installs required runtime packages (`pyyaml`, `watchdog`).
4. **Global AI Rule Injection**: Deploys offGIT integration rules to **Antigravity**, **Claude Code** (`~/.claude/settings.json`), **Cursor** (`~/.cursorrules`), and **Codex**.
5. **Private Thoughts Repository**: Creates and initializes your private `thoughts` repository on GitHub.
6. **Silent Autostart Service**: Registers a background startup service (**Windows Startup VBS**, **macOS LaunchAgent**, or **Linux systemd service**) and starts the background daemon.

---

## Post-Install Verification & Self-Healing

To verify that offGIT is active and healthy, or to run automated self-healing diagnostics at any time:

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
[Displays instant 1-shot fixes for common environment edge cases]
```

---

## Configuration Reference (`~/.offgit/config.yaml`)

You can customize offGIT behavior by editing `~/.offgit/config.yaml`:

```yaml
# Core offGIT Configuration
github_user: "MaheswarPraveen"
default_repo_visibility: "private"    # Default visibility for new repos: "private" or "public"
devlog_interval_seconds: 600          # Cadence for automated batch sweeps (600s = 10 minutes)
llm_tool: "claude"                    # Fallback CLI for headless diff summarization ("claude" | "cursor" | "gemini")

# Directories monitored by the filesystem watcher
watched_directories:
  - "C:\\Users\\xczma\\.gemini\\antigravity\\scratch"
  - "C:\\Users\\xczma\\Documents\\Arduino"

# File extensions monitored for diff generation
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

- **Silent Windows Execution (`CREATE_NO_WINDOW`)**: All background subprocesses run with `subprocess.CREATE_NO_WINDOW` (`0x08000000`), completely eliminating flashing black terminal popups on Windows.
- **Detached Daemon Persistence**: Windows daemon is spawned via detached WMI (`Win32_Process.Create`), ensuring it never exits when parent shells close.
- **Safe Subprocess Execution**: All commands and headless LLM calls execute with strict argument lists (`shell=False`) and timeout protection (15s on LLM calls, 30s on git operations), preventing shell-injection vulnerabilities.
- **Divergence Prevention**: Auto-runs `git pull --rebase --autostash` before pushing. If a merge conflict occurs, it executes `git rebase --abort` immediately to restore a clean local state.
- **Private by Default**: New repositories and the private `thoughts` repository scaffold as **private** by default.
- **Non-Destructive Pointer Injection**: AI editor rules (`CLAUDE.md`, `.cursorrules`, `CODEX.md`) and index tables in `thoughts/README.md` are updated non-destructively using HTML comment markers (`<!-- OFFGIT_DECISIONS_START -->`).
- **Cross-Platform OS Architecture**: Native notification adapters and process management across **Windows** (Toast / VBS Startup launcher), **macOS** (osascript / LaunchAgent), and **Linux** (notify-send / systemd).

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