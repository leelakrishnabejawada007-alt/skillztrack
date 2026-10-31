"""
Personalised, rule-based insights (no AI: every number can be reproduced by hand).

    career_match()  readiness of the student's VERIFIED skills against every career, best first
    levers()        which single skill, once mastered, would raise readiness the most (and by how much)
    skill_rows()    the target career's skills with verified level vs required level
    next_steps()    up to three concrete things to do now, in priority order
    schedule()      calendar dates for roadmap milestones

readiness = sum(min(level, required) x importance) / sum(required x importance)   (same formula as engine.py)
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from . import assessments, engine, services


# ------------------------------------------------------------------------------ pure helpers
def levers(analysis, limit=3):
    """For each skill with a gap: how many readiness points would closing it add?"""
    total = sum(g.required_level * g.importance for g in analysis.gaps)
    if not total:
        return []
    out = [{"skill_id": g.skill_id, "name": g.name, "gap": g.gap, "importance": g.importance,
            "delta": round(100 * g.gap * g.importance / total, 1), "from": g.current_level, "to": g.required_level}
           for g in analysis.weaknesses]
    return sorted(out, key=lambda x: (-x["delta"], x["name"]))[:limit]


def schedule(created_at, start_week, end_week, today=None):
    """Estimated (start, end) dates of a milestone. Weeks count from the day the roadmap was generated."""
    base = datetime.fromisoformat(created_at).replace(tzinfo=timezone.utc)
    start = base + timedelta(weeks=max(0, start_week - 1))
    end = base + timedelta(weeks=max(1, end_week)) - timedelta(days=1)
    return start.date(), end.date()


def finish_date(remaining_hours, hours_per_week, today=None):
    today = today or datetime.now(timezone.utc).date()
    weeks = math.ceil(remaining_hours / max(1, hours_per_week)) if remaining_hours > 0 else 0
    return today + timedelta(weeks=weeks), weeks


def fmt_date(d):
    return f"{d.day} {d.strftime('%b')}"


# ---------------------------------------------------------------------------------- database
def career_match(conn, user_id, target_id=None):
    """Every career ranked by how ready the student's verified skills already make them."""
    levels = assessments.verified_levels(conn, user_id)
    if not levels:
        return []
    out = []
    for c in services.list_careers(conn):
        analysis = engine.analyze(services.requirements_for(conn, c["id"]), levels)
        covered = sum(1 for g in analysis.gaps if g.current_level > 0)
        out.append({"id": c["id"], "slug": c["slug"], "title": c["title"], "icon": c["icon"],
                    "readiness": analysis.readiness_percent, "met": len(analysis.strengths), "total": len(analysis.gaps),
                    "covered": covered, "is_target": c["id"] == target_id})
    return sorted(out, key=lambda m: (-m["readiness"], m["title"]))


def skill_rows(conn, user_id, career_id):
    """Target career skills: verified score/level vs required, ordered by the career's learning sequence."""
    rows = services.requirement_rows(conn, career_id)
    profile = assessments.skill_profile(conn, user_id, [r["skill_id"] for r in rows])
    out = []
    for r in rows:
        p = profile[r["skill_id"]]
        out.append({"skill_id": r["skill_id"], "name": r["name"], "category": r["category"], "required": r["required_level"],
                    "importance": r["importance"], "score": p["score"], "level": p["level"], "verified": p["verified"],
                    "met": p["level"] >= r["required_level"], "weak": [t.topic for t in p["weak"][:3]],
                    "next": p["next"], "confidence": p["confidence"]})
    return out


def next_steps(conn, user, summary, rows, lever_list):
    """Up to three prioritised actions. Rules, in order:
    1 no career -> choose one;  2 unfinished attempt -> continue it;  3 no evidence -> start with the first skill;
    4 gaps but no roadmap -> generate it;  5 biggest readiness levers -> their next assignment;
    6 weakest topic -> practise it;  7 nothing left -> compare careers."""
    steps = []

    def add(icon, title, text, href, cta):
        if all(s["href"] != href for s in steps):
            steps.append({"icon": icon, "title": title, "text": text, "href": href, "cta": cta})

    if not summary["career"]:
        add("compass", "Choose your target career", "Everything on SkillzTrack, from gaps to roadmap, is built around one goal.", "#careerPicker", "Pick a career")
        return steps
    open_attempt = conn.execute(
        "SELECT at.id, a.title FROM attempts at JOIN assignments a ON a.id = at.assignment_id "
        "WHERE at.user_id = ? AND at.status = 'in_progress' ORDER BY at.id DESC LIMIT 1", (user["id"],)).fetchone()
    if open_attempt:
        add("play", f"Continue: {open_attempt['title']}", "Your draft is saved. Pick up where you stopped.", f"/attempts/{open_attempt['id']}", "Resume")
    if not summary["assessed"]:
        first = next((r for r in rows if r["next"]), None)
        if first:
            add("clipboard", f"Start with {first['name']}", "One short assignment gives you your first verified score and unlocks your gap analysis.",
                f"/assignments/{first['next']['slug']}", "Take assignment")
        return steps[:3]
    analysis = summary["analysis"]
    if analysis.weaknesses and not summary["roadmap"]:
        add("route", "Generate your roadmap", f"{len(analysis.weaknesses)} skill gap{'s' if len(analysis.weaknesses) != 1 else ''} turned into a week-by-week plan.", "/gaps", "Build roadmap")
    by_id = {r["skill_id"]: r for r in rows}
    for lv in lever_list:
        row = by_id.get(lv["skill_id"])
        if row and row["next"]:
            add("trending", f"Raise {lv['name']} (+{lv['delta']:g}% readiness)", f"Closing this gap is your biggest single boost. Next: {row['next']['title']}.",
                f"/assignments/{row['next']['slug']}", "Practise")
    weak = next((r for r in rows if r["weak"] and not r["met"]), None)
    if weak:
        add("target", f"Strengthen {weak['weak'][0]} in {weak['name']}", "Your graded attempts show this topic is holding your score back.",
            f"/assignments#skill-{weak['skill_id']}", "See assignments")
    if not analysis.weaknesses:
        add("trophy", "You meet every requirement", "Compare your verified skills against other careers.", "/skill-profile", "See career match")
    return steps[:3]


def build(conn, user, summary):
    """Everything the dashboard needs beyond services.progress_summary()."""
    out = {"match": career_match(conn, user["id"], user["target_career_id"]), "levers": [], "rows": [], "pace": None, "steps": []}
    if summary["career"]:
        out["rows"] = skill_rows(conn, user["id"], summary["career"]["id"])
        if summary["assessed"]:
            out["levers"] = levers(summary["analysis"])
        if summary["roadmap"] and summary["roadmap"]["upcoming"]:
            view = summary["roadmap"]
            finish, weeks = finish_date(view["remaining_hours"], view["roadmap"]["hours_per_week"])
            out["pace"] = {"hours": view["remaining_hours"], "per_week": view["roadmap"]["hours_per_week"], "weeks": weeks,
                           "finish": fmt_date(finish)}
    out["steps"] = next_steps(conn, user, summary, out["rows"], out["levers"])
    return out
