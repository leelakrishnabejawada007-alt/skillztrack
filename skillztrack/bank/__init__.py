"""
The assignment bank: every practical task, quiz pool, hidden test and rubric lives here as plain data.

Adding an assignment = add an `Assignment(...)` to one of the modules below (or a new module listed in
`_MODULES`) and restart (`python run.py reseed` also works). Nothing else needs to change.

Kinds and their `spec`:
    quiz      {"pool": [Q(...), ...], "draw": 5}
    code      {"tests": [T(...), ...]}                 student writes functions
    debug     {"tests": [T(...), ...]}                 student fixes buggy functions (starter has bugs)
    mutation  {"function", "reference", "mutants": [...]}   student writes tests
    sql       {"schema", "questions": [...]}
    commands  {"prompts": [...]}
    rubric    {"criteria": [...]}

`reference` (code/debug/mutation) is a model solution used ONLY by the bank self-test
(tests/test_bank.py) to prove that the hidden tests are fair: the reference must score 100% and the
untouched starter code must not.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DIFFICULTY = {1: "Beginner", 2: "Easy", 3: "Intermediate", 4: "Advanced", 5: "Expert"}
KINDS = ("quiz", "code", "debug", "mutation", "sql", "commands", "rubric")
EVIDENCE_FOR_KIND = {"quiz": "quiz", "code": "executed", "debug": "executed", "mutation": "executed",
                     "sql": "executed", "commands": "static", "rubric": "static"}


@dataclass(frozen=True)
class Assignment:
    slug: str
    skill: str            # skill slug from seed_content.SKILLS
    kind: str
    title: str
    summary: str
    ceiling: int          # highest level this assignment can prove (1-5)
    minutes: int
    instructions: str = ""
    starter: str = ""
    spec: dict = field(default_factory=dict)
    reference: str | None = None
    steps: tuple = ()          # beginner-friendly numbered steps
    example: dict | None = None  # {"input": ..., "output": ...} expected output example
    hints: tuple = ()          # general hints shown on request

    @property
    def difficulty(self) -> str:
        return DIFFICULTY.get(self.ceiling, "Advanced")

    @property
    def evidence(self) -> str:
        return EVIDENCE_FOR_KIND[self.kind]

    @property
    def needs_code_runner(self) -> bool:
        return self.kind in {"code", "debug", "mutation"}


def Q(id_, topic, q, options, answer, why, code=None, hint=None):
    """A quiz question. `answer` is the index of the correct option in `options`."""
    return {"id": id_, "topic": topic, "q": q, "options": list(options), "answer": answer, "why": why, "code": code,
            "hint": hint or f"Review the basics of {topic} and read every option again."}


def T(fn, args, expected=None, label="", topic="general", *, weight=1, visible=False, cmp="exact", tol=1e-6,
      raises=None, fixture=None, hint=None):
    """A hidden test: call fn(*args) and compare with `expected` (or expect an exception name)."""
    t = {"fn": fn, "args": list(args), "expected": expected, "label": label or f"{fn}{tuple(args)!r}"[:70], "topic": topic,
         "weight": weight, "visible": visible, "cmp": cmp, "tol": tol}
    if raises:
        t["expect_error"] = raises
    if fixture:
        t["fixture"] = fixture
    if hint:
        t["hint"] = hint
    return t


_MODULES = ("beginner", "quizzes", "coding", "debugging", "labs", "rubrics")
_cache: list | None = None


def all_assignments() -> list:
    global _cache
    if _cache is None:
        import importlib
        items = []
        for name in _MODULES:
            items.extend(importlib.import_module(f"{__name__}.{name}").ASSIGNMENTS)
        slugs = [a.slug for a in items]
        assert len(slugs) == len(set(slugs)), "duplicate assignment slug"
        assert all(a.kind in KINDS and 1 <= a.ceiling <= 5 for a in items)
        _cache = items
    return _cache


def get(slug: str):
    return next((a for a in all_assignments() if a.slug == slug), None)


def for_skill(skill_slug: str) -> list:
    return [a for a in all_assignments() if a.skill == skill_slug]
