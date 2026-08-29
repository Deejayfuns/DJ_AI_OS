<#
.SYNOPSIS
    Creates a self-signed development certificate for DJ AI OS Authenticode signing.
    THIS CERTIFICATE IS FOR DEVELOPMENT/TESTING ONLY - NEVER FOR PRODUCTION USE.

.DESCRIPTION
    Generates a self-signed code signing certificate, exports it as PFX with password,
    and outputs the base64-encoded PFX for use with CODESIGN_PFX_BASE64 environment variable.

.NOTES
    - Self-signed certificates are NOT trusted by Windows by default
    - They will show "Unknown Publisher" in UAC/SmartScreen
    - They produce cryptographically VALID signatures but UNTRUSTED ones
    - Use only for CI pipeline testing and local development
    - NEVER use for production releases
#>

param(
    [string]$CertName = "DJ AI OS Development Certificate",
    [string]$Password = "devpass",
    [string]$OutputDir = ".\signing",
    [switch]$InstallToStore
)

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "DJ AI OS - Development Certificate Generator" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  WARNING: This creates a SELF-SIGNED certificate for DEVELOPMENT ONLY" -ForegroundColor Yellow
Write-Host "   - NOT trusted by Windows (shows 'Unknown Publisher')" -ForegroundColor Yellow
Write-Host "   - NOT suitable for production distribution" -ForegroundColor Yellow
Write-Host "   - Use ONLY for CI pipeline testing and local development" -ForegroundColor Yellow
Write-Host ""

# Create output directory
$outputPath = Resolve-Path $OutputDir -ErrorAction SilentlyContinue
if (-not $outputPath) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    $outputPath = Resolve-Path $OutputDir
}

$pfxPath = Join-Path $outputPath "dev_cert.pfx"
$cerPath = Join-Path $outputPath "dev_cert.cer"

# Generate self-signed certificate
Write-Host "Generating self-signed certificate..." -ForegroundColor Green
$cert = New-SelfSignedCertificate `
    -Subject "CN=$CertName" `
    -KeyAlgorithm RSA `
    -KeyLength 2048 `
    -KeyUsage DigitalSignature `
    -Type CodeSigning `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -NotAfter (Get-Date).AddYears(1) `
    -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3") `
    -FriendlyName "DJ AI OS Development Certificate" `
    -ErrorAction Stop

Write-Host "Certificate created: $($cert.Thumbprint)" -ForegroundColor Green

# Export PFX with password
Write-Host "Exporting PFX..." -ForegroundColor Green
$securePassword = ConvertTo-SecureString -String $Password -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $securePassword -Force -ErrorAction Stop
Write-Host "PFX exported: $pfxPath" -ForegroundColor Green

# Export CER (public key only)
Write-Host "Exporting CER (public key)..." -ForegroundColor Green
Export-Certificate -Cert $cert -FilePath $cerPath -Force -ErrorAction Stop
Write-Host "CER exported: $cerPath" -ForegroundColor Green

# Output base64 for CI
Write-Host "" -ForegroundColor Cyan
Write-Host "BASE64 ENCODED PFX (for CODESIGN_PFX_BASE64):" -ForegroundColor Cyan
$pfxBytes = [System.IO.File]::ReadAllBytes($pfxPath)
$b64 = [System.Convert]::ToBase64String($pfxBytes)
Write-Host $b64 -ForegroundColor White

Write-Host ""
Write-Host "PASSWORD (for CODESIGN_PASSWORD):" -ForegroundColor Cyan
Write-Host $Password -ForegroundColor White

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "USAGE INSTRUCTIONS" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Local testing:" -ForegroundColor Green
Write-Host "  \$env:CODESIGN_PFX_BASE64 = '$b64'" -ForegroundColor White
Write-Host "  \$env:CODESIGN_PASSWORD = '$Password'" -ForegroundColor White
Write-Host "  python tools/ci/sign_exe.py sign dist/DJ_AI_OS/DJ_AI_OS.exe" -ForegroundColor White
Write-Host ""
Write-Host "GitHub Actions (add as Environment secrets):" -ForegroundColor Green
Write-Host "  CODESIGN_PFX_BASE64 = (the base64 string above)" -ForegroundColor White
Write-Host "  CODESIGN_PASSWORD = '$Password'" -ForegroundColor White
Write-Host ""
Write-Host "Optional: Add timestamp server (RFC3161)" -ForegroundColor Green
Write-Host "  \$env:CODESIGN_TSA_URL = 'http://timestamp.digicert.com'" -ForegroundColor White
Write-Host ""
Write-Host "===========================================" -ForegroundColor Red
Write-Host "SECURITY NOTICE" -ForegroundColor Red
Write-Host "===========================================" -ForegroundColor Red
Write-Host "• NEVER commit the PFX file to git" -ForegroundColor Red
Write-Host "• NEVER use this certificate for production releases" -ForegroundColor Red
Write-Host "• Add 'signing/' to .gitignore" -ForegroundColor Red
Write-Host "• For production: purchase OV/Individual code-signing certificate from a public CA" -ForegroundColor Red
Write-Host ""

if ($InstallToStore) {
    Write-Host "Installing to Trusted Root (for local testing without UAC warnings)..." -ForegroundColor Yellow
    Import-Certificate -FilePath $cerPath -CertStoreLocation "Cert:\CurrentUser\Root" -ErrorAction SilentlyContinue
    Write-Host "Done. Restart applications to see effect." -ForegroundColor Green
}