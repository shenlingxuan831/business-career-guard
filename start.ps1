$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcher = Join-Path $root "skills\finance-security-guard\scripts\launch_guard.py"

$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    & $uv.Source run --python 3.12 $launcher --workspace $root
    exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "uv or Python 3.10+ is required. Install uv from https://docs.astral.sh/uv/ or install Python, then run this file again."
}

if ($python.Name -eq "py.exe") {
    & $python.Source -3 $launcher --workspace $root
} else {
    & $python.Source $launcher --workspace $root
}
