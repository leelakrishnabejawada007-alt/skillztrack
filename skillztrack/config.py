"""All settings in one place. Values come from environment variables, with safe local defaults."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def _env(name, default=""):
    """Read SKILLZTRACK_<name>; fall back to the legacy CAREERTRACK_<name> so existing deployments keep working."""
    return os.environ.get("SKILLZTRACK_" + name, os.environ.get("CAREERTRACK_" + name, default))


def _flag(name, default="0"):
    return _env(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _default_db():
    """New installs use skillztrack.db. An existing careertrack.db (from before the rename) is kept and reused."""
    legacy, current = BASE_DIR / "careertrack.db", BASE_DIR / "skillztrack.db"
    return str(legacy if legacy.exists() and not current.exists() else current)


# Where the SQLite file lives. On Render, point this at a persistent disk (e.g. /var/data/skillztrack.db).
DB_PATH = _env("DB") or _default_db()

# Cookies are marked Secure (HTTPS-only) in production. Keep 0 for http://localhost.
SECURE_COOKIES = _flag("SKILLZTRACK_SECURE_COOKIES")

# PBKDF2 work factor for password hashing (OWASP recommends >= 600,000 for SHA-256).
PBKDF2_ITERATIONS = int(_env("PBKDF2_ITERATIONS", "600000"))

SESSION_DAYS = 7
MAX_BODY_BYTES = 192 * 1024  # reject oversized form posts (code submissions are up to 20k characters per field)

# Run student-submitted Python against hidden tests (see skillztrack/sandbox.py for the safety model and its
# limits). Set to 0 on a public deployment unless grading runs in an isolated container.
CODE_EXEC = _flag("SKILLZTRACK_CODE_EXEC", "1")
