"""
A tiny WSGI web layer built from the standard library (no web framework).

WSGI in one paragraph: a web server (gunicorn in production, wsgiref locally) calls
    application(environ, start_response)
once per HTTP request. `environ` is a dict describing the request; we call
`start_response(status, headers)` and return the response body as a list of bytes.
Everything else in this file - routing, cookies, sessions, CSRF - is built on that.
"""
import json
import logging
import mimetypes
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, quote, unquote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import config, db, events, security
from .levels import LEVEL_LABELS

log = logging.getLogger("skillztrack")

# ------------------------------------------------------------------ templates
jinja = Environment(
    loader=FileSystemLoader(str(config.TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),  # every {{ value }} is HTML-escaped by default
)
jinja.globals["LEVEL_LABELS"] = LEVEL_LABELS
jinja.globals["YEAR"] = datetime.now().year


class HTTPError(Exception):
    def __init__(self, status, message=""):
        self.status, self.message = status, message


STATUS_TEXT = {200: "OK", 303: "See Other", 400: "Bad Request", 403: "Forbidden", 404: "Not Found",
               405: "Method Not Allowed", 413: "Payload Too Large", 429: "Too Many Requests",
               500: "Internal Server Error"}


# ------------------------------------------------------------------- request
class Request:
    def __init__(self, environ):
        self.environ = environ
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        self.path = environ.get("PATH_INFO", "/") or "/"
        self.query = {k: v[0] for k, v in parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True).items()}
        self.cookies = {k: m.value for k, m in SimpleCookie(environ.get("HTTP_COOKIE", "")).items()}
        self.conn = None
        self.user = None
        self.new_csrf = None
        self.flash_consumed = False
        self._form = None

    @property
    def ip(self):
        forwarded = self.environ.get("HTTP_X_FORWARDED_FOR", "")
        return forwarded.split(",")[0].strip() if forwarded else self.environ.get("REMOTE_ADDR", "?")

    @property
    def form(self):
        if self._form is None:
            try:
                length = int(self.environ.get("CONTENT_LENGTH") or 0)
            except ValueError:
                raise HTTPError(400, "Bad request.")
            if length > config.MAX_BODY_BYTES:
                raise HTTPError(413, "Form too large.")
            body = self.environ["wsgi.input"].read(length).decode("utf-8", "replace") if length else ""
            self._form = parse_qs(body, keep_blank_values=True)
        return self._form

    def post(self, name, default=""):
        values = self.form.get(name)
        return values[0].strip() if values else default

    def post_list(self, name):
        return [v.strip() for v in self.form.get(name, [])]

    def post_int(self, name, default=None):
        try:
            return int(self.post(name))
        except ValueError:
            return default

    @property
    def csrf_token(self):
        token = self.cookies.get("pp_csrf")
        if not token:
            if not self.new_csrf:
                self.new_csrf = security.new_token()
            token = self.new_csrf
        return token

    @property
    def wants_json(self):
        return self.environ.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


# ------------------------------------------------------------------ response
class Response:
    def __init__(self, body=b"", status=200, content_type="text/html; charset=utf-8", headers=None):
        self.body = body.encode() if isinstance(body, str) else body
        self.status = status
        self.headers = [("Content-Type", content_type)] + list(headers or [])
        self.cookies = []

    def set_cookie(self, name, value, max_age=None, http_only=True):
        parts = [f"{name}={value}", "Path=/", "SameSite=Lax"]
        if http_only:
            parts.append("HttpOnly")
        if config.SECURE_COOKIES:
            parts.append("Secure")
        if max_age is not None:
            parts.append(f"Max-Age={max_age}")
        self.cookies.append("; ".join(parts))

    def delete_cookie(self, name):
        self.set_cookie(name, "", max_age=0)

    def flash(self, message, category="info"):
        assert category in {"success", "info", "warning", "danger"}
        self.set_cookie("pp_flash", quote(json.dumps({"m": message, "c": category})), max_age=60)
        return self


def redirect(location, flash=None, category="success"):
    resp = Response(b"", status=303, headers=[("Location", location)])
    if flash:
        resp.flash(flash, category)
    return resp


def json_response(data, status=200):
    return Response(json.dumps(data), status=status, content_type="application/json")


def safe_next(value, fallback="/dashboard"):
    """Only allow redirects to paths on this site (prevents open-redirect attacks)."""
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return fallback


def render(req, template, status=200, **ctx):
    flash = None
    raw = req.cookies.get("pp_flash")
    if raw:
        try:
            data = json.loads(unquote(raw))
            if data.get("c") in {"success", "info", "warning", "danger"}:
                flash = {"message": str(data.get("m", "")), "category": data["c"]}
        except ValueError:
            pass
        req.flash_consumed = True
    unread = events.unread_count(req.conn, req.user["id"]) if req.user and req.conn else 0
    nav_career = None
    if req.user and req.user["target_career_id"] and req.conn:
        nav_career = req.conn.execute("SELECT title, icon FROM careers WHERE id = ?", (req.user["target_career_id"],)).fetchone()
    ctx.update(user=req.user, csrf_token=req.csrf_token, flash=flash, path=req.path, unread=unread, nav_career=nav_career)
    return Response(jinja.get_template(template).render(**ctx), status=status)


def error_response(req, status, message=""):
    titles = {403: "Access denied", 404: "Page not found", 405: "Method not allowed", 413: "Too large",
              429: "Slow down", 400: "Bad request", 500: "Something went wrong"}
    try:
        return render(req, "error.html", status=status, code=status, title=titles.get(status, "Error"),
                      message=message or "Please go back and try again.")
    except Exception:  # last-resort plain page if even the template fails
        return Response(f"<h1>{status}</h1><p>{STATUS_TEXT.get(status, 'Error')}</p>", status=status)


# -------------------------------------------------------------------- routing
ROUTES = []


def route(method, pattern, login=False, admin=False):
    # Turn "<int:pk>" style placeholders into named regex groups.
    patterns = {"int": r"\d+", "slug": r"[a-z0-9-]+", "str": r"[a-z_]+"}
    regex = re.sub(r"<(int|slug|str):(\w+)>", lambda m: f"(?P<{m.group(2)}>{patterns[m.group(1)]})", pattern)
    compiled = re.compile(f"^{regex}$")
    int_params = set(re.findall(r"<int:(\w+)>", pattern))  # these must reach the handler as real ints

    def decorator(func):
        ROUTES.append((method, compiled, func, login or admin, admin, int_params))
        return func
    return decorator


# --------------------------------------------------------------- sessions
def load_user(req):
    token = req.cookies.get("pp_session")
    if not token:
        return None
    return req.conn.execute(
        "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ?",
        (security.hash_token(token), datetime.now(timezone.utc).isoformat()),
    ).fetchone()


def start_session(req, resp, user_id):
    req.conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (datetime.now(timezone.utc).isoformat(),))
    token = security.new_token()
    expires = datetime.now(timezone.utc) + timedelta(days=config.SESSION_DAYS)
    req.conn.execute("INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?,?,?)",
                     (security.hash_token(token), user_id, expires.isoformat()))
    resp.set_cookie("pp_session", token, max_age=config.SESSION_DAYS * 86400)


def end_session(req, resp):
    token = req.cookies.get("pp_session")
    if token:
        req.conn.execute("DELETE FROM sessions WHERE token_hash = ?", (security.hash_token(token),))
    resp.delete_cookie("pp_session")


# ------------------------------------------------------- login rate limiting
_attempts, _attempts_lock = {}, threading.Lock()
MAX_ATTEMPTS, WINDOW_SECONDS = 8, 300


def too_many_attempts(key, limit=MAX_ATTEMPTS):
    with _attempts_lock:
        fresh = [t for t in _attempts.get(key, []) if time.time() - t < WINDOW_SECONDS]
        _attempts[key] = fresh
        return len(fresh) >= limit


def record_failed_attempt(key):
    with _attempts_lock:
        _attempts.setdefault(key, []).append(time.time())


def clear_attempts(key):
    with _attempts_lock:
        _attempts.pop(key, None)


# -------------------------------------------------------------------- static
def serve_static(rel):
    target = (config.STATIC_DIR / rel).resolve()
    if config.STATIC_DIR.resolve() not in target.parents or not target.is_file():
        return None
    ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    return Response(target.read_bytes(), content_type=ctype, headers=[("Cache-Control", "public, max-age=300")])


# ------------------------------------------------------------------ dispatch
def dispatch(req):
    if req.method == "GET" and req.path.startswith("/static/"):
        return serve_static(req.path[len("/static/"):]) or error_response(req, 404)

    matched_path = False
    for method, regex, func, needs_login, needs_admin, int_params in ROUTES:
        m = regex.match(req.path)
        if not m:
            continue
        matched_path = True
        if method != req.method:
            continue
        if req.method == "POST":  # CSRF: the hidden form token must equal the cookie token
            sent = req.post("csrf_token") or req.environ.get("HTTP_X_CSRF_TOKEN", "")
            if not security.tokens_match(sent, req.cookies.get("pp_csrf")):
                raise HTTPError(403, "Security check failed. Please reload the page and try again.")
        if needs_admin:
            # The admin area has its own gate (it never sends people to the student login):
            #   not signed in -> admin sign-in page, signed in as a student -> "Admin access only" (403).
            if not req.user:
                if req.method == "GET":
                    return render(req, "admin/signin.html", error=None, identifier="", next=req.path)
                return redirect("/admin", "Please sign in as an administrator.", "info")
            if not req.user["is_admin"]:
                return render(req, "admin/denied.html", status=403)
        elif needs_login and not req.user:
            return redirect("/login?next=" + quote(req.path) if req.method == "GET" else "/login",
                            "Please log in to continue.", "info")
        params = {k: int(v) if k in int_params else v for k, v in m.groupdict().items()}
        return func(req, **params)
    raise HTTPError(405 if matched_path else 404, "That page does not exist." if not matched_path else "")


SECURITY_HEADERS = [
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "same-origin"),
    ("Content-Security-Policy",
     "default-src 'self'; script-src 'self'; "
     "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
     "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"),
]


def application(environ, start_response):
    req = Request(environ)
    req.conn = db.connect()
    try:
        try:
            req.user = load_user(req)
            resp = dispatch(req)
            req.conn.commit()
        except HTTPError as exc:
            req.conn.rollback()
            resp = error_response(req, exc.status, exc.message)
        except Exception:
            req.conn.rollback()
            log.exception("Unhandled error on %s %s", req.method, req.path)
            resp = error_response(req, 500, "An unexpected error occurred. Please try again.")
    finally:
        req.conn.close()

    if req.new_csrf:
        resp.set_cookie("pp_csrf", req.new_csrf, max_age=86400 * 30)
    if req.flash_consumed:
        resp.delete_cookie("pp_flash")
    resp.headers += SECURITY_HEADERS + [("Set-Cookie", c) for c in resp.cookies]
    resp.headers.append(("Content-Length", str(len(resp.body))))
    start_response(f"{resp.status} {STATUS_TEXT.get(resp.status, '')}", resp.headers)
    return [resp.body]


def bootstrap():
    """Create tables, load the starter catalogue the first time, and optionally create the first admin.

    Hosts like Render's free tier give no shell, so an admin can be created by setting
    SKILLZTRACK_ADMIN_USERNAME / SKILLZTRACK_ADMIN_EMAIL / SKILLZTRACK_ADMIN_PASSWORD once
    (then delete the password variable). Nothing happens if that user already exists.
    """
    import os
    from . import services

    conn = db.connect()
    try:
        db.init_db(conn)
        if conn.execute("SELECT COUNT(*) AS n FROM careers").fetchone()["n"] == 0:
            db.seed(conn)
        db.seed_assignments(conn)  # keep assignment metadata in sync with skillztrack/bank on every start
        username = config._env("ADMIN_USERNAME", "").strip()
        email = config._env("ADMIN_EMAIL", "").strip()
        password = config._env("ADMIN_PASSWORD", "")
        if username and email and len(password) >= 8:
            exists = conn.execute("SELECT 1 FROM users WHERE username = ? OR email = ?", (username, email.lower())).fetchone()
            if not exists:
                uid = services.create_user(conn, username, email, username, password)
                conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (uid,))
        conn.commit()
    finally:
        conn.close()
