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
    maybe_scaffold_repo,
    should_trigger_repo_check,
    logger
)

def main():
    parser = argparse.ArgumentParser(description="offGIT Lightweight Fast Prompt Logger")
    parser.add_argument("--repo", type=str, required=True, help="Repository directory")
    parser.add_argument("--prompt", type=str, default="", help="Prompt text")
    parser.add_argument("--tool", type=str, default="claude-code", help="Tool name")
    parser.add_argument("--thinking", type=str, default="", help="AI thinking")

    args = parser.parse_args()
    repo_path = Path(args.repo).resolve()

    if not repo_path.exists():
        return

    summary = args.prompt.strip() or f"User prompt in {args.tool}"

    # 1. Fast local log append (<1ms, no git, no network)
    count = append_prompt_log(str(repo_path), args.tool, summary, args.thinking)

    # 2. Fast local CONTEXT.md snapshot update (local-only)
    update_context_md(str(repo_path), f"- Active Directive: {summary}")

    # 3. Check milestone threshold for repo inception
    if should_trigger_repo_check(count):
        project_name = repo_path.name
        maybe_scaffold_repo(str(repo_path), project_name)

if __name__ == "__main__":
    main()