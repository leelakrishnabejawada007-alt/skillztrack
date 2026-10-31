"""Public and student-facing pages."""
import re
import sqlite3

from . import assessments, events, gamification, insights, security, services
from .levels import LEVEL_CHOICES
from .web import (Response, HTTPError, clear_attempts, end_session, json_response, record_failed_attempt, redirect,
                  render, route, safe_next, start_session, too_many_attempts)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_password(password, username=""):
    return services.password_problem(password, username)


# --------------------------------------------------------------------- public
@route("GET", "/")
def home(req):
    careers = services.list_careers(req.conn)
    count = lambda sql: req.conn.execute(sql).fetchone()["n"]
    stats = {"careers": len(careers), "skills": count("SELECT COUNT(*) AS n FROM skills"),
             "assignments": count("SELECT COUNT(*) AS n FROM assignments"), "resources": count("SELECT COUNT(*) AS n FROM resources")}
    # The hero preview shows a REAL career from the catalogue (the one with the most required skills), not made-up numbers.
    preview = None
    if careers:
        top = max(careers, key=lambda c: c["skill_count"])
        preview = {"career": top, "rows": services.requirement_rows(req.conn, top["id"])[:4]}
    return render(req, "home.html", careers=careers, stats=stats, preview=preview)


@route("GET", "/careers/<slug:slug>")
def career_detail(req, slug):
    career = services.get_career_by_slug(req.conn, slug)
    if not career:
        raise HTTPError(404, "That career does not exist.")
    rows = services.requirement_rows(req.conn, career["id"])
    mine = None
    if req.user:
        match = next((m for m in insights.career_match(req.conn, req.user["id"], req.user["target_career_id"]) if m["id"] == career["id"]), None)
        profile = assessments.skill_profile(req.conn, req.user["id"], [r["skill_id"] for r in rows])
        levels = {sid: p["level"] for sid, p in profile.items() if p["verified"]}
        mine = {"match": match, "levels": levels, "level_list": [round(profile[r["skill_id"]]["score"], 2) for r in rows]}
    return render(req, "career_detail.html", career=career, requirements=rows, mine=mine,
                  importance_labels=services.IMPORTANCE_LABELS)


# ----------------------------------------------------------------------- auth
@route("GET", "/register")
def register_form(req):
    if req.user:
        return redirect("/dashboard")
    return render(req, "auth/register.html", errors={}, values={})


@route("POST", "/register")
def register_submit(req):
    values = {"username": req.post("username"), "full_name": req.post("full_name"), "email": req.post("email").lower()}
    password, confirm = req.form.get("password", [""])[0], req.form.get("password2", [""])[0]
    errors = {}
    if not USERNAME_RE.match(values["username"]):
        errors["username"] = "Use 3-30 letters, numbers, dots, dashes or underscores."
    if not 1 <= len(values["full_name"]) <= 60:
        errors["full_name"] = "Please enter your name (up to 60 characters)."
    if not EMAIL_RE.match(values["email"]) or len(values["email"]) > 120:
        errors["email"] = "Enter a valid email address."
    pw_error = _validate_password(password, values["username"])
    if pw_error:
        errors["password"] = pw_error
    elif password != confirm:
        errors["password2"] = "The two passwords do not match."
    if not errors:
        taken = req.conn.execute("SELECT username, email FROM users WHERE username = ? OR email = ?",
                                 (values["username"], values["email"])).fetchall()
        for row in taken:
            if row["username"].lower() == values["username"].lower():
                errors["username"] = "That username is already taken."
            if row["email"].lower() == values["email"]:
                errors["email"] = "An account with this email already exists."
    if errors:
        return render(req, "auth/register.html", status=400, errors=errors, values=values)
    try:
        user_id = services.create_user(req.conn, values["username"], values["email"], values["full_name"], password)
    except sqlite3.IntegrityError:
        return render(req, "auth/register.html", status=400, errors={"username": "That account already exists."}, values=values)
    resp = redirect("/dashboard", f"Welcome to SkillzTrack, {values['full_name'].split()[0]}! Choose a career to begin.")
    start_session(req, resp, user_id)
    return resp


@route("GET", "/login")
def login_form(req):
    if req.user:
        return redirect("/dashboard")
    return render(req, "auth/login.html", error=None, next=safe_next(req.query.get("next"), ""), identifier="")


@route("POST", "/login")
def login_submit(req):
    identifier, password = req.post("identifier"), req.form.get("password", [""])[0]
    nxt = safe_next(req.post("next"), "")
    key = f"{req.ip}|{identifier.lower()}"
    if too_many_attempts(key):
        return render(req, "auth/login.html", status=429, error="Too many attempts. Please wait a few minutes.",
                      next=nxt, identifier=identifier)
    user = services.find_user_for_login(req.conn, identifier) if identifier else None
    # Always run a hash comparison so response time doesn't reveal whether the account exists.
    ok = security.verify_password(password, user["password_hash"] if user else "pbkdf2_sha256$1$x$x")
    if not (user and ok):
        record_failed_attempt(key)
        return render(req, "auth/login.html", status=400, error="Incorrect username/email or password.",
                      next=nxt, identifier=identifier)
    clear_attempts(key)
    resp = redirect(nxt or "/dashboard", f"Welcome back, {user['full_name'].split()[0] if user['full_name'] else user['username']}!")
    start_session(req, resp, user["id"])
    return resp


@route("POST", "/logout")
def logout(req):
    resp = redirect("/", "You have been logged out.", "info")
    end_session(req, resp)
    return resp


# ------------------------------------------------------------------ dashboard
@route("GET", "/dashboard", login=True)
def dashboard(req):
    summary = services.progress_summary(req.conn, req.user)
    events.after_change(req.conn, req.user["id"])  # also back-fills badges for evidence that pre-dates this feature
    ins = insights.build(req.conn, req.user, summary)
    chart = {"labels": [r["name"] for r in ins["rows"]], "verified": [round(r["score"], 2) for r in ins["rows"]],
             "required": [r["required"] for r in ins["rows"]]}
    return render(req, "dashboard.html", s=summary, careers=services.list_careers(req.conn), ins=ins, chart=chart,
                  game=gamification.overview(req.conn, req.user["id"]), activity=events.recent_activity(req.conn, req.user["id"], 6))


@route("POST", "/career", login=True)
def choose_career(req):
    career = services.get_career(req.conn, req.post_int("career_id", 0))
    if not career:
        raise HTTPError(400, "Please choose a valid career.")
    services.set_target_career(req.conn, req.user["id"], career["id"])
    events.record(req.conn, req.user["id"], "career", f"Set {career['title']} as target career", "/dashboard")
    return redirect("/assignments", f"Target career set to {career['title']}. Now prove your skills: start with the recommended assignments.")


# ----------------------------------------------------------------- assessment
def _require_career(req):
    if not req.user["target_career_id"]:
        return redirect("/dashboard", "Choose a target career first.", "info")
    return None


@route("GET", "/assess", login=True)
def assess_form(req):
    missing = _require_career(req)
    if missing:
        return missing
    career = services.get_career(req.conn, req.user["target_career_id"])
    return render(req, "assess.html", career=career, rows=services.requirement_rows(req.conn, career["id"]),
                  ratings=services.ratings_for(req.conn, req.user["id"]), levels=LEVEL_CHOICES,
                  importance_labels=services.IMPORTANCE_LABELS, errors=None)


@route("POST", "/assess", login=True)
def assess_submit(req):
    missing = _require_career(req)
    if missing:
        return missing
    career = services.get_career(req.conn, req.user["target_career_id"])
    rows = services.requirement_rows(req.conn, career["id"])
    levels, bad = {}, []
    for r in rows:
        raw = req.post(f"skill_{r['skill_id']}")
        if raw in {"0", "1", "2", "3", "4", "5"}:
            levels[r["skill_id"]] = int(raw)
        else:
            bad.append(r["name"])
    if bad:
        return render(req, "assess.html", status=400, career=career, rows=rows, levels=LEVEL_CHOICES,
                      ratings={**services.ratings_for(req.conn, req.user["id"]), **levels},
                      importance_labels=services.IMPORTANCE_LABELS,
                      errors="Please rate every skill from 0 to 5. Missing: " + ", ".join(bad))
    services.save_ratings(req.conn, req.user["id"], levels)
    # Claims are stored for calibration only; they never change the verified profile, gaps or roadmap.
    return redirect("/assignments", "Self-ratings saved. They do not change your skill level: only graded assignments do. "
                                    "Take the recommended assignments to verify them.")


@route("GET", "/gaps", login=True)
def gaps(req):
    missing = _require_career(req)
    if missing:
        return missing
    career = services.get_career(req.conn, req.user["target_career_id"])
    if not services.has_assessed(req.conn, req.user["id"], career["id"]):
        return redirect("/assignments", "Complete at least one assignment first: gaps are calculated from what you demonstrate, not from self-ratings.", "info")
    analysis = services.analyze(req.conn, req.user["id"], career["id"])
    profile = assessments.skill_profile(req.conn, req.user["id"], [g.skill_id for g in analysis.gaps])
    chart = {"labels": [g.name for g in analysis.gaps],
             "current": [g.current_level for g in analysis.gaps],
             "required": [g.required_level for g in analysis.gaps],
             "scores": [round(profile[g.skill_id]["score"], 2) for g in analysis.gaps]}
    sim = [{"required": g.required_level, "importance": g.importance, "level": g.current_level} for g in analysis.gaps]
    return render(req, "gaps.html", sim=sim, career=career, analysis=analysis, groups=services.classify_for_display(analysis),
                  chart=chart, roadmap=services.active_roadmap(req.conn, req.user["id"]), profile=profile)


# -------------------------------------------------------------------- roadmap
@route("POST", "/roadmap/generate", login=True)
def roadmap_generate(req):
    missing = _require_career(req)
    if missing:
        return missing
    hours = req.post_int("hours_per_week", 0)
    if not 2 <= hours <= 40:
        return redirect("/gaps", "Choose between 2 and 40 study hours per week.", "danger")
    career_id = req.user["target_career_id"]
    if not services.has_assessed(req.conn, req.user["id"], career_id):
        return redirect("/assignments", "Complete at least one assignment first so the roadmap is based on evidence.", "info")
    req.conn.execute("UPDATE users SET hours_per_week = ? WHERE id = ?", (hours, req.user["id"]))
    if services.generate_roadmap(req.conn, req.user["id"], career_id, hours) is None:
        return redirect("/gaps", "Great news: you already meet every requirement for this career!")
    events.record(req.conn, req.user["id"], "roadmap", f"Generated a {hours} h/week roadmap", "/roadmap")
    events.notify(req.conn, req.user["id"], "roadmap", "Your roadmap is ready", f"Planned around {hours} study hours per week.", "/roadmap")
    new = events.after_change(req.conn, req.user["id"])
    return redirect("/roadmap", "Your personalised roadmap is ready." + (f" New badge: {', '.join(new)}." if new else ""))


@route("GET", "/roadmap", login=True)
def roadmap(req):
    rm = services.active_roadmap(req.conn, req.user["id"])
    if not rm:
        return render(req, "roadmap.html", view=None, career=services.get_career(req.conn, req.user["target_career_id"])
                      if req.user["target_career_id"] else None)
    return render(req, "roadmap.html", view=services.roadmap_view(req.conn, rm["id"]), career=None)


@route("POST", "/milestone/<int:pk>/status", login=True)
def milestone_status(req, pk):
    result = services.set_milestone_status(req.conn, req.user["id"], pk, req.post("action"))
    if result is None:
        raise HTTPError(404, "Milestone not found.")
    m, note = result
    action = req.post("action")
    if note == "needs_evidence":
        return redirect(f"/roadmap#m{pk}", "A milestone is completed by proving the skill: pass its assignments to reach the target level. "
                                         "Studying alone does not change your level.", "warning")
    new = events.after_change(req.conn, req.user["id"]) if action == "complete" else []
    message = {"complete": "Milestone complete! Your verified level has reached the target." + (f" New badge: {', '.join(new)}." if new else ""),
               "reopen": "Milestone re-opened.", "start": None}[action]
    return redirect(f"/roadmap#m{pk}", message, "success" if action == "complete" else "info")


@route("POST", "/item/<int:pk>/toggle", login=True)
def item_toggle(req, pk):
    progress = services.set_item_done(req.conn, req.user["id"], pk, req.post("done") == "1")
    if progress is None:
        raise HTTPError(404, "Item not found.")
    if req.wants_json:
        return json_response(progress)
    return redirect(f"/roadmap#m{progress['milestone_id']}")


# -------------------------------------------------------------------- profile
@route("GET", "/profile", login=True)
def profile(req):
    return render(req, "profile.html", careers=services.list_careers(req.conn), errors={}, values=dict(req.user))


@route("POST", "/profile", login=True)
def profile_submit(req):
    values = {"full_name": req.post("full_name"), "email": req.post("email").lower(),
              "hours_per_week": req.post_int("hours_per_week", 0), "target_career_id": req.post_int("target_career_id", 0)}
    errors = {}
    if not 1 <= len(values["full_name"]) <= 60:
        errors["full_name"] = "Please enter your name (up to 60 characters)."
    if not EMAIL_RE.match(values["email"]):
        errors["email"] = "Enter a valid email address."
    elif req.conn.execute("SELECT 1 FROM users WHERE email = ? AND id != ?", (values["email"], req.user["id"])).fetchone():
        errors["email"] = "Another account already uses this email."
    if not 2 <= values["hours_per_week"] <= 40:
        errors["hours_per_week"] = "Choose between 2 and 40 hours."
    career = services.get_career(req.conn, values["target_career_id"]) if values["target_career_id"] else None
    if values["target_career_id"] and not career:
        errors["target_career_id"] = "Choose a valid career."
    if errors:
        return render(req, "profile.html", status=400, careers=services.list_careers(req.conn), errors=errors, values=values)
    req.conn.execute("UPDATE users SET full_name=?, email=?, hours_per_week=? WHERE id=?",
                     (values["full_name"], values["email"], values["hours_per_week"], req.user["id"]))
    changed = career and career["id"] != req.user["target_career_id"]
    if career:
        services.set_target_career(req.conn, req.user["id"], career["id"])
    if changed:
        return redirect("/assignments", f"Career goal changed to {career['title']}. Your verified skills carry over; take assignments for any new ones.")
    return redirect("/profile", "Profile updated.")


@route("POST", "/profile/password", login=True)
def change_password(req):
    current, new, confirm = (req.form.get(k, [""])[0] for k in ("current_password", "new_password", "new_password2"))
    error = None
    if not security.verify_password(current, req.user["password_hash"]):
        error = "Your current password is incorrect."
    else:
        error = _validate_password(new, req.user["username"]) or (None if new == confirm else "The new passwords do not match.")
    if error:
        return redirect("/profile", error, "danger")
    req.conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (security.hash_password(new), req.user["id"]))
    return redirect("/profile", "Password changed.")


# ---------------------------------------------------------------------- achievements & alerts
@route("GET", "/achievements", login=True)
def achievements(req):
    return render(req, "achievements.html", game=gamification.overview(req.conn, req.user["id"]),
                  activity=events.recent_activity(req.conn, req.user["id"], 12))


@route("GET", "/notifications", login=True)
def notifications(req):
    rows = req.conn.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 60", (req.user["id"],)).fetchall()
    unread = sum(1 for r in rows if not r["is_read"])
    resp = render(req, "notifications.html", items=rows, new_count=unread)
    req.conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0", (req.user["id"],))
    return resp


@route("POST", "/notifications/clear", login=True)
def notifications_clear(req):
    req.conn.execute("DELETE FROM notifications WHERE user_id = ?", (req.user["id"],))
    return redirect("/notifications", "All notifications cleared.", "info")


@route("GET", "/api/unread", login=True)
def api_unread(req):
    return json_response({"unread": events.unread_count(req.conn, req.user["id"])})
