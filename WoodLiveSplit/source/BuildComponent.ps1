param([Parameter(Mandatory=$true)][string]$LiveSplitPath)
$ErrorActionPreference = 'Stop'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$output = Join-Path (Split-Path -Parent $PSScriptRoot) 'LiveSplit.WoodTUNG.dll'
foreach ($name in @('LiveSplit.Core.dll','UpdateManager.dll')) {
    if (-not (Test-Path -LiteralPath (Join-Path $LiveSplitPath $name))) { throw "Missing $name in the selected LiveSplit folder." }
}
& $compiler /nologo /target:library /optimize+ "/out:$output" "/reference:$(Join-Path $LiveSplitPath 'LiveSplit.Core.dll')" "/reference:$(Join-Path $LiveSplitPath 'UpdateManager.dll')" (Join-Path $PSScriptRoot 'Component.cs')
if ($LASTEXITCODE -ne 0) { throw 'Component build failed.' }
Write-Host "Built $output"
