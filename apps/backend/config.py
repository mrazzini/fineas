"""Runtime configuration read from environment variables."""
import os


APP_ENV = os.getenv("APP_ENV", "development")

# Owner auth — plaintext password is fine for a single-owner personal app,
# since the value only lives in the server's .env file.
OWNER_PASSWORD = os.getenv("FINEAS_OWNER_PASSWORD", "")
SESSION_SECRET = os.getenv("FINEAS_SESSION_SECRET", "")
SESSION_MAX_AGE = int(os.getenv("FINEAS_SESSION_MAX_AGE", "86400"))
SESSION_COOKIE_NAME = "fineas_session"

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB per CSV


def is_production() -> bool:
    return APP_ENV == "production"


def assert_auth_configured() -> None:
    if is_production():
        missing = [
            name
            for name, value in (
                ("FINEAS_OWNER_PASSWORD", OWNER_PASSWORD),
                ("FINEAS_SESSION_SECRET", SESSION_SECRET),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                f"Missing required auth env vars in production: {', '.join(missing)}"
            )
