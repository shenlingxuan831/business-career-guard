$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $root "skills\finance-security-guard"
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$targetRoot = Join-Path $codexHome "skills"
$target = Join-Path $targetRoot "finance-security-guard"

if (-not (Test-Path (Join-Path $source "SKILL.md"))) {
    throw "Skill source not found: $source"
}

New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
if (Test-Path $target) {
    $resolvedRoot = [System.IO.Path]::GetFullPath($targetRoot)
    $resolvedTarget = [System.IO.Path]::GetFullPath($target)
    if (-not $resolvedTarget.StartsWith($resolvedRoot)) {
        throw "Unexpected install target: $resolvedTarget"
    }
    Remove-Item -LiteralPath $target -Recurse -Force
}
Copy-Item -LiteralPath $source -Destination $target -Recurse

Write-Host "Installed 金融保安.skill to $target"
Write-Host "Run .\start.ps1 to open the local workbench."

