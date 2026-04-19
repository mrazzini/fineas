"""Password verification + signed-session cookie utilities.

Single-owner model: one bcrypt hash in the environment. Successful login
issues a timestamp-signed token carried in an HttpOnly cookie; the
dependencies below check that token on subsequent requests.
"""
from fastapi import HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner
from passlib.context import CryptContext

import config

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token payload is just a constant — it proves the signer knew the secret,
# which is all we need for a single-owner app.
_TOKEN_PAYLOAD = "owner"


def _signer() -> TimestampSigner:
    if not config.SESSION_SECRET:
        # In development we still want login to work if the developer set
        # a hash but forgot the secret; fall back to a loud default.
        if config.is_production():
            raise RuntimeError("FINEAS_SESSION_SECRET must be set in production")
        return TimestampSigner("insecure-development-secret")
    return TimestampSigner(config.SESSION_SECRET)


def verify_password(plain: str) -> bool:
    """Constant-time verify against the configured bcrypt hash."""
    if not config.OWNER_PASSWORD_HASH:
        return False
    try:
        return _pwd_context.verify(plain, config.OWNER_PASSWORD_HASH)
    except ValueError:
        # Malformed hash in env — treat as failed login rather than 500.
        return False


def create_session_token() -> str:
    return _signer().sign(_TOKEN_PAYLOAD).decode("utf-8")


def is_valid_session(token: str | None) -> bool:
    if not token:
        return False
    try:
        _signer().unsign(token, max_age=config.SESSION_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def current_owner(request: Request) -> bool:
    """Non-raising dependency — True if the caller has a valid session cookie."""
    return is_valid_session(request.cookies.get(config.SESSION_COOKIE_NAME))


def require_owner(request: Request) -> bool:
    """Raising variant — use on mutating endpoints that must be authenticated."""
    if not current_owner(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return True


def owner_scope(is_authed: bool) -> str:
    """Map auth state to the data-owner discriminator used in queries."""
    return "real" if is_authed else "demo"
