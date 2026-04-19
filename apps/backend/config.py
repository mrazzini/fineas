"""Runtime configuration read from environment variables.

Keeps the bare-`os.getenv` style used elsewhere in the codebase rather than
pulling in pydantic-settings. `APP_ENV=production` triggers fail-fast checks
for secrets that must never run with defaults in production.
"""
import os


APP_ENV = os.getenv("APP_ENV", "development")

# Owner auth
OWNER_PASSWORD_HASH = os.getenv("FINEAS_OWNER_PASSWORD_HASH", "")
SESSION_SECRET = os.getenv("FINEAS_SESSION_SECRET", "")
SESSION_MAX_AGE = int(os.getenv("FINEAS_SESSION_MAX_AGE", "86400"))
SESSION_COOKIE_NAME = "fineas_session"

# Data-load guardrails
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB per CSV


def is_production() -> bool:
    return APP_ENV == "production"


def assert_auth_configured() -> None:
    """Refuse to boot in production without auth secrets configured."""
    if is_production():
        missing = [
            name
            for name, value in (
                ("FINEAS_OWNER_PASSWORD_HASH", OWNER_PASSWORD_HASH),
                ("FINEAS_SESSION_SECRET", SESSION_SECRET),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                f"Missing required auth env vars in production: {', '.join(missing)}"
            )
