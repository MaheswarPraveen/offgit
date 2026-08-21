# OffGit

An ambient cross-IDE continuity and auto-sync harness for developers.

OffGit sits underneath Claude Code, Cursor, Google Antigravity, Godot Engine, and Arduino IDE. It continuously keeps your GitHub repositories synchronized, generates structured devlogs and live context snapshots, and enables seamless tool-switching (e.g. when quota runs out) without losing conversational or technical momentum.

## Core Capabilities

- **Two-Clock Timing Model**:
  - `CONTEXT.md` (Live State): Local write is instant on every prompt. Remote push is debounced 2 minutes.
  - `DEVLOG.md` (Historical Log): Hard fixed 10-minute interval loop that evaluates real `git diff HEAD`.
- **Cross-Tool Continuity**: Standardized pointer files (`CLAUDE.md`, `.cursorrules`, `.cursor/rules/context.mdc`) ensure any incoming AI editor reads `CONTEXT.md` on startup.
- **LLM-Phrased Repo-Creation Gate**: Milestone tracking (`prompt_threshold: [5, 15, 30, 60]`) generates natural, context-aware confirmation questions before creating remote repositories.
- **Private Thoughts Corpus**: Automatically extracts genuine architectural decisions and syncs them into your private `thoughts` repository.
- **Source Attribution**: Tags every sync event (e.g. `AI-assisted (Claude Code)`, `AI-assisted (Cursor)`, `Manual edit`).

## Quick Start

### Installation

```powershell
python install_and_launch.py
```

This verifies prerequisites (`git`, `gh`, `node`, `claude`), installs Python dependencies (`pyyaml`, `watchdog`), verifies GitHub CLI authentication, registers Windows Task Scheduler for logon autostart, and starts the background watcher.

## File Structure

```text
~/.offgit/
├── sync_engine.py          # Core engine (diffs, summaries, devlogs, context snapshots, commits)
├── prompt_counter.py       # Prompt logging, instant local CONTEXT.md updates, LLM-phrased popups
├── debounce_trigger.py     # Debounce wrapper for Cursor, Claude Code, and Antigravity hooks
├── watcher.py              # Watchdog observer + fixed 10-min devlog interval loop for Arduino/Godot
├── config.yaml             # Single-point tuning (timeouts, diff limits, tool choice, thresholds)
├── install_and_launch.py   # One-click installer with winget checks and Task Scheduler autostart
├── requirements.txt        # pyyaml, watchdog
├── logs/
│   └── engine.log          # System logs
└── thoughts/               # Local clone of the private thoughts decision corpus repo
```

## License

MIT License
