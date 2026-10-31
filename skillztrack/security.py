"""Password hashing, session tokens and CSRF tokens - all with the standard library."""
import hashlib
import hmac
import secrets

from . import config


def hash_password(password, iterations=None):
    iterations = iterations or config.PBKDF2_ITERATIONS
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(password, stored):
    try:
        _, iterations, salt, digest = stored.split("$")
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(candidate, digest)  # constant-time comparison


def new_token():
    return secrets.token_urlsafe(32)


def hash_token(token):
    """We store only a hash of the session token, so a leaked database can't be used to hijack sessions."""
    return hashlib.sha256(token.encode()).hexdigest()


def tokens_match(a, b):
    return bool(a) and bool(b) and hmac.compare_digest(a, b)
