param([string]$GamePath, [string]$LiveSplitPath, [switch]$NoLaunch,
      [string]$ShortcutPath = (Join-Path ([Environment]::GetFolderPath('Desktop')) 'TUNG LiveSplit.lnk'))
$ErrorActionPreference = 'Stop'

function Select-Executable([string]$Title, [string]$Filter) {
    Add-Type -AssemblyName System.Windows.Forms
    $picker = New-Object System.Windows.Forms.OpenFileDialog
    $picker.Title = $Title
    $picker.Filter = $Filter
    try {
        if ($picker.ShowDialog() -ne 'OK') { throw 'Setup cancelled. No files were installed.' }
        return $picker.FileName
    } finally { $picker.Dispose() }
}

function Find-Tung {
    $steam = (Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue).SteamPath
    if (-not $steam) { $steam = Join-Path ${env:ProgramFiles(x86)} 'Steam' }
    $libraries = @($steam)
    $libraryFile = Join-Path $steam 'steamapps\libraryfolders.vdf'
    if (Test-Path -LiteralPath $libraryFile) {
        foreach ($match in [regex]::Matches([IO.File]::ReadAllText($libraryFile), '"path"\s+"([^"]+)"')) {
            $libraries += $match.Groups[1].Value.Replace('\\', '\')
        }
    }
    foreach ($library in ($libraries | Select-Object -Unique)) {
        $manifest = Join-Path $library 'steamapps\appmanifest_4341400.acf'
        if (Test-Path -LiteralPath $manifest) {
            $match = [regex]::Match([IO.File]::ReadAllText($manifest), '"installdir"\s+"([^"]+)"')
            if ($match.Success) {
                $candidate = Join-Path $library ('steamapps\common\' + $match.Groups[1].Value)
                if (Test-Path -LiteralPath (Join-Path $candidate 'TUNG\Binaries\Win64\TUNG-Win64-Shipping.exe')) { return $candidate }
            }
        }
    }
}

try {
    Write-Host 'Wood LiveSplit Setup' -ForegroundColor Cyan
    foreach ($name in @('WoodLiveSplit.tungmod','LiveSplit.WoodTUNG.dll','Wood-TUNG.lsl','TUNG-AnyPercent.lss')) {
        if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $name))) { throw "Missing $name. Package WoodLiveSplit.lua as WoodLiveSplit.tungmod and place it beside this installer. Keep the DLL, layout and splits beside it too." }
    }
    if (-not $GamePath) { $GamePath = Find-Tung }
    if (-not $GamePath) {
        $gameExe = Select-Executable 'Select TUNG.exe in your game installation' 'TUNG executable (TUNG.exe)|TUNG.exe'
        $GamePath = Split-Path -Parent $gameExe
    }
    if (-not (Test-Path -LiteralPath (Join-Path $GamePath 'TUNG\Binaries\Win64\TUNG-Win64-Shipping.exe'))) { throw 'The selected folder is not a TUNG installation.' }
    if (-not (Test-Path -LiteralPath (Join-Path $GamePath 'TUNG\Binaries\Win64\ue4ss\Mods\WoodRuntime\Scripts\main.lua'))) { throw 'Install the Wood mod loader first, then run this setup again.' }
    if (-not $LiveSplitPath) {
        $running = Get-Process LiveSplit -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($running) { $LiveSplitPath = Split-Path -Parent $running.Path }
    }
    if (-not $LiveSplitPath) {
        if (Test-Path -LiteralPath $ShortcutPath) {
            $existingShortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($ShortcutPath)
            if (Test-Path -LiteralPath $existingShortcut.TargetPath) { $LiveSplitPath = Split-Path -Parent $existingShortcut.TargetPath }
        }
    }
    if (-not $LiveSplitPath) {
        $liveExe = Select-Executable 'Select your LiveSplit.exe (one-time setup)' 'LiveSplit executable (LiveSplit.exe)|LiveSplit.exe'
        $LiveSplitPath = Split-Path -Parent $liveExe
    }
    if (-not (Test-Path -LiteralPath (Join-Path $LiveSplitPath 'LiveSplit.exe'))) { throw 'The selected folder does not contain LiveSplit.exe.' }
    if (Get-Process LiveSplit -ErrorAction SilentlyContinue) { throw 'Close LiveSplit first so your current run can be saved, then run setup again.' }
    if (Get-Process TUNG-Win64-Shipping -ErrorAction SilentlyContinue) { throw 'Close TUNG before installing the updated mod, then run setup again.' }

    $mods = Join-Path $GamePath 'Mods'
    $components = Join-Path $LiveSplitPath 'Components'
    $bundle = Join-Path $LiveSplitPath 'WoodTUNG'
    foreach ($folder in @($mods,$components,$bundle)) { New-Item -ItemType Directory -Path $folder -Force | Out-Null }
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'WoodLiveSplit.tungmod') -Destination (Join-Path $mods 'WoodLiveSplit.tungmod') -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'LiveSplit.WoodTUNG.dll') -Destination (Join-Path $components 'LiveSplit.WoodTUNG.dll') -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Wood-TUNG.lsl') -Destination (Join-Path $bundle 'Wood-TUNG.lsl') -Force
    $splits = Join-Path $bundle 'TUNG-AnyPercent.lss'
    # Re-running setup preserves the runner's saved splits and PBs.
    if (-not (Test-Path -LiteralPath $splits)) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'TUNG-AnyPercent.lss') -Destination $splits }
    [xml]$run = [IO.File]::ReadAllText($splits)
    $run.SelectSingleNode('/Run/LayoutPath').InnerText = [string](Join-Path $bundle 'Wood-TUNG.lsl')
    $run.Save($splits)

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = Join-Path $LiveSplitPath 'LiveSplit.exe'
    $shortcut.WorkingDirectory = $LiveSplitPath
    $shortcut.Arguments = '-s "' + $splits + '" -l "' + (Join-Path $bundle 'Wood-TUNG.lsl') + '"'
    $shortcut.Save()
    Write-Host 'Installed! Use the TUNG LiveSplit desktop shortcut, then launch TUNG normally.' -ForegroundColor Green
    Write-Host 'Start a normal Speedrun attempt. Valves split when you interact with them.'
    if (-not $NoLaunch) {
        Start-Process -FilePath (Join-Path $LiveSplitPath 'LiveSplit.exe') -WorkingDirectory $LiveSplitPath -ArgumentList $shortcut.Arguments -WindowStyle Hidden
    }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
