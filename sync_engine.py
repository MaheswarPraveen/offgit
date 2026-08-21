import os
import sys
import json
import time
import shutil
import logging
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

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("offGIT")

SOURCE_ATTRIBUTIONS = {
    "claude-code": "AI-assisted (Claude Code)",
    "cursor": "AI-assisted (Cursor)",
    "antigravity": "AI-assisted (Antigravity)",
    "watcher": "Manual edit",
    "cli": "CLI execution"
}

def load_config() -> dict:
    defaults = {
        "llm_tool": "claude",
        "devlog_interval_seconds": 600,
        "context_push_debounce_seconds": 120,
        "diff_char_limit": 8000,
        "watched_extensions": [".ino", ".gd", ".py", ".ts", ".cpp", ".h", ".js", ".c", ".hpp", ".tscn", ".md"],
        "prompt_threshold": [5, 15, 30, 60],
        "thoughts_repo_path": str(THOUGHTS_DIR),
        "github_user": "MaheswarPraveen",
        "notifications": "windows_toast",
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

def run_cmd(cmd: list[str] | str, cwd: str | None = None) -> tuple[int, str, str]:
    shell = not isinstance(cmd, list)
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd,
            shell=shell,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        logger.error(f"Command failed ({cmd}): {e}")
        return 1, "", str(e)

def ensure_gitignore(repo_path: str) -> None:
    gitignore_path = Path(repo_path) / ".gitignore"
    entry = "\n.offgit/\n"
    try:
        if gitignore_path.exists():
            content = gitignore_path.read_text(encoding="utf-8")
            if ".offgit" not in content:
                gitignore_path.write_text(content.rstrip() + entry, encoding="utf-8")
        else:
            gitignore_path.write_text(".offgit/\n", encoding="utf-8")
    except Exception as e:
        logger.warning(f"Could not update .gitignore in {repo_path}: {e}")

def ensure_tool_pointers(repo_path: str) -> None:
    pointer_line = "See CONTEXT.md for current project state."
    r_path = Path(repo_path)

    claude_md = r_path / "CLAUDE.md"
    try:
        if claude_md.exists():
            c = claude_md.read_text(encoding="utf-8")
            if pointer_line not in c:
                claude_md.write_text(f"{pointer_line}\n\n{c}", encoding="utf-8")
        else:
            claude_md.write_text(f"{pointer_line}\n", encoding="utf-8")
    except Exception as e:
        logger.debug(f"Could not write CLAUDE.md in {repo_path}: {e}")

    cursor_rules_dir = r_path / ".cursor" / "rules"
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)
    cursor_mdc = cursor_rules_dir / "context.mdc"
    try:
        if not cursor_mdc.exists():
            cursor_mdc.write_text(f"---\ndescription: Live Project Context\nglobs: *\n---\n{pointer_line}\n", encoding="utf-8")
    except Exception as e:
        logger.debug(f"Could not write Cursor context.mdc in {repo_path}: {e}")

    cursorrules_file = r_path / ".cursorrules"
    try:
        if not cursorrules_file.exists():
            cursorrules_file.write_text(f"{pointer_line}\n", encoding="utf-8")
    except Exception as e:
        logger.debug(f"Could not write .cursorrules in {repo_path}: {e}")

def get_diff(repo_path: str) -> str:
    if not (Path(repo_path) / ".git").exists():
        return ""

    code, _, _ = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_path)
    if code == 0:
        code, diff_out, _ = run_cmd(["git", "diff", "HEAD"], cwd=repo_path)
        if not diff_out:
            code, diff_out, _ = run_cmd(["git", "diff", "--cached"], cwd=repo_path)
        if not diff_out:
            code, status_out, _ = run_cmd(["git", "status", "--porcelain"], cwd=repo_path)
            if status_out:
                diff_out = f"Untracked / Modified files:\n{status_out}"
    else:
        code, status_out, _ = run_cmd(["git", "status", "--porcelain"], cwd=repo_path)
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

    if cli_cmd in ["claude", "cursor-agent"]:
        code, out, _ = run_cmd(f'{cli_cmd} -p "{prompt[:4000].replace(chr(34), chr(39))}"')
        if code == 0 and out.strip():
            return strip_emojis(out.strip())

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
        "Based on these 5 developer prompts, generate a natural 1-sentence confirmation question "
        "asking the user if they want a GitHub repository created and scaffolded for this project.\n\n"
        f"PROMPTS:\n{json.dumps(summaries, indent=2)}\n\n"
        "Rules: No emojis. Plain ASCII text only. Output ONLY the question."
    )

    if cli_cmd in ["claude", "cursor-agent"]:
        code, out, _ = run_cmd(f'{cli_cmd} -p "{prompt[:2000].replace(chr(34), chr(39))}"')
        if code == 0 and out.strip():
            clean_q = strip_emojis(out.strip()).strip('"').strip("'")
            if "?" in clean_q:
                return clean_q

    last_action = summaries[-1] if summaries else project_hint
    return f"Looks like you are actively working on '{last_action}' - want me to create a GitHub repo for this?"

def suggest_repo_name(prompt_log: list[dict], fallback_name: str, tool: str) -> str:
    """Suggests a clean, kebab-case repository name based on recent prompts."""
    if not prompt_log:
        return fallback_name.lower().replace(" ", "-")

    summaries = [p.get("summary", "") for p in prompt_log[-5:] if p.get("summary")]
    cli_cmd = CONFIG.get("llm_tool", "claude")

    prompt = (
        "Based on these 5 developer prompts, suggest a concise 2-4 word kebab-case repository name.\n\n"
        f"PROMPTS:\n{json.dumps(summaries, indent=2)}\n\n"
        "Rules: Output ONLY the lowercase kebab-case name (e.g. 'esp32-sensor-relay' or 'godot-combat-system'). No quotes, no markdown."
    )

    if cli_cmd in ["claude", "cursor-agent"]:
        code, out, _ = run_cmd(f'{cli_cmd} -p "{prompt[:2000].replace(chr(34), chr(39))}"')
        if code == 0 and out.strip():
            candidate = strip_emojis(out.strip()).strip('"').strip("'").lower()
            candidate = "".join(c if (c.isalnum() or c == "-") else "-" for c in candidate).strip("-")
            if candidate and len(candidate) <= 50:
                return candidate

    last_summary = summaries[-1] if summaries else fallback_name
    words = "".join(c if c.isalnum() else " " for c in last_summary.lower()).split()[:3]
    return "-".join(words) or fallback_name

def prompt_for_repo_name(suggested_name: str, question_text: str) -> str | None:
    """Prompts the user to enter/confirm the GitHub repository name."""
    clean_q = strip_emojis(question_text).replace("'", "''").replace('"', '`"')
    clean_sug = strip_emojis(suggested_name).replace("'", "''").replace('"', '`"')

    ps_script = f"""
[void][Reflection.Assembly]::LoadWithPartialName('Microsoft.VisualBasic')
$title = 'offGIT - Name Your Repository'
$msg = "{clean_q}`n`nEnter repository name (or click Cancel to postpone):"
$name = [Microsoft.VisualBasic.Interaction]::InputBox($msg, $title, '{clean_sug}')
if ([string]::IsNullOrWhiteSpace($name)) {{ exit 1 }} else {{ Write-Output $name; exit 0 }}
"""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True
        )
        if res.returncode == 0 and res.stdout.strip():
            chosen = res.stdout.strip().split("\n")[-1].strip()
            chosen_clean = "".join(c if (c.isalnum() or c in "-_.") else "-" for c in chosen.lower()).strip("-")
            return chosen_clean if chosen_clean else suggested_name
        return None
    except Exception as e:
        logger.warning(f"GUI InputBox fallback: {e}")
        print(f"\n[offGIT] {question_text}")
        val = input(f"Enter repository name (default: '{suggested_name}'): ").strip()
        if not val:
            return suggested_name
        if val.lower() in ["n", "no", "cancel"]:
            return None
        return "".join(c if (c.isalnum() or c in "-_.") else "-" for c in val.lower()).strip("-")

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
    if not (Path(repo_path) / ".git").exists():
        return

    ensure_gitignore(repo_path)
    run_cmd(["git", "add", "-A"], cwd=repo_path)

    code, staged_diff, _ = run_cmd(["git", "diff", "--cached", "--quiet"], cwd=repo_path)
    if code == 0:
        logger.info(f"No changes staged in {repo_path}, nothing to commit.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"docs: offgit sync ({timestamp})"
    code, _, err = run_cmd(["git", "commit", "-m", commit_msg], cwd=repo_path)
    if code != 0:
        logger.error(f"Commit failed in {repo_path}: {err}")
        return

    code, _, err = run_cmd(["git", "push"], cwd=repo_path)
    if code == 0:
        logger.info(f"Pushed commit to remote in {repo_path}")
        notify(f"offGIT Synced: {Path(repo_path).name}", f"Pushed updates to GitHub at {timestamp}")
    else:
        logger.warning(f"Git push failed in {repo_path} (remote may not be set): {err}")

def should_trigger_repo_check(count: int) -> bool:
    """Evaluates if the prompt count should trigger a repository creation check (after 5th prompt / every 5 prompts)."""
    if count < 5:
        return False
    threshold = CONFIG.get("prompt_threshold", 5)
    if isinstance(threshold, int):
        return count % threshold == 0
    if isinstance(threshold, list):
        return count in threshold or (count % 5 == 0)
    return count % 5 == 0

def maybe_scaffold_repo(repo_path: str, project_name: str) -> bool:
    """Prompts user with LLM-phrased question and allows custom repo naming before creation."""
    if (Path(repo_path) / ".git").exists():
        code, remote_out, _ = run_cmd(["git", "remote", "get-url", "origin"], cwd=repo_path)
        if code == 0 and remote_out.strip():
            return False

    auto_dir = Path(repo_path) / ".offgit"
    count_file = auto_dir / "prompt-count"
    count = 0
    if count_file.exists():
        try:
            count = int(count_file.read_text(encoding="utf-8").strip())
        except ValueError:
            count = 0

    if not should_trigger_repo_check(count):
        return False

    prompt_context = read_prompt_log(repo_path)
    tool = CONFIG.get("llm_tool", "claude")

    suggested_name = suggest_repo_name(prompt_context, project_name, tool)
    question_text = phrase_repo_question(prompt_context, suggested_name, tool)

    final_repo_name = prompt_for_repo_name(suggested_name, question_text)

    if not final_repo_name:
        logger.info(f"User postponed repository creation for {project_name} at prompt {count}.")
        return False

    logger.info(f"Creating repository with confirmed name: {final_repo_name}")
    p_path = Path(repo_path)
    p_path.mkdir(parents=True, exist_ok=True)

    readme = p_path / "README.md"
    if not readme.exists():
        readme.write_text(f"# {final_repo_name}\n\nProject created autonomously by offGIT.\n", encoding="utf-8")

    arch = p_path / "ARCHITECTURE.md"
    if not arch.exists():
        arch.write_text(f"# Architecture: {final_repo_name}\n\n## Overview\n\nInitial architectural design.\n", encoding="utf-8")

    ensure_gitignore(repo_path)
    ensure_tool_pointers(repo_path)

    if not (p_path / ".git").exists():
        run_cmd(["git", "init"], cwd=repo_path)
        run_cmd(["git", "branch", "-M", "main"], cwd=repo_path)

    gh_user = CONFIG.get("github_user", "MaheswarPraveen")
    code, out, err = run_cmd(f'gh repo create {gh_user}/{final_repo_name} --public --confirm', cwd=repo_path)
    if code == 0:
        run_cmd(["git", "remote", "add", "origin", f"https://github.com/{gh_user}/{final_repo_name}.git"], cwd=repo_path)
        run_cmd(["git", "add", "-A"], cwd=repo_path)
        run_cmd(["git", "commit", "-m", "feat: initial project scaffolding by offGIT"], cwd=repo_path)
        run_cmd(["git", "push", "-u", "origin", "main"], cwd=repo_path)
        logger.info(f"Successfully created and pushed remote repo {gh_user}/{final_repo_name}")
        notify("Repository Created", f"Created and scaffolded {gh_user}/{final_repo_name}")
        return True
    else:
        logger.error(f"gh repo create failed: {err}")

    return Falsedef classify_thought(diff: str, prompt_context: list[dict], tool: str) -> None:
    if not prompt_context and not diff:
        return

    last_summary = prompt_context[-1].get("summary", "") if prompt_context else ""
    last_thinking = prompt_context[-1].get("ai_thinking", "") if prompt_context else ""

    if not last_summary or len(last_summary) < 10:
        return

    thoughts_repo = Path(CONFIG.get("thoughts_repo_path", THOUGHTS_DIR))
    if not (thoughts_repo / ".git").exists():
        return

    slug = "".join(c if c.isalnum() else "-" for c in last_summary.lower())[:40].strip("-")
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}-{slug}.md"
    file_path = thoughts_repo / filename

    content = f"# Technical Decision: {last_summary}\n\n"
    content += f"**Date:** {date_str}  \n"
    content += f"**Tool:** {tool}  \n\n"
    content += f"## Problem & Directive\n\n{last_summary}\n\n"
    if last_thinking:
        content += f"## AI Architectural Reasoning\n\n{last_thinking}\n\n"
    if diff:
        content += f"## Accompanying Diff Summary\n\n```diff\n{diff[:2000]}\n```\n"

    file_path.write_text(strip_emojis(content), encoding="utf-8")

    readme_path = thoughts_repo / "README.md"
    all_mds = sorted(thoughts_repo.glob("*.md"), reverse=True)
    readme_lines = [
        "# Private Technical Thoughts & Decision Corpus\n",
        "Private repository of architecture decisions and developer reasoning maintained by offGIT.\n",
        "## Recent Decisions\n"
    ]
    for md in all_mds:
        if md.name != "README.md":
            title = md.stem.replace("-", " ").capitalize()
            readme_lines.append(f"- [{title}]({md.name})")

    readme_path.write_text("\n".join(readme_lines) + "\n", encoding="utf-8")

    run_cmd(["git", "add", "-A"], cwd=str(thoughts_repo))
    run_cmd(["git", "commit", "-m", f"docs(thoughts): record {slug}"], cwd=str(thoughts_repo))
    run_cmd(["git", "push", "origin", "main"], cwd=str(thoughts_repo))
    logger.info(f"Auto-synced thought to private thoughts repo: {filename}")

def schedule_debounced_context_push(repo_path: str, delay_seconds: int = 120, max_wait_seconds: int = 300) -> None:
    auto_dir = Path(repo_path) / ".offgit"
    auto_dir.mkdir(parents=True, exist_ok=True)

    ts_file = auto_dir / "last-prompt.timestamp"
    first_file = auto_dir / "first-prompt.timestamp"
    now = time.time()

    ts_file.write_text(str(now), encoding="utf-8")
    if not first_file.exists():
        first_file.write_text(str(now), encoding="utf-8")

    cmd = (
        f"python -c \""
        f"import time, os, subprocess, sys; "
        f"delay = {delay_seconds}; "
        f"max_wait = {max_wait_seconds}; "
        f"ts_f = r'{ts_file}'; "
        f"first_f = r'{first_file}'; "
        f"repo = r'{repo_path}'; "
        f"time.sleep(delay); "
        f"now_t = time.time(); "
        f"last_t = float(open(ts_f).read().strip()) if os.path.exists(ts_f) else now_t; "
        f"first_t = float(open(first_f).read().strip()) if os.path.exists(first_f) else now_t; "
        f"if (now_t - last_t >= delay) or (now_t - first_t >= max_wait): "
        f"    subprocess.run([sys.executable, r'{Path.home() / '.offgit' / 'sync_engine.py'}', '--repo', repo, '--trigger', 'context-debounce']); "
        f"    if os.path.exists(first_f): os.remove(first_f);\""
    )
    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def notify(title: str, message: str) -> None:
    clean_title = strip_emojis(title).replace("'", "''")
    clean_msg = strip_emojis(message).replace("'", "''")

    ps_cmd = (
        f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; "
        f"$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
        f"$textNodes = $template.GetElementsByTagName('text'); "
        f"$textNodes.Item(0).AppendChild($template.CreateTextNode('{clean_title}')) > $null; "
        f"$textNodes.Item(1).AppendChild($template.CreateTextNode('{clean_msg}')) > $null; "
        f"$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
        f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('offGIT').Show($toast);"
    )
    subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def run_sync(repo_path: str, trigger_source: str) -> None:
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
    classify_thought(diff, prompt_context, trigger_source)

def main():
    parser = argparse.ArgumentParser(description="offGIT Core Engine")
    parser.add_argument("--repo", type=str, help="Path to project repository")
    parser.add_argument("--trigger", type=str, default="cli", help="Trigger source identifier")
    parser.add_argument("--log-prompt", action="store_true", help="Append an entry to prompt-log.jsonl")
    parser.add_argument("--tool", type=str, default="cli", help="Tool name for prompt logging")
    parser.add_argument("--summary", type=str, default="", help="Prompt summary text")
    parser.add_argument("--thinking", type=str, default="", help="AI thinking / architecture explanation")

    args = parser.parse_args()

    if args.log_prompt and args.repo:
        count = append_prompt_log(args.repo, args.tool, args.summary, args.thinking)
        update_context_md(args.repo, f"- Active prompt: {args.summary}")
        schedule_debounced_context_push(args.repo, CONFIG.get("context_push_debounce_seconds", 120))
        print(f"Logged prompt to offGIT. Current count: {count}")
    elif args.repo:
        run_sync(args.repo, args.trigger)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()