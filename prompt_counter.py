import os
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".offgit"))
from sync_engine import (
    CONFIG,
    append_prompt_log,
    update_context_md,
    schedule_debounced_context_push,
    maybe_scaffold_repo,
    logger
)

def main():
    parser = argparse.ArgumentParser(description="offGIT Prompt Counter & Trigger")
    parser.add_argument("--repo", type=str, required=True, help="Repository directory")
    parser.add_argument("--prompt", type=str, default="", help="Prompt text")
    parser.add_argument("--tool", type=str, default="claude-code", help="Tool name")
    parser.add_argument("--thinking", type=str, default="", help="AI thinking")

    args = parser.parse_args()
    repo_path = Path(args.repo).resolve()

    if not repo_path.exists():
        return

    summary = args.prompt.strip() or f"User prompt in {args.tool}"

    # 1. Increment counter & log prompt
    count = append_prompt_log(str(repo_path), args.tool, summary, args.thinking)

    # 2. Instant local write of CONTEXT.md
    update_context_md(str(repo_path), f"- Active Directive: {summary}")

    # 3. Schedule 2-minute debounced push
    debounce_sec = CONFIG.get("context_push_debounce_seconds", 120)
    schedule_debounced_context_push(str(repo_path), debounce_sec)

    # 4. Check prompt milestone threshold
    milestones = CONFIG.get("prompt_threshold", [5, 15, 30, 60])
    if count in milestones:
        project_name = repo_path.name
        maybe_scaffold_repo(str(repo_path), project_name)

if __name__ == "__main__":
    main()