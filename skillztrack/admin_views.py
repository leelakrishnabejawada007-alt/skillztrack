"""
Admin panel (/admin) - only for users with is_admin = 1.

Instead of writing five near-identical CRUD page sets, one configuration dict (TABLES)
describes each table's fields, and a few generic views handle list / create / edit / delete.
Table and column names only ever come from this dict, never from user input, so the
dynamic SQL below is safe; all VALUES are passed as ? parameters.
"""
import re
import sqlite3

from .web import HTTPError, redirect, render, route

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


# ------------------------------------------------------------------ dashboard
@route("GET", "/admin", admin=True)
def admin_index(req):
    counts = {t: req.conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
              for t in ("users", "careers", "skills", "resources", "roadmaps")}
    recent = req.conn.execute("SELECT username, email, created_at FROM users ORDER BY id DESC LIMIT 5").fetchall()
    return render(req, "admin/index.html", counts=counts, recent=recent, tables=TABLES)


# ---------------------------------------------------------------------- users
@route("GET", "/admin/users", admin=True)
def admin_users(req):
    users = req.conn.execute(
        "SELECT u.id, u.username, u.email, u.full_name, u.is_admin, u.created_at, c.title AS career, "
        "(SELECT COUNT(*) FROM milestones m JOIN roadmaps r ON r.id = m.roadmap_id WHERE r.user_id = u.id AND m.status='completed') AS done "
        "FROM users u LEFT JOIN careers c ON c.id = u.target_career_id ORDER BY u.id").fetchall()
    return render(req, "admin/users.html", users=users, tables=TABLES)


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
