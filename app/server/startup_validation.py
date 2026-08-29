"""
DJ AI OS — Production Startup Validation

Validates required production environment variables on server startup.
Fails fast with clear error messages if critical secrets are missing.
"""

import os
import sys
from typing import List, Tuple


class StartupValidationError(Exception):
    """Raised when required production configuration is missing."""
    pass


# ─── Required Production Variables ───
# Format: (env_var_name, description, is_secret)
REQUIRED_PRODUCTION_VARS: List[Tuple[str, str, bool]] = [
    # Database
    ("DJ_AI_OS_DATABASE_URL", "PostgreSQL connection string (prod)", True),
    # Stripe
    ("STRIPE_SECRET_KEY", "Stripe secret key (sk_live_...)", True),
    ("STRIPE_WEBHOOK_SECRET", "Stripe webhook signing secret (whsec_...)", True),
    # Admin Auth
    ("ADMIN_TOKEN", "Admin API bearer token (64-char hex)", True),
    # License Signing (vendor machine)
    ("DJ_AI_OS_LICENSE_PRIVATE_KEY", "Ed25519 private key for license/update signing", True),
    # Update Infrastructure
    ("DJ_AI_OS_UPDATE_BASE_URL", "Base URL for signed update manifest + artifacts", False),
    # Client-facing API
    ("DJ_AI_OS_API_URL", "Public HTTPS API endpoint for desktop clients", False),
]

# Optional but recommended
RECOMMENDED_VARS: List[Tuple[str, str]] = [
    ("SENTRY_DSN", "Error tracking (Sentry)"),
    ("CORS_ORIGINS", "Allowed origins for admin SPA + client"),
    ("LOG_LEVEL", "Log level (DEBUG/INFO/WARNING/ERROR)"),
    ("LOG_JSON", "Structured JSON logging (true/false)"),
]


def validate_production_env(skip_optional: bool = False) -> List[str]:
    """
    Validate all required production environment variables are set.

    Args:
        skip_optional: If True, only check REQUIRED_PRODUCTION_VARS.
                       If False, also warn about missing RECOMMENDED_VARS.

    Returns:
        List of warning messages (non-fatal issues).

    Raises:
        StartupValidationError: If any required variable is missing or invalid.
    """
    missing = []
    invalid = []
    warnings = []

    # Check required vars
    for var_name, description, is_secret in REQUIRED_PRODUCTION_VARS:
        value = os.environ.get(var_name, "").strip()
        if not value:
            missing.append(f"  {var_name}: {description}")
            continue

        # Basic format validation
        if var_name == "DJ_AI_OS_DATABASE_URL":
            if not value.startswith(("postgresql+asyncpg://", "postgresql://")):
                invalid.append(f"  {var_name}: must be postgresql+asyncpg:// (got: {value[:30]}...)")

        elif var_name == "STRIPE_SECRET_KEY":
            if not value.startswith(("sk_live_", "sk_test_")):
                invalid.append(f"  {var_name}: must start with sk_live_ or sk_test_")

        elif var_name == "STRIPE_WEBHOOK_SECRET":
            if not value.startswith("whsec_"):
                invalid.append(f"  {var_name}: must start with whsec_")

        elif var_name == "ADMIN_TOKEN":
            # Must be 64 hex chars (32 bytes)
            if len(value) != 64 or not all(c in "0123456789abcdefABCDEF" for c in value):
                invalid.append(f"  {var_name}: must be 64 hex characters (generate with: python -c \"import secrets; print(secrets.token_hex(32))\")")

        elif var_name == "DJ_AI_OS_LICENSE_PRIVATE_KEY":
            if "BEGIN PRIVATE KEY" not in value and "BEGIN ED25519 PRIVATE KEY" not in value:
                invalid.append(f"  {var_name}: must be PEM-format Ed25519 private key")

        elif var_name in ("DJ_AI_OS_UPDATE_BASE_URL", "DJ_AI_OS_API_URL"):
            if not value.startswith("https://"):
                invalid.append(f"  {var_name}: must be HTTPS URL (production requires TLS)")

    if missing:
        raise StartupValidationError(
            "MISSING REQUIRED PRODUCTION ENVIRONMENT VARIABLES:\n" + "\n".join(missing) +
            "\n\nCopy .env.production.example to .env and fill in all values."
        )

    if invalid:
        raise StartupValidationError(
            "INVALID PRODUCTION ENVIRONMENT VARIABLES:\n" + "\n".join(invalid)
        )

    # Check recommended vars (warnings only)
    if not skip_optional:
        for var_name, description in RECOMMENDED_VARS:
            if not os.environ.get(var_name, "").strip():
                warnings.append(f"  {var_name}: {description} (recommended)")

    return warnings


def print_validation_summary(warnings: List[str]) -> None:
    """Print startup validation summary to stdout."""
    print("=" * 60)
    print("DJ AI OS - Production Startup Validation")
    print("=" * 60)
    print("[OK] All required environment variables validated")
    if warnings:
        print("\n[WARN] Recommended variables not set:")
        for w in warnings:
            print(w)
    print("=" * 60)


def run_startup_validation() -> None:
    """
    Run validation and exit on failure.
    Call this early in server startup (before FastAPI app creation).
    """
    # Allow skipping validation for local dev / tests
    if os.environ.get("DJ_AI_OS_SKIP_STARTUP_VALIDATION", "").lower() in ("1", "true", "yes"):
        print("[WARN] Startup validation SKIPPED (DJ_AI_OS_SKIP_STARTUP_VALIDATION=1)")
        return

    # Only enforce in production-like environments
    is_production = (
        os.environ.get("DJ_AI_OS_DATABASE_URL", "").startswith("postgresql") or
        os.environ.get("DJ_AI_OS_API_URL", "").startswith("https://") or
        os.environ.get("ENVIRONMENT", "").lower() in ("production", "prod", "staging")
    )

    if not is_production:
        print("[INFO] Development environment detected - skipping strict production validation")
        print("   Set DJ_AI_OS_DATABASE_URL to postgresql+asyncpg:// to enable validation")
        return

    try:
        warnings = validate_production_env()
        print_validation_summary(warnings)
    except StartupValidationError as e:
        print("=" * 60, file=sys.stderr)
        print("[FAIL] STARTUP VALIDATION FAILED", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(str(e), file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        sys.exit(1)