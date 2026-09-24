$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path 'D:\UTE_Advanced_OOP_Final_Project').Path
$nestedRoot = (Resolve-Path (Join-Path $projectRoot 'vehicle_sales_system')).Path
if ($nestedRoot -ne (Join-Path $projectRoot 'vehicle_sales_system')) { throw 'Unexpected nested path' }
$backupRoot = Join-Path ([IO.Path]::GetTempPath()) ('ignite-structure-backup-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $backupRoot | Out-Null
$backupRoot = (Resolve-Path $backupRoot).Path
$oldRoot = Join-Path $backupRoot 'old-root'
New-Item -ItemType Directory -Path $oldRoot | Out-Null
# Back up every nested file, including local configuration and uploads.
Copy-Item -LiteralPath $nestedRoot -Destination (Join-Path $backupRoot 'refactored') -Recurse
$manifest = Get-ChildItem -LiteralPath $nestedRoot -Recurse -File -Force | ForEach-Object {
    [pscustomobject]@{Path=$_.FullName.Substring($nestedRoot.Length+1); Hash=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash}
}
foreach ($entry in $manifest) {
    $saved = Join-Path (Join-Path $backupRoot 'refactored') $entry.Path
    if ((Get-FileHash -LiteralPath $saved -Algorithm SHA256).Hash -ne $entry.Hash) { throw 'Backup verification failed' }
}
$children = @(Get-ChildItem -LiteralPath $nestedRoot -Force)
foreach ($child in $children) {
    if ($child.Name -in @('.git','.venv','venv')) { throw 'Unexpected protected directory in nested project' }
    $target = Join-Path $projectRoot $child.Name
    if ($child.Name -eq '.env' -and (Test-Path -LiteralPath $target)) { throw 'Two local environment files require reconciliation' }
    if (Test-Path -LiteralPath $target) {
        $resolved = (Resolve-Path -LiteralPath $target).Path
        if (-not $resolved.StartsWith($projectRoot + '\') -or $resolved -eq (Join-Path $projectRoot '.git')) { throw 'Unsafe replacement target' }
        Move-Item -LiteralPath $resolved -Destination (Join-Path $oldRoot $child.Name)
    }
    if (-not $child.FullName.StartsWith($nestedRoot + '\')) { throw 'Unsafe source target' }
    Move-Item -LiteralPath $child.FullName -Destination $target
}
foreach ($entry in $manifest) {
    if ((Get-FileHash -LiteralPath (Join-Path $projectRoot $entry.Path) -Algorithm SHA256).Hash -ne $entry.Hash) { throw 'Promoted file verification failed' }
}
if (@(Get-ChildItem -LiteralPath $nestedRoot -Force).Count -ne 0) { throw 'Nested directory is not empty' }
Remove-Item -LiteralPath $nestedRoot
$manifest | ConvertTo-Json | Set-Content (Join-Path $projectRoot 'output\structure_fix\promoted-manifest.json')
$backupRoot | Set-Content (Join-Path $projectRoot 'output\structure_fix\backup-location.txt')
Write-Output ('Promoted and hash-verified ' + $manifest.Count + ' files. Backup: ' + $backupRoot)
