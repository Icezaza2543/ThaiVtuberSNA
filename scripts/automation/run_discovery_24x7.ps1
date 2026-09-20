param(
    [int]$IntervalMinutes = 180,
    [int]$DirectoryEveryCycles = 8,
    [int]$BrowserEveryCycles = 2,
    [int]$ExperimentalEveryCycles = 4,
    [int]$MaxResults = 20,
    [int]$MaxPages = 2,
    [switch]$Once
)

$ErrorActionPreference = "Continue"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Python virtual environment not found at $Python. Create .venv and install discovery dependencies first."
}

if ($IntervalMinutes -lt 30 -and -not $Once) {
    throw "IntervalMinutes must be at least 30 for continuous mode. Use -Once for a single test cycle."
}

$Scratch = Join-Path $Root "scratch\discovery-24x7"
$LogDir = Join-Path $Scratch "logs"
$BackupDir = Join-Path $Scratch "backups"
$RunDir = Join-Path $Scratch "runs"
New-Item -ItemType Directory -Force -Path $LogDir, $BackupDir, $RunDir | Out-Null

function Write-Log {
    param(
        [string]$Message,
        [string]$LogFile
    )
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Invoke-Python {
    param(
        [string[]]$Arguments,
        [string]$LogFile,
        [string]$StepName
    )
    Write-Log "START $StepName" $LogFile
    & $Python @Arguments 2>&1 | Tee-Object -FilePath $LogFile -Append
    $code = $LASTEXITCODE
    if ($code -eq 0) {
        Write-Log "OK    $StepName" $LogFile
        return $true
    }
    Write-Log "WARN  $StepName exited with code $code; continuing to next bounded step." $LogFile
    return $false
}

$cycle = 0
Write-Host ""
Write-Host "ThaiVirtualCreatorRegistry 24/7 discovery loop"
Write-Host "Repo: $Root"
Write-Host "Python: $Python"
if ($Once) {
    Write-Host "Mode: ONE TEST CYCLE"
} else {
    Write-Host "Mode: CONTINUOUS every $IntervalMinutes minutes (directory every $DirectoryEveryCycles cycles)"
}
Write-Host "Press Ctrl+C at any time to stop safely."
Write-Host ""

while ($true) {
    $cycle += 1
    $Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $IsoStamp = Get-Date -Format "yyyy-MM-ddTHH-mm-ss"
    $LogFile = Join-Path $LogDir "cycle-$Stamp.log"
    $BackupFile = Join-Path $BackupDir "registry-$Stamp.json"
    $RawOutput = Join-Path $Root "intake\raw\$IsoStamp-local-vtuberthai-directory-new.jsonl"
    $RawSummary = "$RawOutput.summary.json"

    Write-Log "=== CYCLE $cycle ===" $LogFile

    if (Test-Path (Join-Path $Root "data\registry.json")) {
        Copy-Item (Join-Path $Root "data\registry.json") $BackupFile -Force
        Write-Log "Backup: $BackupFile" $LogFile
    }

    if ($Once -or (($DirectoryEveryCycles -gt 0) -and (($cycle % $DirectoryEveryCycles) -eq 0))) {
        Invoke-Python -LogFile $LogFile -StepName "Hub VTuber Thai directory diff" -Arguments @(
            "scripts/collect/collect_vtuberthai_directory.py",
            "--workers", "3",
            "--output", $RawOutput,
            "--summary", $RawSummary
        ) | Out-Null

        if (Test-Path $RawSummary) {
            try {
                $DirectorySummary = Get-Content $RawSummary -Raw | ConvertFrom-Json
                Write-Log (
                    "Directory yield: profiles={0}, profiles_with_new_accounts={1}, " +
                    "new_account_observations={2}" -f
                    $DirectorySummary.profiles_discovered,
                    $DirectorySummary.profiles_with_new_accounts,
                    $DirectorySummary.emitted_rows
                ) $LogFile
            } catch {
                Write-Log "WARN  Could not parse directory summary: $($_.Exception.Message)" $LogFile
            }
        }
    } else {
        Write-Log "SKIP  directory crawl this cycle" $LogFile
    }

    if ($Once -or (($BrowserEveryCycles -gt 0) -and (($cycle % $BrowserEveryCycles) -eq 0))) {
        $CoreOutput = Join-Path $RunDir "core-$Stamp.json"
        Invoke-Python -LogFile $LogFile -StepName "Core browser discovery: YouTube/Twitch/TikTok/GankNow" -Arguments @(
            "-m", "registry", "discover-all",
            "--headless",
            "--platform", "youtube",
            "--platform", "twitch",
            "--platform", "tiktok",
            "--platform", "ganknow",
            "--max-results", "$MaxResults",
            "--max-pages", "$MaxPages",
            "--timeout", "30",
            "--output", $CoreOutput
        ) | Out-Null
    } else {
        Write-Log "SKIP  core browser discovery this cycle" $LogFile
    }

    if ($Once -or (($ExperimentalEveryCycles -gt 0) -and (($cycle % $ExperimentalEveryCycles) -eq 0))) {
        $ExperimentalOutput = Join-Path $RunDir "experimental-$Stamp.json"
        Invoke-Python -LogFile $LogFile -StepName "Experimental public surfaces: Facebook/Instagram/Kick" -Arguments @(
            "-m", "registry", "discover-all",
            "--headless",
            "--platform", "facebook",
            "--platform", "instagram",
            "--platform", "kick",
            "--query", "VTuberTH",
            "--query", "ThaiVTuber",
            "--query", "วีทูบเบอร์ไทย",
            "--query", "Virtual Creator Thailand",
            "--max-results", "$MaxResults",
            "--max-pages", "$MaxPages",
            "--timeout", "30",
            "--output", $ExperimentalOutput
        ) | Out-Null
    } else {
        Write-Log "SKIP  experimental browser discovery this cycle" $LogFile
    }

    Invoke-Python -LogFile $LogFile -StepName "Registry validation" -Arguments @(
        "-m", "registry", "validate"
    ) | Out-Null

    $SaturationOutput = Join-Path $RunDir "saturation-$Stamp.md"
    Invoke-Python -LogFile $LogFile -StepName "Saturation snapshot" -Arguments @(
        "scripts/maintenance/discovery_saturation.py",
        "--window-size", "12",
        "--start-batch", "240",
        "--format", "md",
        "--output", $SaturationOutput
    ) | Out-Null

    Write-Log "Cycle $cycle finished. Log: $LogFile" $LogFile
    Write-Log "Tracked changes are intentionally left local for review; this loop does not git push or merge." $LogFile

    if ($Once) {
        Write-Log "One-cycle test complete." $LogFile
        break
    }

    $sleepSeconds = $IntervalMinutes * 60
    Write-Log "Sleeping $IntervalMinutes minutes. Press Ctrl+C to stop." $LogFile
    Start-Sleep -Seconds $sleepSeconds
}
