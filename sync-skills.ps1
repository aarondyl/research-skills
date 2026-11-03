param(
    [string]$SkillsPath = (Join-Path $env:USERPROFILE '.codex/skills'),
    [switch]$Push
)
$ErrorActionPreference = 'Stop'
$repoPath = $PSScriptRoot
$sourcePath = (Resolve-Path -LiteralPath $SkillsPath).Path
$destinationPath = Join-Path $repoPath 'skills'
$allowedExtensions = @('.md', '.py', '.js', '.cjs', '.mjs', '.json', '.yaml', '.yml', '.txt', '.html', '.css', '.ps1', '.toml')
foreach ($skill in Get-ChildItem -LiteralPath $sourcePath -Directory) {
    if ($skill.Name.StartsWith('.') -or -not (Test-Path -LiteralPath (Join-Path $skill.FullName 'SKILL.md'))) { continue }
    foreach ($file in Get-ChildItem -LiteralPath $skill.FullName -Recurse -File) {
        $relative = $file.FullName.Substring($skill.FullName.Length + 1)
        if ($relative -match '(^|[\\/])(\.[^\\/]+|__pycache__|node_modules)([\\/]|$)') { continue }
        if ($file.Extension -notin $allowedExtensions) { continue }
        if ($file.Name -match '(?i)^(credentials|secrets|auth|token|tokens)\.') { continue }
        $content = [System.IO.File]::ReadAllText($file.FullName)
        if ($content -match 'gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----') {
            throw "Potential secret detected; inspect before upload: $relative"
        }
        $target = Join-Path (Join-Path $destinationPath $skill.Name) $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $target
    }
}
Write-Host 'Local skill backup updated.'
if ($Push) {
    & git -C $repoPath add -- skills README.md .gitignore sync-skills.ps1
    if ($LASTEXITCODE -ne 0) { throw 'Git staging failed' }
    & git -C $repoPath diff --cached --quiet
    $diffExit = $LASTEXITCODE
    if ($diffExit -eq 1) {
        & git -C $repoPath commit -m 'Back up custom Codex skills'
        if ($LASTEXITCODE -ne 0) { throw 'Git commit failed' }
    } elseif ($diffExit -ne 0) { throw 'Git diff failed' }
    & git -C $repoPath push origin main
    if ($LASTEXITCODE -ne 0) { throw 'Push failed; local commit retained. Inspect remote changes before retrying.' }
}
