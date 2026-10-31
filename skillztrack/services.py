"""
Domain logic: users, assessment, roadmap generation and progress.

Views stay thin ("read request -> call a service -> render a template").
The actual *rules* (gap, priority, ordering, resource choice) live in engine.py;
this module only moves data between SQLite and the engine.
"""
import json
import sqlite3
from collections import defaultdict

from . import assessments, engine, events, insights, security
from .levels import level_label

IMPORTANCE_LABELS = {1: "nice to have", 2: "important", 3: "core"}
DIFFICULTY_RANK = {"beginner": 0, "intermediate": 1, "advanced": 2}
STATUSES = ("not_started", "in_progress", "completed")


# ----------------------------------------------------------------------------- users
def create_user(conn, username, email, full_name, password):
    cur = conn.execute(
        "INSERT INTO users (username, email, full_name, password_hash) VALUES (?,?,?,?)",
        (username, email.lower(), full_name, security.hash_password(password)),
    )
    return cur.lastrowid


def find_user_for_login(conn, identifier):
    return conn.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?", (identifier, identifier.lower())
    ).fetchone()


def get_user(conn, user_id):
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


# ------------------------------------------------------------------------- catalogue
def list_careers(conn):
    return conn.execute(
        "SELECT c.*, COUNT(cs.id) AS skill_count FROM careers c "
        "LEFT JOIN career_skills cs ON cs.career_id = c.id GROUP BY c.id ORDER BY c.title"
    ).fetchall()


def get_career(conn, career_id):
    return conn.execute("SELECT * FROM careers WHERE id = ?", (career_id,)).fetchone()


def get_career_by_slug(conn, slug):
    return conn.execute("SELECT * FROM careers WHERE slug = ?", (slug,)).fetchone()


def requirement_rows(conn, career_id):
    return conn.execute(
        "SELECT cs.*, s.name, s.slug AS skill_slug, s.description, s.category FROM career_skills cs "
        "JOIN skills s ON s.id = cs.skill_id WHERE cs.career_id = ? ORDER BY cs.sequence, s.name",
        (career_id,),
    ).fetchall()


def requirements_for(conn, career_id):
    return [
        engine.Requirement(r["skill_id"], r["name"], r["required_level"], r["importance"], r["sequence"])
        for r in requirement_rows(conn, career_id)
    ]


# ------------------------------------------------------------------------ assessment
# Two different things are stored per skill, and they are deliberately never mixed:
#   claimed level   (table `assessments`)  what the student SAYS - used for calibration and to choose a first assignment
#   verified level  (table `skill_scores`) what graded assignments PROVED - the only input to gap analysis and roadmaps
def ratings_for(conn, user_id):
    """Self-ratings (claims). NOT used for gap analysis."""
    return {r["skill_id"]: r["level"] for r in conn.execute(
        "SELECT skill_id, level FROM assessments WHERE user_id = ?", (user_id,))}


def levels_for(conn, user_id):
    """Verified levels from graded assignments. Skills without evidence are absent (= treated as level 0, unverified)."""
    return assessments.verified_levels(conn, user_id)


def career_skill_ids(conn, career_id):
    return [r["skill_id"] for r in conn.execute("SELECT skill_id FROM career_skills WHERE career_id = ?", (career_id,))]


def has_assessed(conn, user_id, career_id):
    """True once at least one graded assignment exists for a skill this career needs."""
    return assessments.has_evidence(conn, user_id, career_skill_ids(conn, career_id))


def save_ratings(conn, user_id, levels):
    for skill_id, level in levels.items():
        conn.execute(
            "INSERT INTO assessments (user_id, skill_id, level) VALUES (?,?,?) "
            "ON CONFLICT(user_id, skill_id) DO UPDATE SET level = excluded.level, updated_at = datetime('now')",
            (user_id, skill_id, engine.clamp_level(level)))


def analyze(conn, user_id, career_id):
    return engine.analyze(requirements_for(conn, career_id), levels_for(conn, user_id))


def classify_for_display(analysis):
    """Split results into the three groups the student sees."""
    mastered = [g for g in analysis.gaps if g.gap == 0]
    missing = [g for g in analysis.weaknesses if g.current_level == 0]
    improve = [g for g in analysis.weaknesses if g.current_level > 0]
    return {"mastered": mastered, "improve": improve, "missing": missing}


# ------------------------------------------------------------------------ career goal
def set_target_career(conn, user_id, career_id):
    """Changing the career retires the old roadmap (it was built for a different career)."""
    user = get_user(conn, user_id)
    if user["target_career_id"] != career_id:
        conn.execute("UPDATE roadmaps SET is_active = 0 WHERE user_id = ? AND is_active = 1", (user_id,))
    conn.execute("UPDATE users SET target_career_id = ? WHERE id = ?", (career_id, user_id))


# --------------------------------------------------------------------------- roadmap
def active_roadmap(conn, user_id):
    return conn.execute("SELECT * FROM roadmaps WHERE user_id = ? AND is_active = 1", (user_id,)).fetchone()


def _reason(plan, gap, career_title, prof):
    need = f"{career_title} needs {gap.name} at level {gap.required_level} ({level_label(gap.required_level)})."
    if prof and prof["verified"]:
        evidence = (f"Your VERIFIED score is {prof['score']:.1f}/5 (level {prof['level']}, {prof['confidence']} confidence, "
                    f"from {prof['assignments']} assignment{'s' if prof['assignments'] != 1 else ''}), a gap of {gap.gap}.")
    else:
        evidence = ("You have no graded assignment for this skill yet, so it counts as level 0. Passing its assignments at this "
                    "level completes the milestone automatically.")
    parts = [need, evidence]
    if prof and prof["weak"]:
        parts.append("Weak topics in your attempts: " + ", ".join(t.topic for t in prof["weak"][:4]) + ".")
    parts.append(f"It is {IMPORTANCE_LABELS.get(gap.importance, 'important')} for this career, so its priority score is "
                 f"{gap.gap} x {gap.importance} = {gap.priority}.")
    if plan.is_priority:
        parts.append("It is one of your top three priorities.")
    parts.append(f"It is step {plan.sequence} because it builds on the skills placed before it in this career's learning order.")
    return " ".join(parts)


def generate_roadmap(conn, user_id, career_id, hours_per_week):
    """(Re)build the active roadmap from the current assessment.

    Progress is preserved: ticked resources carry over, and milestones the student
    already completed stay in the roadmap as 'completed'.
    Returns the new roadmap id, or None when there is nothing left to learn.
    """
    career = get_career(conn, career_id)
    analysis = analyze(conn, user_id, career_id)
    weaknesses = analysis.weaknesses
    gap_by_skill = {g.skill_id: g for g in weaknesses}

    old = active_roadmap(conn, user_id)
    carried_done, carried_ticks = {}, {}
    if old and old["career_id"] == career_id:
        for m in conn.execute("SELECT * FROM milestones WHERE roadmap_id = ?", (old["id"],)):
            for it in conn.execute("SELECT resource_id, done FROM milestone_resources WHERE milestone_id = ?", (m["id"],)):
                carried_ticks[(m["skill_id"], it["resource_id"])] = it["done"]
            if m["status"] == "completed":
                carried_done[m["skill_id"]] = m
    if old:
        conn.execute("UPDATE roadmaps SET is_active = 0 WHERE id = ?", (old["id"],))

    keep_done = {sid: m for sid, m in carried_done.items() if sid not in gap_by_skill}
    if not weaknesses and not keep_done:
        return None

    roadmap_id = conn.execute(
        "INSERT INTO roadmaps (user_id, career_id, hours_per_week, readiness) VALUES (?,?,?,?)",
        (user_id, career_id, hours_per_week, analysis.readiness_percent),
    ).lastrowid

    plans = engine.plan_milestones(weaknesses, hours_per_week)
    profile = assessments.skill_profile(conn, user_id, [p.skill_id for p in plans])
    pool = defaultdict(list)
    for r in conn.execute(
        f"SELECT id, skill_id, difficulty, hours, is_free FROM resources WHERE skill_id IN "
        f"({','.join('?' * max(1, len(plans)))})", [p.skill_id for p in plans] or [0]):
        pool[r["skill_id"]].append(engine.ResourceInfo(r["id"], r["difficulty"], r["hours"], bool(r["is_free"])))

    for plan in plans:
        gap = gap_by_skill[plan.skill_id]
        mid = conn.execute(
            "INSERT INTO milestones (roadmap_id, skill_id, sequence, title, reason, from_level, target_level, hours, "
            "start_week, end_week, is_priority, focus_topics) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (roadmap_id, plan.skill_id, plan.sequence, f"{plan.name}: reach {level_label(plan.target_level)}",
             _reason(plan, gap, career["title"], profile.get(plan.skill_id)), plan.from_level, plan.target_level,
             plan.estimated_hours, plan.start_week, plan.end_week, int(plan.is_priority),
             json.dumps([t.topic for t in profile.get(plan.skill_id, {}).get("weak", [])[:4]])),
        ).lastrowid
        any_done = False
        for rid in engine.pick_resources(pool[plan.skill_id], plan.difficulty_bands):
            done = carried_ticks.get((plan.skill_id, rid), 0)
            any_done = any_done or bool(done)
            conn.execute("INSERT INTO milestone_resources (milestone_id, resource_id, done) VALUES (?,?,?)", (mid, rid, done))
        if any_done:
            conn.execute("UPDATE milestones SET status = 'in_progress' WHERE id = ?", (mid,))

    for skill_id, m in keep_done.items():  # keep finished work visible
        mid = conn.execute(
            "INSERT INTO milestones (roadmap_id, skill_id, sequence, title, reason, from_level, target_level, hours, "
            "start_week, end_week, is_priority, status, completed_at) VALUES (?,?,?,?,?,?,?,?,0,0,0,'completed',?)",
            (roadmap_id, skill_id, m["sequence"], m["title"], m["reason"], m["from_level"], m["target_level"],
             m["hours"], m["completed_at"]),
        ).lastrowid
        for it in conn.execute("SELECT resource_id, done FROM milestone_resources WHERE milestone_id = ?", (m["id"],)):
            conn.execute("INSERT INTO milestone_resources (milestone_id, resource_id, done) VALUES (?,?,?)",
                         (mid, it["resource_id"], it["done"]))
    return roadmap_id


def roadmap_view(conn, roadmap_id):
    """Everything the roadmap page needs, as plain dicts."""
    roadmap = conn.execute(
        "SELECT r.*, c.title AS career_title FROM roadmaps r JOIN careers c ON c.id = r.career_id WHERE r.id = ?",
        (roadmap_id,)).fetchone()
    milestones = []
    profile = assessments.skill_profile(
        conn, roadmap["user_id"], [r["skill_id"] for r in conn.execute("SELECT skill_id FROM milestones WHERE roadmap_id = ?", (roadmap_id,))])
    for m in conn.execute(
        "SELECT m.*, s.name AS skill_name FROM milestones m JOIN skills s ON s.id = m.skill_id "
        "WHERE m.roadmap_id = ? ORDER BY m.sequence", (roadmap_id,)):
        items = conn.execute(
            "SELECT mr.id, mr.done, r.title, r.url, r.provider, r.rtype, r.difficulty, r.hours, r.is_free "
            "FROM milestone_resources mr JOIN resources r ON r.id = mr.resource_id WHERE mr.milestone_id = ? ORDER BY mr.id",
            (m["id"],)).fetchall()
        done = sum(1 for i in items if i["done"])
        d = dict(m)
        prof = profile.get(m["skill_id"])
        if m["status"] != "completed" and m["end_week"]:
            first, last = insights.schedule(roadmap["created_at"], m["start_week"], m["end_week"])
            d.update(start_date=insights.fmt_date(first), end_date=insights.fmt_date(last))
        d.update(items=items, done=done, total=len(items), percent=engine.progress_percent(done, len(items)),
                 from_label=level_label(m["from_level"]), target_label=level_label(m["target_level"]),
                 profile=prof, focus=json.loads(m["focus_topics"] or "[]"))
        milestones.append(d)
    completed = [m for m in milestones if m["status"] == "completed"]
    upcoming = [m for m in milestones if m["status"] != "completed"]
    return {
        "roadmap": roadmap,
        "upcoming": upcoming,
        "completed": completed,
        "percent": engine.progress_percent(len(completed), len(milestones)),
        "total_weeks": max((m["end_week"] for m in upcoming), default=0),
        "remaining_hours": sum(m["hours"] for m in upcoming),
    }


def _owned_item(conn, user_id, item_id):
    return conn.execute(
        "SELECT mr.id, mr.done, m.id AS milestone_id, m.status, m.roadmap_id FROM milestone_resources mr "
        "JOIN milestones m ON m.id = mr.milestone_id JOIN roadmaps r ON r.id = m.roadmap_id "
        "WHERE mr.id = ? AND r.user_id = ?", (item_id, user_id)).fetchone()


def set_item_done(conn, user_id, item_id, done):
    item = _owned_item(conn, user_id, item_id)
    if not item:
        return None
    conn.execute("UPDATE milestone_resources SET done = ? WHERE id = ?", (int(done), item_id))
    if done and item["status"] == "not_started":
        conn.execute("UPDATE milestones SET status = 'in_progress' WHERE id = ?", (item["milestone_id"],))
    progress = milestone_progress(conn, item["milestone_id"])
    progress["completed_now"] = bool(done)  # the item's NEW state, for the page to reflect
    if done:
        res = conn.execute("SELECT r.id, r.title FROM milestone_resources mr JOIN resources r ON r.id = mr.resource_id WHERE mr.id = ?",
                           (item_id,)).fetchone()
        events.record_once(conn, user_id, "study", f"Studied: {res['title']}", f"/roadmap#m{item['milestone_id']}", res["id"])
        progress["new_badges"] = events.after_change(conn, user_id)
    return progress


def milestone_progress(conn, milestone_id):
    m = conn.execute("SELECT id, status, roadmap_id FROM milestones WHERE id = ?", (milestone_id,)).fetchone()
    row = conn.execute("SELECT COALESCE(SUM(done),0) AS d, COUNT(*) AS t FROM milestone_resources WHERE milestone_id = ?",
                       (milestone_id,)).fetchone()
    rm = conn.execute("SELECT COALESCE(SUM(status='completed'),0) AS d, COUNT(*) AS t FROM milestones WHERE roadmap_id = ?",
                      (m["roadmap_id"],)).fetchone()
    return {
        "milestone_id": m["id"], "status": m["status"],
        "resource_done": row["d"], "resource_total": row["t"],
        "resource_percent": engine.progress_percent(row["d"], row["t"]),
        "roadmap_percent": engine.progress_percent(rm["d"], rm["t"]),
    }


def set_milestone_status(conn, user_id, milestone_id, action):
    """action: start | complete | reopen. Returns (milestone, note) or None if it is not the student's.

    A milestone can only be COMPLETED when the verified level (from graded assignments) has reached its target.
    Ticking resources shows study progress but never raises a skill level; only passing assignments does.
    """
    m = conn.execute(
        "SELECT m.* FROM milestones m JOIN roadmaps r ON r.id = m.roadmap_id WHERE m.id = ? AND r.user_id = ?",
        (milestone_id, user_id)).fetchone()
    if not m:
        return None
    note = "ok"
    if action == "complete":
        if levels_for(conn, user_id).get(m["skill_id"], 0) >= m["target_level"]:
            conn.execute("UPDATE milestones SET status='completed', completed_at=datetime('now') WHERE id = ?", (milestone_id,))
            _milestone_done(conn, user_id, m["skill_id"], m["title"])
        else:
            note = "needs_evidence"
    elif action == "reopen":
        conn.execute("UPDATE milestones SET status='in_progress', completed_at=NULL WHERE id = ?", (milestone_id,))
    elif action == "start":
        conn.execute("UPDATE milestones SET status='in_progress' WHERE id = ? AND status='not_started'", (milestone_id,))
    else:
        return None
    return m, note


def _milestone_done(conn, user_id, skill_id, title):
    """Log a completed milestone once per skill and tell the student."""
    if events.record_once(conn, user_id, "milestone", f"Completed milestone: {title}", "/roadmap", skill_id):
        events.notify(conn, user_id, "milestone", "Milestone complete", title, "/roadmap")


def refresh_after_assessment(conn, user_id, skill_id):
    """Called after a graded attempt: complete milestones the evidence now supports, then rebuild the roadmap."""
    rm = active_roadmap(conn, user_id)
    if not rm:
        return None
    level = levels_for(conn, user_id).get(skill_id, 0)
    for m in conn.execute("SELECT title FROM milestones WHERE roadmap_id = ? AND skill_id = ? AND status != 'completed' AND target_level <= ?",
                          (rm["id"], skill_id, level)).fetchall():
        _milestone_done(conn, user_id, skill_id, m["title"])
    conn.execute(
        "UPDATE milestones SET status='completed', completed_at=datetime('now') WHERE roadmap_id = ? AND skill_id = ? "
        "AND status != 'completed' AND target_level <= ?", (rm["id"], skill_id, level))
    return generate_roadmap(conn, user_id, rm["career_id"], rm["hours_per_week"])


# ---------------------------------------------------------------------------- progress
def progress_summary(conn, user):
    """Numbers for the dashboard. Overall = roadmap milestones done / milestones total."""
    summary = {"career": None, "analysis": None, "groups": None, "roadmap": None, "milestones_total": 0,
               "milestones_done": 0, "skills_ready": 0, "skills_total": 0,
               "overall_percent": 0, "up_next": [], "assessed": False}
    if not user["target_career_id"]:
        return summary
    career = get_career(conn, user["target_career_id"])
    summary["career"] = career
    summary["assessed"] = has_assessed(conn, user["id"], career["id"])
    analysis = analyze(conn, user["id"], career["id"])
    summary["analysis"] = analysis
    summary["groups"] = classify_for_display(analysis)
    summary["skills_total"] = len(analysis.gaps)
    levels = levels_for(conn, user["id"])
    summary["skills_verified"] = sum(1 for g in analysis.gaps if g.skill_id in levels)
    summary["skills_ready"] = len(analysis.strengths) if summary["assessed"] else 0


    rm = active_roadmap(conn, user["id"])
    if rm:
        view = roadmap_view(conn, rm["id"])
        summary["roadmap"] = view
        summary["milestones_total"] = len(view["upcoming"]) + len(view["completed"])
        summary["milestones_done"] = len(view["completed"])
        summary["up_next"] = view["upcoming"][:3]
    summary["overall_percent"] = engine.progress_percent(summary["milestones_done"], summary["milestones_total"])
    return summary
