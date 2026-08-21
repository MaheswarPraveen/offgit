import os
import sys
import time
import threading
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

sys.path.insert(0, str(Path.home() / ".offgit"))
from sync_engine import CONFIG, run_sync, get_diff, logger

class IdleEventHandler(FileSystemEventHandler):
    def __init__(self, extensions):
        super().__init__()
        self.extensions = set(ext.lower() for ext in extensions)
        self.active_repos = set()

    def on_any_event(self, event):
        if event.is_directory:
            return

        ext = Path(event.src_path).suffix.lower()
        if ext in self.extensions:
            if ".offgit" in event.src_path or ".git" in event.src_path:
                return

            repo_dir = self.find_repo_root(event.src_path)
            self.active_repos.add(repo_dir)
            logger.debug(f"File modification in {event.src_path} (repo: {repo_dir})")

    def find_repo_root(self, file_path: str) -> str:
        cur = Path(file_path).resolve().parent
        while cur != cur.parent:
            if (cur / ".git").exists() or (cur / ".offgit").exists():
                return str(cur)
            cur = cur.parent
        return str(Path(file_path).parent)

def devlog_fixed_interval_loop(handler: IdleEventHandler):
    """Hard 10-minute fixed interval loop (Section 6) - checks if diff is non-empty and syncs."""
    interval = CONFIG.get("devlog_interval_seconds", 600)
    logger.info(f"Devlog fixed interval loop started (interval: {interval}s)")

    while True:
        time.sleep(interval)
        repos = list(handler.active_repos)
        for repo in repos:
            try:
                diff = get_diff(repo)
                if diff.strip():
                    logger.info(f"Fixed 10-min interval sync for active repo: {repo}")
                    run_sync(repo, "watcher")
            except Exception as e:
                logger.error(f"Error in fixed interval sync on {repo}: {e}")

def main():
    logger.info("Starting offGIT filesystem watcher & interval engine...")
    dirs = [d for d in CONFIG.get("watched_directories", []) if os.path.exists(d)]
    exts = CONFIG.get("watched_extensions", [".ino", ".gd", ".py", ".ts", ".cpp", ".h"])

    if not dirs:
        logger.warning("No valid watched_directories found in config.yaml.")
        return

    handler = IdleEventHandler(exts)
    observer = Observer()

    for d in dirs:
        logger.info(f"Watching directory: {d}")
        observer.schedule(handler, d, recursive=True)

    # Start hard 10-minute interval loop in separate thread
    loop_thread = threading.Thread(target=devlog_fixed_interval_loop, args=(handler,), daemon=True)
    loop_thread.start()

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()