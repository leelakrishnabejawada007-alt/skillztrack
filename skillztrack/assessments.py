"""
Assignment attempts, grading and the VERIFIED skill profile (the database side of the evidence engine).

    start_attempt()   -> creates an attempt (quiz questions are drawn and shuffled on the server)
    submit_attempt()  -> grades it with graders.py, stores every test/criterion as evidence,
                         then recomputes the skill score with assessment_engine.py
    skill_profile()   -> verified score, confidence, weak topics, calibration vs self-rating, next step

Self-ratings (table `assessments`) are never read for scoring. They appear here only to measure calibration.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import assessment_engine as ae
from . import bank, graders

MAX_FIELD_CHARS = 20_000


# ----------------------------------------------------------------------------------- lookup
def get_assignment(conn, slug):
    """(db_row, bank_assignment) or (None, None)."""
    row = conn.execute(
        "SELECT a.*, s.name AS skill_name, s.slug AS skill_slug FROM assignments a JOIN skills s ON s.id = a.skill_id "
        "WHERE a.slug = ? AND a.is_active = 1", (slug,)).fetchone()
    if not row:
        return None, None
    return row, bank.get(slug)


def assignments_for_skill(conn, user_id, skill_id):
    """Assignments for a skill with this student's attempt statistics."""
    stats = {r["assignment_id"]: r for r in conn.execute(
        "SELECT assignment_id, COUNT(*) AS n, MAX(pct) AS best FROM attempts WHERE user_id = ? AND status = 'graded' "
        "GROUP BY assignment_id", (user_id,))}
    open_ids = {r["assignment_id"] for r in conn.execute(
        "SELECT assignment_id FROM attempts WHERE user_id = ? AND status = 'in_progress'", (user_id,))}
    out = []
    for a in conn.execute("SELECT * FROM assignments WHERE skill_id = ? AND is_active = 1 ORDER BY ceiling, id", (skill_id,)):
        st = stats.get(a["id"])
        d = dict(a)
        d.update(used=st["n"] if st else 0, best_pct=st["best"] if st else None, in_progress=a["id"] in open_ids,
                 attempts_left=ae.max_attempts(a["ceiling"]) - (st["n"] if st else 0))
        out.append(d)
    return out


def get_attempt(conn, user_id, attempt_id):
    return conn.execute(
        "SELECT at.*, a.slug, a.title, a.kind, a.ceiling, a.evidence, a.minutes, a.skill_id, s.name AS skill_name "
        "FROM attempts at JOIN assignments a ON a.id = at.assignment_id JOIN skills s ON s.id = a.skill_id "
        "WHERE at.id = ? AND at.user_id = ?", (attempt_id, user_id)).fetchone()


def attempts_for_assignment(conn, user_id, assignment_id):
    return conn.execute(
        "SELECT id, attempt_no, pct, skill_score, graded_at FROM attempts WHERE user_id = ? AND assignment_id = ? "
        "AND status = 'graded' ORDER BY id DESC", (user_id, assignment_id)).fetchall()


# ------------------------------------------------------------------------------------ attempts
def graded_count(conn, user_id, assignment_id):
    return conn.execute("SELECT COUNT(*) AS n FROM attempts WHERE user_id = ? AND assignment_id = ? AND status = 'graded'",
                        (user_id, assignment_id)).fetchone()["n"]


def start_attempt(conn, user_id, assignment_row):
    """Return (attempt_id, None) or (None, reason). Resumes an unfinished attempt if there is one."""
    open_attempt = conn.execute(
        "SELECT id FROM attempts WHERE user_id = ? AND assignment_id = ? AND status = 'in_progress' ORDER BY id DESC LIMIT 1",
        (user_id, assignment_row["id"])).fetchone()
    if open_attempt:
        return open_attempt["id"], None
    limit = ae.max_attempts(assignment_row["ceiling"])
    if graded_count(conn, user_id, assignment_row["id"]) >= limit:
        return None, f"You have used all {limit} attempts for this assignment."
    ba = bank.get(assignment_row["slug"])
    payload = graders.make_quiz_payload(ba.spec) if ba.kind == "quiz" else {}
    cur = conn.execute("INSERT INTO attempts (user_id, assignment_id, payload) VALUES (?,?,?)",
                       (user_id, assignment_row["id"], json.dumps(payload)))
    return cur.lastrowid, None


def extract_submission(ba, payload, get):
    """Read the student's answer from a form. `get(name)` returns the posted text ('' if absent)."""
    clip = lambda v: (v or "").replace("\r\n", "\n").replace("\r", "\n")[:MAX_FIELD_CHARS]
    if ba.kind == "quiz":
        return {q["id"]: get(f"q_{q['id']}") for q in payload["questions"]}
    if ba.kind in {"code", "debug", "mutation"}:
        return {"code": clip(get("code"))}
    if ba.kind == "sql":
        return {q["id"]: clip(get(q["id"])) for q in ba.spec["questions"]}
    if ba.kind == "commands":
        return {p["id"]: clip(get(p["id"])) for p in ba.spec["prompts"]}
    return {"text": clip(get("text"))}


def save_draft(conn, attempt_id, submission):
    conn.execute("UPDATE attempts SET submission = ? WHERE id = ? AND status = 'in_progress'", (json.dumps(submission), attempt_id))


def draft_for(attempt):
    try:
        return json.loads(attempt["submission"] or "{}")
    except ValueError:
        return {}


def submit_attempt(conn, user_id, attempt, submission):
    """Grade and record an attempt. Raises graders.SubmissionRejected if it cannot be graded (nothing is recorded,
    the draft is kept). Returns a dict describing the result."""
    ba = bank.get(attempt["slug"])
    payload = json.loads(attempt["payload"] or "{}")
    save_draft(conn, attempt["id"], submission)
    result = graders.grade_submission(ba, payload, submission)

    earned, possible, pct = ae.summarise_points(result.items)
    attempt_no = graded_count(conn, user_id, attempt["assignment_id"]) + 1
    score = ae.attempt_score(attempt["ceiling"], pct, attempt_no)
    started = datetime.fromisoformat(attempt["started_at"]).replace(tzinfo=timezone.utc)
    duration = max(0, int((datetime.now(timezone.utc) - started).total_seconds()))
    cur = conn.execute(
        "UPDATE attempts SET status = 'graded', attempt_no = ?, points = ?, possible = ?, pct = ?, skill_score = ?, breakdown = ?, "
        "submission = ?, graded_at = datetime('now'), duration_seconds = ? WHERE id = ? AND user_id = ? AND status = 'in_progress'",
        (attempt_no, earned, possible, pct, score, json.dumps(result.items), json.dumps(submission), duration, attempt["id"], user_id))
    if cur.rowcount != 1:  # already graded by a concurrent request
        raise graders.SubmissionRejected("This attempt was already submitted.")
    before = conn.execute("SELECT score, level FROM skill_scores WHERE user_id = ? AND skill_id = ?",
                          (user_id, attempt["skill_id"])).fetchone()
    skill = recompute_skill(conn, user_id, attempt["skill_id"], attempt["id"])
    return {"pct": pct, "attempt_score": score, "attempt_no": attempt_no, "skill": skill,
            "before": dict(before) if before else None, "skill_id": attempt["skill_id"]}


# ------------------------------------------------------------------------------ skill scores
def _evidence_rows(conn, user_id, skill_id=None):
    sql = ("SELECT at.assignment_id, at.pct, at.attempt_no, a.ceiling, a.evidence, a.skill_id FROM attempts at "
           "JOIN assignments a ON a.id = at.assignment_id WHERE at.user_id = ? AND at.status = 'graded'")
    args = [user_id]
    if skill_id:
        sql += " AND a.skill_id = ?"
        args.append(skill_id)
    by_skill = {}
    for r in conn.execute(sql, args):
        by_skill.setdefault(r["skill_id"], []).append(
            ae.AttemptEvidence(r["assignment_id"], r["ceiling"], r["evidence"], r["pct"] or 0.0, r["attempt_no"]))
    return by_skill


def recompute_skill(conn, user_id, skill_id, attempt_id=None):
    """Derive the skill score from ALL graded attempts and persist it (plus a history point)."""
    result = ae.skill_score(_evidence_rows(conn, user_id, skill_id).get(skill_id, []))
    if result is None:
        conn.execute("DELETE FROM skill_scores WHERE user_id = ? AND skill_id = ?", (user_id, skill_id))
        return None
    conn.execute(
        "INSERT INTO skill_scores (user_id, skill_id, score, level, confidence, assignments_count) VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(user_id, skill_id) DO UPDATE SET score = excluded.score, level = excluded.level, "
        "confidence = excluded.confidence, assignments_count = excluded.assignments_count, updated_at = datetime('now')",
        (user_id, skill_id, result.score, result.level, result.confidence, result.assignments))
    conn.execute("INSERT INTO skill_score_history (user_id, skill_id, attempt_id, score, level) VALUES (?,?,?,?,?)",
                 (user_id, skill_id, attempt_id, result.score, result.level))
    return result


def rebuild_scores(conn, user_id=None):
    """Recompute every stored skill score from raw attempts (use after changing the bank or the scoring rules)."""
    users = [user_id] if user_id else [r["id"] for r in conn.execute("SELECT id FROM users")]
    for uid in users:
        by_skill = _evidence_rows(conn, uid)
        conn.execute("DELETE FROM skill_scores WHERE user_id = ?", (uid,))
        for skill_id, evs in by_skill.items():
            r = ae.skill_score(evs)
            conn.execute("INSERT INTO skill_scores (user_id, skill_id, score, level, confidence, assignments_count) VALUES (?,?,?,?,?,?)",
                         (uid, skill_id, r.score, r.level, r.confidence, r.assignments))


def verified_levels(conn, user_id):
    """{skill_id: level} for skills with evidence. Skills without evidence are simply absent."""
    return {r["skill_id"]: r["level"] for r in conn.execute("SELECT skill_id, level FROM skill_scores WHERE user_id = ?", (user_id,))}


def has_evidence(conn, user_id, skill_ids):
    ids = list(skill_ids)
    if not ids:
        return False
    marks = ",".join("?" * len(ids))
    return conn.execute(f"SELECT 1 FROM skill_scores WHERE user_id = ? AND skill_id IN ({marks}) LIMIT 1", [user_id, *ids]).fetchone() is not None


# ------------------------------------------------------------------------------------ profile
def _latest_breakdowns(conn, user_id):
    """{skill_id: [breakdown list of the LATEST graded attempt of each assignment]}"""
    out = {}
    for r in conn.execute(
        "SELECT a.skill_id, at.breakdown FROM attempts at JOIN assignments a ON a.id = at.assignment_id "
        "WHERE at.user_id = ? AND at.status = 'graded' AND at.id = (SELECT MAX(x.id) FROM attempts x "
        "WHERE x.user_id = at.user_id AND x.assignment_id = at.assignment_id AND x.status = 'graded')", (user_id,)):
        out.setdefault(r["skill_id"], []).append(json.loads(r["breakdown"]))
    return out


def skill_profile(conn, user_id, skill_ids):
    """Verified profile for each skill id: {skill_id: dict}. Skills without evidence have verified=False."""
    ids = list(dict.fromkeys(skill_ids))
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    stored = {r["skill_id"]: r for r in conn.execute(
        f"SELECT * FROM skill_scores WHERE user_id = ? AND skill_id IN ({marks})", [user_id, *ids])}
    claims = {r["skill_id"]: r["level"] for r in conn.execute(
        f"SELECT skill_id, level FROM assessments WHERE user_id = ? AND skill_id IN ({marks})", [user_id, *ids])}
    evidence = _evidence_rows(conn, user_id)
    breakdowns = _latest_breakdowns(conn, user_id)
    stats = {r["assignment_id"]: (r["n"], r["best"]) for r in conn.execute(
        "SELECT assignment_id, COUNT(*) AS n, MAX(pct) AS best FROM attempts WHERE user_id = ? AND status = 'graded' GROUP BY assignment_id",
        (user_id,))}
    profile = {}
    for sid in ids:
        row, claimed = stored.get(sid), claims.get(sid)
        options = [ae.AssignmentOption(a["id"], a["slug"], a["ceiling"], stats.get(a["id"], (0, None))[0], stats.get(a["id"], (0, None))[1])
                   for a in conn.execute("SELECT id, slug, ceiling FROM assignments WHERE skill_id = ? AND is_active = 1", (sid,))]
        score = row["score"] if row else 0.0
        nxt = ae.recommend_next(options, score, claimed)
        nxt_info = None
        if nxt:
            r = conn.execute("SELECT slug, title, kind, ceiling, minutes FROM assignments WHERE id = ?", (nxt.id,)).fetchone()
            nxt_info = dict(r)
        detail = ae.skill_score(evidence.get(sid, []))
        tstats = ae.topic_stats(breakdowns.get(sid, []))
        profile[sid] = {
            "skill_id": sid, "verified": row is not None, "score": score, "level": row["level"] if row else 0,
            "confidence": row["confidence"] if row else None, "assignments": row["assignments_count"] if row else 0,
            "progress": detail.progress_to_next if detail else 0, "capped": bool(detail and detail.capped),
            "contradictory": bool(detail and detail.contradictory), "claimed": claimed,
            "calibration": ae.calibration(claimed, row["level"]) if row else "no_claim" if claimed is None else "unverified",
            "weak": ae.weak_topics(tstats), "strong": ae.strong_topics(tstats), "next": nxt_info,
        }
    return profile


def score_history(conn, user_id, skill_id):
    return conn.execute(
        "SELECT h.score, h.level, h.created_at, a.title FROM skill_score_history h LEFT JOIN attempts at ON at.id = h.attempt_id "
        "LEFT JOIN assignments a ON a.id = at.assignment_id WHERE h.user_id = ? AND h.skill_id = ? ORDER BY h.id",
        (user_id, skill_id)).fetchall()


def history_all(conn, user_id, limit=200):
    return conn.execute(
        "SELECT h.score, h.level, h.created_at, s.name AS skill_name FROM skill_score_history h JOIN skills s ON s.id = h.skill_id "
        "WHERE h.user_id = ? ORDER BY h.id DESC LIMIT ?", (user_id, limit)).fetchall()


def recent_attempts(conn, user_id, limit=8):
    return conn.execute(
        "SELECT at.id, at.pct, at.skill_score, at.graded_at, a.title, a.slug, s.name AS skill_name FROM attempts at "
        "JOIN assignments a ON a.id = at.assignment_id JOIN skills s ON s.id = a.skill_id "
        "WHERE at.user_id = ? AND at.status = 'graded' ORDER BY at.id DESC LIMIT ?", (user_id, limit)).fetchall()


def previous_score(conn, user_id, skill_id, attempt_id):
    """The skill score recorded just before this attempt's history point (None if it was the first)."""
    row = conn.execute(
        "SELECT score, level FROM skill_score_history WHERE user_id = ? AND skill_id = ? AND id < "
        "(SELECT COALESCE(MIN(id), 0) FROM skill_score_history WHERE attempt_id = ?) ORDER BY id DESC LIMIT 1",
        (user_id, skill_id, attempt_id)).fetchone()
    return dict(row) if row else None
