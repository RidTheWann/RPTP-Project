$ErrorActionPreference = 'Stop'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python was not found on PATH. Install Python 3 and retry.'
}
if (-not (Get-Command cl -ErrorAction SilentlyContinue)) {
    throw 'MSVC cl.exe was not found. Open Developer PowerShell for Visual Studio or an x64 Native Tools command prompt, then rerun.'
}

python tools/check_forbidden_artifacts.py --root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/rptp_gate0_spike.py --out build/gate0-msvc --compiler cl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host 'MSVC Gate 0 spike completed. Save the full command output and review build/gate0-msvc/report.json.'
