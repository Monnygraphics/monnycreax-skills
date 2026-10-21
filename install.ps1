# Installs MonnyCreaX skills into ~/.claude/skills.
#   .\install.ps1 reel-editor humanizer
#   .\install.ps1 -Category video-editing
#   .\install.ps1 -All [-Force]
[CmdletBinding(PositionalBinding = $false)]
param(
  [Parameter(Position = 0, ValueFromRemainingArguments = $true)][string[]]$Names,
  [string]$Category,
  [switch]$All,
  [switch]$Force,
  [switch]$List
)
$ErrorActionPreference = 'Stop'
$root = Join-Path $PSScriptRoot 'skills'
$dest = Join-Path $HOME '.claude\skills'
$skills = Get-ChildItem $root -Directory | ForEach-Object {
  $cat = $_.Name; Get-ChildItem $_.FullName -Directory | ForEach-Object { [pscustomobject]@{ Name = $_.Name; Category = $cat; Path = $_.FullName } }
}

if ($List -or (-not $All -and -not $Category -and -not $Names)) {
  $skills | Sort-Object Category, Name | Format-Table Name, Category -AutoSize
  Write-Host "Usage: .\install.ps1 <name> [<name>...] | -Category <category> | -All   (add -Force to overwrite)"
  return
}

$pick = if ($All) { $skills }
        elseif ($Category) { $skills | Where-Object Category -eq $Category }
        else { $skills | Where-Object { $Names -contains $_.Name } }
if ($Names) { $Names | Where-Object { $skills.Name -notcontains $_ } | ForEach-Object { Write-Warning "No skill named '$_' (run .\install.ps1 -List)" } }
if (-not $pick) { Write-Warning 'Nothing to install.'; return }

New-Item -ItemType Directory -Force $dest | Out-Null
foreach ($s in $pick) {
  $target = Join-Path $dest $s.Name
  if (Test-Path $target) {
    if (-not $Force) { Write-Host "skip     $($s.Name) (already installed; use -Force to replace)"; continue }
    Remove-Item $target -Recurse -Force
  }
  Copy-Item $s.Path $target -Recurse
  Write-Host "installed $($s.Name)"
}
Write-Host "`nDone. Restart Claude Code to load the new skills."
