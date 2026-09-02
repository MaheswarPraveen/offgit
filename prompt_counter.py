import os
import sys
import json
import shutil
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

MILESTONES = {5, 15, 30, 60}
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

def is_gh_authenticated() -> tuple[bool, str]:
    """Fast, local-first check for GitHub authentication that avoids network timeouts."""
    if shutil.which("gh") is None:
        return False, "GitHub CLI ('gh') is not installed."

    # 1. Fast local token check (sub-100ms, reads local config without network lag)
    try:
        res = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=2, creationflags=NO_WINDOW)
        if res.returncode == 0 and res.stdout.strip():
            return True, ""
    except Exception:
        pass

    # 2. Check local hosts.yml config directly (< 1ms)
    try:
        config_paths = [
            Path(os.environ.get("APPDATA", "")) / "GitHub CLI" / "hosts.yml",
            Path.home() / ".config" / "gh" / "hosts.yml"
        ]
        for cp in config_paths:
            if cp.exists() and ("oauth_token" in cp.read_text(encoding="utf-8", errors="ignore") or "user:" in cp.read_text(encoding="utf-8", errors="ignore")):
                return True, ""
    except Exception:
        pass

    # 3. Fallback to status with generous 8s timeout
    try:
        res = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=8, creationflags=NO_WINDOW)
        if res.returncode == 0:
            return True, ""
        return False, "GitHub CLI is not logged in."
    except Exception as e:
        return False, str(e)

def is_already_github_repo(repo: Path) -> bool:
    """Checks if the project is already an initialized git repository with a remote origin."""
    if not (repo / ".git").exists():
        return False
    try:
        res = subprocess.run(["git", "remote", "get-url", "origin"], cwd=str(repo), capture_output=True, text=True, timeout=3, creationflags=NO_WINDOW)
        return res.returncode == 0 and bool(res.stdout.strip())
    except Exception:
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=str, required=True)
    parser.add_argument("--prompt", type=str, default="")
    parser.add_argument("--tool", type=str, default="antigravity")
    parser.add_argument("--thinking", type=str, default="")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    off_dir = repo / ".offgit"
    off_dir.mkdir(parents=True, exist_ok=True)

    summary = (args.prompt.strip() or f"User prompt in {args.tool}").encode("ascii", "ignore").decode("ascii")
    thinking = args.thinking.strip().encode("ascii", "ignore").decode("ascii")

    # 1. Update count
    count_file = off_dir / "prompt-count"
    count = 0
    if count_file.exists():
        try:
            count = int(count_file.read_text(encoding="utf-8").strip())
        except ValueError:
            count = 0
    count += 1
    count_file.write_text(str(count), encoding="utf-8")

    # 2. Append to log
    log_file = off_dir / "prompt-log.jsonl"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": args.tool,
        "summary": summary,
        "ai_thinking": thinking
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    # 3. Update CONTEXT.md (instant local snapshot)
    context_file = repo / "CONTEXT.md"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = [
        f"# Live Project Context: {repo.name}",
        f"\n**Last Synced:** {now_str}",
        "\n## Current Focus & Active State\n",
        f"- Directive: {summary}"
    ]
    if thinking:
        md.append(f"- Rationale: {thinking}")
    md.extend([
        "\n## Open Decisions & Next Steps\n",
        "- Continue active implementation according to current focus.",
        "- Refer to DEVLOG.md for historical architecture decisions.\n"
    ])
    context_file.write_text("\n".join(md), encoding="utf-8")

    # 4. Check milestone
    if count in MILESTONES:
        if is_already_github_repo(repo):
            print(f"[offGIT] Logged prompt #{count} for '{repo.name}'. (GitHub repository active)")
        else:
            # Generate clean suggested name from project or directive
            words = "".join(c if c.isalnum() else " " for c in summary.lower()).split()[:3]
            sug_name = "-".join(words) or repo.name.lower()
            if len(sug_name) > 30:
                sug_name = repo.name.lower()

            # Always present milestone question directly in chat
            authed, auth_msg = is_gh_authenticated()
            if authed:
                print(f"[offGIT MILESTONE {count}] Suggested repo: '{sug_name}'. Question: Looks like we reached milestone {count} on '{repo.name}' - want me to create a GitHub repo for '{sug_name}'?")
            else:
                print(f"[offGIT MILESTONE {count}] Suggested repo: '{sug_name}'. Question: Looks like we reached milestone {count} on '{repo.name}' - want me to connect your GitHub and create repo '{sug_name}'?")
    else:
        print(f"[offGIT] Logged prompt #{count} for '{repo.name}'.")

if __name__ == "__main__":
    main()