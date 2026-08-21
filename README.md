# offGIT

**The ambient developer continuity harness that keeps your code, devlogs, and context synced across AI editors without friction.**

---

## What is offGIT?

**offGIT** is a lightweight background daemon that runs silently on your machine, connecting **Google Antigravity, Cursor, Claude Code, Godot Engine, and Arduino IDE** into a unified, auto-syncing development environment.

It ensures you never lose technical context when switching tools, eliminates manual git overhead, and autonomously documents your codebase in real-time.

```
                         +-------------------------------+
                         |         CORE ENGINE           |
                         |        sync_engine.py         |
                         |                               |
                         |  get_diff(repo_path)          |
                         |  summarize_with_llm(diff)     |
                         |  phrase_repo_question(ctx)    |
                         |  write_devlog(repo, summary)  |
                         |  update_context_md(repo)      |
                         |  commit_and_push(repo)        |
                         |  maybe_scaffold_repo(repo)    |
                         |  classify_thought(diff, ctx)  |
                         +---------------+---------------+
                                         ^
                                         | Calls engine
        +----------------+---------------+---------------+----------------+
        |                |                               |                |
 +------+------+  +------+------+                 +------+------+  +------+------+
 | Claude Code |  |   Cursor    |                 | Antigravity |  | Idle Watcher|
 | hooks:      |  | hooks:      |                 | hooks:      |  | (watchdog)  |
 | PromptSubmit|  | afterEdit + |                 | PostToolUse |  | Arduino IDE |
 | Stop        |  | debounce    |                 | PromptSubmit|  | Godot Engine|
 +-------------+  +-------------+                 +-------------+  +-------------+
```

---

## The Problems offGIT Solves

### 1. The "Tool-Hopping" Context Loss
* **The Problem:** You are coding in Cursor and exhaust your monthly quota. You open Claude Code or Antigravity to continue, but the new tool has no idea what you just built, forcing you to spend 10 minutes re-explaining the architecture and recent changes.
* **How offGIT Solves It:** offGIT continuously maintains a live **`CONTEXT.md`** file in your repo root. Standard instruction pointers (`CLAUDE.md`, `.cursorrules`, `.cursor/rules/context.mdc`) ensure any incoming tool reads this snapshot on session startup and immediately resumes work with full context.

### 2. The "Uncommitted Code" Black Hole
* **The Problem:** In standalone editors like Godot Engine or Arduino IDE, hours of work sit uncommitted on local disk. If your machine sleeps or you switch tasks, your progress and rationale are undocumented.
* **How offGIT Solves It:** A background filesystem observer tracks file modifications across `.gd`, `.ino`, `.py`, `.cpp`, `.ts`, and `.h`. On a fixed 10-minute interval, it analyzes the real `git diff HEAD`, generates a structured entry in **`DEVLOG.md`**, and pushes commits automatically.

### 3. Friction in Starting New Projects
* **The Problem:** When you start exploring a new idea, opening a browser, creating a GitHub repository, choosing `.gitignore` templates, and configuring remotes interrupts your creative momentum.
* **How offGIT Solves It:** offGIT tracks conversational momentum (at prompt milestones: 5, 15, 30, 60). At 5 prompts, it drafts a context-aware question based on what you discussed and offers to scaffold and publish the GitHub repo in one click.

---

## Core Architecture & Mechanisms

### 1. The Two-Clock Timing Model

| File | Update Frequency | Purpose |
| :--- | :--- | :--- |
| **`CONTEXT.md`** | **Instant local write on every prompt**; remote push debounced 2 minutes. | Live current-state snapshot (active focus, recent directives, open decisions) used for instant cross-tool handoffs. |
| **`DEVLOG.md`** | **Fixed 10-minute interval loop** (evaluated by `watcher.py`). | Append-only historical changelog and architectural rationale tagged with source attribution. |

### 2. Source Attribution
Every entry in `DEVLOG.md` is tagged with the exact tool that produced the change:
- `AI-assisted (Claude Code)`
- `AI-assisted (Cursor)`
- `AI-assisted (Antigravity)`
- `Manual edit` (for Godot / Arduino IDE edits)

### 3. Private Thoughts Decision Corpus
When genuine architectural decisions or trade-offs are discussed, offGIT automatically records them as dated Markdown documents in a private `thoughts` repository (`~/.offgit/thoughts/`). This creates a persistent corpus of your technical decision history.

---

## Repository File Layout

When working in an offGIT-enabled workspace, the following structure is maintained:

```text
<project-root>/
├── CONTEXT.md                 # Overwritten live snapshot of active state and next steps
├── DEVLOG.md                  # Append-only chronological devlog with AI rationale
├── CLAUDE.md                  # "See CONTEXT.md for current project state."
├── .cursorrules               # "See CONTEXT.md for current project state."
├── .cursor/rules/context.mdc  # Cursor rule pointer
├── .gitignore                 # Automatically ignores .offgit/ internal logs
└── .offgit/
    ├── prompt-log.jsonl       # Raw prompt & AI thinking log (local-only, gitignored)
    └── prompt-count           # Milestone counter (5, 15, 30, 60)
```

---

## Installation & Setup

### 1. One-Click Setup
Run the automated installer from the repository root:

```powershell
python install_and_launch.py
```

This will:
1. Verify system prerequisites (`git`, `gh`, `node`, `claude`).
2. Install required Python packages (`pyyaml`, `watchdog`).
3. Verify GitHub CLI authentication (`gh auth status`).
4. Register the Windows Task Scheduler task (`offGIT`) for background auto-start on logon.
5. Launch the background filesystem watcher.

### 2. Configuration (`~/.offgit/config.yaml`)

```yaml
llm_tool: claude                       # "claude" or "cursor-agent" for headless summaries
devlog_interval_seconds: 600           # 10 min hard interval for DEVLOG.md sync
context_push_debounce_seconds: 120     # 2 min debounce for CONTEXT.md push
diff_char_limit: 8000                  # Maximum diff size sent to summarizer
watched_extensions:                    # Watched file extensions
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
prompt_threshold:                      # Prompt counts that trigger repo creation check
  - 5
  - 15
  - 30
  - 60
thoughts_repo_path: ~/.offgit/thoughts # Local clone of private thoughts repo
notifications: windows_toast           # Desktop notification provider
```

---

## Attribution & Credits

Created and maintained by:
- **Flash 3.7**
- **Opus 4.6**
- **Sonnet 5**
- **Antigravity**

---

## License

MIT License
