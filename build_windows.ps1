[CmdletBinding()]
param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'Build on native Windows x64.' }
Push-Location $PSScriptRoot
try {
    # Invoke native programs with argv arrays; PowerShell must check their exit codes.
    function Invoke-Python {
        param([string[]]$Arguments)
        & $Python @Arguments
        if ($LASTEXITCODE -ne 0) { throw "Python step failed ($LASTEXITCODE): $($Arguments -join ' ')" }
    }
    Invoke-Python -Arguments @('-c', @'
import platform, struct, sys
from importlib import metadata
assert sys.platform == 'win32' and struct.calcsize('P') == 8 and platform.machine().lower() in {'amd64','x86_64'}, 'Native Windows x64 Python required'
print(platform.platform(), platform.machine(), sys.version)
for name in ['PyInstaller','PySide6','numpy','ase','pydantic','cp2k-input-tools','PyYAML','psutil','packaging','Pillow']:
    print(name, metadata.version(name))
'@)
    Invoke-Python -Arguments @('-m', 'pip', 'check')
    # Remove stale distributable names, never user-selected files or projects.
    foreach ($name in @('CP2K_Studio_v1.0_Windows_x64_Portable.zip', 'SHA256SUMS.txt')) {
        $path = Join-Path $PSScriptRoot "dist/$name"
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path }
    }
    Invoke-Python -Arguments @('scripts/windows_build_assets.py')
    Invoke-Python -Arguments @('-m', 'PyInstaller', '--noconfirm', '--clean', '--distpath', 'dist', '--workpath', 'build/windows', 'CP2K_Studio_Windows.spec')
    Invoke-Python -Arguments @('scripts/windows_portable.py', 'dist/CP2K Studio')
    # windows_portable verifies PE/resources, launches a bounded smoke test, then
    # creates, extracts, hashes and verifies ZIP before publishing its final name.
    Get-Item -LiteralPath 'dist/CP2K_Studio_v1.0_Windows_x64_Portable.zip' | Select-Object FullName, Length
    Get-Content -LiteralPath 'dist/SHA256SUMS.txt'
} finally {
    Pop-Location
}
