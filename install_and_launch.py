import os
import sys
import shutil
import subprocess
from pathlib import Path

def run(cmd, check=True):
    return subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)

def ensure_winget_package(cmd_name, winget_id, label):
    if shutil.which(cmd_name) is None:
        print(f"[offGIT] Installing {label} via winget...")
        run(f"winget install --id {winget_id} -e --silent --accept-package-agreements --accept-source-agreements")
    else:
        print(f"[offGIT] {label} already installed.")

def main():
    print("[offGIT] Verifying system prerequisites...")
    ensure_winget_package("git", "Git.Git", "Git")
    ensure_winget_package("gh", "GitHub.cli", "GitHub CLI")
    ensure_winget_package("node", "OpenJS.NodeJS.LTS", "Node.js")

    if shutil.which("claude") is None:
        print("[offGIT] Checking Claude Code CLI...")
    if shutil.which("cursor-agent") is None:
        print("[offGIT] Cursor CLI check (optional).")

    req_file = Path.home() / ".offgit" / "requirements.txt"
    run(f'"{sys.executable}" -m pip install -r "{req_file}" -q')

    status = run("gh auth status", check=False)
    if status.returncode != 0:
        print("[offGIT] GitHub login required â€” opening browser for OAuth authorization...")
        run("gh auth login --web --git-protocol https -h github.com")
    else:
        print("[offGIT] GitHub CLI authenticated.")

    watcher_script = Path.home() / ".offgit" / "watcher.py"
    pythonw = Path(sys.executable).parent / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable)

    schtasks_cmd = (
        f'schtasks /create /tn "offGIT" /tr '
        f'"{pythonw} {watcher_script}" '
        f'/sc onlogon /f'
    )
    subprocess.run(schtasks_cmd, shell=True, capture_output=True)

    # Launch background watcher
    subprocess.Popen([str(pythonw), str(watcher_script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("[offGIT] Done. offGIT is running in the background and registered for autostart.")

if __name__ == "__main__":
    main()