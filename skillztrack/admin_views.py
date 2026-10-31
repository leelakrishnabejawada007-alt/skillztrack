"""
Admin area (/admin) - only for users with is_admin = 1.

    not signed in            -> the admin sign-in page (never the student login)
    signed in as a student   -> "Admin access only" (HTTP 403)
    signed in as an admin    -> the dashboard, with its own top bar (no student sidebar)

Admin sign-in rejects student accounts, and 5 wrong passwords lock that account out of /admin for 5 minutes.
Admins are created from the terminal only (python run.py set-admin ...); no web page can create one.

Instead of writing five near-identical CRUD page sets, one configuration dict (TABLES)
describes each table's fields, and a few generic views handle list / create / edit / delete.
Table and column names only ever come from this dict, never from user input, so the
dynamic SQL below is safe; all VALUES are passed as ? parameters.
"""
import re
import sqlite3

from . import security, services
from .web import (HTTPError, clear_attempts, end_session, record_failed_attempt, redirect, render, route, safe_next,
                  start_session, too_many_attempts)

CATEGORIES = [("programming", "Programming"), ("web", "Web development"), ("data", "Data & AI"),
              ("security", "Security & systems"), ("professional", "Professional skills")]
RTYPES = [("course", "Course"), ("video", "Video"), ("article", "Article"), ("book", "Book"),
          ("practice", "Practice"), ("docs", "Documentation")]
DIFFICULTIES = [("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced")]
IMPORTANCE = [(1, "Nice to have"), (2, "Important"), (3, "Core")]

TABLES = {
    "careers": {
        "title": "Careers", "singular": "career",
        "list_sql": "SELECT id, title, slug, icon FROM careers ORDER BY title",
        "columns": [("title", "Title"), ("slug", "Slug"), ("icon", "Icon")],
        "fields": [
            {"name": "title", "label": "Title", "kind": "text", "max": 100},
            {"name": "slug", "label": "Slug (URL name)", "kind": "slug", "max": 110},
            {"name": "tagline", "label": "Tagline", "kind": "text", "max": 160, "required": False},
            {"name": "description", "label": "Description", "kind": "textarea", "max": 1500, "required": False},
            {"name": "icon", "label": "Icon (e.g. bi-cloud, bi-database, bi-shield-lock, bi-code-slash, bi-bar-chart-line, bi-terminal)", "kind": "text", "max": 40, "default": "bi-compass"},
        ],
    },
    "skills": {
        "title": "Skills", "singular": "skill",
        "list_sql": "SELECT id, name, slug, category FROM skills ORDER BY name",
        "columns": [("name", "Name"), ("slug", "Slug"), ("category", "Category")],
        "fields": [
            {"name": "name", "label": "Name", "kind": "text", "max": 80},
            {"name": "slug", "label": "Slug", "kind": "slug", "max": 90},
            {"name": "category", "label": "Category", "kind": "select", "choices": CATEGORIES},
            {"name": "description", "label": "Description", "kind": "textarea", "max": 500, "required": False},
        ],
    },
    "career_skills": {
        "title": "Career requirements", "singular": "requirement",
        "list_sql": "SELECT cs.id, c.title AS career, s.name AS skill, cs.required_level, cs.importance, cs.sequence "
                    "FROM career_skills cs JOIN careers c ON c.id = cs.career_id JOIN skills s ON s.id = cs.skill_id "
                    "ORDER BY c.title, cs.sequence",
        "columns": [("career", "Career"), ("skill", "Skill"), ("required_level", "Target level"),
                    ("importance", "Importance"), ("sequence", "Order")],
        "fields": [
            {"name": "career_id", "label": "Career", "kind": "fk", "fk": ("careers", "title")},
            {"name": "skill_id", "label": "Skill", "kind": "fk", "fk": ("skills", "name")},
            {"name": "required_level", "label": "Required level (1-5)", "kind": "int", "min": 1, "max": 5, "default": 3},
            {"name": "importance", "label": "Importance", "kind": "select", "choices": IMPORTANCE, "default": 2},
            {"name": "sequence", "label": "Learning order (1 = first)", "kind": "int", "min": 1, "max": 99, "default": 1},
        ],
    },
    "resources": {
        "title": "Roadmap materials", "singular": "material",
        "list_sql": "SELECT r.id, r.title, s.name AS skill, r.difficulty, r.rtype, r.is_free FROM resources r "
                    "JOIN skills s ON s.id = r.skill_id ORDER BY s.name, r.title",
        "columns": [("title", "Title"), ("skill", "Skill"), ("difficulty", "Level"), ("rtype", "Type")],
        "fields": [
            {"name": "skill_id", "label": "Skill", "kind": "fk", "fk": ("skills", "name")},
            {"name": "title", "label": "Title", "kind": "text", "max": 160},
            {"name": "provider", "label": "Provider", "kind": "text", "max": 80, "required": False},
            {"name": "url", "label": "URL (must start with https://)", "kind": "url", "max": 300},
            {"name": "rtype", "label": "Type", "kind": "select", "choices": RTYPES},
            {"name": "difficulty", "label": "Difficulty", "kind": "select", "choices": DIFFICULTIES},
            {"name": "hours", "label": "Estimated hours", "kind": "int", "min": 1, "max": 500, "default": 5},
            {"name": "is_free", "label": "Free to use", "kind": "bool", "default": 1},
        ],
    },
}
SLUG_RE = re.compile(r"^[a-z0-9-]+$")


def _cfg(table):
    if table not in TABLES:
        raise HTTPError(404, "Unknown admin section.")
    return TABLES[table]


def _options(conn, field):
    if field["kind"] == "fk":
        tbl, label = field["fk"]
        return [(r["id"], r[label]) for r in conn.execute(f"SELECT id, {label} FROM {tbl} ORDER BY {label}")]
    return field.get("choices")


def _parse(req, cfg):
    values, errors = {}, {}
    for f in cfg["fields"]:
        name, kind, raw = f["name"], f["kind"], req.post(f["name"])
        required = f.get("required", True)
        if kind == "bool":
            values[name] = 1 if raw in {"1", "on"} else 0
            continue
        if not raw:
            if required:
                errors[name] = "This field is required."
            values[name] = f.get("default", "") if not required else ""
            continue
        if kind in {"text", "textarea", "url", "slug"}:
            if len(raw) > f["max"]:
                errors[name] = f"Keep this under {f['max']} characters."
            elif kind == "slug" and not SLUG_RE.match(raw):
                errors[name] = "Use lowercase letters, numbers and dashes only."
            elif kind == "url" and not re.match(r"^https?://[^\s]+$", raw):
                errors[name] = "Enter a full web address starting with http:// or https://"
            values[name] = raw
        elif kind in {"int", "fk"} or (kind == "select" and isinstance(f["choices"][0][0], int)):
            try:
                number = int(raw)
            except ValueError:
                errors[name] = "Enter a whole number."
                values[name] = raw
                continue
            if kind == "int" and not f["min"] <= number <= f["max"]:
                errors[name] = f"Enter a number from {f['min']} to {f['max']}."
            if kind == "select" and number not in {c[0] for c in f["choices"]}:
                errors[name] = "Choose one of the options."
            values[name] = number
        elif kind == "select":
            if raw not in {c[0] for c in f["choices"]}:
                errors[name] = "Choose one of the options."
            values[name] = raw
    return values, errors


def _form_context(req, cfg, values, errors, skill_ids=None):
    fields = []
    for f in cfg["fields"]:
        fields.append({**f, "value": values.get(f["name"], f.get("default", "")), "error": errors.get(f["name"]),
                       "options": _options(req.conn, f)})
    skills = req.conn.execute("SELECT id, name FROM skills ORDER BY name").fetchall() if cfg.get("m2m_skills") else None
    return {"fields": fields, "skills": skills, "selected_skills": set(skill_ids or [])}


def _save_m2m(conn, project_id, skill_ids):
    conn.execute("DELETE FROM project_skills WHERE project_id = ?", (project_id,))
    for sid in skill_ids:
        conn.execute("INSERT OR IGNORE INTO project_skills (project_id, skill_id) VALUES (?, ?)", (project_id, sid))


def _selected_skill_ids(req):
    return [int(v) for v in req.post_list("skill_ids") if v.isdigit()]


# ----------------------------------------------------------------- sign-in / out
ADMIN_MAX_FAILS = 5  # wrong passwords before the account is locked out of /admin (web.WINDOW_SECONDS = 5 minutes)
NOT_ADMIN_MESSAGE = "Incorrect email or password, or this account is not an administrator."


def _signin_page(req, error, identifier="", nxt="/admin", status=200):
    return render(req, "admin/signin.html", status=status, error=error, identifier=identifier, next=nxt)


def _admin_next(value):
    """Only ever send an admin back to a page inside /admin."""
    value = safe_next(value, "/admin")
    return value if value == "/admin" or value.startswith("/admin/") else "/admin"


@route("GET", "/admin/login")
def admin_login_form(req):
    return redirect("/admin")


@route("POST", "/admin/login")
def admin_login(req):
    identifier, password = req.post("identifier"), req.form.get("password", [""])[0]
    nxt = _admin_next(req.post("next"))
    key = "admin|" + identifier.lower()  # per account, so guessing from many addresses is limited too
    if too_many_attempts(key, ADMIN_MAX_FAILS):
        return _signin_page(req, "Too many failed attempts. Try again in 5 minutes.", identifier, nxt, 429)
    user = services.find_user_for_login(req.conn, identifier) if identifier else None
    # Always hash-compare so timing does not reveal whether the account exists.
    ok = security.verify_password(password, user["password_hash"] if user else "pbkdf2_sha256$1$x$x")
    if not (user and ok and user["is_admin"]):
        record_failed_attempt(key)  # a student with the right password is turned away and counted too
        return _signin_page(req, NOT_ADMIN_MESSAGE, identifier, nxt, 400)
    clear_attempts(key)
    old = req.cookies.get("pp_session")  # replace whoever was signed in on this browser
    if old:
        req.conn.execute("DELETE FROM sessions WHERE token_hash = ?", (security.hash_token(old),))
    resp = redirect(nxt, f"Signed in as {user['full_name'] or user['username']}.")
    start_session(req, resp, user["id"])
    return resp


@route("POST", "/admin/logout")
def admin_logout(req):
    resp = redirect("/admin", "You have been signed out.", "info")
    end_session(req, resp)
    return resp


# ------------------------------------------------------------------ dashboard
@route("GET", "/admin", admin=True)
def admin_index(req):
    def one(sql):
        return req.conn.execute(sql).fetchone()[0]
    stats = {
        "students": one("SELECT COUNT(*) FROM users WHERE is_admin = 0"),
        "not_started": one("SELECT COUNT(*) FROM users u WHERE u.is_admin = 0 AND NOT EXISTS "
                           "(SELECT 1 FROM attempts a WHERE a.user_id = u.id AND a.status = 'graded')"),
        "roadmaps": one("SELECT COUNT(*) FROM roadmaps WHERE is_active = 1"),
        "readiness": one("SELECT AVG(readiness) FROM roadmaps WHERE is_active = 1"),
        "graded": one("SELECT COUNT(*) FROM attempts WHERE status = 'graded'"),
        "graded_week": one("SELECT COUNT(*) FROM attempts WHERE status = 'graded' AND graded_at >= datetime('now', '-7 days')"),
        "in_progress": one("SELECT COUNT(*) FROM attempts WHERE status = 'in_progress'"),
        "careers": one("SELECT COUNT(*) FROM careers"),
        "skills": one("SELECT COUNT(*) FROM skills"),
        "resources": one("SELECT COUNT(*) FROM resources"),
        "assignments": one("SELECT COUNT(*) FROM assignments"),
    }
    recent_users = req.conn.execute(
        "SELECT id, username, email, created_at FROM users WHERE is_admin = 0 ORDER BY id DESC LIMIT 5").fetchall()
    recent_attempts = req.conn.execute(
        "SELECT at.id, u.id AS user_id, u.username, a.title, at.pct, at.graded_at FROM attempts at "
        "JOIN users u ON u.id = at.user_id JOIN assignments a ON a.id = at.assignment_id "
        "WHERE at.status = 'graded' ORDER BY at.id DESC LIMIT 8").fetchall()
    return render(req, "admin/index.html", stats=stats, recent_users=recent_users, recent_attempts=recent_attempts, tables=TABLES)


@route("GET", "/admin/attempts", admin=True)
def admin_attempts(req):
    """Every graded or started attempt, newest first (read-only; per-student detail is on the user page)."""
    rows = req.conn.execute(
        "SELECT at.id, u.id AS user_id, u.username, u.full_name, a.title, a.kind, s.name AS skill, at.attempt_no, at.status, "
        "at.pct, at.skill_score, at.started_at, at.graded_at FROM attempts at JOIN users u ON u.id = at.user_id "
        "JOIN assignments a ON a.id = at.assignment_id JOIN skills s ON s.id = a.skill_id ORDER BY at.id DESC LIMIT 500").fetchall()
    return render(req, "admin/attempts.html", rows=rows, tables=TABLES)


# ---------------------------------------------------------------------- users
@route("GET", "/admin/users", admin=True)
def admin_users(req):
    users = req.conn.execute(
        "SELECT u.id, u.username, u.email, u.full_name, u.is_admin, u.created_at, c.title AS career, "
        "(SELECT COUNT(*) FROM milestones m JOIN roadmaps r ON r.id = m.roadmap_id WHERE r.user_id = u.id AND m.status='completed') AS done "
        "FROM users u LEFT JOIN careers c ON c.id = u.target_career_id ORDER BY u.id").fetchall()
    return render(req, "admin/users.html", users=users, tables=TABLES)


@route("GET", "/admin/users/<int:pk>", admin=True)
def admin_user_detail(req, pk):
    """Everything stored about one user, on one page (password hash and session tokens are never shown)."""
    from . import gamification
    q = lambda sql, *a: req.conn.execute(sql, (pk, *a)).fetchall()
    u = req.conn.execute(
        "SELECT u.id, u.username, u.email, u.full_name, u.is_admin, u.hours_per_week, u.created_at, "
        "u.target_career_id, c.title AS career FROM users u LEFT JOIN careers c ON c.id = u.target_career_id WHERE u.id = ?",
        (pk,)).fetchone()
    if not u:
        raise HTTPError(404, "User not found.")
    data = {
        "sessions": req.conn.execute("SELECT COUNT(*) AS n, MAX(expires_at) AS last FROM sessions WHERE user_id = ?", (pk,)).fetchone(),
        "self_assessment": q("SELECT s.name, a.level, a.updated_at FROM assessments a JOIN skills s ON s.id = a.skill_id WHERE a.user_id = ? ORDER BY s.name"),
        "skill_scores": q("SELECT s.name, ss.score, ss.level, ss.confidence, ss.assignments_count, ss.updated_at FROM skill_scores ss JOIN skills s ON s.id = ss.skill_id WHERE ss.user_id = ? ORDER BY ss.score DESC"),
        "score_history": q("SELECT s.name, h.score, h.level, h.created_at FROM skill_score_history h JOIN skills s ON s.id = h.skill_id WHERE h.user_id = ? ORDER BY h.id DESC LIMIT 100"),
        "roadmaps": q("SELECT r.id, c.title AS career, r.hours_per_week, r.readiness, r.is_active, r.created_at, "
                      "(SELECT COUNT(*) FROM milestones m WHERE m.roadmap_id = r.id) AS total, "
                      "(SELECT COUNT(*) FROM milestones m WHERE m.roadmap_id = r.id AND m.status = 'completed') AS done "
                      "FROM roadmaps r JOIN careers c ON c.id = r.career_id WHERE r.user_id = ? ORDER BY r.id DESC"),
        "milestones": q("SELECT m.sequence, m.title, s.name AS skill, m.from_level, m.target_level, m.hours, m.start_week, m.end_week, m.status, m.completed_at, "
                        "(SELECT COUNT(*) FROM milestone_resources mr WHERE mr.milestone_id = m.id AND mr.done = 1) AS res_done, "
                        "(SELECT COUNT(*) FROM milestone_resources mr WHERE mr.milestone_id = m.id) AS res_total "
                        "FROM milestones m JOIN roadmaps r ON r.id = m.roadmap_id JOIN skills s ON s.id = m.skill_id "
                        "WHERE r.user_id = ? AND r.is_active = 1 ORDER BY m.sequence"),
        "attempts": q("SELECT at.id, a.title, a.kind, s.name AS skill, at.attempt_no, at.status, at.pct, at.skill_score, at.started_at, at.graded_at, at.duration_seconds "
                      "FROM attempts at JOIN assignments a ON a.id = at.assignment_id JOIN skills s ON s.id = a.skill_id WHERE at.user_id = ? ORDER BY at.id DESC"),
        "projects": q("SELECT p.title, pp.status, pp.updated_at FROM project_progress pp JOIN projects p ON p.id = pp.project_id WHERE pp.user_id = ? ORDER BY pp.updated_at DESC"),
        "achievements": q("SELECT code, earned_at FROM achievements WHERE user_id = ? ORDER BY earned_at DESC"),
        "activity": q("SELECT kind, title, link, created_at FROM activity_log WHERE user_id = ? ORDER BY id DESC LIMIT 200"),
        "notifications": q("SELECT kind, title, body, is_read, created_at FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 100"),
    }
    try:
        game = gamification.overview(req.conn, pk)
    except Exception:  # never let a stats problem hide the raw data
        game = None
    return render(req, "admin/user_detail.html", u=u, d=data, game=game, tables=TABLES)


@route("POST", "/admin/users/<int:pk>/toggle-admin", admin=True)
def admin_toggle(req, pk):
    if pk == req.user["id"]:
        return redirect("/admin/users", "You cannot change your own admin status.", "warning")
    req.conn.execute("UPDATE users SET is_admin = 1 - is_admin WHERE id = ?", (pk,))
    return redirect("/admin/users", "User role updated.")


@route("POST", "/admin/users/<int:pk>/delete", admin=True)
def admin_delete_user(req, pk):
    if pk == req.user["id"]:
        return redirect("/admin/users", "You cannot delete your own account here.", "warning")
    req.conn.execute("DELETE FROM users WHERE id = ?", (pk,))
    return redirect("/admin/users", "User deleted.")


# ------------------------------------------------------------- generic CRUD
@route("GET", "/admin/<str:table>", admin=True)
def admin_list(req, table):
    cfg = _cfg(table)
    return render(req, "admin/list.html", table=table, cfg=cfg, rows=req.conn.execute(cfg["list_sql"]).fetchall(), tables=TABLES)


@route("GET", "/admin/<str:table>/new", admin=True)
def admin_new(req, table):
    cfg = _cfg(table)
    return render(req, "admin/form.html", table=table, cfg=cfg, obj=None, tables=TABLES, **_form_context(req, cfg, {}, {}))


@route("POST", "/admin/<str:table>/new", admin=True)
def admin_create(req, table):
    cfg = _cfg(table)
    values, errors = _parse(req, cfg)
    skill_ids = _selected_skill_ids(req)
    if not errors:
        cols = [f["name"] for f in cfg["fields"]]
        try:
            cur = req.conn.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                                   [values[c] for c in cols])
            if cfg.get("m2m_skills"):
                _save_m2m(req.conn, cur.lastrowid, skill_ids)
        except sqlite3.IntegrityError:
            req.conn.rollback()
            errors["__all__"] = "That record conflicts with an existing one (duplicate name/slug/URL or an invalid link)."
    if errors:
        ctx = _form_context(req, cfg, values, errors, skill_ids)
        return render(req, "admin/form.html", status=400, table=table, cfg=cfg, obj=None, tables=TABLES, form_error=errors.get("__all__"), **ctx)
    return redirect(f"/admin/{table}", f"{cfg['singular'].capitalize()} created.")


def _get_obj(req, table, pk):
    row = req.conn.execute(f"SELECT * FROM {table} WHERE id = ?", (pk,)).fetchone()
    if not row:
        raise HTTPError(404, "Record not found.")
    return row


@route("GET", "/admin/<str:table>/<int:pk>/edit", admin=True)
def admin_edit(req, table, pk):
    cfg = _cfg(table)
    obj = _get_obj(req, table, pk)
    skill_ids = [r["skill_id"] for r in req.conn.execute("SELECT skill_id FROM project_skills WHERE project_id = ?", (pk,))] \
        if cfg.get("m2m_skills") else None
    return render(req, "admin/form.html", table=table, cfg=cfg, obj=obj, tables=TABLES, **_form_context(req, cfg, dict(obj), {}, skill_ids))


@route("POST", "/admin/<str:table>/<int:pk>/edit", admin=True)
def admin_update(req, table, pk):
    cfg = _cfg(table)
    obj = _get_obj(req, table, pk)
    values, errors = _parse(req, cfg)
    skill_ids = _selected_skill_ids(req)
    if not errors:
        cols = [f["name"] for f in cfg["fields"]]
        try:
            req.conn.execute(f"UPDATE {table} SET {', '.join(c + ' = ?' for c in cols)} WHERE id = ?",
                             [values[c] for c in cols] + [pk])
            if cfg.get("m2m_skills"):
                _save_m2m(req.conn, pk, skill_ids)
        except sqlite3.IntegrityError:
            req.conn.rollback()
            errors["__all__"] = "That change conflicts with an existing record."
    if errors:
        ctx = _form_context(req, cfg, values, errors, skill_ids)
        return render(req, "admin/form.html", status=400, table=table, cfg=cfg, obj=obj, tables=TABLES, form_error=errors.get("__all__"), **ctx)
    return redirect(f"/admin/{table}", f"{cfg['singular'].capitalize()} updated.")


@route("POST", "/admin/<str:table>/<int:pk>/delete", admin=True)
def admin_delete(req, table, pk):
    cfg = _cfg(table)
    _get_obj(req, table, pk)
    req.conn.execute(f"DELETE FROM {table} WHERE id = ?", (pk,))
    return redirect(f"/admin/{table}", f"{cfg['singular'].capitalize()} deleted.", "info")
