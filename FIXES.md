# offGIT Known Issues & Error Reference (FIXES.md)

This document contains canonical error signatures, root causes, and verified fixes across the offGIT ecosystem. AI agents and developers should consult this file first before diagnosing issues to save context tokens and achieve 1-shot fixes.

---

## 1. Windows: Black Terminal Windows Flashing / Popping Up Repeatedly

- **Symptom**: Command prompt or PowerShell console windows momentarily pop up and close on the desktop during background operations.
- **Root Cause**: On Windows, calling `subprocess.run()` or `subprocess.Popen()` from a background process (`pythonw.exe`) without `creationflags=subprocess.CREATE_NO_WINDOW` (`0x08000000`) causes Windows to spawn a temporary console window for each child process (`git.exe`, `gh.exe`, `powershell.exe`).
- **Canonical Fix**:
  ```python
  no_window_flag = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
  subprocess.run(cmd, shell=False, capture_output=True, creationflags=no_window_flag)
  ```

---

## 2. Windows: Background Daemon Terminating After Parent Shell Exits

- **Symptom**: `pythonw.exe` starts but exits within 5-10 seconds after the PowerShell terminal or parent script terminates.
- **Root Cause**: Windows Job Objects automatically kill child processes spawned by a temporary subshell when the parent shell closes.
- **Canonical Fix**: Spawn the background process via WMI `Win32_Process.Create` (detached from the shell job object):
  ```powershell
  Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = 'pythonw.exe ~/.offgit/watcher.py'}
  ```

---

## 3. Remote Git: Upstream Rebase Merge Conflicts & Stuck Working Trees

- **Symptom**: Git operations fail with `fatal: It seems that there is already a rebase-merge directory` or half-rebased conflict states.
- **Root Cause**: Running `git pull --rebase --autostash` on a diverged remote branch leaves Git in an active rebase conflict state if auto-merging fails.
- **Canonical Fix**: Immediately abort the rebase on failure to restore the local working tree to a clean state before proceeding:
  ```python
  pull_code, _, pull_err = run_cmd(["git", "pull", "--rebase", "--autostash", "origin", "main"], cwd=repo_path, timeout=20)
  if pull_code != 0:
      run_cmd(["git", "rebase", "--abort"], cwd=repo_path, timeout=10)
      return
  ```

---

## 4. GitHub CLI: Unauthenticated Runs & Missing Binary Failures

- **Symptom**: `gh repo create` or `git push` fails silently or returns exit code 1 with authentication errors.
- **Root Cause**: GitHub CLI is not installed or `gh auth status` is unauthenticated.
- **Canonical Fix**:
  - Run pre-flight check `check_github_prerequisites()`.
  - If unauthenticated, halt and prompt the user to execute `gh auth login --web` to launch the browser OAuth flow.

---

## 5. Milestone Prompting: Redundant Inception Prompts for Existing Repositories

- **Symptom**: Agent asks *"Want me to create a GitHub repo?"* at prompt 15/30/60 even though the repository was already created and published.
- **Root Cause**: Milestone check only evaluated prompt counts (`count in [5, 15, 30, 60]`) without checking if a git remote `origin` already exists.
- **Canonical Fix**:
  ```python
  def is_already_github_repo(repo: Path) -> bool:
      if not (repo / ".git").exists(): return False
      res = subprocess.run(["git", "remote", "get-url", "origin"], cwd=str(repo), capture_output=True, text=True, timeout=3, creationflags=NO_WINDOW)
      return res.returncode == 0 and bool(res.stdout.strip())
  ```

---

## 6. Prompt Counter Latency: High Turn Latency During Chat

- **Symptom**: Chat agent hangs for 3-6 seconds before answering simple prompts.
- **Root Cause**: `prompt_counter.py` importing heavy third-party modules (`yaml`, `watchdog`, `sync_engine`) and calling external LLM CLI subprocesses (`claude -p`) on every turn.
- **Canonical Fix**: Decouple `prompt_counter.py` into a standalone, zero-dependency script using pure Python standard library (`json`, `pathlib`, `datetime`). Drops total execution time to **< 190ms**.

---

## 7. Subprocess Quoting & Shell Injection Landmine

- **Symptom**: Subprocess crashes on code diffs containing quotes, `$`, backticks, or semicolons.
- **Root Cause**: Using `shell=True` with string interpolation `f'{cli_cmd} -p "{prompt}"'`.
- **Canonical Fix**: Pass arguments as an explicit list `[cli_cmd, "-p", prompt]` with `shell=False`.

---

## 8. Thoughts Repository: Synthetic Checkpoint Spam & Duplicate Thrash

- **Symptom**: `thoughts` repository gets flooded with dozens of duplicate markdown files (e.g. `..._1016_...md`, `..._1022_...md`) containing trivial conversational comments (*"what what about my first hi"*, *"are these going to thoughts"*).
- **Root Cause**:
  1. `classify_thought()` was fabricating synthetic entries from static `CONTEXT.md` directives when `valid_entries` was empty, writing a new file every 10 minutes for every watched folder.
  2. Filenames included minute timestamps (`%H%M`), creating new duplicate files on every batch cycle.
  3. Acceptance threshold was too loose (`len >= 8`), ingesting casual chat into architecture decision files.
- **Canonical Fix**:
  1. **Strict Return on Empty**: If there are no new un-synced prompts with genuine technical substance, `classify_thought` returns immediately and writes zero files.
  2. **Substantive Architecture Filter (`is_genuine_architectural_thought`)**: Requires `ai_thinking >= 30` characters or explicit technical domain keywords (`implement`, `refactor`, `architecture`, `kinematics`, `firmware`, `algorithm`, `protocol`). Drops all meta-questions and conversational chit-chat.
  3. **Clean Filenames Without Minute Timestamps**: Uses `YYYY-MM-DD_<project>_<topic>.md` to prevent duplicate files across batch cycles.

---

## 9. Contribution Graph Blackouts: Uninitialized Projects & Placeholder Noreply Emails

- **Symptom**: Developer works for hours across dozens of turns, but the GitHub contribution graph shows zero activity or black squares.
- **Root Cause**:
  1. **Uninitialized Directory**: The project folder in `scratch/` was created without running `git init`. `commit_and_push()` skipped non-git folders silently (`if not .git.exists(): return`).
  2. **Unlinked Placeholder Email**: Global Git config was set to `Username@users.noreply.github.com` instead of the user's primary verified GitHub email. GitHub refuses to credit commits to the contribution graph unless the author email is verified on the account.
  3. **No Remote Configured**: A local git repo existed but had no remote `origin`, leaving commits stranded on the local drive.
- **Canonical Fix**:
  1. **Global Email Enforcement**: Set global git config to verified email:
     `git config --global user.email "maheswarpraveen@gmail.com"`
  2. **Dynamic Email Resolver (`get_verified_git_email`)**: Replaces any unverified noreply strings dynamically with verified primary email on every commit.
  3. **Auto-Init Git**: If a watched project folder lacks `.git`, `commit_and_push()` runs `git init -b main` automatically.
  4. **Auto-Scaffold Remote**: If no remote is configured and `gh` is authenticated, offGIT automatically creates the GitHub repository (`gh repo create <target> --source . --remote origin --push`) and establishes continuous sync.

---

## 10. Linux & WSL: "Daemon Not Running" False Warning & Sudo Installer Hangs

- **Symptom**: `sync_engine.py --fix` outputs `[WARNING] Background watcher daemon is not running` on Linux/Ubuntu/WSL even when `watcher.py` is actively running. On fresh installs, `install.sh` hangs or crashes on `sudo apt` or `ModuleNotFoundError: No module named 'watchdog'`.
- **Root Cause**:
  1. `sync_engine.py` hardcoded a Windows-only `powershell Get-Process -Name pythonw` check, failing on all POSIX environments.
  2. Ubuntu/Debian does not bundle `pip` with `python3` (`No module named pip`), and PEP 668 prevents bare pip installs without `--break-system-packages`.
  3. `install.sh` ran `sudo apt` without non-interactive guards, hanging on password prompts in piped `curl | bash` executions.
- **Canonical Fix**:
  1. **Cross-Platform Process Health**: In `sync_engine.py`, query `~/.offgit/watcher.pid` and verify liveness with `os.kill(pid, 0)` on POSIX / `kernel32.OpenProcess` on Windows. Fall back to `pgrep -f watcher.py` and `systemctl --user is-active offgit.service`.
  2. **Native APT Package Installation**: Install `python3-yaml`, `python3-watchdog`, and `python3-pip` directly via APT.
  3. **Graceful Daemon Autostart Fallback**: Test if `systemctl --user` is functional; if in WSL/containers without user systemd, fall back to `nohup` and persist invocation in `~/.bashrc`.

---

## 11. Rogue Git Initialization & Auto-Scaffolding on Generic Placeholder Folders

- **Symptom**: Unintended GitHub repositories (e.g. `Default-Project`) created automatically, or `.git` initialized in user home (`~`) or root `Documents`, breaking nested repository git operations.
- **Root Cause**:
  1. `find_repo_root()` in `watcher.py` fell back to `Path(file_path).parent` when no `.git` existed, passing arbitrary parent folders into `run_sync()`.
  2. `commit_and_push()` in `sync_engine.py` auto-initialized git on any folder and called `gh repo create` to push to remote. When OpenCode opened in its default empty directory (`Documents/Default Project`), offGIT versioned and pushed it as a new GitHub repository.
- **Canonical Fix**:
  1. **Protected Path Boundary (`is_protected_directory`)**: Strictly forbid `git init` and auto-scaffolding in home (`~`), filesystem root, common OS directories (`Documents`, `Desktop`, `Downloads`, `Projects`), and generic placeholders (`Default Project`, `Default-Project`, `tmp`).
  2. **Strict Repo Root Discovery**: `find_repo_root()` returns `None` if no `.git` or `.offgit` exists and the path is not a recognized direct child of a watched project directory.