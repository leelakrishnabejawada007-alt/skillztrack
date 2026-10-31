"""Pages for the evidence-based assessment flow (/assignments, /attempts, /skill-profile)."""
import json
import threading
import time

from . import assessment_engine as ae
from . import assessments, bank, events, graders, sandbox, services
from .levels import level_label
from .web import HTTPError, json_response, redirect, render, route

# A student may grade at most this many times per window (the code runner is the expensive part).
_SUBMIT_LIMIT, _SUBMIT_WINDOW = 25, 600
_submits, _submit_lock = {}, threading.Lock()

KIND_LABELS = {"quiz": "Quiz", "code": "Coding challenge", "debug": "Debugging task", "mutation": "Testing challenge",
               "sql": "SQL lab", "commands": "Command lab", "rubric": "Mini-project"}
KIND_ICONS = {"quiz": "bi-ui-checks", "code": "bi-code-slash", "debug": "bi-bug", "mutation": "bi-shield-check",
              "sql": "bi-database", "commands": "bi-terminal", "rubric": "bi-kanban"}


def _too_many_submits(user_id):
    now = time.time()
    with _submit_lock:
        recent = [t for t in _submits.get(user_id, []) if now - t < _SUBMIT_WINDOW]
        if len(recent) >= _SUBMIT_LIMIT:
            _submits[user_id] = recent
            return True
        recent.append(now)
        _submits[user_id] = recent
        return False


def _decorate(assignments):
    for a in assignments:
        a["kind_label"] = KIND_LABELS[a["kind"]]
        a["icon"] = KIND_ICONS[a["kind"]]
        a["level_name"] = level_label(a["ceiling"])
        # used by the hub's status filter: mastered (best >= 80%), in_progress, tried, or new
        a["status"] = ("in_progress" if a.get("in_progress") else "mastered" if (a.get("best_pct") or 0) >= 0.8
                       else "tried" if a.get("used") else "new")
    return assignments


# --------------------------------------------------------------------------------------- hub
@route("GET", "/assignments", login=True)
def hub(req):
    uid = req.user["id"]
    career = services.get_career(req.conn, req.user["target_career_id"]) if req.user["target_career_id"] else None
    rows = services.requirement_rows(req.conn, career["id"]) if career else []
    career_ids = [r["skill_id"] for r in rows]
    profile = assessments.skill_profile(req.conn, uid, career_ids)
    cards = [{"req": r, "p": profile[r["skill_id"]], "assignments": _decorate(assessments.assignments_for_skill(req.conn, uid, r["skill_id"]))}
             for r in rows]
    others = []
    for s in req.conn.execute("SELECT id, name, category FROM skills ORDER BY name"):
        if s["id"] in career_ids:
            continue
        items = assessments.assignments_for_skill(req.conn, uid, s["id"])
        if items:
            others.append({"skill": s, "assignments": _decorate(items)})
    verified = sum(1 for c in cards if c["p"]["verified"])
    return render(req, "assessments/hub.html", career=career, cards=cards, others=others, verified=verified,
                  code_enabled=sandbox.code_execution_enabled(), recent=assessments.recent_attempts(req.conn, uid),
                  max_attempts=ae.MAX_ATTEMPTS)


# ---------------------------------------------------------------------------- assignment page
@route("GET", "/assignments/<slug:slug>", login=True)
def assignment_detail(req, slug):
    row, ba = assessments.get_assignment(req.conn, slug)
    if not row or not ba:
        raise HTTPError(404, "That assignment does not exist.")
    uid = req.user["id"]
    attempts = assessments.attempts_for_assignment(req.conn, uid, row["id"])
    open_attempt = req.conn.execute(
        "SELECT id FROM attempts WHERE user_id = ? AND assignment_id = ? AND status = 'in_progress'", (uid, row["id"])).fetchone()
    profile = assessments.skill_profile(req.conn, uid, [row["skill_id"]])[row["skill_id"]]
    info = dict(row, kind_label=KIND_LABELS[row["kind"]], icon=KIND_ICONS[row["kind"]], level_name=level_label(row["ceiling"]))
    return render(req, "assessments/assignment.html", a=info, ba=ba, attempts=attempts, open_attempt=open_attempt, p=profile,
                  used=len(attempts), max_attempts=ae.max_attempts(row["ceiling"]), evidence_labels=ae.EVIDENCE_LABELS,
                  beginner=ae.is_beginner(row["ceiling"]),
                  runner_off=ba.needs_code_runner and not sandbox.code_execution_enabled(),
                  next_retake_factor=ae.retake_factor(len(attempts) + 1, row["ceiling"]))


@route("POST", "/assignments/<slug:slug>/start", login=True)
def assignment_start(req, slug):
    row, ba = assessments.get_assignment(req.conn, slug)
    if not row or not ba:
        raise HTTPError(404, "That assignment does not exist.")
    if ba.needs_code_runner and not sandbox.code_execution_enabled():
        return redirect(f"/assignments/{slug}", "Code execution is switched off on this server, so this assignment is unavailable.", "warning")
    attempt_id, reason = assessments.start_attempt(req.conn, req.user["id"], row)
    if attempt_id is None:
        return redirect(f"/assignments/{slug}", reason, "warning")
    return redirect(f"/attempts/{attempt_id}")


# ------------------------------------------------------------------------------ taking / result
def _owned_attempt(req, pk):
    attempt = assessments.get_attempt(req.conn, req.user["id"], pk)
    if not attempt:
        raise HTTPError(404, "Attempt not found.")
    return attempt


@route("GET", "/attempts/<int:pk>", login=True)
def attempt_page(req, pk):
    at = _owned_attempt(req, pk)
    ba = bank.get(at["slug"])
    if at["status"] == "graded":
        return _result_page(req, at, ba)
    draft = assessments.draft_for(at)
    payload = json.loads(at["payload"] or "{}")
    ctx = dict(at=at, ba=ba, draft=draft, kind_label=KIND_LABELS[at["kind"]])
    if at["kind"] == "quiz":
        ctx["questions"] = graders.present_quiz(ba.spec, payload)
    elif at["kind"] == "sql":
        ctx["prompts"] = ba.spec["questions"]
    elif at["kind"] == "commands":
        ctx["prompts"] = ba.spec["prompts"]
    else:
        ctx["code"] = draft.get("code") or draft.get("text") or ba.starter
    return render(req, "assessments/take.html", **ctx)


@route("POST", "/attempts/<int:pk>/submit", login=True)
def attempt_submit(req, pk):
    at = _owned_attempt(req, pk)
    if at["status"] == "graded":
        return redirect(f"/attempts/{pk}")
    if _too_many_submits(req.user["id"]):
        return redirect(f"/attempts/{pk}", "You are submitting very quickly. Please wait a few minutes.", "warning")
    ba = bank.get(at["slug"])
    payload = json.loads(at["payload"] or "{}")
    submission = assessments.extract_submission(ba, payload, lambda name: (req.form.get(name) or [""])[0])
    try:
        info = assessments.submit_attempt(req.conn, req.user["id"], at, submission)
    except graders.SubmissionRejected as exc:
        return redirect(f"/attempts/{pk}", f"Not graded: {exc} (your work was kept; fix it and submit again).", "danger")
    services.refresh_after_assessment(req.conn, req.user["id"], info["skill_id"])
    after, before = info["skill"], info["before"]
    uid = req.user["id"]
    events.record(req.conn, uid, "attempt", f"Scored {round(100 * info['pct'])}% on {at['title']}", f"/attempts/{pk}")
    if after.level > (before["level"] if before else 0):
        events.record(req.conn, uid, "level", f"{at['skill_name']} reached level {after.level} ({level_label(after.level)})", "/skill-profile")
        events.notify(req.conn, uid, "level", f"{at['skill_name']}: level {after.level}",
                      f"Your verified level is now {level_label(after.level)}.", "/skill-profile")
    new_badges = events.after_change(req.conn, uid)
    msg = f"Graded: {round(100 * info['pct'])}% of the points. "
    if before is None:
        msg += f"{at['skill_name']} is now verified at {after.score:.1f}/5 (level {after.level})."
    elif after.score > before["score"]:
        msg += f"{at['skill_name']} improved from {before['score']:.1f} to {after.score:.1f}/5."
    else:
        msg += f"{at['skill_name']} stays at {after.score:.1f}/5; your best attempt still counts."
    if new_badges:
        msg += " New badge" + ("s" if len(new_badges) > 1 else "") + ": " + ", ".join(new_badges) + "."
    return redirect(f"/attempts/{pk}", msg, "success" if info["pct"] >= ae.MASTERY_PCT else "info")


def _result_page(req, at, ba):
    uid = req.user["id"]
    items = json.loads(at["breakdown"])
    stats = ae.topic_stats([items])
    profile = assessments.skill_profile(req.conn, uid, [at["skill_id"]])[at["skill_id"]]
    used = assessments.graded_count(req.conn, uid, at["assignment_id"])
    return render(req, "assessments/result.html", at=at, ba=ba, items=items, p=profile, weak=ae.weak_topics(stats),
                  strong=ae.strong_topics(stats), prev=assessments.previous_score(req.conn, uid, at["skill_id"], at["id"]),
                  used=used, left=ae.max_attempts(at["ceiling"]) - used, next_factor=ae.retake_factor(used + 1, at["ceiling"]),
                  show_explain=used >= 2 or used >= ae.max_attempts(at["ceiling"]), mastery=ae.MASTERY_PCT,
                  kind_label=KIND_LABELS[at["kind"]], retake_free=ae.FREE_ATTEMPTS)


# ---------------------------------------------------------------------------------- profile
@route("GET", "/skill-profile", login=True)
def skill_profile_page(req):
    uid = req.user["id"]
    career = services.get_career(req.conn, req.user["target_career_id"]) if req.user["target_career_id"] else None
    rows = services.requirement_rows(req.conn, career["id"]) if career else []
    career_ids = [r["skill_id"] for r in rows]
    extra = [r["skill_id"] for r in req.conn.execute("SELECT skill_id FROM skill_scores WHERE user_id = ?", (uid,)) if r["skill_id"] not in career_ids]
    profile = assessments.skill_profile(req.conn, uid, career_ids + extra)
    names = {r["id"]: r["name"] for r in req.conn.execute("SELECT id, name FROM skills")}
    career_rows = [{"req": r, "p": profile[r["skill_id"]]} for r in rows]
    other_rows = [{"name": names[sid], "p": profile[sid]} for sid in extra]
    chart = {"labels": [r["req"]["name"] for r in career_rows],
             "verified": [round(r["p"]["score"], 2) for r in career_rows],
             "claimed": [r["p"]["claimed"] if r["p"]["claimed"] is not None else 0 for r in career_rows],
             "required": [r["req"]["required_level"] for r in career_rows]}
    from . import insights
    history = assessments.history_all(req.conn, uid, 12)
    palette, groups = ["#6366f1", "#06b6d4", "#f59e0b", "#10b981", "#f43f5e", "#8b5cf6"], {}
    for h in sorted(history, key=lambda r: r["created_at"]):
        groups.setdefault(h["skill_name"], []).append({"t": h["created_at"], "y": round(h["score"], 2), "label": h["created_at"][:16]})
    history_chart = {"type": "line", "max": 5, "title": "Verified score over time",
                     "series": [{"name": n, "color": palette[i], "points": pts} for i, (n, pts) in enumerate(list(groups.items())[:6])]}
    return render(req, "assessments/profile.html", history_chart=history_chart, career=career, rows=career_rows, other_rows=other_rows, chart=chart,
                  match=insights.career_match(req.conn, uid, req.user["target_career_id"]),
                  recent=assessments.recent_attempts(req.conn, uid, 12), history=history,
                  evidence_labels=ae.EVIDENCE_LABELS)


# ------------------------------------------------------------------------------- draft autosave
_drafts, _draft_lock = {}, threading.Lock()


@route("POST", "/attempts/<int:pk>/draft", login=True)
def attempt_draft(req, pk):
    """Silently store the student's work in progress (called by the editor every few seconds). Nothing is graded."""
    at = _owned_attempt(req, pk)
    if at["status"] != "in_progress":
        return json_response({"saved": False, "reason": "already graded"}, 409)
    now = time.time()
    with _draft_lock:
        recent = [t for t in _drafts.get(req.user["id"], []) if now - t < 60]
        if len(recent) >= 40:
            _drafts[req.user["id"]] = recent
            return json_response({"saved": False, "reason": "slow down"}, 429)
        recent.append(now)
        _drafts[req.user["id"]] = recent
    ba = bank.get(at["slug"])
    payload = json.loads(at["payload"] or "{}")
    submission = assessments.extract_submission(ba, payload, lambda name: (req.form.get(name) or [""])[0])
    assessments.save_draft(req.conn, pk, submission)
    return json_response({"saved": True})
