# Live Project Context: offgit

**Last Synced:** 2026-08-31 16:45:28

## Current Focus & Active State

- Directive: Eliminate hardcoded paths and user references: implement dynamic home-directory resolution (~), automatic gh username detection, and harness directory discovery
- Rationale: Refactoring config.yaml, sync_engine.py, and watcher.py to dynamically expand user home directories and detect GitHub user credentials without leaking hardcoded folder names
- Applied workspace modifications (+0/-0 lines).

## Recent Context Stream

- **[antigravity]** (2026-08-31 10:50:04): Create unified one-click install.sh for macOS and Linux with automated dependency resolution, LaunchAgent, and systemd service registration
  *Rationale:* Building cross-platform install.sh for macOS and Linux supporting brew, apt, pacman, dnf, browser OAuth, global rule deployment, launchd, and systemd autostart
- **[antigravity]** (2026-08-31 10:54:54): Revamp Windows installation in README.md with 1-line PowerShell web installer, Git clone steps, and Download ZIP guide
  *Rationale:* Adding 1-line irm|iex web installer, explicit git clone walkthrough, and zero-prerequisite ZIP download instructions for Windows
- **[antigravity]** (2026-08-31 10:55:51): Refactor README.md to strict professional engineering standard: zero emojis, crisp single-standard installation commands, and zero fluff
  *Rationale:* Simplifying README.md into high-signal, clean, professional documentation with zero emojis and concise installation commands
- **[antigravity]** (2026-08-31 11:01:22): Verify GitHub sync and repository commit status
  *Rationale:* Checking git status, remote log, and GitHub API to confirm all commits and installer updates are pushed live
- **[antigravity]** (2026-08-31 11:04:06): Eliminate hardcoded paths and user references: implement dynamic home-directory resolution (~), automatic gh username detection, and harness directory discovery
  *Rationale:* Refactoring config.yaml, sync_engine.py, and watcher.py to dynamically expand user home directories and detect GitHub user credentials without leaking hardcoded folder names

## Open Decisions & Next Steps

- Continue active implementation according to current focus.
- Refer to DEVLOG.md for historical architecture decisions.
