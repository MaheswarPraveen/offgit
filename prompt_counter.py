from __future__ import annotations
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

    # 1. Check local hosts.yml config directly (< 1ms)
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

    # 2. Fast local token check (reads local config via gh CLI without network lag)
    try:
        res = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=2, creationflags=NO_WINDOW)
        if res.returncode == 0 and res.stdout.strip():
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

def is_watcher_running() -> bool:
    """Checks if the offGIT watcher daemon is actively running (< 1ms)."""
    pid_file = Path.home() / ".offgit" / "watcher.pid"
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        if os.name == "nt":
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False

def ensure_watcher_running() -> None:
    """Quietly resurrects the watcher daemon if it is not currently running."""
    if is_watcher_running():
        return

    offgit_dir = Path.home() / ".offgit"
    watcher_script = offgit_dir / "watcher.py"
    if not watcher_script.exists():
        return

    try:
        if os.name == "nt":
            # On Windows, launch via WMI through start_offgit.vbs to decouple
            # completely from the parent process tree / Windows Job Object
            vbs = offgit_dir / "start_offgit.vbs"
            if vbs.exists():
                subprocess.run(["wscript.exe", str(vbs)], creationflags=NO_WINDOW, timeout=5)
            else:
                py_exe = Path(sys.executable)
                pyw = py_exe.parent / "pythonw.exe"
                exe = str(pyw) if pyw.exists() else sys.executable
                DETACHED = 0x00000008
                subprocess.Popen(
                    [exe, str(watcher_script), "--force"],
                    creationflags=DETACHED | NO_WINDOW,
                    close_fds=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL
                )
        else:
            subprocess.Popen(
                [sys.executable, str(watcher_script), "--force"],
                start_new_session=True,
                close_fds=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
    except Exception:
        pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=str, required=True)
    parser.add_argument("--prompt", type=str, default="")
    parser.add_argument("--tool", type=str, default="antigravity")
    parser.add_argument("--thinking", type=str, default="")
    args = parser.parse_args()
    ensure_watcher_running()

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

    # 3. Update CONTEXT.md inside .offgit/ (hidden harness directory)
    context_file = off_dir / "CONTEXT.md"
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
        "- Refer to .offgit/DEVLOG.md for chronological development updates.\n"
    ])
    context_file.write_text("\n".join(md), encoding="utf-8")

    # Active root clutter purge: remove legacy root CONTEXT.md if present
    legacy_context = repo / "CONTEXT.md"
    if legacy_context.exists():
        try:
            legacy_context.unlink()
        except Exception:
            pass

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