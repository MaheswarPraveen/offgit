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
    if req_file.exists():
        run(f'"{sys.executable}" -m pip install -r "{req_file}" -q')

    # Hard gate: Require GitHub CLI login
    status = run("gh auth status", check=False)
    while status.returncode != 0:
        print("[offGIT AUTH REQUIRED] GitHub CLI is not logged in.")
        print("[offGIT] Opening web browser for GitHub authorization...")
        run("gh auth login --web --git-protocol https -h github.com", check=False)
        status = run("gh auth status", check=False)
        if status.returncode != 0:
            print("[offGIT] Login unsuccessful. offGIT requires an authenticated GitHub CLI session to operate.")
            print("[offGIT] Retrying...")

    print("[offGIT] GitHub CLI verified and authenticated.")

    # Configure user startup script
    startup_dir = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup_vbs = startup_dir / "offGIT.vbs"
    py_dir = Path(sys.executable).parent
    pythonw = py_dir / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable)

    watcher_script = Path.home() / ".offgit" / "watcher.py"
    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """{pythonw}"" ""{watcher_script}""", 0, False
'''
    startup_vbs.write_text(vbs_content, encoding="utf-8")
    (Path.home() / ".offgit" / "start_offgit.vbs").write_text(vbs_content, encoding="utf-8")

    # Start background watcher
    subprocess.Popen([str(pythonw), str(watcher_script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("[offGIT] Done. offGIT is authenticated, running in the background, and registered for autostart.")

if __name__ == "__main__":
    main()