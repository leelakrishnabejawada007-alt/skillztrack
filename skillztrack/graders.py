"""
Graders: one function per assignment kind. Each returns a GradeResult whose `items` are the
evidence stored in the database (points earned, topic, feedback per test / question / criterion).

    quiz      multiple choice, options shuffled per attempt, graded on the server
    code      student functions run against hidden test cases in the sandbox
    debug     same as code, but the starter code contains bugs to fix
    mutation  student WRITES tests; they must pass the correct code AND catch deliberately broken versions
    sql       student queries run on a real SQLite database; results compared with the reference query
    commands  shell/git/formula answers checked against accepted patterns (and forbidden patterns)
    rubric    HTML/CSS, JavaScript, Dockerfile, IAM policy or written text checked by named rubric checks
"""
from __future__ import annotations

import json
import math
import random
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass, field

from . import sandbox
from .rubric_checks import run_check


class SubmissionRejected(Exception):
    """The submission cannot be graded (syntax/policy error, empty answer, runner unavailable)."""


@dataclass
class GradeResult:
    items: list = field(default_factory=list)
    note: str = ""


def _item(id_, label, topic, earned, possible, feedback="", **extra):
    return {"id": id_, "label": label, "topic": topic, "earned": round(float(earned), 3), "possible": float(possible),
            "passed": earned >= possible - 1e-9, "feedback": feedback, **extra}


# ============================================================================ quiz
def make_quiz_payload(spec, rng=None):
    rng = rng or random.SystemRandom()
    pool = list(spec["pool"])
    picked = rng.sample(pool, min(spec.get("draw", len(pool)), len(pool)))
    questions = []
    for q in picked:
        order = list(range(len(q["options"])))
        rng.shuffle(order)
        questions.append({"id": q["id"], "order": order})
    return {"questions": questions}


def present_quiz(spec, payload):
    by_id = {q["id"]: q for q in spec["pool"]}
    out = []
    for entry in payload["questions"]:
        q = by_id[entry["id"]]
        out.append({"id": q["id"], "q": q["q"], "code": q.get("code"), "topic": q["topic"],
                    "options": [(i, q["options"][i]) for i in entry["order"]]})
    return out


def grade_quiz(spec, payload, answers):
    by_id = {q["id"]: q for q in spec["pool"]}
    items = []
    answered = 0
    for entry in payload["questions"]:
        q = by_id[entry["id"]]
        raw = answers.get(q["id"], "")
        picked = int(raw) if raw.isdigit() and int(raw) < len(q["options"]) else None
        answered += picked is not None
        correct = picked == q["answer"]
        if correct:
            feedback = "Correct."
        elif picked is None:
            feedback = "Not answered. Hint: " + q.get("hint", "")
        else:
            feedback = "Not quite. Hint: " + q.get("hint", "")
        # the explanation is stored but only shown once the student passes it or has retried (no instant spoilers)
        items.append(_item(q["id"], q["q"].split("\n")[0][:110], q["topic"], 1 if correct else 0, 1, feedback, explain=q["why"]))
    if answered == 0:
        raise SubmissionRejected("Answer at least one question before submitting.")
    return GradeResult(items)


# ========================================================================== helpers
def _normalise_expected(value):
    def default(o):
        if isinstance(o, (set, frozenset)):
            try:
                return sorted(o)
            except TypeError:
                return sorted(map(repr, o))
        return "<" + type(o).__name__ + ">"
    return json.loads(json.dumps(value, default=default))


def _approx(a, b, tol):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        if isinstance(a, float) and math.isnan(a) and isinstance(b, float) and math.isnan(b):
            return True
        return math.isclose(a, b, rel_tol=tol, abs_tol=tol)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_approx(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_approx(a[k], b[k], tol) for k in a)
    return a == b


def _matches(actual, expected, mode="exact", tol=1e-6):
    if mode == "approx":
        return _approx(actual, expected, tol)
    if mode == "unordered" and isinstance(actual, list) and isinstance(expected, list):
        key = lambda v: json.dumps(v, sort_keys=True)
        return sorted(map(key, actual)) == sorted(map(key, expected))
    return actual == expected


def _short(value, limit=160):
    text = json.dumps(value, default=str) if not isinstance(value, str) else repr(value)
    return text if len(text) <= limit else text[:limit] + "..."


def _check_source(source, forbidden=()):
    problem = sandbox.screen_source(source)
    if problem:
        raise SubmissionRejected(problem)
    if forbidden:
        import ast
        for node in ast.walk(ast.parse(source)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for name in names:
                if name.split(".")[0] in forbidden:
                    raise SubmissionRejected(f"This assignment asks you to implement it yourself, so importing '{name}' is not allowed.")
    if not sandbox.code_execution_enabled():
        raise SubmissionRejected("Code execution is switched off on this server, so this assignment cannot be graded.")


# ============================================================================= code
def grade_code(spec, submission):
    source = submission.get("code", "")
    _check_source(source, spec.get("forbidden_imports", ()))
    tests = spec["tests"]
    try:
        results = sandbox.run_cases(source, [{k: t.get(k) for k in ("fn", "args", "kwargs", "fixture")} for t in tests])
    except sandbox.SandboxUnavailable as exc:
        raise SubmissionRejected(str(exc))
    items = []
    for i, (t, res) in enumerate(zip(tests, results), start=1):
        weight = float(t.get("weight", 1))
        label = t.get("label", f"Test {i}")
        topic = t.get("topic", "general")
        visible = t.get("visible", False)
        expect_err = t.get("expect_error")
        if expect_err:
            ok = (not res["ok"]) and expect_err in res.get("mro", [])
            fb = "Raised the expected error." if ok else f"Expected your code to raise {expect_err}."
            items.append(_item(f"t{i}", label, topic, weight if ok else 0, weight, fb))
            continue
        if not res["ok"]:
            items.append(_item(f"t{i}", label, topic, 0, weight, res["error"] + (" Hint: " + t["hint"] if t.get("hint") else ""),
                               detail=({"input": _short(t.get("args", []))} if visible else None)))
            continue
        expected = _normalise_expected(t["expected"])
        ok = _matches(res["value"], expected, t.get("cmp", "exact"), t.get("tol", 1e-6))
        if ok:
            items.append(_item(f"t{i}", label, topic, weight, weight, "Passed."))
        elif visible:
            items.append(_item(f"t{i}", label, topic, 0, weight, "Wrong result." + (" Hint: " + t["hint"] if t.get("hint") else ""),
                               detail={"input": _short(t.get("args", [])), "expected": _short(expected), "got": _short(res["value"])}))
        else:
            items.append(_item(f"t{i}", label, topic, 0, weight, t.get("hint") and "Wrong result. Hint: " + t["hint"]
                               or "Wrong result on a hidden test. Re-read the requirement for this case."))
    return GradeResult(items)


# ========================================================================= mutation
def _meets(res, expected):
    """Does one sandbox result satisfy a student's expectation (a value, or {"raises": "ErrorName"})?"""
    if isinstance(expected, dict) and set(expected) == {"raises"}:
        return (not res["ok"]) and expected["raises"] in res.get("mro", [])
    return res["ok"] and _approx(res["value"], _normalise_expected(expected), 1e-9)


def grade_mutation(spec, submission):
    source = submission.get("code", "")
    _check_source(source)
    fn = spec["function"]
    try:
        produced = sandbox.run_cases(source, [{"fn": "test_cases", "args": []}])[0]
        if not produced["ok"]:
            raise SubmissionRejected("Could not read your tests: " + produced["error"] + " (define test_cases() that returns a list).")
        raw = produced["value"]
        lo, hi = spec.get("min_tests", 3), spec.get("max_tests", 40)
        if not isinstance(raw, list) or not all(isinstance(t, list) and len(t) == 2 and isinstance(t[0], list) for t in raw):
            raise SubmissionRejected("test_cases() must return a list of [args_list, expected] pairs, e.g. [[[2, 3], 5], ...].")
        if not lo <= len(raw) <= hi:
            raise SubmissionRejected(f"Provide between {lo} and {hi} test cases (you gave {len(raw)}).")
        calls = [{"fn": fn, "args": t[0]} for t in raw]
        ref = sandbox.run_cases(spec["reference"], calls)
    except sandbox.SandboxUnavailable as exc:
        raise SubmissionRejected(str(exc))

    valid = []
    wrong = []
    for (args, expected), r in zip(raw, ref):
        if _meets(r, expected):
            valid.append((args, expected))
        else:
            wrong.append((args, expected, r.get("value", r.get("error"))))
    items = []
    weight_valid = 2.0
    frac = len(valid) / len(raw)
    fb = "All your expected values are correct." if not wrong else (
        f"{len(wrong)} of your test(s) expect the wrong result, e.g. {fn}({_short(wrong[0][0])}) is {_short(wrong[0][2])}, not {_short(wrong[0][1])}.")
    items.append(_item("valid", "Your expected values match the correct implementation", "writing correct tests", weight_valid * frac, weight_valid, fb))

    for m in spec["mutants"]:
        if not valid:
            items.append(_item(m["id"], m["label"], m["topic"], 0, 1, "No valid tests to try against this bug."))
            continue
        try:
            out = sandbox.run_cases(m["src"], [{"fn": fn, "args": a} for a, _ in valid])
        except sandbox.SandboxUnavailable as exc:
            raise SubmissionRejected(str(exc))
        killed = any(not _meets(r, e) for r, (_, e) in zip(out, valid))
        items.append(_item(m["id"], m["label"], m["topic"], 1 if killed else 0, 1,
                           "Your tests catch this bug." if killed else "Your tests do NOT catch this bug: " + m.get("hint", "add a test that would fail for it.")))
    return GradeResult(items)


# ============================================================================== sql
_SQL_ALLOWED = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
if hasattr(sqlite3, "SQLITE_RECURSIVE"):
    _SQL_ALLOWED.add(sqlite3.SQLITE_RECURSIVE)
_SQL_STEP_LIMIT = 3000  # progress callbacks of 1000 VM steps each


def _sql_connection(schema):
    conn = sqlite3.connect(":memory:")
    conn.executescript(schema)
    conn.commit()
    conn.set_authorizer(lambda action, *rest: sqlite3.SQLITE_OK if action in _SQL_ALLOWED else sqlite3.SQLITE_DENY)
    return conn


def _run_query(conn, sql):
    sql = sql.strip().rstrip(";").strip()
    if not re.match(r"(?is)^\s*(select|with)\b", sql):
        raise ValueError("Only a single SELECT query is allowed.")
    counter = {"n": 0}

    def guard():
        counter["n"] += 1
        return 1 if counter["n"] > _SQL_STEP_LIMIT else 0
    conn.set_progress_handler(guard, 1000)
    try:
        cur = conn.execute(sql)
        rows = cur.fetchmany(2001)
    except (sqlite3.Error, sqlite3.Warning) as exc:
        text = str(exc)
        raise ValueError("Query too slow or too heavy." if "interrupted" in text else text)
    finally:
        conn.set_progress_handler(None, 0)
    if len(rows) > 2000:
        raise ValueError("Query returned too many rows.")
    return [tuple(round(v, 4) if isinstance(v, float) else v for v in row) for row in rows]


def grade_sql(spec, submission):
    answers = {q["id"]: submission.get(q["id"], "").strip() for q in spec["questions"]}
    if not any(answers.values()):
        raise SubmissionRejected("Write at least one query before submitting.")
    conn = _sql_connection(spec["schema"])
    items = []
    try:
        for q in spec["questions"]:
            weight, sql = float(q.get("weight", 1)), answers[q["id"]]
            label = f"{q['id'].upper()}: {q['label']}"
            if not sql:
                items.append(_item(q["id"], label, q["topic"], 0, weight, "No query written."))
                continue
            expected = _run_query(conn, q["expected_sql"])
            try:
                got = _run_query(conn, sql)
            except ValueError as exc:
                items.append(_item(q["id"], label, q["topic"], 0, weight, "SQL error: " + str(exc)[:160]))
                continue
            if expected and got and len(got[0]) != len(expected[0]):
                items.append(_item(q["id"], label, q["topic"], 0, weight, f"Returned {len(got[0])} column(s) but {len(expected[0])} were asked for."))
            elif q.get("ordered") and got == expected:
                items.append(_item(q["id"], label, q["topic"], weight, weight, "Correct result in the right order."))
            elif Counter(got) == Counter(expected):
                if q.get("ordered"):
                    items.append(_item(q["id"], label, q["topic"], weight * 0.5, weight, "Right rows, but the order is wrong (check ORDER BY and ties)."))
                else:
                    items.append(_item(q["id"], label, q["topic"], weight, weight, "Correct result."))
            else:
                items.append(_item(q["id"], label, q["topic"], 0, weight,
                                   f"Wrong result: got {len(got)} row(s), expected {len(expected)}. Check filters, joins and grouping."))
    finally:
        conn.close()
    return GradeResult(items)


# ========================================================================== commands
def grade_commands(spec, submission):
    answers = {p["id"]: " ".join(str(submission.get(p["id"], "")).split()) for p in spec["prompts"]}
    if not any(answers.values()):
        raise SubmissionRejected("Answer at least one prompt before submitting.")
    items = []
    for p in spec["prompts"]:
        weight, text = float(p.get("weight", 1)), answers[p["id"]]
        if p.get("strip_spaces"):
            text = re.sub(r"\s+", "", text)
        flags = re.I if p.get("ci") else 0
        if not text:
            items.append(_item(p["id"], p["label"], p["topic"], 0, weight, "No answer."))
        elif len(text) > 400:
            items.append(_item(p["id"], p["label"], p["topic"], 0, weight, "Answer too long."))
        else:
            rejected = next((msg for rx, msg in p.get("reject", []) if re.search(rx, text, flags)), None)
            ok = any(re.search(rx, text, flags) for rx in p["accept"])
            if rejected:
                items.append(_item(p["id"], p["label"], p["topic"], 0, weight, rejected))
            elif ok:
                items.append(_item(p["id"], p["label"], p["topic"], weight, weight, "Accepted."))
            else:
                items.append(_item(p["id"], p["label"], p["topic"], 0, weight, "Not accepted. Hint: " + p["hint"]))
    return GradeResult(items)


# ============================================================================ rubric
def grade_rubric(spec, submission):
    text = submission.get("text", "")
    if len(text.strip()) < spec.get("min_chars", 40):
        raise SubmissionRejected("Your submission is too short to assess.")
    if len(text) > 30_000:
        raise SubmissionRejected("Your submission is too long (limit 30,000 characters).")
    items = []
    for c in spec["criteria"]:
        weight = float(c.get("weight", 1))
        passed, detail = run_check(c["check"], text, **c.get("args", {}))
        items.append(_item(c["id"], c["label"], c["topic"], weight if passed else 0, weight, detail))
    return GradeResult(items)


GRADERS = {"code": grade_code, "debug": grade_code, "mutation": grade_mutation, "sql": grade_sql,
           "commands": grade_commands, "rubric": grade_rubric}


def grade_submission(assignment, payload, submission):
    """Dispatch to the right grader. `assignment` is a bank.Assignment."""
    if assignment.kind == "quiz":
        return grade_quiz(assignment.spec, payload, submission)
    return GRADERS[assignment.kind](assignment.spec, submission)
