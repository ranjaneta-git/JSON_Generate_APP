#Requires -Version 5.1

<#
.SYNOPSIS
    Automated testing of distribution package
.DESCRIPTION
    Validates the distribution package structure and basic functionality
.EXAMPLE
    .\test_distribution.ps1 -DistributionPath "C:\Path\To\Extracted\Folder"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$DistributionPath
)

$ErrorActionPreference = "Continue"
$testsPassed = 0
$testsFailed = 0

function Test-Item {
    param(
        [string]$Name,
        [bool]$Condition,
        [string]$FailureMessage = ""
    )
    Write-Host "Testing: $Name..." -NoNewline -ForegroundColor Cyan
    if ($Condition) {
        Write-Host " ✓ PASS" -ForegroundColor Green
        $script:testsPassed++
        return $true
    } else {
        Write-Host " ✗ FAIL" -ForegroundColor Red
        if ($FailureMessage) {
            Write-Host "  └─ $FailureMessage" -ForegroundColor Yellow
        }
        $script:testsFailed++
        return $false
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Distribution Package Validation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Testing: $DistributionPath`n" -ForegroundColor Gray

# Validate distribution path exists
if (-not (Test-Path $DistributionPath)) {
    Write-Error "Distribution path does not exist: $DistributionPath"
    exit 1
}

Write-Host "[1] Testing Package Structure..." -ForegroundColor Yellow
Write-Host ""

# Test 1: Main executable exists
Test-Item "Main executable exists" `
    (Test-Path "$DistributionPath\ModbusConfigGen.exe") `
    "ModbusConfigGen.exe not found"

# Test 2: README
Test-Item "README.txt exists" `
    (Test-Path "$DistributionPath\README.txt") `
    "README.txt is required for users"

# Test 3: Folders
Test-Item "Docs folder exists" `
    (Test-Path "$DistributionPath\Docs") `
    "Docs folder is required"

Test-Item "Examples folder exists" `
    (Test-Path "$DistributionPath\Examples") `
    "Examples folder is required"

Test-Item "Logs folder exists" `
    (Test-Path "$DistributionPath\Logs") `
    "Logs folder should exist (can be empty)"

Write-Host "`n[2] Testing Documentation..." -ForegroundColor Yellow
Write-Host ""

# Test 4: Documentation files
$hasUserGuidePdf = Test-Path "$DistributionPath\Docs\User_Guide.pdf"
$hasUserGuideTxt = Test-Path "$DistributionPath\Docs\User_Guide.txt"
Test-Item "User Guide exists (PDF or TXT)" `
    ($hasUserGuidePdf -or $hasUserGuideTxt) `
    "At least one format (PDF or TXT) required"

$hasQuickStartPdf = Test-Path "$DistributionPath\Docs\Quick_Start.pdf"
$hasQuickStartTxt = Test-Path "$DistributionPath\Docs\Quick_Start.txt"
Test-Item "Quick Start exists (PDF or TXT)" `
    ($hasQuickStartPdf -or $hasQuickStartTxt) `
    "At least one format (PDF or TXT) required"

$hasFieldRefPdf = Test-Path "$DistributionPath\Docs\Field_Reference.pdf"
$hasFieldRefTxt = Test-Path "$DistributionPath\Docs\Field_Reference.txt"
Test-Item "Field Reference exists (PDF or TXT)" `
    ($hasFieldRefPdf -or $hasFieldRefTxt) `
    "Field Reference recommended"

Write-Host "`n[3] Testing Example Files..." -ForegroundColor Yellow
Write-Host ""

# Test 5: Examples
Test-Item "Register Config example exists" `
    (Test-Path "$DistributionPath\Examples\Test_Phase1_Register_Config.json") `
    "Example file helps users get started"

Test-Item "ParamMap Config example exists" `
    (Test-Path "$DistributionPath\Examples\Test_Phase1_Generated_ParamMap_Config.json") `
    "Example output file recommended"

Write-Host "`n[4] Testing Executable Properties..." -ForegroundColor Yellow
Write-Host ""

# Test 6: Executable properties
if (Test-Path "$DistributionPath\ModbusConfigGen.exe") {
    $exe = Get-Item "$DistributionPath\ModbusConfigGen.exe"
    
    Test-Item "Executable is not empty" `
        ($exe.Length -gt 10MB) `
        "Executable seems too small (< 10MB)"
    
    Test-Item "Executable is reasonable size" `
        ($exe.Length -lt 100MB) `
        "Executable seems too large (> 100MB)"
    
    $exeSizeMB = [math]::Round($exe.Length / 1MB, 2)
    Write-Host "  └─ Executable size: $exeSizeMB MB" -ForegroundColor Gray
}

Write-Host "`n[5] Testing Write Permissions..." -ForegroundColor Yellow
Write-Host ""

# Test 7: Write permissions
$canWrite = $false
try {
    $testFile = "$DistributionPath\write_test.tmp"
    "test" | Out-File $testFile -ErrorAction Stop
    Remove-Item $testFile -ErrorAction Stop
    $canWrite = $true
} catch {
    $canWrite = $false
}

Test-Item "Directory is writable" `
    $canWrite `
    "Users must have write permissions to save files"

Write-Host "`n[6] Testing File Integrity..." -ForegroundColor Yellow
Write-Host ""

# Test 8: JSON file integrity
if (Test-Path "$DistributionPath\Examples\Test_Phase1_Register_Config.json") {
    try {
        $json = Get-Content "$DistributionPath\Examples\Test_Phase1_Register_Config.json" -Raw | ConvertFrom-Json
        Test-Item "Example JSON is valid" `
            ($json -ne $null) `
            "JSON file may be corrupted"
    } catch {
        Test-Item "Example JSON is valid" `
            $false `
            "JSON parsing failed: $_"
    }
}

# Test 9: README content check
if (Test-Path "$DistributionPath\README.txt") {
    $readmeContent = Get-Content "$DistributionPath\README.txt" -Raw
    
    Test-Item "README contains Quick Start section" `
        ($readmeContent -match "QUICK START") `
        "README should guide users"
    
    Test-Item "README contains Troubleshooting section" `
        ($readmeContent -match "TROUBLESHOOTING") `
        "README should help with common issues"
}

Write-Host "`n[7] Manual Testing Required..." -ForegroundColor Yellow
Write-Host ""

Write-Host "The following tests require manual verification:" -ForegroundColor Gray
Write-Host "  1. Launch ModbusConfigGen.exe" -ForegroundColor White
Write-Host "  2. Verify GUI opens without console window" -ForegroundColor White
Write-Host "  3. Import Examples/Test_Phase1_Register_Config.json" -ForegroundColor White
Write-Host "  4. Add a new register" -ForegroundColor White
Write-Host "  5. Generate configurations" -ForegroundColor White
Write-Host "  6. Export files" -ForegroundColor White
Write-Host ""

$launchTest = Read-Host "Did you test launching the application? (Y/N/Skip)"
if ($launchTest -eq "Y") {
    Test-Item "Application launched successfully" $true
} elseif ($launchTest -eq "N") {
    Test-Item "Application launched successfully" $false "Manual test failed"
} else {
    Write-Host "  └─ Manual test skipped" -ForegroundColor Yellow
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Passed: $testsPassed" -ForegroundColor Green
Write-Host "Failed: $testsFailed" -ForegroundColor $(if ($testsFailed -eq 0) { "Green" } else { "Red" })

if ($testsFailed -eq 0) {
    Write-Host "`n✅ Distribution package is READY for deployment!" -ForegroundColor Green
    Write-Host "`nRecommended next steps:" -ForegroundColor Yellow
    Write-Host "  1. Test on clean Windows VM (no Python installed)" -ForegroundColor White
    Write-Host "  2. Test on Windows 10 and Windows 11" -ForegroundColor White
    Write-Host "  3. Verify antivirus doesn't quarantine the .exe" -ForegroundColor White
    Write-Host "  4. Get feedback from pilot users" -ForegroundColor White
    exit 0
} else {
    Write-Host "`n❌ Distribution package has issues - fix before deploying!" -ForegroundColor Red
    Write-Host "`nReview failed tests above and rebuild." -ForegroundColor Yellow
    exit 1
}
