import os
import sys
import json
import time
import shutil
import logging
import platform
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

CONFIG_DIR = Path.home() / ".offgit"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
LOG_DIR = CONFIG_DIR / "logs"
LOG_FILE = LOG_DIR / "engine.log"
THOUGHTS_DIR = CONFIG_DIR / "thoughts"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
THOUGHTS_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("offGIT")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

SOURCE_ATTRIBUTIONS = {
    "claude-code": "AI-assisted (Claude Code)",
    "cursor": "AI-assisted (Cursor)",
    "antigravity": "AI-assisted (Antigravity)",
    "codex": "AI-assisted (Codex)",
    "watcher": "Manual edit (Arduino IDE / Thonny / Godot)",
    "cli": "CLI execution"
}

def load_config() -> dict:
    defaults = {
        "llm_tool": "claude",
        "devlog_interval_seconds": 600,
        "context_push_debounce_seconds": 120,
        "diff_char_limit": 8000,
        "default_repo_visibility": "private",
        "watched_extensions": [".ino", ".gd", ".py", ".ts", ".cpp", ".h", ".js", ".c", ".hpp", ".tscn", ".md"],
        "prompt_threshold": [5, 15, 30, 60],
        "thoughts_repo_path": str(THOUGHTS_DIR),
        "github_user": "",
        "notifications": "native",
        "watched_directories": [
            str(Path.home() / ".gemini" / "antigravity" / "scratch"),
            str(Path.home() / "Documents" / "Arduino"),
            str(Path.home() / "Documents" / "Godot")
        ]
    }

    if CONFIG_FILE.exists() and yaml:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_conf = yaml.safe_load(f)
                if user_conf:
                    defaults.update(user_conf)
        except Exception as e:
            logger.error(f"Error loading config.yaml: {e}")

    return defaults

CONFIG = load_config()

def strip_emojis(text: str) -> str:
    if not text:
        return ""
    return text.encode("ascii", "ignore").decode("ascii")

def run_cmd(cmd: list[str] | str, cwd: str | None = None, timeout: int = 30) -> tuple[int, str, str]:
    """Executes a command safely with zero console window popups (CREATE_NO_WINDOW) and strict timeouts."""
    is_list = isinstance(cmd, list)
    no_window_flag = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd,
            shell=not is_list,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=no_window_flag
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except subprocess.TimeoutExpired as te:
        logger.warning(f"Command timed out after {timeout}s: {cmd}")
        return 124, "", f"Timed out after {timeout}s"
    except Exception as e:
        logger.error(f"Command execution failed ({cmd}): {e}")
        return 1, "", str(e)

def check_github_prerequisites() -> tuple[bool, str]:
    """Strict pre-flight gate: verifies GitHub CLI is installed and authenticated."""
    if shutil.which("gh") is None:
        return False, "GitHub CLI ('gh') is not installed. offGIT requires GitHub CLI to operate. Install via: winget install GitHub.cli (or brew install gh / apt install gh)"

    code, out, err = run_cmd(["gh", "auth", "status"], timeout=10)
    if code != 0:
        return False, "GitHub CLI is not authenticated. offGIT requires an authenticated GitHub session. Please run: gh auth login"

    return True, ""

def ensure_gitignore(repo_path: str) -> None:
    gitignore_path = Path(repo_path) / ".gitignore"
    entry = "\n.offgit/\nlogs/\n*.log\n"
    try:
        if gitignore_path.exists():
            content = gitignore_path.read_text(encoding="utf-8")
            if ".offgit" not in content:
                gitignore_path.write_text(content.rstrip() + entry, encoding="utf-8")
        else:
            gitignore_path.write_text(".offgit/\nlogs/\n*.log\n", encoding="utf-8")
    except Exception as e:
        logger.warning(f"Could not update .gitignore in {repo_path}: {e}")

def ensure_tool_pointers(repo_path: str) -> None:
    """Non-destructively ensures AI editors have a pointer to CONTEXT.md without stomping on existing content."""
    pointer_line = "See CONTEXT.md for current project state."
    r_path = Path(repo_path)

    for doc_name in ["CLAUDE.md", "CODEX.md", ".cursorrules"]:
        f_path = r_path / doc_name
        try:
            if f_path.exists():
                c = f_path.read_text(encoding="utf-8")
                if pointer_line not in c:
                    f_path.write_text(f"{c.rstrip()}\n\n# Project Context\n{pointer_line}\n", encoding="utf-8")
            else:
                f_path.write_text(f"{pointer_line}\n", encoding="utf-8")
        except Exception as e:
            logger.debug(f"Could not write {doc_name} in {repo_path}: {e}")

    cursor_rules_dir = r_path / ".cursor" / "rules"
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)
    cursor_mdc = cursor_rules_dir / "context.mdc"
    try:
        if not cursor_mdc.exists():
            cursor_mdc.write_text(f"---\ndescription: Live Project Context\nglobs: *\n---\n{pointer_line}\n", encoding="utf-8")
    except Exception as e:
        logger.debug(f"Could not write Cursor context.mdc in {repo_path}: {e}")

def get_diff(repo_path: str) -> str:
    if not (Path(repo_path) / ".git").exists():
        return ""

    code, _, _ = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_path, timeout=5)
    if code == 0:
        code, diff_out, _ = run_cmd(["git", "diff", "HEAD"], cwd=repo_path, timeout=10)
        if not diff_out:
            code, diff_out, _ = run_cmd(["git", "diff", "--cached"], cwd=repo_path, timeout=10)
        if not diff_out:
            code, status_out, _ = run_cmd(["git", "status", "--porcelain"], cwd=repo_path, timeout=10)
            if status_out:
                diff_out = f"Untracked / Modified files:\n{status_out}"
    else:
        code, status_out, _ = run_cmd(["git", "status", "--porcelain"], cwd=repo_path, timeout=10)
        diff_out = f"Initial files:\n{status_out}" if status_out else ""

    limit = CONFIG.get("diff_char_limit", 8000)
    if len(diff_out) > limit:
        diff_out = diff_out[:limit] + "\n... [diff truncated for length]"

    return strip_emojis(diff_out)

def read_prompt_log(repo_path: str) -> list[dict]:
    log_file = Path(repo_path) / ".offgit" / "prompt-log.jsonl"
    if not log_file.exists():
        return []

    entries = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        logger.warning(f"Error reading prompt log from {log_file}: {e}")

    return entries[-10:]

def append_prompt_log(repo_path: str, tool: str, summary: str, ai_thinking: str = "") -> int:
    off_dir = Path(repo_path) / ".offgit"
    off_dir.mkdir(parents=True, exist_ok=True)
    ensure_gitignore(repo_path)

    log_file = off_dir / "prompt-log.jsonl"
    count_file = off_dir / "prompt-count"

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "summary": strip_emojis(summary),
        "ai_thinking": strip_emojis(ai_thinking)
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    count = 0
    if count_file.exists():
        try:
            count = int(count_file.read_text(encoding="utf-8").strip())
        except ValueError:
            count = 0
    count += 1
    count_file.write_text(str(count), encoding="utf-8")
    return count

def summarize_with_llm(diff: str, prompt_context: list[dict], tool: str) -> str:
    if not diff and not prompt_context:
        return "- Routine maintenance / empty diff."

    cli_cmd = CONFIG.get("llm_tool", "claude")
    prompt = (
        "Generate a factual, concise 3-5 bullet point changelog entry based on this git diff and prompt context.\n"
        "Strict rules: No emojis. Plain factual statements only. Highlight changed files, functions, and architecture decisions.\n\n"
        f"PROMPT CONTEXT:\n{json.dumps(prompt_context, indent=2)}\n\n"
        f"GIT DIFF:\n{diff}\n"
    )

    # Safe list execution (shell=False) with strict 15s timeout
    if cli_cmd in ["claude", "cursor-agent", "codex", "openai"]:
        code, out, err = run_cmd([cli_cmd, "-p", prompt[:4000]], timeout=15)
        if code == 0 and out.strip():
            return strip_emojis(out.strip())
        else:
            logger.debug(f"LLM headless summarizer failed (code {code}): {err}")

    # Fallback diff heuristic
    bullets = []
    lines = diff.split("\n")
    modified_files = set()
    added_lines = 0
    deleted_lines = 0

    for line in lines:
        if line.startswith("+++ b/"):
            modified_files.add(line[6:])
        elif line.startswith("+") and not line.startswith("+++"):
            added_lines += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted_lines += 1

    if prompt_context:
        latest = prompt_context[-1]
        summary = latest.get("summary", "")
        thinking = latest.get("ai_thinking", "")
        if summary:
            bullets.append(f"- Directive: {summary}")
        if thinking:
            bullets.append(f"- Rationale: {thinking}")

    if modified_files:
        files_str = ", ".join(f"`{f}`" for f in sorted(modified_files)[:5])
        bullets.append(f"- Updated {files_str} (+{added_lines}/-{deleted_lines} lines).")
    elif lines:
        bullets.append(f"- Applied workspace modifications (+{added_lines}/-{deleted_lines} lines).")

    return "\n".join(bullets)

def phrase_repo_question(prompt_log: list[dict], project_hint: str, tool: str) -> str:
    fallback = f"Looks like you are actively working on '{project_hint}' - want me to create a GitHub repo for this?"
    if not prompt_log:
        return fallback

    summaries = [p.get("summary", "") for p in prompt_log[-5:] if p.get("summary")]
    cli_cmd = CONFIG.get("llm_tool", "claude")

    prompt = (
        "Based on these developer prompts, generate a natural 1-sentence confirmation question "
        "asking the user if they want a GitHub repository created and scaffolded for this project.\n\n"
        f"PROMPTS:\n{json.dumps(summaries, indent=2)}\n\n"
        "Rules: No emojis. Plain ASCII text only. Output ONLY the question."
    )

    if cli_cmd in ["claude", "cursor-agent", "codex", "openai"]:
        code, out, _ = run_cmd([cli_cmd, "-p", prompt[:2000]], timeout=10)
        if code == 0 and out.strip():
            clean_q = strip_emojis(out.strip()).strip('"').strip("'")
            if "?" in clean_q:
                return clean_q

    last_action = summaries[-1] if summaries else project_hint
    return f"Looks like you are actively working on '{last_action}' - want me to create a GitHub repo for this?"

def suggest_repo_name(prompt_log: list[dict], fallback_name: str, tool: str) -> str:
    if not prompt_log:
        return fallback_name.lower().replace(" ", "-")

    summaries = [p.get("summary", "") for p in prompt_log[-5:] if p.get("summary")]
    cli_cmd = CONFIG.get("llm_tool", "claude")

    prompt = (
        "Based on these developer prompts, suggest a concise 2-4 word kebab-case repository name.\n\n"
        f"PROMPTS:\n{json.dumps(summaries, indent=2)}\n\n"
        "Rules: Output ONLY the lowercase kebab-case name (e.g. 'esp32-sensor-relay'). No quotes, no markdown."
    )

    if cli_cmd in ["claude", "cursor-agent", "codex", "openai"]:
        code, out, _ = run_cmd([cli_cmd, "-p", prompt[:2000]], timeout=10)
        if code == 0 and out.strip():
            candidate = strip_emojis(out.strip()).strip('"').strip("'").lower()
            candidate = "".join(c if (c.isalnum() or c == "-") else "-" for c in candidate).strip("-")
            if candidate and len(candidate) <= 50:
                return candidate

    last_summary = summaries[-1] if summaries else fallback_name
    words = "".join(c if c.isalnum() else " " for c in last_summary.lower()).split()[:3]
    return "-".join(words) or fallback_name

def write_devlog(repo_path: str, summary: str, trigger_source: str) -> None:
    devlog_path = Path(repo_path) / "DEVLOG.md"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    attribution = SOURCE_ATTRIBUTIONS.get(trigger_source, f"Source ({trigger_source})")

    entry = f"\n## {now_str} - {attribution}\n\n{strip_emojis(summary)}\n"

    if devlog_path.exists():
        content = devlog_path.read_text(encoding="utf-8")
        devlog_path.write_text(content.rstrip() + "\n" + entry, encoding="utf-8")
    else:
        repo_name = Path(repo_path).name
        header = f"# Development Log: {repo_name}\n\nAutomated continuity log maintained by offGIT.\n"
        devlog_path.write_text(header + entry, encoding="utf-8")

    logger.info(f"Appended entry to DEVLOG.md in {repo_path} ({attribution})")

def update_context_md(repo_path: str, summary: str) -> None:
    context_path = Path(repo_path) / "CONTEXT.md"
    repo_name = Path(repo_path).name
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prompt_context = read_prompt_log(repo_path)

    md_lines = [
        f"# Live Project Context: {repo_name}",
        f"\n**Last Synced:** {now_str}",
        "\n## Current Focus & Active State\n",
        strip_emojis(summary),
        "\n## Recent Context Stream\n"
    ]

    if prompt_context:
        for p in prompt_context[-5:]:
            ts = p.get("ts", "")[:19].replace("T", " ")
            tool = p.get("tool", "unknown")
            s = strip_emojis(p.get("summary", ""))
            t = strip_emojis(p.get("ai_thinking", ""))
            md_lines.append(f"- **[{tool}]** ({ts}): {s}")
            if t:
                md_lines.append(f"  *Rationale:* {t[:200]}")
    else:
        md_lines.append("- Initial project state established.")

    md_lines.append("\n## Open Decisions & Next Steps\n")
    md_lines.append("- Continue active implementation according to current focus.")
    md_lines.append("- Refer to DEVLOG.md for historical architecture decisions.\n")

    context_path.write_text("\n".join(md_lines), encoding="utf-8")
    logger.info(f"Overwrote live CONTEXT.md in {context_path}")
    ensure_tool_pointers(repo_path)

def commit_and_push(repo_path: str) -> None:
    """Stages, commits, pulls with rebase to prevent remote divergences, and pushes safely."""
    if not (Path(repo_path) / ".git").exists():
        return

    ensure_gitignore(repo_path)
    run_cmd(["git", "add", "-A"], cwd=repo_path, timeout=10)

    code, staged_diff, _ = run_cmd(["git", "diff", "--cached", "--quiet"], cwd=repo_path, timeout=5)
    if code == 0:
        logger.info(f"No changes staged in {repo_path}, nothing to commit.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"docs: offgit sync ({timestamp})"
    code, _, err = run_cmd(["git", "commit", "-m", commit_msg], cwd=repo_path, timeout=10)
    if code != 0:
        logger.error(f"Commit failed in {repo_path}: {err}")
        return

    # Check remote destination
    code_remote, remote_url, _ = run_cmd(["git", "remote", "get-url", "origin"], cwd=repo_path, timeout=5)
    if code_remote != 0 or not remote_url:
        logger.info(f"Local commit created. No remote configured for {repo_path}.")
        return

    # Pull with rebase first to prevent push rejection if upstream moved
    pull_code, _, pull_err = run_cmd(["git", "pull", "--rebase", "--autostash", "origin", "main"], cwd=repo_path, timeout=20)
    if pull_code != 0:
        logger.warning(f"git pull --rebase encountered a conflict in {repo_path}: {pull_err}")
        run_cmd(["git", "rebase", "--abort"], cwd=repo_path, timeout=10)
        logger.info(f"Aborted rebase in {repo_path} to restore clean local state. Skipping push for this cycle.")
        return

    # Push to remote
    code_push, _, push_err = run_cmd(["git", "push", "origin", "main"], cwd=repo_path, timeout=30)
    if code_push == 0:
        logger.info(f"Pushed commit to remote in {repo_path}")
        notify(f"offGIT Synced: {Path(repo_path).name}", f"Pushed updates to GitHub at {timestamp}")
    else:
        logger.error(f"Git push failed in {repo_path}: {push_err}")

def should_trigger_repo_check(count: int) -> bool:
    milestones = CONFIG.get("prompt_threshold", [5, 15, 30, 60])
    if isinstance(milestones, list):
        return count in milestones
    if isinstance(milestones, int):
        return count == milestones
    return count in [5, 15, 30, 60]

def scaffold_repo_direct(repo_path: str, repo_name: str, visibility: str = "") -> bool:
    """Scaffolds and publishes a repository directly with configurable visibility (private/public)."""
    ready, msg = check_github_prerequisites()
    if not ready:
        logger.error(f"offGIT repository creation blocked: {msg}")
        print(f"[offGIT BLOCKED] {msg}")
        return False

    p_path = Path(repo_path)
    p_path.mkdir(parents=True, exist_ok=True)
    clean_name = "".join(c if (c.isalnum() or c in "-_.") else "-" for c in repo_name.lower()).strip("-")

    if not clean_name:
        clean_name = p_path.name

    # Check configured visibility default
    vis_flag = visibility or CONFIG.get("default_repo_visibility", "private")
    if vis_flag not in ["public", "private"]:
        vis_flag = "private"

    logger.info(f"Provisioning repository '{clean_name}' with visibility '{vis_flag}'")

    readme = p_path / "README.md"
    if not readme.exists():
        readme_content = f"""# {clean_name}

**Production-grade technical implementation and project repository.**

---

## Overview

This repository contains the codebase and architectural specifications for **{clean_name}**.

- **Live Project State**: Consult [`CONTEXT.md`](./CONTEXT.md) for current focus and open technical decisions.
- **Changelog & Rationale**: Review [`DEVLOG.md`](./DEVLOG.md) for chronological development updates and technical trade-offs.
- **Architecture**: See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for system design and component specifications.

---

## Getting Started

Refer to project configuration and dependency files to initialize the local build environment.

---

*Continuous context and repository synchronization maintained by offGIT.*

---

## Credits & Attribution

Created with and maintained with:
- **Flash 3.7**
- **Opus 4.6**
- **Sonnet 5**
- **Antigravity**
"""
        readme.write_text(readme_content, encoding="utf-8")

    arch = p_path / "ARCHITECTURE.md"
    if not arch.exists():
        arch_content = f"""# System Architecture: {clean_name}

## 1. Architectural Overview

This document outlines the core system design, component boundaries, and implementation patterns for **{clean_name}**.

---

## 2. Key Components

- **Core Module**: Primary application logic and state management.
- **Interfaces & Adapters**: Ingestion, input handling, and external protocol bridges.
- **Configuration & Storage**: Persistent parameters, configuration schemas, and data structures.

---

## 3. Decision Log

Historical architectural decisions and technical trade-offs are documented continuously in [`DEVLOG.md`](./DEVLOG.md).
"""
        arch.write_text(arch_content, encoding="utf-8")

    context_file = p_path / "CONTEXT.md"
    if not context_file.exists():
        update_context_md(repo_path, f"- Initial project repository initialized for {clean_name}.")

    ensure_gitignore(repo_path)
    ensure_tool_pointers(repo_path)

    if not (p_path / ".git").exists():
        run_cmd(["git", "init"], cwd=repo_path, timeout=5)
        run_cmd(["git", "branch", "-M", "main"], cwd=repo_path, timeout=5)

    run_cmd(["git", "add", "-A"], cwd=repo_path, timeout=10)
    run_cmd(["git", "commit", "-m", "feat: initial project scaffolding and architecture setup"], cwd=repo_path, timeout=10)

    gh_user = CONFIG.get("github_user", "")
    target = f"{gh_user}/{clean_name}" if gh_user else clean_name
    create_cmd = ["gh", "repo", "create", target, f"--{vis_flag}", "--source", ".", "--remote", "origin", "--push"]
    
    code, out, err = run_cmd(create_cmd, cwd=repo_path, timeout=30)
    if code == 0:
        logger.info(f"Successfully created and pushed remote repo {target} ({vis_flag})")
        notify("Repository Created", f"Created and published {target} on GitHub ({vis_flag})")
        return True
    else:
        logger.warning(f"gh repo create encountered an issue ({err}), attempting fallback git remote setup...")
        run_cmd(["git", "remote", "add", "origin", f"https://github.com/{target}.git"], cwd=repo_path, timeout=5)
        code_p, _, err_p = run_cmd(["git", "push", "-u", "origin", "main"], cwd=repo_path, timeout=30)
        if code_p == 0:
            return True
        logger.error(f"Failed to publish remote repository {target}: {err_p}")
        return False

def clean_prompt_summary(text: str) -> str:
    """Strips XML tags, metadata blocks, and cleans text into a concise topic summary."""
    if not text:
        return ""
    import re
    # Remove XML-like tags
    cleaned = re.sub(r"<[^>]+>", " ", text)
    # Remove metadata lines
    cleaned = re.sub(r"The current local time is:[^\n]+", " ", cleaned)
    cleaned = re.sub(r"\[SYSTEM_MESSAGE\][^\n]*", " ", cleaned)
    # Clean whitespace
    cleaned = " ".join(cleaned.split()).strip()
    return cleaned

def classify_thought(diff: str, prompt_context: list[dict], tool: str, repo_path: str = "") -> None:
    """Extracts un-synced thoughts with clean YYYY-MM-DD_<project>_<slug> naming and structured index table."""
    if not prompt_context:
        return

    try:
        thoughts_repo = Path(CONFIG.get("thoughts_repo_path", THOUGHTS_DIR))
        if not (thoughts_repo / ".git").exists():
            run_cmd(["git", "init"], cwd=str(thoughts_repo), timeout=5)
            run_cmd(["git", "branch", "-M", "main"], cwd=str(thoughts_repo), timeout=5)

        ts_file = None
        last_sync_ts = ""
        if repo_path:
            ts_file = Path(repo_path) / ".offgit" / "last-thought-sync.ts"
            if ts_file.exists():
                try:
                    last_sync_ts = ts_file.read_text(encoding="utf-8").strip()
                except Exception:
                    last_sync_ts = ""

        new_thoughts_count = 0
        latest_processed_ts = last_sync_ts
        proj_name = Path(repo_path).name if repo_path else "general"
        proj_slug = "".join(c if c.isalnum() else "-" for c in proj_name.lower()).strip("-")

        for entry in prompt_context:
            entry_ts = entry.get("ts", "")
            if last_sync_ts and entry_ts <= last_sync_ts:
                continue

            raw_summary = entry.get("summary", "").strip()
            summary = clean_prompt_summary(raw_summary)
            thinking = entry.get("ai_thinking", "").strip()
            entry_tool = entry.get("tool", tool)

            if not summary or len(summary) < 8 or summary.lower() in ["hi", "hello", "hey", "cool", "yes", "no", "ok", "okay"]:
                continue

            # Generate memorable 3-5 word slug
            words = "".join(c if c.isalnum() else " " for c in summary.lower()).split()[:5]
            topic_slug = "-".join(words) or "technical-decision"

            date_str = datetime.now().strftime("%Y-%m-%d")
            time_str = datetime.now().strftime("%H:%M")
            filename = f"{date_str}_{proj_slug}_{topic_slug}.md"
            file_path = thoughts_repo / filename

            title_text = summary[:70] + ("..." if len(summary) > 70 else "")

            content = f"# Architecture Decision: {title_text}\n\n"
            content += f"- **Date**: `{date_str} {time_str}`\n"
            content += f"- **Project**: `{proj_name}`\n"
            content += f"- **Tool**: `{entry_tool}`\n\n"
            content += "---\n\n"
            content += f"## Problem & Directive\n\n{summary}\n\n"
            if thinking:
                content += f"## AI Architectural Reasoning\n\n{thinking}\n\n"
            if diff:
                content += f"## Accompanying Code Diff\n\n```diff\n{diff[:2000]}\n```\n"

            file_path.write_text(strip_emojis(content), encoding="utf-8")
            new_thoughts_count += 1
            if entry_ts > latest_processed_ts:
                latest_processed_ts = entry_ts

        if new_thoughts_count > 0:
            # Build structured chronological table
            readme_path = thoughts_repo / "README.md"
            all_mds = sorted(thoughts_repo.glob("*.md"), reverse=True)
            table_rows = []

            for md in all_mds:
                if md.name == "README.md":
                    continue
                # Parse filename format: YYYY-MM-DD_project_topic.md or legacy format
                parts = md.stem.split("_")
                if len(parts) >= 3:
                    d_str = parts[0]
                    p_str = parts[1]
                    t_str = " ".join(parts[2:]).replace("-", " ").capitalize()
                else:
                    d_str = md.stem[:10] if len(md.stem) >= 10 else "—"
                    p_str = proj_slug
                    t_str = md.stem[11:].replace("-", " ").capitalize() if len(md.stem) > 11 else md.stem

                table_rows.append(f"| `{d_str}` | `{p_str}` | **{t_str}** | [`View Note`](./{md.name}) |")

            table_content = "| Date | Project | Topic / Decision | Note Link |\n| :--- | :--- | :--- | :--- |\n" + "\n".join(table_rows)
            start_marker = "<!-- OFFGIT_DECISIONS_START -->"
            end_marker = "<!-- OFFGIT_DECISIONS_END -->"

            header_text = "# Private Technical Thoughts & Architecture Corpus\n\nChronological decision log and architectural reasoning maintained automatically by **offGIT**.\n\n---\n\n## Decision Index\n\n"
            new_readme = f"{header_text}{start_marker}\n{table_content}\n{end_marker}\n"
            readme_path.write_text(new_readme, encoding="utf-8")

            # Stage, commit, and push thoughts
            run_cmd(["git", "add", "-A"], cwd=str(thoughts_repo), timeout=10)
            commit_msg = f"docs(thoughts): record {new_thoughts_count} decisions ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
            run_cmd(["git", "commit", "-m", commit_msg], cwd=str(thoughts_repo), timeout=10)

            code_r, remote_out, _ = run_cmd(["git", "remote", "get-url", "origin"], cwd=str(thoughts_repo), timeout=5)
            if code_r == 0 and remote_out.strip():
                pull_code, _, _ = run_cmd(["git", "pull", "--rebase", "--autostash", "origin", "main"], cwd=str(thoughts_repo), timeout=20)
                if pull_code != 0:
                    run_cmd(["git", "rebase", "--abort"], cwd=str(thoughts_repo), timeout=10)
                    return
                run_cmd(["git", "push", "origin", "main"], cwd=str(thoughts_repo), timeout=30)
                logger.info(f"Auto-synced {new_thoughts_count} thoughts to private thoughts repo with structured table.")

            if ts_file and latest_processed_ts:
                ts_file.write_text(latest_processed_ts, encoding="utf-8")

    except Exception as e:
        logger.error(f"Error in classify_thought: {e}", exc_info=True)

def notify(title: str, message: str) -> None:
    """Cross-platform notification provider supporting Windows, macOS, and Linux without console popups."""
    clean_title = strip_emojis(title).replace("'", "''").replace('"', '\"')
    clean_msg = strip_emojis(message).replace("'", "''").replace('"', '\"')
    current_os = platform.system()
    no_window_flag = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    try:
        if current_os == "Windows":
            ps_cmd = (
                f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; "
                f"$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
                f"$textNodes = $template.GetElementsByTagName('text'); "
                f"$textNodes.Item(0).AppendChild($template.CreateTextNode('{clean_title}')) > $null; "
                f"$textNodes.Item(1).AppendChild($template.CreateTextNode('{clean_msg}')) > $null; "
                f"$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
                f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('offGIT').Show($toast);"
            )
            subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=no_window_flag)
        elif current_os == "Darwin":
            osa_cmd = f'display notification "{clean_msg}" with title "{clean_title}"'
            subprocess.Popen(["osascript", "-e", osa_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif current_os == "Linux":
            if shutil.which("notify-send"):
                subprocess.Popen(["notify-send", clean_title, clean_msg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logger.debug(f"Notification error: {e}")

def run_sync(repo_path: str, trigger_source: str) -> None:
    ready, msg = check_github_prerequisites()
    if not ready:
        logger.warning(f"offGIT sync blocked: {msg}")
        print(f"[offGIT BLOCKED] {msg}")
        return

    if not repo_path or not os.path.exists(repo_path):
        logger.warning(f"Invalid repo_path passed to run_sync: {repo_path}")
        return

    logger.info(f"Running offGIT sync on {repo_path} (trigger: {trigger_source})")

    diff = get_diff(repo_path)
    prompt_context = read_prompt_log(repo_path)

    if not diff and not prompt_context:
        logger.info(f"No diff and no prompt context in {repo_path}, skipping sync.")
        return

    summary = summarize_with_llm(diff, prompt_context, trigger_source)

    write_devlog(repo_path, summary, trigger_source)
    update_context_md(repo_path, summary)
    commit_and_push(repo_path)
    classify_thought(diff, prompt_context, trigger_source, repo_path)

def run_self_healing_diagnostics(repo_path: str | None = None) -> None:
    """Performs automated self-healing diagnostics and prints known error patterns from FIXES.md."""
    print("===================================================")
    print("      offGIT Self-Healing Diagnostics & Fixes      ")
    print("===================================================")

    # 1. Check prerequisites
    ready, msg = check_github_prerequisites()
    if ready:
        print("[OK] GitHub CLI is installed and authenticated.")
    else:
        print(f"[FAIL] {msg}")

    # 2. Check background daemon status
    res_ps = run_cmd(["powershell", "-NoProfile", "-Command", "Get-Process -Name pythonw -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"])
    if res_ps[0] == 0 and res_ps[1].strip():
        print(f"[OK] Background watcher daemon is running (PID: {res_ps[1].strip()}).")
    else:
        print("[WARNING] Background watcher daemon is not running. Attempting auto-restart...")
        vbs_path = Path.home() / ".offgit" / "start_offgit.vbs"
        if vbs_path.exists():
            run_cmd(["wscript.exe", str(vbs_path)])
            print("[OK] Restarted background watcher daemon.")

    # 3. Print FIXES.md summary
    fixes_file = Path.home() / ".offgit" / "FIXES.md"
    if fixes_file.exists():
        print("\n--- Canonical Error Signatures & Fixes (FIXES.md) ---")
        print(fixes_file.read_text(encoding="utf-8"))

def main():
    parser = argparse.ArgumentParser(description="offGIT Core Engine")
    parser.add_argument("--repo", type=str, help="Path to project repository")
    parser.add_argument("--trigger", type=str, default="cli", help="Trigger source identifier")
    parser.add_argument("--log-prompt", action="store_true", help="Append an entry to prompt-log.jsonl")
    parser.add_argument("--scaffold", action="store_true", help="Scaffold and create GitHub repository")
    parser.add_argument("--fix", action="store_true", help="Run self-healing diagnostics and display FIXES.md error reference")
    parser.add_argument("--diagnose", action="store_true", help="Alias for --fix")
    parser.add_argument("--name", type=str, default="", help="Repository name for scaffolding")
    parser.add_argument("--visibility", type=str, default="", help="Repository visibility: private or public")
    parser.add_argument("--tool", type=str, default="cli", help="Tool name for prompt logging")
    parser.add_argument("--summary", type=str, default="", help="Prompt summary text")
    parser.add_argument("--thinking", type=str, default="", help="AI thinking / architecture explanation")

    args = parser.parse_args()

    if args.fix or args.diagnose:
        run_self_healing_diagnostics(args.repo)
        return

    if args.scaffold and args.repo:
        name = args.name or Path(args.repo).name
        vis = args.visibility or CONFIG.get("default_repo_visibility", "private")
        success = scaffold_repo_direct(args.repo, name, vis)
        if success:
            print(f"[offGIT] Successfully created and pushed repository '{name}' ({vis}) to GitHub.")
        else:
            print(f"[offGIT] Failed to create repository '{name}'.")
    elif args.log_prompt and args.repo:
        count = append_prompt_log(args.repo, args.tool, args.summary, args.thinking)
        update_context_md(args.repo, f"- Active prompt: {args.summary}")
        print(f"Logged prompt to offGIT. Current count: {count}")
    elif args.repo:
        run_sync(args.repo, args.trigger)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()