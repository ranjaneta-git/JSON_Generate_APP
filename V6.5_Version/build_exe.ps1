#Requires -Version 5.1

<#
.SYNOPSIS
    Build standalone Windows executable for Modbus Config Generator
.DESCRIPTION
    Automates the complete build process: doc conversion, PyInstaller build, packaging
.NOTES
    Requires: Python 3.8+, PyInstaller, Pandoc (optional for PDF)
.EXAMPLE
    .\build_exe.ps1
    .\build_exe.ps1 -Version "6.6.1" -SkipPDF
#>

param(
    [string]$Version = "6.6.0",
    [switch]$SkipPDF,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Modbus Config Generator - Build .EXE" -ForegroundColor Cyan
Write-Host "  Version: $Version" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Validate prerequisites
Write-Host "`n[1/9] Validating prerequisites..." -ForegroundColor Yellow

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found! Install Python 3.8+"
    exit 1
}

$pythonVersion = python --version 2>&1
Write-Host "   Python: $pythonVersion" -ForegroundColor Gray

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "   Installing PyInstaller..." -ForegroundColor Gray
    pip install pyinstaller
}

$pyinstallerVersion = pyinstaller --version 2>&1
Write-Host "   PyInstaller: $pyinstallerVersion" -ForegroundColor Gray

if (-not $SkipPDF -and -not (Get-Command pandoc -ErrorAction SilentlyContinue)) {
    Write-Warning "Pandoc not found. Skipping PDF conversion. Install from: https://pandoc.org"
    $SkipPDF = $true
}

if (-not $SkipPDF) {
    $pandocVersion = pandoc --version | Select-Object -First 1
    Write-Host "   Pandoc: $pandocVersion" -ForegroundColor Gray
}

# 2. Clean previous builds
Write-Host "`n[2/9] Cleaning previous builds..." -ForegroundColor Yellow
$cleanDirs = @("build", "dist", "Build")
foreach ($dir in $cleanDirs) {
    if (Test-Path $dir) {
        Remove-Item -Recurse -Force $dir
        Write-Host "   Removed: $dir" -ForegroundColor Gray
    }
}

$cleanFiles = @("*.spec")
foreach ($pattern in $cleanFiles) {
    Get-ChildItem $pattern -ErrorAction SilentlyContinue | Remove-Item -Force
}

# 3. Create build structure
Write-Host "`n[3/9] Creating build structure..." -ForegroundColor Yellow
$dirs = @("Build", "Build\Docs", "Build\Examples", "Build\Logs", "Build\Output")
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Write-Host "   Created: $dir" -ForegroundColor Gray
}

# 4. Convert documentation
Write-Host "`n[4/9] Converting documentation..." -ForegroundColor Yellow

$docs = @{
    "USER_GUIDE.md" = "User_Guide"
    "QUICK_START_ENHANCED.md" = "Quick_Start"
    "COMPLETE_FIELD_REFERENCE.md" = "Field_Reference"
}

foreach ($source in $docs.Keys) {
    if (-not (Test-Path $source)) {
        Write-Warning "   $source not found, skipping..."
        continue
    }
    
    $basename = $docs[$source]
    
    # Always create TXT version
    Write-Host "   Converting $source to TXT..." -ForegroundColor Gray
    if (Get-Command pandoc -ErrorAction SilentlyContinue) {
        pandoc $source -o "Build\Docs\$basename.txt" --from gfm --to plain
    } else {
        # Fallback: simple copy with extension change
        Copy-Item $source -Destination "Build\Docs\$basename.txt"
    }
    
    # PDF if not skipped and pandoc available
    if (-not $SkipPDF -and (Get-Command pandoc -ErrorAction SilentlyContinue)) {
        Write-Host "   Converting $source to PDF..." -ForegroundColor Gray
        try {
            pandoc $source -o "Build\Docs\$basename.pdf" --from gfm --pdf-engine=wkhtmltopdf --toc -V geometry:margin=1in
        } catch {
            Write-Warning "   PDF conversion failed for $source. Continuing..."
        }
    }
}

# 5. Create README.txt
Write-Host "`n[5/9] Creating README.txt..." -ForegroundColor Yellow
$readmeContent = @"
========================================================================
   MODBUS CONFIGURATION GENERATOR PRO v$Version
   Windows Standalone Edition
========================================================================

QUICK START:
------------
1. Double-click "ModbusConfigGen.exe" to launch the application
2. The GUI will open automatically (no console window)
3. To try examples:
   - Click "Import" button
   - Navigate to "Examples" folder
   - Select "Test_Phase1_Register_Config.json"

WHAT THIS APPLICATION DOES:
----------------------------
- Manage Modbus register definitions in a visual table
- Auto-generate firmware-compatible JSON configuration files
- Import/export configurations for backup and sharing
- Validate register configurations before deployment

DOCUMENTATION:
--------------
- Docs/User_Guide$(if($SkipPDF){'.txt'}else{'.pdf'})         Complete user manual (start here!)
- Docs/Quick_Start$(if($SkipPDF){'.txt'}else{'.pdf'})         One-page quick reference
- Docs/Field_Reference$(if($SkipPDF){'.txt'}else{'.pdf'})     All 37 field explanations
$(if(-not $SkipPDF){"- Docs/*.txt versions also provided for plain text viewing"})

EXAMPLE FILES:
--------------
- Examples/Test_Phase1_Register_Config.json
  Sample register configuration to import

SYSTEM REQUIREMENTS:
--------------------
- Operating System: Windows 7 / 10 / 11 (64-bit)
- RAM: 512 MB minimum
- Disk Space: 50 MB
- Display: 1280x720 minimum resolution
- NO Python installation required!
- NO internet connection required!

FIRST-TIME USER?
----------------
1. Read: Docs/Quick_Start$(if($SkipPDF){'.txt'}else{'.pdf'}) (quick overview)
2. Try:  Import Examples/Test_Phase1_Register_Config.json
3. Edit: Add a new register using the "Add" button
4. Generate: Click "Generate All Configurations"
5. Check: Output files in your selected directory

TROUBLESHOOTING:
----------------
Problem: Double-clicking .exe does nothing
Solution: Right-click → "Run as Administrator"

Problem: Windows says "Windows protected your PC"
Solution: Click "More info" → "Run anyway"
         (This is a false positive - app is safe)

Problem: Application won't save files
Solution: Run from a folder with write permissions (not C:\Program Files)

Problem: Validation errors appear
Solution: Check Logs/ folder for validation_errors_*.txt with details

SUPPORT:
--------
Version: $Version
Build Date: $(Get-Date -Format "yyyy-MM-dd HH:mm")
Contact: [Your support email/website]

LICENSE:
--------
Copyright (C) 2026 Thermelgy
All rights reserved.

========================================================================
"@

$readmeContent | Out-File "Build\README.txt" -Encoding UTF8
Write-Host "   Created: Build\README.txt" -ForegroundColor Gray

# 6. Copy examples
Write-Host "`n[6/9] Copying example files..." -ForegroundColor Yellow
if (Test-Path "Examples\Test_Phase1_Register_Config.json") {
    Copy-Item "Examples\Test_Phase1_Register_Config.json" -Destination "Build\Examples\"
    Write-Host "   Copied: Test_Phase1_Register_Config.json" -ForegroundColor Gray
}
if (Test-Path "Examples\Test_Phase1_Generated_ParamMap_Config.json") {
    Copy-Item "Examples\Test_Phase1_Generated_ParamMap_Config.json" -Destination "Build\Examples\"
    Write-Host "   Copied: Test_Phase1_Generated_ParamMap_Config.json" -ForegroundColor Gray
}
if (Test-Path "Examples\README_EXAMPLES.md") {
    if (Get-Command pandoc -ErrorAction SilentlyContinue) {
        pandoc Examples\README_EXAMPLES.md -o Build\Examples\README_EXAMPLES.txt --from gfm --to plain
    } else {
        Copy-Item "Examples\README_EXAMPLES.md" -Destination "Build\Examples\README_EXAMPLES.txt"
    }
    Write-Host "   Created: README_EXAMPLES.txt" -ForegroundColor Gray
}

# 7. Build executable
Write-Host "`n[7/9] Building executable with PyInstaller..." -ForegroundColor Yellow
Write-Host "   This may take 2-3 minutes..." -ForegroundColor Gray

$iconParam = if (Test-Path "icon.ico") { "--icon=icon.ico" } else { "" }

$buildCommand = @"
pyinstaller --name=ModbusConfigGen ``
  --onefile ``
  --windowed ``
  $iconParam ``
  --add-data "forward_engine.py;." ``
  --add-data "reverse_engine.py;." ``
  --add-data "transform_wrapper.py;." ``
  --add-data "bmiot_constants.py;." ``
  --add-data "json_formatter.py;." ``
  --add-data "ui_helpers.py;." ``
  --hidden-import=forward_engine ``
  --hidden-import=reverse_engine ``
  --hidden-import=transform_wrapper ``
  --hidden-import=bmiot_constants ``
  --hidden-import=json_formatter ``
  --hidden-import=ui_helpers ``
  --exclude-module numpy ``
  --exclude-module pandas ``
  --exclude-module matplotlib ``
  --exclude-module pytest ``
  --clean ``
  --noconfirm ``
  modbus_tkinter_app_v6.6_complete.py
"@

Invoke-Expression $buildCommand

if (-not (Test-Path "dist\ModbusConfigGen.exe")) {
    Write-Error "Build failed! Check error messages above."
    exit 1
}

Write-Host "   Build completed successfully!" -ForegroundColor Green

# 8. Assemble distribution
Write-Host "`n[8/9] Assembling distribution package..." -ForegroundColor Yellow
Copy-Item "dist\ModbusConfigGen.exe" -Destination "Build\"

$exeSize = (Get-Item "Build\ModbusConfigGen.exe").Length / 1MB
Write-Host "   Executable size: $([math]::Round($exeSize, 2)) MB" -ForegroundColor Gray

# Count files
$fileCount = (Get-ChildItem -Recurse Build\ -File).Count
Write-Host "   Total files in distribution: $fileCount" -ForegroundColor Gray

# 9. Create ZIP
Write-Host "`n[9/9] Creating distribution ZIP..." -ForegroundColor Yellow
$zipName = "ModbusConfigGen_v${Version}_Windows_x64.zip"

if (Test-Path $zipName) {
    Remove-Item $zipName -Force
}

Compress-Archive -Path "Build\*" -DestinationPath $zipName -CompressionLevel Optimal

$zipSize = (Get-Item $zipName).Length / 1MB

# Summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  BUILD SUCCESSFUL!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`nDistribution Package:" -ForegroundColor Cyan
Write-Host "  File: $zipName" -ForegroundColor White
Write-Host "  Size: $([math]::Round($zipSize, 2)) MB (compressed)" -ForegroundColor White
Write-Host "  Executable: $([math]::Round($exeSize, 2)) MB (uncompressed)" -ForegroundColor White
Write-Host "  Files: $fileCount total" -ForegroundColor White

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "  1. Test: Extract and run ModbusConfigGen.exe" -ForegroundColor White
Write-Host "  2. Validate: Run test_distribution.ps1 (if available)" -ForegroundColor White
Write-Host "  3. VM Test: Test on clean Windows VM (recommended)" -ForegroundColor White
Write-Host "  4. Distribute: Share $zipName with team" -ForegroundColor White

Write-Host "`nDistribution package ready! ✅" -ForegroundColor Green
