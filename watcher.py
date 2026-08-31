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
from sync_engine import CONFIG, run_sync, get_diff, read_prompt_log, check_github_prerequisites, logger

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

def discover_watched_repos() -> set[str]:
    repos = set()
    for base in CONFIG.get("watched_directories", []):
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
                    prompts = read_prompt_log(repo)
                    if diff.strip() or prompts:
                        logger.info(f"Firing 10-minute batch sync for: {repo}")
                        run_sync(repo, "watcher")
                        synced_count += 1
                except Exception as e:
                    logger.error(f"Error in 10-minute batch sync on {repo}: {e}")

            logger.info(f"Completed 10-minute batch sync cycle (scanned {len(all_candidate_repos)} repos, synced {synced_count}).")
        except Exception as loop_err:
            logger.error(f"Error in batch loop iteration: {loop_err}\n{traceback.format_exc()}")

def main():
    try:
        ready, msg = check_github_prerequisites()
        if not ready:
            logger.error(f"Cannot start offGIT Watcher: {msg}")
            return

        logger.info("Starting offGIT filesystem watcher & 10-minute batch engine...")
        dirs = [d for d in CONFIG.get("watched_directories", []) if os.path.exists(d)]
        exts = CONFIG.get("watched_extensions", [
            ".ino", ".gd", ".py", ".ts", ".cpp", ".h", ".js", ".c", ".hpp", ".tscn", ".md", ".json", ".txt"
        ])

        if not dirs:
            logger.warning("No valid watched_directories found in config.yaml.")
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

if __name__ == "__main__":
    main()