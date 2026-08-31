$ErrorActionPreference = "Continue"

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "         offGIT - One-Click Setup & Launch         " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verify / Install Package Dependencies via Winget
function Ensure-Package($cmd, $id, $label) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "[1/5] Installing $label via winget..." -ForegroundColor Yellow
        winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements
    } else {
        Write-Host "[1/5] $label is installed." -ForegroundColor Green
    }
}

Ensure-Package "git" "Git.Git" "Git"
Ensure-Package "gh" "GitHub.cli" "GitHub CLI"
Ensure-Package "node" "OpenJS.NodeJS.LTS" "Node.js"

# 2. Refresh Environment Path
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# 3. Setup Python Runtime & Dependencies
Write-Host "`n[2/5] Configuring Python environment and dependencies..." -ForegroundColor Yellow
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "Installing Python 3.12..." -ForegroundColor Yellow
    winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

$offgitHome = "$env:USERPROFILE\.offgit"
New-Item -ItemType Directory -Path $offgitHome, "$offgitHome\logs", "$offgitHome\thoughts" -Force | Out-Null
Copy-Item "$PSScriptRoot\*" $offgitHome -Recurse -Force -ErrorAction SilentlyContinue

pip install pyyaml watchdog -q

# 4. GitHub Authentication Gate (Interactive Web Flow)
Write-Host "`n[3/5] Verifying GitHub authentication..." -ForegroundColor Yellow
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[offGIT AUTH REQUIRED] Opening your browser to authorize GitHub CLI..." -ForegroundColor Magenta
    Write-Host "Please complete the login in the browser window that opens." -ForegroundColor Cyan
    gh auth login --web --git-protocol https -h github.com
}
Write-Host "GitHub CLI is authenticated and ready." -ForegroundColor Green

# 5. Global IDE Integration Rules
Write-Host "`n[4/5] Installing global IDE integration rules..." -ForegroundColor Yellow
$geminiConfig = "$env:USERPROFILE\.gemini\config"
$scratchDir = "$env:USERPROFILE\.gemini\antigravity\scratch"
New-Item -ItemType Directory -Path "$geminiConfig\rules", $scratchDir -Force | Out-Null

$ruleText = @"
# offGIT Global Integration Rule

You are operating with **offGIT**, an ambient agentic development harness running in the background.

## Automatic Instructions for Every Session

1. **Dedicated Project Subdirectory**:
   - When the user starts a project or discusses a concept (e.g. ESP32, Godot game, web app), ensure work is associated with a dedicated subdirectory (e.g. `C:\Users\xczma\.gemini\antigravity\scratch\<project-name>`).

2. **Context Ingestion on Startup**:
   - If a `CONTEXT.md` file exists in the active project root, read it immediately to ingest the current active state, recent directives, and open architectural decisions.

3. **Prompt & Context Logging**:
   - For every task, project turn, or significant user directive, ensure the project directory has its prompt and reasoning recorded by executing:
     `python "$env:USERPROFILE\.offgit\prompt_counter.py" --repo "<project_directory>" --tool antigravity --prompt "<user_request>" --thinking "<your_architectural_rationale>"`
   - This keeps `CONTEXT.md` updated in real-time (< 1ms) and increments the milestone counter.

4. **In-Chat Milestone Inception (Prompts 5, 15, 30, 60)**:
   - When `prompt_counter.py` returns `[offGIT MILESTONE <count>]`, proactively ask the user directly in your chat response using the question and suggested name (e.g. *"Looks like we've reached milestone 5 for this project — want me to create and scaffold a GitHub repository for `<suggested-name>`?"*).
   - When the user confirms or gives a custom name, execute:
     `python "$env:USERPROFILE\.offgit\sync_engine.py" --repo "<project_directory>" --scaffold --name "<confirmed_name>"`
"@

[System.IO.File]::WriteAllText("$geminiConfig\GEMINI.md", $ruleText, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText("$geminiConfig\AGENTS.md", $ruleText, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText("$geminiConfig\rules\offgit.md", $ruleText, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText("$scratchDir\GEMINI.md", $ruleText, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText("$scratchDir\AGENTS.md", $ruleText, [System.Text.UTF8Encoding]::new($false))

# 6. Windows Startup Registration & Background Launch
Write-Host "`n[5/5] Registering silent autostart on logon and launching daemon..." -ForegroundColor Yellow
$startupFolder = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$startupVbs = "$startupFolder\offGIT.vbs"

$pythonExe = (Get-Command python).Source
$pythonDir = Split-Path $pythonExe
$pythonw = Join-Path $pythonDir "pythonw.exe"
if (-not (Test-Path $pythonw)) { $pythonw = $pythonExe }

$watcherScript = "$offgitHome\watcher.py"

$vbsContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """$pythonw"" ""$watcherScript""", 0, False
"@

[System.IO.File]::WriteAllText($startupVbs, $vbsContent, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText("$offgitHome\start_offgit.vbs", $vbsContent, [System.Text.UTF8Encoding]::new($false))

# Kill any previous instance and start fresh
Get-Process -Name pythonw -ErrorAction SilentlyContinue | Stop-Process -Force
wscript.exe "$startupVbs"

Write-Host "`n===================================================" -ForegroundColor Green
Write-Host " [SUCCESS] offGIT is installed and running!       " -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host "offGIT is now monitoring your development environment in the background."
Write-Host "Every project you create in Antigravity, Cursor, Claude Code, Godot, or Arduino IDE"
Write-Host "will be continuously documented, synced, and version-controlled automatically."
