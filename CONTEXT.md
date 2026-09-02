# Live Project Context: offgit

**Last Synced:** 2026-09-02 11:33:20

## Current Focus & Active State

- Directive: Implement 4 production hardening fixes: LLM fallback chain, per-repo lockfile, thought filename collision guard, and multi-instance watcher prevention
- Rationale: Hardening sync_engine.py and watcher.py against concurrent race conditions, silent LLM degradation, filename collisions, and duplicate daemon instances

## Recent Context Stream

- **[antigravity]** (2026-08-31 11:04:06): Eliminate hardcoded paths and user references: implement dynamic home-directory resolution (~), automatic gh username detection, and harness directory discovery
  *Rationale:* Refactoring config.yaml, sync_engine.py, and watcher.py to dynamically expand user home directories and detect GitHub user credentials without leaking hardcoded folder names
- **[antigravity]** (2026-08-31 11:28:11): Add native support for OpenCode AI terminal assistant: source attribution, OPENCODE.md context pointer, and rule deployment
  *Rationale:* Integrating OpenCode into offGIT: adding OpenCode source attribution, OPENCODE.md rule generation, hook configuration, and documentation
- **[antigravity]** (2026-09-02 05:05:46): Fix gh auth timeout milestone suppression and eliminate synthetic checkpoint spam in thoughts
  *Rationale:* Resolved GitHub CLI timeout in prompt_counter with sub-100ms local token check and purged 191 duplicate synthetic spam files from thoughts
- **[antigravity]** (2026-09-02 05:06:34): Enforce permanent anti-spam and high-signal quality standard for private thoughts repository
  *Rationale:* Locking down strict quality gates in FIXES.md and sync_engine to guarantee thoughts repository remains clean, curated, and free of synthetic checkpoints or conversational chatter
- **[antigravity]** (2026-09-02 05:44:21): Implement 4 production hardening fixes: LLM fallback chain, per-repo lockfile, thought filename collision guard, and multi-instance watcher prevention
  *Rationale:* Hardening sync_engine.py and watcher.py against concurrent race conditions, silent LLM degradation, filename collisions, and duplicate daemon instances

## Open Decisions & Next Steps

- Continue active implementation according to current focus.
- Refer to DEVLOG.md for historical architecture decisions.
