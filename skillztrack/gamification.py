"""
Badges, XP, learner levels and streaks.

Like engine.py, the rules are PURE and readable; only collect() touches the database.
Everything is derived from real evidence (graded attempts, verified skill scores, completed milestones,
studied materials). Nothing is awarded for simply logging in, and nothing is random.

XP (deterministic, recomputed from stored data every time, so it can never drift):
    10 per graded attempt
  + 40 per assignment mastered (best result >= 80%)
  + 25 per verified skill level reached (sum of levels across skills)
  + 30 per milestone completed
  +  3 per study material ticked
Learner level n needs 50 * (n - 1)^2 XP (level 2 = 50, level 3 = 200, level 4 = 450 ...).
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

MASTERY_PCT = 0.80
ACTIVE_KINDS = ("attempt", "study", "milestone")

LEVEL_TITLES = ["Newcomer", "Explorer", "Builder", "Practitioner", "Specialist", "Expert", "Master"]

# code, name, description, icon, metric, target
BADGES = [
    ("first_steps", "First Steps", "Complete your first graded assignment.", "flag", "attempts", 1),
    ("mastery", "Mastery", "Score 80% or more on an assignment.", "target", "mastered", 1),
    ("flawless", "Flawless", "Score 100% on an assignment.", "sparkles", "perfect", 1),
    ("proven_trio", "Proven Trio", "Verify 3 different skills.", "layers", "skills_verified", 3),
    ("well_rounded", "Well-Rounded", "Verify 8 different skills.", "grid", "skills_verified", 8),
    ("intermediate", "Intermediate Unlocked", "Reach verified level 3 in any skill.", "trending", "max_level", 3),
    ("advanced", "Advanced Thinker", "Reach verified level 4 in any skill.", "rocket", "max_level", 4),
    ("polyglot", "Many Ways to Prove It", "Complete 4 different kinds of assignment.", "puzzle", "kinds", 4),
    ("comeback", "Comeback Kid", "Fail an assignment (under 50%), then master it (80%+).", "refresh", "comeback", 1),
    ("self_aware", "Self-Aware", "Have 3 self-ratings that match your verified level.", "scale", "calibrated", 3),
    ("pathfinder", "Pathfinder", "Generate your first roadmap.", "route", "roadmaps", 1),
    ("milestone_maker", "Milestone Maker", "Complete your first roadmap milestone.", "milestone", "milestones", 1),
    ("momentum", "Momentum", "Complete 3 roadmap milestones.", "bolt", "milestones", 3),
    ("scholar", "Dedicated Scholar", "Tick off 10 study materials.", "book", "study", 10),
    ("on_a_roll", "On a Roll", "Be active 3 days in a row.", "flame", "streak_longest", 3),
    ("week_warrior", "Week Warrior", "Be active 7 days in a row.", "calendar", "streak_longest", 7),
    ("halfway", "Halfway There", "Reach 50% readiness for your target career.", "half", "readiness", 50),
    ("career_ready", "Career Ready", "Reach 85% readiness for your target career.", "trophy", "readiness", 85),
]
BADGE_BY_CODE = {b[0]: b for b in BADGES}


# --------------------------------------------------------------------------------- pure rules
def streaks(days, today):
    """(current, longest) streak of consecutive active days. The current streak survives until the end of tomorrow's
    deadline: it counts if the last active day is today or yesterday."""
    days = sorted(set(days))
    if not days:
        return 0, 0
    longest = run = 1
    for prev, cur in zip(days, days[1:]):
        run = run + 1 if (cur - prev).days == 1 else 1
        longest = max(longest, run)
    current = 0
    if (today - days[-1]).days <= 1:
        current = 1
        for i in range(len(days) - 1, 0, -1):
            if (days[i] - days[i - 1]).days == 1:
                current += 1
            else:
                break
    return current, longest


def xp_total(stats):
    return (10 * stats["attempts"] + 40 * stats["mastered"] + 25 * stats["level_sum"]
            + 30 * stats["milestones"] + 3 * stats["study"])


def level_info(xp):
    """Learner level, its title and progress to the next one."""
    level = int(math.sqrt(xp / 50)) + 1
    floor_xp, ceil_xp = 50 * (level - 1) ** 2, 50 * level ** 2
    return {"level": level, "title": LEVEL_TITLES[min(level - 1, len(LEVEL_TITLES) - 1)], "xp": xp,
            "floor": floor_xp, "next_at": ceil_xp, "into": xp - floor_xp, "span": ceil_xp - floor_xp,
            "percent": round(100 * (xp - floor_xp) / (ceil_xp - floor_xp))}


def evaluate(stats, earned_at=None):
    """Every badge with progress. `earned_at` maps code -> timestamp for badges already stored."""
    earned_at = earned_at or {}
    out = []
    for code, name, desc, icon, metric, target in BADGES:
        value = stats.get(metric, 0) or 0
        earned = code in earned_at or value >= target
        out.append({"code": code, "name": name, "description": desc, "icon": icon, "metric": metric, "target": target,
                    "value": min(value, target), "percent": 100 if earned else round(100 * min(value, target) / target),
                    "earned": earned, "earned_at": earned_at.get(code)})
    return out


# ------------------------------------------------------------------------------------ database
def _days(conn, user_id):
    marks = ",".join("?" * len(ACTIVE_KINDS))
    rows = conn.execute(f"SELECT DISTINCT date(created_at) AS d FROM activity_log WHERE user_id = ? AND kind IN ({marks})",
                        (user_id, *ACTIVE_KINDS)).fetchall()
    return {date.fromisoformat(r["d"]) for r in rows}


def collect(conn, user_id):
    """Real numbers for the badge rules, read from the database."""
    from . import assessments, services  # local imports: services imports this package's events module

    best = conn.execute(
        "SELECT a.id, a.kind, MAX(at.pct) AS best, COUNT(*) AS n FROM attempts at JOIN assignments a ON a.id = at.assignment_id "
        "WHERE at.user_id = ? AND at.status = 'graded' GROUP BY a.id", (user_id,)).fetchall()
    attempts = conn.execute("SELECT COUNT(*) AS n FROM attempts WHERE user_id = ? AND status = 'graded'", (user_id,)).fetchone()["n"]
    comeback = conn.execute(
        "SELECT COUNT(*) AS n FROM (SELECT at.assignment_id FROM attempts at WHERE at.user_id = ? AND at.status = 'graded' "
        "GROUP BY at.assignment_id HAVING MIN(CASE WHEN at.attempt_no = 1 THEN at.pct END) < 0.5 AND MAX(at.pct) >= ?)",
        (user_id, MASTERY_PCT)).fetchone()["n"]
    scores = conn.execute("SELECT skill_id, level FROM skill_scores WHERE user_id = ?", (user_id,)).fetchall()
    profile = assessments.skill_profile(conn, user_id, [r["skill_id"] for r in scores])
    count = lambda kind: conn.execute("SELECT COUNT(DISTINCT ref) AS n FROM activity_log WHERE user_id = ? AND kind = ?",
                                      (user_id, kind)).fetchone()["n"]
    current, longest = streaks(_days(conn, user_id), datetime.now(timezone.utc).date())

    readiness, user = None, services.get_user(conn, user_id)
    if user["target_career_id"] and scores:
        readiness = services.analyze(conn, user_id, user["target_career_id"]).readiness_percent

    return {
        "attempts": attempts,
        "mastered": sum(1 for r in best if (r["best"] or 0) >= MASTERY_PCT),
        "perfect": sum(1 for r in best if (r["best"] or 0) >= 0.999),
        "kinds": len({r["kind"] for r in best}),
        "comeback": comeback,
        "skills_verified": len(scores),
        "max_level": max((r["level"] for r in scores), default=0),
        "level_sum": sum(r["level"] for r in scores),
        "calibrated": sum(1 for p in profile.values() if p["verified"] and p["calibration"] == "calibrated"),
        "roadmaps": conn.execute("SELECT COUNT(*) AS n FROM roadmaps WHERE user_id = ?", (user_id,)).fetchone()["n"],
        "milestones": count("milestone"),
        "study": count("study"),
        "streak_current": current, "streak_longest": longest,
        "readiness": readiness or 0,
    }


def earned_map(conn, user_id):
    return {r["code"]: r["earned_at"] for r in conn.execute("SELECT code, earned_at FROM achievements WHERE user_id = ?", (user_id,))}


def overview(conn, user_id):
    """Everything a page needs to show badges, XP, level and streak."""
    stats = collect(conn, user_id)
    badges = evaluate(stats, earned_map(conn, user_id))
    return {"stats": stats, "badges": badges, "earned": sorted((b for b in badges if b["earned"]), key=lambda b: b["earned_at"] or "", reverse=True),
            "locked": sorted((b for b in badges if not b["earned"]), key=lambda b: -b["percent"]),
            "xp": level_info(xp_total(stats)), "streak": stats["streak_current"], "longest": stats["streak_longest"]}
