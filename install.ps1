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

# Handle local execution vs remote irm | iex execution
if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "sync_engine.py"))) {
    Write-Host "Deploying files from local clone..." -ForegroundColor Yellow
    Get-ChildItem -Path $PSScriptRoot -File | ForEach-Object {
        Copy-Item $_.FullName -Destination $offgitHome -Force
    }
} else {
    Write-Host "Downloading latest offGIT harness files from GitHub..." -ForegroundColor Yellow
    $rawBase = "https://raw.githubusercontent.com/MaheswarPraveen/offgit/main"
    $files = @("sync_engine.py", "prompt_counter.py", "watcher.py", "debounce_trigger.py", "config.yaml", "FIXES.md", "README.md")
    foreach ($f in $files) {
        Invoke-WebRequest -Uri "$rawBase/$f" -OutFile "$offgitHome\$f" -UseBasicParsing
    }
}

# Install Python runtime libraries
python -m pip install pyyaml watchdog --quiet

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
   - When `prompt_counter.py` returns `[offGIT MILESTONE <count>]`, proactively ask the user directly in your chat response using the question and suggested name.
   - When the user confirms or gives a custom name, execute:
     `python "$env:USERPROFILE\.offgit\sync_engine.py" --repo "<project_directory>" --scaffold --name "<confirmed_name>"`

5. **Token-Efficient Self-Healing & Error Reference (FIXES.md)**:
   - When diagnosing errors or debugging offGIT behavior, consult `~/.offgit/FIXES.md` (or run `python "$env:USERPROFILE\.offgit\sync_engine.py" --fix`) first before performing broad search to achieve 1-shot fixes with minimal token usage.
"@

[System.IO.File]::WriteAllText("$geminiConfig\GEMINI.md", $ruleText, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText("$geminiConfig\AGENTS.md", $ruleText, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText("$geminiConfig\rules\offgit.md", $ruleText, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText("$scratchDir\GEMINI.md", $ruleText, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText("$scratchDir\AGENTS.md", $ruleText, [System.Text.UTF8Encoding]::new($false))

# 6. Windows Startup Registration & Silent Background Launch via WMI
Write-Host "`n[5/5] Registering silent autostart on logon and launching daemon..." -ForegroundColor Yellow
$appData = if ($env:APPDATA) { $env:APPDATA } else { "$env:USERPROFILE\AppData\Roaming" }
$startupFolder = "$appData\Microsoft\Windows\Start Menu\Programs\Startup"
if (-not (Test-Path $startupFolder)) {
    New-Item -ItemType Directory -Path $startupFolder -Force | Out-Null
}
$startupVbs = "$startupFolder\offGIT.vbs"

$pythonExe = (Get-Command python).Source
$pythonDir = Split-Path $pythonExe
$pythonw = Join-Path $pythonDir "pythonw.exe"
if (-not (Test-Path $pythonw)) { $pythonw = $pythonExe }

$vbsContent = @"
Set objWMIService = GetObject("winmgmts:\\.\root\cimv2")
Set objProcess = objWMIService.Get("Win32_Process")
intReturn = objProcess.Create("""$pythonw"" ""$offgitHome\watcher.py""", Null, Null, intProcessID)
"@

[System.IO.File]::WriteAllText($startupVbs, $vbsContent, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText("$offgitHome\start_offgit.vbs", $vbsContent, [System.Text.UTF8Encoding]::new($false))

# Kill previous instance and start clean detached daemon
Get-Process -Name pythonw -ErrorAction SilentlyContinue | Stop-Process -Force
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = """$pythonw"" ""$offgitHome\watcher.py"""} | Out-Null

Write-Host "`n===================================================" -ForegroundColor Green
Write-Host " [SUCCESS] offGIT is installed and running!       " -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host "offGIT is now monitoring your development environment in the background."
Write-Host "Every project you create in Antigravity, Cursor, Claude Code, Godot, or Arduino IDE"
Write-Host "will be continuously documented, synced, and version-controlled automatically.`n"
Write-Host "To verify status at any time, run:"
Write-Host "  python ""$env:USERPROFILE\.offgit\sync_engine.py"" --fix`n"