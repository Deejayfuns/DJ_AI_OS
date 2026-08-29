# DJ AI OS - Authenticode Signing Infrastructure

## Overview

This directory contains the development/test signing infrastructure for DJ AI OS Windows Authenticode signing.

**Key principle:** The pipeline works WITHOUT a production certificate. A self-signed development certificate is used for testing the signing flow. Production signing requires purchasing an OV/Individual code-signing certificate from a public CA.

## Files

| File | Purpose |
|------|---------|
| `sign_exe.py` | Main signing helper - signs and verifies EXEs |
| `create_dev_cert.ps1` | PowerShell script to generate self-signed dev certificate |
| `README_SIGNING.md` | This documentation |

## Quick Start (Local Development)

### 1. Generate Development Certificate

```powershell
# Run in PowerShell (as regular user, not admin)
.\tools\ci\create_dev_cert.ps1
```

This creates:
- `signing/dev_cert.pfx` - Private key + certificate (password protected)
- `signing/dev_cert.cer` - Public certificate only
- Outputs BASE64 encoded PFX and password for CI

### 2. Set Environment Variables

```powershell
$env:CODESIGN_PFX_BASE64 = "<base64-from-step-1>"
$env:CODESIGN_PASSWORD = "devpass"
# Optional: for timestamping
$env:CODESIGN_TSA_URL = "http://timestamp.digicert.com"
```

### 3. Build and Sign

```bash
python build_exe.py --sign
```

Or manually:
```bash
python build_exe.py
python tools/ci/sign_exe.py sign dist/DJ_AI_OS/DJ_AI_OS.exe
```

### 4. Verify

```bash
python tools/ci/sign_exe.py verify dist/DJ_AI_OS/DJ_AI_OS.exe
```

## CI Integration (GitHub Actions)

### Current Behavior (No Certificate)

```yaml
# build-gate job - runs normally, produces unsigned EXE
- name: Build (onedir mode)
  run: python build_exe.py
```

### Future: With Certificate Secrets

1. Add GitHub Actions **Environment** called `signing` (or use `release` environment)
2. Add secrets to that environment:
   - `CODESIGN_PFX_BASE64` - Base64 encoded production PFX
   - `CODESIGN_PASSWORD` - PFX password
   - `CODESIGN_TSA_URL` - RFC3161 timestamp server (e.g., `http://timestamp.digicert.com`)

3. Extend `build-gate` job:
```yaml
- name: Build
  run: python build_exe.py

- name: Sign EXE (if certificate configured)
  if: env.CODESIGN_PFX_BASE64 != ''
  env:
    CODESIGN_PFX_BASE64: ${{ secrets.CODESIGN_PFX_BASE64 }}
    CODESIGN_PASSWORD: ${{ secrets.CODESIGN_PASSWORD }}
    CODESIGN_TSA_URL: ${{ secrets.CODESIGN_TSA_URL }}
  run: python build_exe.py --sign
```

## Security

### NEVER commit:
- `signing/dev_cert.pfx` (or any `.pfx`, `.p12`)
- Private keys
- Certificate passwords
- Base64-encoded certificates in source code

### .gitignore
Add to `.gitignore`:
```
signing/
*.pfx
*.p12
*cert*.pem
```

### Certificate Types

| Type | Trust Level | Cost | Use Case |
|------|-------------|------|----------|
| Self-signed (dev) | None (Unknown Publisher) | Free | CI testing, local development |
| OV/Individual (Standard) | Trusted Publisher | ~$200-400/yr | Production V1.0 |
| EV (Extended Validation) | Trusted + Instant SmartScreen reputation | ~$300-600/yr | Optional (not technically required) |

**EV is NOT technically mandatory** for Authenticode. Standard OV/Individual certificate satisfies Windows signature validation. EV only accelerates SmartScreen reputation building.

## Signature Verification

The `sign_exe.py verify` command uses:
```bash
signtool verify /pa /v <exe>
```

This checks:
- File has Authenticode signature
- Signature is cryptographically valid
- Certificate chain validation (with `/pa` uses default Windows policy)

**Note:** A self-signed certificate will show "Successfully verified" cryptographically but the publisher will be untrusted by Windows (shows "Unknown Publisher" in UAC). This is EXPECTED for development.

## Timestamp Server (RFC3161)

Required for production signatures to remain valid after certificate expiration.

Free/public TSA options:
- `http://timestamp.digicert.com`
- `http://timestamp.sectigo.com`
- `http://timestamp.globalsign.com`

Set via `CODESIGN_TSA_URL` environment variable.

## Architecture

```
build_exe.py (--sign)
    │
    ▼
tools/ci/sign_exe.py sign <exe>
    │
    ├─► Finds signtool.exe (Windows SDK)
    ├─► Loads PFX from CODESIGN_PFX_BASE64
    ├─► Runs: signtool sign /fd sha256 /f <pfx> /p <pwd> [/tr <tsa> /td sha256] <exe>
    └─► Verifies: signtool verify /pa /v <exe>
```

## Testing Without Windows

The signing helper and build hook are Windows-only. On non-Windows:
- `build_exe.py` works normally (PyInstaller cross-platform)
- `--sign` flag will fail gracefully with "Authenticode signing only works on Windows"
- CI `build-gate` runs on `windows-latest` so signing tests execute there

## Troubleshooting

### signtool.exe not found
Install Windows SDK (includes Windows 10/11 SDK) or Visual Studio with "Windows SDK" component.

### "No certificate configured"
Set `CODESIGN_PFX_BASE64` and `CODESIGN_PASSWORD` environment variables.

### "Unknown Publisher" after signing
Expected with self-signed certificate. Install the `.cer` to "Trusted Root Certification Authorities" on test machine to trust it locally:
```powershell
Import-Certificate -FilePath dev_cert.cer -CertStoreLocation "Cert:\CurrentUser\Root"
```

## Production Release Checklist

- [ ] Purchase OV/Individual code-signing certificate from public CA (Sectigo, DigiCert, GlobalSign, etc.)
- [ ] Export as PFX with strong password
- [ ] Base64 encode: `base64 -w0 cert.pfx`
- [ ] Add to GitHub Environment secrets (`CODESIGN_PFX_BASE64`, `CODESIGN_PASSWORD`)
- [ ] Configure `CODESIGN_TSA_URL` (RFC3161 timestamp server)
- [ ] Run `build_exe.py --sign` in release CI
- [ ] Verify signed EXE on clean Windows VM (SmartScreen should show publisher name)
- [ ] Update `RELEASE_GATE_AUDIT.md` P0-1 status