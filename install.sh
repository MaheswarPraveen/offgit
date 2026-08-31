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

install_package() {
    PKG=$1
    if command -v brew >/dev/null 2>&1; then
        brew install "$PKG" || true
    elif command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -qq && sudo apt-get install -y -qq "$PKG" || true
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y -q "$PKG" || true
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --noconfirm "$PKG" || true
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
        type -p curl >/dev/null || sudo apt install curl -y
        curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
        sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
        sudo apt update && sudo apt install gh -y
    else
        install_package github-cli
    fi
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Installing python3..."
    install_package python3
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
cp -rf "$SCRIPT_DIR"/*.py "$OFFGIT_DIR/" 2>/dev/null || true
cp -rf "$SCRIPT_DIR"/config.yaml "$OFFGIT_DIR/" 2>/dev/null || true
cp -rf "$SCRIPT_DIR"/FIXES.md "$OFFGIT_DIR/" 2>/dev/null || true
cp -rf "$SCRIPT_DIR"/README.md "$OFFGIT_DIR/" 2>/dev/null || true

# Install Python dependencies
echo "Installing Python dependencies (pyyaml, watchdog)..."
python3 -m pip install --quiet pyyaml watchdog 2>/dev/null || python3 -m pip install --quiet --break-system-packages pyyaml watchdog 2>/dev/null || pip3 install --quiet pyyaml watchdog

# 5. Deploy Global AI Rules
echo "[5/6] Injecting global IDE rules (Antigravity, Claude, Cursor, Codex)..."

# Claude Code
mkdir -p "$HOME/.claude"
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

# Cursor
mkdir -p "$HOME/.cursor"
cat << 'EOF' > "$HOME/.cursorrules"
# offGIT Cursor Integration Rule
- Ingest CONTEXT.md on startup for current project directives and technical rationale.
- Refer to DEVLOG.md for change history.
- Run python3 ~/.offgit/sync_engine.py --fix for error recovery.
EOF

# 6. Configure Autostart Daemon (LaunchAgent on macOS / systemd on Linux)
echo "[6/6] Registering and starting background watcher daemon..."

# Kill any existing instance
pkill -f "watcher.py" >/dev/null 2>&1 || true

if [ "$OS_TYPE" = "Darwin" ]; then
    # macOS LaunchAgent
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
    # Linux systemd user service or nohup fallback
    if command -v systemctl >/dev/null 2>&1; then
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
        systemctl --user daemon-reload
        systemctl --user enable --now offgit.service
        echo "Registered Linux systemd user service: offgit.service"
    else
        # Fallback background execution
        nohup python3 "$HOME/.offgit/watcher.py" >> "$HOME/.offgit/logs/engine.log" 2>&1 &
        echo "Started background daemon via nohup."
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