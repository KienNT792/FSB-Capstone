<#
.SYNOPSIS
Rebuild Sprint 1 generated data from the current repository state.

.DESCRIPTION
Runs the Sprint 1 data workflow end-to-end with an explicit project virtualenv
Python. This script is intended for machines that may have different local
generated artifacts, such as data/test_history.db or timestamped rows.

It never calls global pip or global python for project scripts.

.EXAMPLE
.\scripts\run_sprint1.ps1

.EXAMPLE
.\scripts\run_sprint1.ps1 -InstallRequirements -PopulateTimestamps
#>

[CmdletBinding()]
param(
    [string]$VenvPython = ".\.venv\Scripts\python.exe",
    [string]$RtpPath = "data\repos\rtp-torrent",
    [string]$SummaryPath = "data\rtp-project-summary.md",
    [string]$DbPath = "data\test_history.db",
    [string]$GitRoot = "data\git-repos",
    [double]$FailureRateThreshold = 0.01,
    [int]$MinBuilds = 100,
    [int]$ProjectLimit = 5,
    [int]$MinSelected = 3,
    [double]$MinShaCoverage = 70.0,
    [double]$MinRowCoverage = 70.0,
    [switch]$InstallRequirements,
    [switch]$SkipTests,
    [switch]$SkipTimestampDryRun,
    [switch]$PopulateTimestamps,
    [switch]$AllowTimestampFailure,
    [string[]]$TimestampProjects = @()
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Checked {
    param(
        [string]$Label,
        [scriptblock]$Command
    )
    Write-Step $Label
    & $Command
    if ($LASTEXITCODE -ne $null -and $LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

function Invoke-Python {
    param([string[]]$Arguments)
    & $VenvPython @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE`: $($Arguments -join ' ')"
    }
}

function Resolve-RelativePath {
    param([string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }
    return Join-Path (Get-Location) $Path
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $RepoRoot

try {
    Write-Step "Repository"
    Write-Host "Root: $RepoRoot"

    Write-Step "Virtualenv safety check"
    if (-not (Test-Path $VenvPython)) {
        throw @"
Virtualenv Python was not found: $VenvPython

Create a local venv first, for example:
  uv venv --cache-dir .\.uv-cache --python 3.11 --seed .venv
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Do not run project scripts with global python or global pip.
"@
    }
    & $VenvPython -c "import sys; print(sys.version); print(sys.executable)"
    if ($LASTEXITCODE -ne 0) {
        throw "Venv Python is present but not runnable: $VenvPython"
    }

    if ($InstallRequirements) {
        Invoke-Checked "Install requirements inside .venv" {
            & $VenvPython -m pip install -r requirements.txt
        }
    }

    Invoke-Python @(
        "-c",
        "import sys, duckdb; import git; print('Runtime OK:', sys.version.split()[0])"
    )

    Write-Step "Input data checks"
    if (-not (Test-Path $RtpPath)) {
        throw "RTPTorrent data root not found: $RtpPath"
    }
    if (-not (Test-Path (Join-Path $RtpPath "tr_all_built_commits.csv"))) {
        throw "Mapping file not found: $(Join-Path $RtpPath 'tr_all_built_commits.csv')"
    }
    Write-Host "RTPTorrent root: $RtpPath"

    Invoke-Checked "Select RTPTorrent projects" {
        & $VenvPython data\scripts\select_rtp_projects.py `
            --rtp-path $RtpPath `
            --summary-path $SummaryPath `
            --failure-rate-threshold $FailureRateThreshold `
            --min-builds $MinBuilds `
            --limit $ProjectLimit `
            --min-selected $MinSelected
    }

    Invoke-Checked "Load selected projects into DuckDB" {
        & $VenvPython data\scripts\load_rtp_dataset.py `
            --db-path $DbPath `
            --rtp-path $RtpPath `
            --summary-path $SummaryPath `
            --auto `
            --force
    }

    if (-not $SkipTests) {
        Invoke-Checked "Run Sprint 1/timestamp unit tests" {
            & $VenvPython -m pytest tests\test_add_timestamps.py
        }
    }

    Invoke-Checked "DuckDB smoke summary" {
        & $VenvPython -c @"
import duckdb
con = duckdb.connect(r'$DbPath')
rows = con.execute(
    '''
    SELECT repo,
           COUNT(*) AS rows,
           SUM(commit_sha IS NOT NULL) AS mapped_rows,
           SUM(timestamp IS NOT NULL) AS timestamped_rows,
           SUM(job_sequence IS NOT NULL) AS sequenced_rows
    FROM test_runs
    GROUP BY repo
    ORDER BY repo
    '''
).fetchall()
for row in rows:
    print(row)
total = con.execute('SELECT COUNT(*) FROM test_runs').fetchone()[0]
if total < 10000:
    raise SystemExit(f'Expected at least 10000 test_runs rows, got {total}')
con.close()
"@
    }

    if (-not $SkipTimestampDryRun) {
        if (-not (Test-Path $GitRoot)) {
            New-Item -ItemType Directory -Force $GitRoot | Out-Null
        }

        $timestampArgs = @(
            "scripts\add_timestamps.py",
            "--db-path", $DbPath,
            "--git-root", $GitRoot,
            "--min-sha-coverage", "$MinShaCoverage",
            "--min-row-coverage", "$MinRowCoverage"
        )

        if ($TimestampProjects.Count -gt 0) {
            $timestampArgs += "--projects"
            $timestampArgs += $TimestampProjects
        } else {
            $timestampArgs += "--auto"
        }

        $dryRunArgs = $timestampArgs + "--dry-run"
        Write-Step "Timestamp coverage dry-run"
        & $VenvPython @dryRunArgs
        $dryRunExit = $LASTEXITCODE
        if ($dryRunExit -ne 0 -and -not $AllowTimestampFailure) {
            throw "Timestamp dry-run failed with exit code $dryRunExit. Use -AllowTimestampFailure to continue when an archived repo is unresolved."
        }

        if ($PopulateTimestamps) {
            Write-Step "Populate timestamps"
            & $VenvPython @timestampArgs
            $timestampExit = $LASTEXITCODE
            if ($timestampExit -ne 0 -and -not $AllowTimestampFailure) {
                throw "Timestamp population failed with exit code $timestampExit."
            }
        }
    }

    Write-Step "Done"
    Write-Host "Sprint 1 artifacts regenerated:"
    Write-Host "  Summary: $SummaryPath"
    Write-Host "  DuckDB:   $DbPath"
    Write-Host ""
    Write-Host "Useful next commands:"
    Write-Host "  .\.venv\Scripts\python.exe scripts\add_timestamps.py --db-path $DbPath --git-root $GitRoot --auto --dry-run"
    Write-Host "  .\.venv\Scripts\python.exe -m pytest tests\"
}
finally {
    Pop-Location
}
