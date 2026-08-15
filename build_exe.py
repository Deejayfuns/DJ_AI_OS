#!/usr/bin/env python3
"""
DJ AI OS - Build Script for Windows Executable

Usage:
    python build_exe.py              # Build (onedir, fast startup)
    python build_exe.py --onefile    # Build single exe (slower startup)
    python build_exe.py --installer  # Also create Inno Setup installer
    python build_exe.py --clean      # Clean build artifacts only
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
SPEC_FILE = PROJECT_ROOT / "DJ_AI_OS.spec"


def get_version():
    """Get version from app/config/version.py (sürüm tek kaynağı)."""
    try:
        import importlib.util
        import sys
        # Repo root'u sys.path'e ekle ki paketlenmeden de import edilsin.
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        spec = importlib.util.spec_from_file_location(
            "djaios_version", PROJECT_ROOT / "app" / "config" / "version.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "APP_VERSION", "1.0.0")
    except Exception:
        return "1.0.0"


def clean_artifacts():
    """Remove build/dist/spec artifacts."""
    for name in ["build", "dist", "__pycache__"]:
        path = PROJECT_ROOT / name
        if path.exists():
            shutil.rmtree(path)
            print(f"Cleaned: {path}")


def build(onefile=False):
    """Run PyInstaller with the lean spec."""
    if not SPEC_FILE.exists():
        print("❌ DJ_AI_OS.spec not found. Run from project root.")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC_FILE),
        "--noconfirm",
        "--distpath", str(PROJECT_ROOT / "dist"),
        "--workpath", str(PROJECT_ROOT / "build"),
    ]

    if onefile:
        cmd.append("--onefile")

    print(f"Building DJ AI OS v{get_version()}...")
    print(f"Mode: {'Single EXE' if onefile else 'Directory (faster startup)'}")
    print("Running:", " ".join(cmd))

    try:
        subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
        version = get_version()
        print("\n[OK] Build successful!")
        if onefile:
            print(f"[OK] Output: {PROJECT_ROOT / 'dist' / f'DJ_AI_OS_v{version}.exe'}")
        else:
            dist_dir = PROJECT_ROOT / "dist" / "DJ_AI_OS"
            print(f"[OK] Output: {dist_dir}")
            print(f"[OK] Run: {dist_dir / 'DJ_AI_OS.exe'}")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed (exit {e.returncode})")
        sys.exit(1)


def create_installer():
    """Create Windows installer with Inno Setup (if installed)."""
    version = get_version()
    iss_path = PROJECT_ROOT / "installer.iss"

    iss_content = f"""; DJ AI OS Inno Setup Script
#define MyAppName "DJ AI OS"
#define MyAppVersion "{version}"
#define MyAppPublisher "ASTRA Engineering"
#define MyAppExeName "DJ_AI_OS.exe"

[Setup]
AppId={{{{ASTRA-DJ-AI-OS}}}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
DefaultDirName={{autopf}}\\{{#MyAppName}}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=DJ_AI_OS_v{version}_Setup
SetupIconFile=assets\\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

[Files]
Source: "dist\\DJ_AI_OS\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{commondesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#MyAppName}}}}"; Flags: nowait postinstall skipifsilent
"""

    iss_path.write_text(iss_content, encoding="utf-8")
    print(f"Created: {iss_path}")

    # Locate iscc (not always on PATH)
    import shutil
    iscc = shutil.which("iscc")
    if not iscc:
        for candidate in (
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
            r"C:\Program Files (x86)\Inno Setup 7\ISCC.exe",
            r"C:\Program Files\Inno Setup 7\ISCC.exe",
        ):
            if Path(candidate).exists():
                iscc = candidate
                break

    if not iscc:
        print("⚠️  Inno Setup (iscc) not found. Install from https://jrsoftware.org/isinfo.php")
        print(f"   Then run: iscc {iss_path}")
        return

    try:
        subprocess.run([iscc, str(iss_path)], cwd=PROJECT_ROOT, check=True)
        print(f"✅ Installer created: {PROJECT_ROOT / 'dist' / f'DJ_AI_OS_v{version}_Setup.exe'}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Installer build failed (exit {e.returncode})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build DJ AI OS Windows executable")
    parser.add_argument("--onefile", action="store_true", help="Single EXE (slower startup)")
    parser.add_argument("--installer", action="store_true", help="Also build Inno Setup installer")
    parser.add_argument("--clean", action="store_true", help="Clean artifacts only")
    args = parser.parse_args()

    if args.clean:
        clean_artifacts()
        sys.exit(0)

    build(onefile=args.onefile)

    if args.installer:
        create_installer()
