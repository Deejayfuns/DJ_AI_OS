#!/usr/bin/env python3
"""
DJ AI OS — Update Manifest Signing Tool (Vendor Only)

Usage:
    python tools/sign_update_manifest.py \
        --manifest update_manifest.json \
        --artifacts-dir dist/update_artifacts \
        --output update_manifest_signed.json

Environment:
    DJ_AI_OS_LICENSE_PRIVATE_KEY — Ed25519 private key (PEM format)
    Or vendor_private_key.pem in repo root (gitignored)

The tool:
1. Reads manifest.json (without signature)
2. Computes SHA256 for each module artifact
3. Validates all required fields
4. Signs with Ed25519 private key
5. Outputs signed manifest ready for CDN upload
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path for imports
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.license import signature as sig


REQUIRED_MANIFEST_FIELDS = [
    "version",
    "min_client_version",
    "released_at",
    "critical",
    "changelog",
    "download_url",
    "modules",
]

REQUIRED_MODULE_FIELDS = [
    "name",
    "version",
    "sha256",
    "size",
    "hot_reload",
]


def canonical_json(payload: Dict) -> bytes:
    """Canonical JSON for signing (same as app.license.signature)."""
    data = {k: v for k, v in payload.items() if k != "signature"}
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_private_key() -> bytes:
    """Load Ed25519 private key from env or gitignored file."""
    env_pem = os.environ.get("DJ_AI_OS_LICENSE_PRIVATE_KEY", "").strip()
    if env_pem:
        return env_pem.encode("utf-8")

    private_key_file = ROOT / "vendor_private_key.pem"
    if private_key_file.exists():
        return private_key_file.read_bytes()

    raise ValueError(
        "Private key not found. Set DJ_AI_OS_LICENSE_PRIVATE_KEY env var "
        "or place vendor_private_key.pem in repo root (gitignored)."
    )


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_manifest(manifest: Dict) -> List[str]:
    """Validate manifest schema. Returns list of errors (empty if valid)."""
    errors = []

    # Top-level required fields
    for field in REQUIRED_MANIFEST_FIELDS:
        if field not in manifest:
            errors.append(f"Missing required field: {field}")

    if "modules" in manifest:
        if not isinstance(manifest["modules"], list):
            errors.append("'modules' must be a list")
        else:
            for i, mod in enumerate(manifest["modules"]):
                if not isinstance(mod, dict):
                    errors.append(f"modules[{i}] must be an object")
                    continue
                for field in REQUIRED_MODULE_FIELDS:
                    if field not in mod:
                        errors.append(f"modules[{i}] missing required field: {field}")

                # Validate types
                if "size" in mod and not isinstance(mod["size"], int):
                    errors.append(f"modules[{i}].size must be integer")
                if "hot_reload" in mod and not isinstance(mod["hot_reload"], bool):
                    errors.append(f"modules[{i}].hot_reload must be boolean")
                if "sha256" in mod and mod["sha256"]:  # allow empty placeholder before populate
                    sha = mod["sha256"]
                    if not isinstance(sha, str) or len(sha) != 64:
                        errors.append(f"modules[{i}].sha256 must be 64-char hex string")

    # Version format validation
    if "version" in manifest:
        try:
            parts = str(manifest["version"]).split(".")
            if len(parts) < 2 or not all(p.isdigit() for p in parts):
                errors.append("version must be semantic (e.g., '0.2.0')")
        except Exception:
            errors.append("version must be string")

    if "min_client_version" in manifest:
        try:
            parts = str(manifest["min_client_version"]).split(".")
            if len(parts) < 2 or not all(p.isdigit() for p in parts):
                errors.append("min_client_version must be semantic (e.g., '0.1.0')")
        except Exception:
            errors.append("min_client_version must be string")

    # released_at ISO format
    if "released_at" in manifest:
        try:
            datetime.fromisoformat(manifest["released_at"].replace("Z", "+00:00"))
        except Exception:
            errors.append("released_at must be ISO 8601 format (e.g., '2026-08-12T00:00:00Z')")

    # critical boolean
    if "critical" in manifest and not isinstance(manifest["critical"], bool):
        errors.append("critical must be boolean")

    # download_url
    if "download_url" in manifest and not isinstance(manifest["download_url"], str):
        errors.append("download_url must be string")

    # changelog string
    if "changelog" in manifest and not isinstance(manifest["changelog"], str):
        errors.append("changelog must be string")

    return errors


def populate_sha256_from_artifacts(manifest: Dict, artifacts_dir: Path) -> Dict:
    """Compute SHA256 and size for each module from artifact files."""
    updated = json.loads(json.dumps(manifest))  # deep copy

    for mod in updated.get("modules", []):
        name = mod.get("name", "")
        if not name:
            continue

        artifact_path = artifacts_dir / name
        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")

        mod["sha256"] = compute_sha256(artifact_path)
        mod["size"] = artifact_path.stat().st_size

    return updated


def sign_manifest(manifest: Dict, private_key_pem: bytes) -> Dict:
    """Sign manifest with Ed25519 private key."""
    # Ensure no existing signature
    manifest.pop("signature", None)

    signature = sig.sign(manifest, private_key_pem=private_key_pem)
    manifest["signature"] = signature
    return manifest


def verify_manifest(manifest: Dict) -> bool:
    """Verify manifest signature with embedded public key (for self-test)."""
    signature = manifest.get("signature", "")
    if not signature:
        return False
    return sig.verify(manifest, signature)


def main():
    parser = argparse.ArgumentParser(
        description="Sign update manifest with Ed25519 (vendor only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic signing (artifacts in ./dist/update_artifacts)
  python tools/sign_update_manifest.py --manifest update_manifest.json

  # With custom artifacts dir and output
  python tools/sign_update_manifest.py \\
      --manifest update_manifest.json \\
      --artifacts-dir ./dist/update_artifacts \\
      --output update_manifest_signed.json

  # Verify only (no private key needed)
  python tools/sign_update_manifest.py --manifest update_manifest_signed.json --verify-only
        """
    )

    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to manifest.json (unsigned input or signed for verification)",
    )
    parser.add_argument(
        "--artifacts-dir",
        default="dist/update_artifacts",
        help="Directory containing module artifact files (default: dist/update_artifacts)",
    )
    parser.add_argument(
        "--output",
        default="update_manifest_signed.json",
        help="Output path for signed manifest (default: update_manifest_signed.json)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify signature, do not sign",
    )

    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    artifacts_dir = Path(args.artifacts_dir)
    output_path = Path(args.output)

    if not manifest_path.exists():
        print(f"[FAIL] Manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[READ] Reading manifest: {manifest_path}")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    # Validate schema
    errors = validate_manifest(manifest)
    if errors:
        print("[FAIL] Manifest validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    if args.verify_only:
        # Verify mode
        print("[VERIFY] Verifying manifest signature...")
        if verify_manifest(manifest):
            print("[OK] Signature VALID")
            sys.exit(0)
        else:
            print("[FAIL] Signature INVALID", file=sys.stderr)
            sys.exit(1)

    # Sign mode
    print(f"[ARTIFACTS] Loading artifacts from: {artifacts_dir}")
    if not artifacts_dir.exists():
        print(f"[FAIL] Artifacts directory not found: {artifacts_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        manifest = populate_sha256_from_artifacts(manifest, artifacts_dir)
    except FileNotFoundError as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        sys.exit(1)

    print("[KEY] Loading private key...")
    try:
        private_key_pem = load_private_key()
    except ValueError as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        sys.exit(1)

    print("[SIGN]  Signing manifest...")
    manifest = sign_manifest(manifest, private_key_pem)

    # Self-verify
    if not verify_manifest(manifest):
        print("[FAIL] Self-verification failed after signing!", file=sys.stderr)
        sys.exit(1)

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"[OK] Signed manifest written to: {output_path}")
    print(f"   Version: {manifest['version']}")
    print(f"   Modules: {len(manifest['modules'])}")
    print(f"   Download URL: {manifest['download_url']}")
    print(f"   Signature: {manifest['signature'][:16]}...")


if __name__ == "__main__":
    main()