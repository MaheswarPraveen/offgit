import os
import sys
import time
import argparse
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".offgit"))
from sync_engine import CONFIG

def main():
    parser = argparse.ArgumentParser(description="OffGit Debounce Trigger Wrapper")
    parser.add_argument("--repo", type=str, required=True, help="Path to repository")
    parser.add_argument("--trigger", type=str, default="hook", help="Trigger source")
    args = parser.parse_args()

    repo_path = Path(args.repo).resolve()
    auto_dir = repo_path / ".offgit"
    auto_dir.mkdir(parents=True, exist_ok=True)

    timestamp_file = auto_dir / "last-edit.timestamp"
    lock_file = auto_dir / "debounce.lock"

    now = time.time()
    timestamp_file.write_text(str(now), encoding="utf-8")

    if lock_file.exists():
        try:
            lock_time = float(lock_file.read_text(encoding="utf-8").strip())
            if now - lock_time < CONFIG.get("context_push_debounce_seconds", 120) * 2:
                sys.exit(0)
        except Exception:
            pass

    lock_file.write_text(str(now), encoding="utf-8")
    idle_limit = CONFIG.get("context_push_debounce_seconds", 120)

    cmd = (
        f"python -c \""
        f"import time, os, subprocess, sys; "
        f"idle = {idle_limit}; "
        f"ts_file = r'{timestamp_file}'; "
        f"lock_file = r'{lock_file}'; "
        f"repo = r'{repo_path}'; "
        f"trigger = '{args.trigger}'; "
        f"time.sleep(idle); "
        f"last_ts = float(open(ts_file).read().strip()); "
        f"if time.time() - last_ts >= idle: "
        f"    subprocess.run([sys.executable, r'{Path.home() / '.offgit' / 'sync_engine.py'}', '--repo', repo, '--trigger', trigger]); "
        f"if os.path.exists(lock_file): os.remove(lock_file);\""
    )

    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    main()