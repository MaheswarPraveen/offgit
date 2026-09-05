#!/usr/bin/env bash
# ===================================================
#          offGIT - One-Click Setup & Launch
#             (macOS & Linux Unified)
# ===================================================

set -e

echo "==================================================="
echo "          offGIT - One-Click Setup & Launch        "
echo "==================================================="
echo ""

# 1. Detect OS & Package Manager
OS_TYPE="$(uname -s)"
echo "[1/6] Detecting operating system: $OS_TYPE"

run_as_root() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif sudo -n true 2>/dev/null; then
        sudo "$@"
    elif [ -t 0 ]; then
        sudo "$@"
    else
        echo "[Notice] Root permissions required for '$*'. Skipping unattended execution."
        return 1
    fi
}

install_package() {
    PKG=$1
    if command -v brew >/dev/null 2>&1; then
        brew install "$PKG" || true
    elif command -v apt-get >/dev/null 2>&1; then
        run_as_root apt-get update -qq && run_as_root apt-get install -y -qq "$PKG" || true
    elif command -v dnf >/dev/null 2>&1; then
        run_as_root dnf install -y -q "$PKG" || true
    elif command -v pacman >/dev/null 2>&1; then
        run_as_root pacman -Sy --noconfirm "$PKG" || true
    fi
}

# 2. Check and Install Prerequisites (git, gh, python3)
echo "[2/6] Verifying prerequisites (git, gh, python3)..."
if ! command -v git >/dev/null 2>&1; then
    echo "Installing git..."
    install_package git
fi

if ! command -v gh >/dev/null 2>&1; then
    echo "Installing GitHub CLI (gh)..."
    if [ "$OS_TYPE" = "Darwin" ]; then
        install_package gh
    elif command -v apt-get >/dev/null 2>&1; then
        type -p curl >/dev/null || run_as_root apt-get install curl -y
        curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | run_as_root dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null || true
        run_as_root chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null || true
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | run_as_root tee /etc/apt/sources.list.d/github-cli.list > /dev/null || true
        run_as_root apt-get update -qq && run_as_root apt-get install gh -y -qq || true
    else
        install_package github-cli
    fi
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Installing python3..."
    install_package python3
fi

if command -v apt-get >/dev/null 2>&1; then
    install_package python3-pip
    install_package python3-yaml
    install_package python3-watchdog
fi

# 3. GitHub Authentication Check
echo "[3/6] Verifying GitHub authentication status..."
if ! gh auth status >/dev/null 2>&1; then
    echo ""
    echo "==================================================="
    echo " GitHub CLI authentication required."
    echo " Launching browser login (gh auth login)..."
    echo "==================================================="
    gh auth login --web -p https -w
fi
echo "GitHub CLI is authenticated successfully."

# 4. Deploy offGIT Core Harness
echo "[4/6] Deploying offGIT harness to ~/.offgit..."
OFFGIT_DIR="$HOME/.offgit"
mkdir -p "$OFFGIT_DIR/logs" "$OFFGIT_DIR/thoughts"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/sync_engine.py" ]; then
    cp -rf "$SCRIPT_DIR"/*.py "$OFFGIT_DIR/" 2>/dev/null || true
    cp -rf "$SCRIPT_DIR"/config.yaml "$OFFGIT_DIR/" 2>/dev/null || true
    cp -rf "$SCRIPT_DIR"/FIXES.md "$OFFGIT_DIR/" 2>/dev/null || true
    cp -rf "$SCRIPT_DIR"/README.md "$OFFGIT_DIR/" 2>/dev/null || true
else
    echo "Downloading latest offGIT harness files from GitHub..."
    RAW_BASE="https://raw.githubusercontent.com/MaheswarPraveen/offgit/main"
    for f in sync_engine.py prompt_counter.py watcher.py debounce_trigger.py config.yaml FIXES.md README.md; do
        curl -fsSL "$RAW_BASE/$f" -o "$OFFGIT_DIR/$f"
    done
fi

# Install Python dependencies
echo "Installing Python dependencies (pyyaml, watchdog)..."
python3 -m pip install --quiet pyyaml watchdog 2>/dev/null || python3 -m pip install --quiet --break-system-packages pyyaml watchdog 2>/dev/null || pip3 install --quiet pyyaml watchdog

# 5. Deploy Global AI Rules
echo "[5/6] Injecting global IDE rules (Antigravity, Claude, Cursor, Codex)..."

GEMINI_DIR="$HOME/.gemini/config"
SCRATCH_DIR="$HOME/.gemini/antigravity/scratch"
mkdir -p "$GEMINI_DIR/rules" "$SCRATCH_DIR" "$HOME/.claude" "$HOME/.cursor" "$HOME/.config/opencode"

RULE_TEXT="# offGIT Global Integration Rule

You are operating with **offGIT**, an ambient agentic development harness running in the background.

## Automatic Instructions for Every Session

1. **Dedicated Project Subdirectory**:
   - When the user starts a project or discusses a concept, ensure work is associated with a dedicated subdirectory (e.g. $SCRATCH_DIR/<project-name>).

2. **Context Ingestion on Startup**:
   - If a CONTEXT.md file exists in the active project root, read it immediately to ingest the current active state, recent directives, and open architectural decisions.

3. **Prompt & Context Logging**:
   - For every task, project turn, or significant user directive, ensure the project directory has its prompt and reasoning recorded by executing:
     python3 ~/.offgit/prompt_counter.py --repo \"<project_directory>\" --tool antigravity --prompt \"<user_request>\" --thinking \"<your_architectural_rationale>\"
   - This keeps CONTEXT.md updated in real-time (< 1ms) and increments the milestone counter.

4. **In-Chat Milestone Inception (Prompts 5, 15, 30, 60)**:
   - When prompt_counter.py returns [offGIT MILESTONE <count>], proactively ask the user directly in your chat response using the question and suggested name.
   - When the user confirms or gives a custom name, execute:
     python3 ~/.offgit/sync_engine.py --repo \"<project_directory>\" --scaffold --name \"<confirmed_name>\"

5. **Token-Efficient Self-Healing & Error Reference (FIXES.md)**:
   - When diagnosing errors or debugging offGIT behavior, consult ~/.offgit/FIXES.md (or run python3 ~/.offgit/sync_engine.py --fix) first before performing broad search to achieve 1-shot fixes with minimal token usage."

echo "$RULE_TEXT" > "$GEMINI_DIR/GEMINI.md"
echo "$RULE_TEXT" > "$GEMINI_DIR/AGENTS.md"
echo "$RULE_TEXT" > "$GEMINI_DIR/rules/offgit.md"
echo "$RULE_TEXT" > "$SCRATCH_DIR/GEMINI.md"
echo "$RULE_TEXT" > "$SCRATCH_DIR/AGENTS.md"
echo "$RULE_TEXT" > "$HOME/.config/opencode/OPENCODE.md"

if [ ! -f "$HOME/.claude/settings.json" ]; then
    cat << 'EOF' > "$HOME/.claude/settings.json"
{
  "hooks": {
    "UserPromptSubmit": "python3 ~/.offgit/prompt_counter.py --repo \"$PWD\" --tool claude-code --prompt \"$PROMPT\"",
    "Stop": "python3 ~/.offgit/sync_engine.py --repo \"$PWD\" --trigger claude-code"
  }
}
EOF
fi

cat << 'EOF' > "$HOME/.cursorrules"
# offGIT Cursor Integration Rule
- Ingest CONTEXT.md on startup for current project directives and technical rationale.
- Refer to DEVLOG.md for change history.
- Run python3 ~/.offgit/sync_engine.py --fix for error recovery.
EOF

# 6. Configure Autostart Daemon (LaunchAgent on macOS / systemd on Linux)
echo "[6/6] Registering and starting background watcher daemon..."

pkill -f "watcher.py" >/dev/null 2>&1 || true

if [ "$OS_TYPE" = "Darwin" ]; then
    PLIST_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$PLIST_DIR"
    PLIST_PATH="$PLIST_DIR/com.offgit.watcher.plist"
    
    cat << EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.offgit.watcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(which python3)</string>
        <string>$HOME/.offgit/watcher.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/.offgit/logs/engine.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.offgit/logs/engine.log</string>
</dict>
</plist>
EOF
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    launchctl load "$PLIST_PATH"
    echo "Registered macOS LaunchAgent: com.offgit.watcher"

else
    USE_SYSTEMD=false
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl --user is-system-running >/dev/null 2>&1 || systemctl --user status >/dev/null 2>&1; then
            USE_SYSTEMD=true
        fi
    fi

    if [ "$USE_SYSTEMD" = true ]; then
        SERVICE_DIR="$HOME/.config/systemd/user"
        mkdir -p "$SERVICE_DIR"
        SERVICE_PATH="$SERVICE_DIR/offgit.service"
        
        cat << EOF > "$SERVICE_PATH"
[Unit]
Description=offGIT Background File Watcher & 10-Minute Batch Engine
After=network.target

[Service]
Type=simple
ExecStart=$(which python3) $HOME/.offgit/watcher.py
Restart=always
RestartSec=5
StandardOutput=append:$HOME/.offgit/logs/engine.log
StandardError=append:$HOME/.offgit/logs/engine.log

[Install]
WantedBy=default.target
EOF
        systemctl --user daemon-reload || true
        systemctl --user enable --now offgit.service || true
        echo "Registered Linux systemd user service: offgit.service"
    else
        nohup python3 "$HOME/.offgit/watcher.py" >> "$HOME/.offgit/logs/engine.log" 2>&1 &
        echo "Started background daemon via nohup."
        AUTOSTART_CMD='pgrep -f "watcher.py" >/dev/null 2>&1 || nohup python3 "$HOME/.offgit/watcher.py" >> "$HOME/.offgit/logs/engine.log" 2>&1 &'
        if [ -f "$HOME/.bashrc" ] && ! grep -q "watcher.py" "$HOME/.bashrc"; then
            echo "$AUTOSTART_CMD" >> "$HOME/.bashrc"
        elif [ -f "$HOME/.profile" ] && ! grep -q "watcher.py" "$HOME/.profile"; then
            echo "$AUTOSTART_CMD" >> "$HOME/.profile"
        fi
    fi
fi

echo ""
echo "==================================================="
echo " [SUCCESS] offGIT is authenticated, running, and ready!"
echo "==================================================="
echo ""
echo "Verify status at any time by running:"
echo "  python3 ~/.offgit/sync_engine.py --fix"
echo ""