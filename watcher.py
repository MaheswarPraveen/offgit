from __future__ import annotations
import os
import sys
import time
import shutil
import logging
import threading
import traceback
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Ensure safe stdout/stderr when running as background daemon (pythonw)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

sys.path.insert(0, str(Path.home() / ".offgit"))
from sync_engine import CONFIG, run_sync, get_diff, read_prompt_log, get_unsynced_prompts, check_github_prerequisites, logger

class IdleEventHandler(FileSystemEventHandler):
    def __init__(self, extensions):
        super().__init__()
        self.extensions = set(ext.lower() for ext in extensions)
        self.active_repos = set()

    def on_any_event(self, event):
        if event.is_directory:
            return

        ext = Path(event.src_path).suffix.lower()
        if ext in self.extensions or event.src_path.endswith("CONTEXT.md"):
            if ".git" in event.src_path.split(os.sep):
                return

            repo_dir = self.find_repo_root(event.src_path)
            if repo_dir:
                self.active_repos.add(repo_dir)
                logger.debug(f"File modification in {event.src_path} (repo: {repo_dir})")

    def find_repo_root(self, file_path: str) -> str:
        cur = Path(file_path).resolve().parent
        while cur != cur.parent:
            if (cur / ".git").exists() or (cur / ".offgit").exists():
                return str(cur)
            cur = cur.parent
        return str(Path(file_path).parent)

def get_watched_directories() -> list[str]:
    """Dynamically resolves and expands user home directory paths (~) across Windows, macOS, and Linux."""
    dirs = []
    candidates = CONFIG.get("watched_directories", [
        "~/.gemini/antigravity/scratch",
        "~/Documents/Arduino",
        "~/Projects",
        "~/workspace",
        "~/dev"
    ])
    for d in candidates:
        try:
            expanded = Path(d).expanduser().resolve()
            if expanded.exists():
                dirs.append(str(expanded))
        except Exception as e:
            logger.debug(f"Could not resolve directory {d}: {e}")
    return dirs

def discover_watched_repos() -> set[str]:
    """Finds all existing git/offgit project directories under dynamic watched directories."""
    repos = set()
    for base in get_watched_directories():
        base_p = Path(base)
        if not base_p.exists():
            continue
        if (base_p / ".git").exists() or (base_p / ".offgit").exists():
            repos.add(str(base_p))
        try:
            for child in base_p.iterdir():
                if child.is_dir() and ((child / ".git").exists() or (child / ".offgit").exists()):
                    repos.add(str(child))
        except Exception as e:
            logger.debug(f"Error scanning {base}: {e}")
    return repos

def devlog_10min_batch_loop(handler: IdleEventHandler):
    interval = CONFIG.get("devlog_interval_seconds", 600)
    logger.info(f"10-minute batch sync loop started (interval: {interval}s)")

    while True:
        try:
            time.sleep(interval)
            ready, msg = check_github_prerequisites()
            if not ready:
                logger.warning(f"10-minute batch sync paused: {msg}")
                continue

            all_candidate_repos = set(handler.active_repos).union(discover_watched_repos())
            handler.active_repos.clear()

            synced_count = 0
            for repo in all_candidate_repos:
                try:
                    diff = get_diff(repo)
                    unsynced_prompts = get_unsynced_prompts(repo)
                    if diff.strip() or unsynced_prompts:
                        logger.info(f"Firing 10-minute batch sync for: {repo}")
                        run_sync(repo, "watcher")
                        synced_count += 1
                except Exception as e:
                    logger.error(f"Error in 10-minute batch sync on {repo}: {e}")

            logger.info(f"Completed 10-minute batch sync cycle (scanned {len(all_candidate_repos)} repos, synced {synced_count}).")
        except Exception as loop_err:
            logger.error(f"Error in batch loop iteration: {loop_err}\n{traceback.format_exc()}")

WATCHER_PID_FILE = Path.home() / ".offgit" / "watcher.pid"

def _is_process_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        if os.name == "nt":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError, PermissionError):
        return False

def _acquire_watcher_lock() -> bool:
    """Ensures only one watcher instance runs. Returns True if lock acquired, False if another instance is alive."""
    if WATCHER_PID_FILE.exists():
        try:
            existing_pid = int(WATCHER_PID_FILE.read_text(encoding="utf-8").strip())
            if _is_process_alive(existing_pid) and existing_pid != os.getpid():
                return False
            # Stale PID file from a dead process, safe to overwrite
            logger.info(f"Cleaning up stale watcher PID file (PID {existing_pid} is no longer running)")
        except (ValueError, Exception):
            pass
    WATCHER_PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    return True

def _release_watcher_lock() -> None:
    try:
        if WATCHER_PID_FILE.exists():
            stored_pid = int(WATCHER_PID_FILE.read_text(encoding="utf-8").strip())
            if stored_pid == os.getpid():
                WATCHER_PID_FILE.unlink()
    except Exception:
        pass

def main():
    try:
        if not _acquire_watcher_lock():
            existing_pid = WATCHER_PID_FILE.read_text(encoding="utf-8").strip()
            logger.warning(f"offGIT watcher already running (PID: {existing_pid}). Exiting duplicate instance.")
            return

        ready, msg = check_github_prerequisites()
        if not ready:
            logger.error(f"Cannot start offGIT Watcher: {msg}")
            _release_watcher_lock()
            return

        logger.info("Starting offGIT filesystem watcher & 10-minute batch engine...")
        dirs = get_watched_directories()
        exts = CONFIG.get("watched_extensions", [
            ".ino", ".gd", ".py", ".ts", ".cpp", ".h", ".js", ".c", ".hpp", ".tscn", ".md", ".json", ".txt"
        ])

        if not dirs:
            logger.warning("No valid watched_directories found in config.yaml.")
            _release_watcher_lock()
            return

        handler = IdleEventHandler(exts)
        observer = Observer()

        for d in dirs:
            logger.info(f"Watching directory: {d}")
            observer.schedule(handler, d, recursive=True)

        loop_thread = threading.Thread(target=devlog_10min_batch_loop, args=(handler,), daemon=True)
        loop_thread.start()

        observer.start()
        while True:
            time.sleep(1)
    except Exception as e:
        logger.error(f"FATAL crash in watcher: {e}\n{traceback.format_exc()}")
    finally:
        _release_watcher_lock()

if __name__ == "__main__":
    main()