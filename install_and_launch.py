import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path

def run(cmd, check=True, timeout=120):
    is_list = isinstance(cmd, list)
    return subprocess.run(cmd, shell=not is_list, check=check, capture_output=True, text=True, timeout=timeout)

def ensure_package_windows(cmd_name, winget_id, label):
    if shutil.which(cmd_name) is None:
        print(f"[offGIT] Installing {label} via winget...")
        run(f"winget install --id {winget_id} -e --silent --accept-package-agreements --accept-source-agreements", check=False)
    else:
        print(f"[offGIT] {label} already installed.")

def main():
    system = platform.system()
    print(f"[offGIT] Initializing cross-platform installer on {system}...")

    # 1. Dependency Resolution
    if system == "Windows":
        ensure_package_windows("git", "Git.Git", "Git")
        ensure_package_windows("gh", "GitHub.cli", "GitHub CLI")
        ensure_package_windows("node", "OpenJS.NodeJS.LTS", "Node.js")
    elif system == "Darwin":
        if shutil.which("brew"):
            if shutil.which("gh") is None:
                print("[offGIT] Installing GitHub CLI via Homebrew...")
                run(["brew", "install", "gh"], check=False)
        else:
            print("[offGIT] Homebrew not found. Please ensure 'git' and 'gh' are installed.")
    elif system == "Linux":
        if shutil.which("gh") is None:
            print("[offGIT] GitHub CLI not found. Please install via your package manager (e.g. sudo apt install gh).")

    # 2. Python Dependencies
    print("[offGIT] Installing Python dependencies (pyyaml, watchdog)...")
    run([sys.executable, "-m", "pip", "install", "pyyaml", "watchdog", "-q"], check=False)

    # 3. GitHub Authentication Pre-flight Gate
    print("[offGIT] Verifying GitHub CLI authentication...")
    status = run(["gh", "auth", "status"], check=False)
    while status.returncode != 0:
        print("\n[offGIT AUTH REQUIRED] GitHub CLI is not authenticated.")
        print("[offGIT] Launching web browser for GitHub authorization...")
        run(["gh", "auth", "login", "--web", "--git-protocol", "https", "-h", "github.com"], check=False)
        status = run(["gh", "auth", "status"], check=False)
        if status.returncode != 0:
            print("[offGIT] Login incomplete. offGIT requires an authenticated GitHub CLI session.")
            input("Press Enter after completing login in your browser to retry...")

    print("[offGIT] GitHub CLI verified and authenticated.")

    # 4. Copy engine files to ~/.offgit
    offgit_home = Path.home() / ".offgit"
    offgit_home.mkdir(parents=True, exist_ok=True)
    (offgit_home / "logs").mkdir(parents=True, exist_ok=True)
    (offgit_home / "thoughts").mkdir(parents=True, exist_ok=True)

    cur_dir = Path(__file__).resolve().parent
    for f in cur_dir.glob("*.py"):
        shutil.copy(f, offgit_home / f.name)
    for f in cur_dir.glob("*.yaml"):
        shutil.copy(f, offgit_home / f.name)

    # 5. Register Autostart and Launch
    watcher_script = offgit_home / "watcher.py"
    if system == "Windows":
        startup_dir = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        startup_vbs = startup_dir / "offGIT.vbs"
        py_dir = Path(sys.executable).parent
        pythonw = py_dir / "pythonw.exe"
        if not pythonw.exists():
            pythonw = Path(sys.executable)

        vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """{pythonw}"" ""{watcher_script}""", 0, False
'''
        startup_vbs.write_text(vbs_content, encoding="utf-8")
        (offgit_home / "start_offgit.vbs").write_text(vbs_content, encoding="utf-8")
        subprocess.Popen([str(pythonw), str(watcher_script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        # Unix background daemon launch
        subprocess.Popen([sys.executable, str(watcher_script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("\n[SUCCESS] offGIT is authenticated, configured, and running in the background.")

if __name__ == "__main__":
    main()