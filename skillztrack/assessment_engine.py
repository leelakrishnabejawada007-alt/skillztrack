"""
SkillzTrack's evidence engine: turns graded assignment attempts into a 0-5 skill score.

Like engine.py this module is PURE (no database, no web). Plain values in, plain values out,
so every rule can be unit-tested and explained.

THE RULES
    1. An assignment has a CEILING (1-5): the highest level it can prove. A beginner quiz
       can never prove "Expert"; only hard, executed work can.
    2. attempt score = ceiling x min(1, pct / 0.8) x retake factor
       - pct is the share of rubric/test points earned (0..1).
       - 80% counts as full mastery of that tier, so one unlucky edge case does not cap you.
       - Attempts 1-2 count fully; each later attempt on the SAME assignment is worth 15% less
         (stops brute-forcing hidden tests).
    3. Per assignment only the best attempt counts.
    4. skill score = the best assignment score for that skill ...
    5. ... but ONE assignment can prove at most 3.5 ("Intermediate"). Advanced/Expert needs
       evidence from at least two different assignments (breadth, not a lucky run).
    6. level = floor(score). A 3.7 means "Intermediate, 70% of the way to Advanced".
    7. Confidence: low = 1 assignment; medium = 2; high = 3+ including at least one
       auto-tested (executed) one and no contradictions. A contradiction (aced a hard task
       but failed an easier one) lowers confidence by one step.
    8. Self-ratings are NEVER evidence. They are only compared with the verified level
       (calibration) and used to choose which assignment to suggest first.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

MASTERY_PCT = 0.80
FREE_ATTEMPTS = 2
RETAKE_FACTOR = 0.85
MAX_ATTEMPTS = 5
SINGLE_EVIDENCE_CAP = 3.5
WEAK_TOPIC_PCT = 0.60
CONTRADICTION_LOW = 0.50
CONFIDENCE_ORDER = ("low", "medium", "high")
EVIDENCE_LABELS = {
    "executed": "Auto-tested (code run against hidden tests)",
    "static": "Rubric-checked (structure and content analysed)",
    "quiz": "Quiz (multiple choice)",
}


# --------------------------------------------------------------------------- data
@dataclass(frozen=True)
class AttemptEvidence:
    assignment_id: int
    ceiling: int
    evidence: str          # executed | static | quiz
    pct: float             # 0..1 of available points earned
    attempt_no: int        # 1 = first graded attempt on this assignment


@dataclass(frozen=True)
class SkillResult:
    score: float
    level: int
    confidence: str
    assignments: int
    best_assignment_id: int | None
    capped: bool
    contradictory: bool

    @property
    def progress_to_next(self) -> int:
        """Percent of the way from the current level to the next one."""
        if self.level >= 5:
            return 100
        return round(100 * (self.score - self.level))


@dataclass(frozen=True)
class TopicStat:
    topic: str
    earned: float
    possible: float

    @property
    def pct(self) -> float:
        return self.earned / self.possible if self.possible else 0.0


# ------------------------------------------------------------------------- rules
def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


BEGINNER_CEILING = 2
BEGINNER_MAX_ATTEMPTS = 10


def is_beginner(ceiling: int) -> bool:
    """Beginner tasks (ceiling 1-2) are for learning: more retries and no retake penalty."""
    return int(ceiling) <= BEGINNER_CEILING


def max_attempts(ceiling: int) -> int:
    return BEGINNER_MAX_ATTEMPTS if is_beginner(ceiling) else MAX_ATTEMPTS


def retake_factor(attempt_no: int, ceiling: int = 5) -> float:
    """Rule 2: attempts beyond the free ones are worth 15% less each (never for beginner tasks)."""
    if is_beginner(ceiling):
        return 1.0
    extra = max(0, int(attempt_no) - FREE_ATTEMPTS)
    return RETAKE_FACTOR ** extra


def attempt_score(ceiling: int, pct: float, attempt_no: int = 1) -> float:
    """Rule 2: the 0-5 score a single attempt earns."""
    mastery = min(1.0, clamp01(pct) / MASTERY_PCT)
    return round(ceiling * mastery * retake_factor(attempt_no, ceiling), 2)


def level_for(score: float) -> int:
    return max(0, min(5, math.floor(score + 1e-9)))


def _step_down(confidence: str) -> str:
    return CONFIDENCE_ORDER[max(0, CONFIDENCE_ORDER.index(confidence) - 1)]


def skill_score(attempts: Iterable[AttemptEvidence]) -> SkillResult | None:
    """Rules 3-7. Returns None when there is no evidence at all."""
    best: dict[int, tuple[float, AttemptEvidence]] = {}
    for a in attempts:
        s = attempt_score(a.ceiling, a.pct, a.attempt_no)
        if a.assignment_id not in best or s > best[a.assignment_id][0]:
            best[a.assignment_id] = (s, a)
    if not best:
        return None

    top_id, (top_score, top) = max(best.items(), key=lambda kv: (kv[1][0], kv[1][1].ceiling))
    count = len(best)
    capped = count < 2 and top_score > SINGLE_EVIDENCE_CAP
    score = min(top_score, SINGLE_EVIDENCE_CAP) if count < 2 else top_score

    # contradiction: strong on a harder task, weak on an easier one
    best_pct = {aid: ev.pct for aid, (_, ev) in best.items()}
    contradictory = any(
        ev.ceiling < top.ceiling and ev.pct < CONTRADICTION_LOW and best_pct[top_id] >= MASTERY_PCT
        for aid, (_, ev) in best.items() if aid != top_id
    )

    executed = any(ev.evidence == "executed" for _, ev in best.values())
    if count >= 3 and executed:
        confidence = "high"
    elif count >= 2:
        confidence = "medium"
    else:
        confidence = "low"
    if contradictory:
        confidence = _step_down(confidence)

    score = round(score, 2)
    return SkillResult(score=score, level=level_for(score), confidence=confidence, assignments=count,
                       best_assignment_id=top_id, capped=capped, contradictory=contradictory)


# ---------------------------------------------------------------------- insights
def topic_stats(breakdowns: Iterable[Sequence[Mapping]]) -> list[TopicStat]:
    """Aggregate rubric/test items by topic. Pass one breakdown per assignment (its latest attempt)."""
    totals: dict[str, list[float]] = {}
    for items in breakdowns:
        for item in items:
            topic = item.get("topic") or "general"
            t = totals.setdefault(topic, [0.0, 0.0])
            t[0] += float(item.get("earned", 0))
            t[1] += float(item.get("possible", 0))
    return [TopicStat(k, v[0], v[1]) for k, v in totals.items() if v[1] > 0]


def weak_topics(stats: Sequence[TopicStat], threshold: float = WEAK_TOPIC_PCT) -> list[TopicStat]:
    return sorted((s for s in stats if s.pct < threshold), key=lambda s: (s.pct, s.topic))


def strong_topics(stats: Sequence[TopicStat], threshold: float = MASTERY_PCT) -> list[TopicStat]:
    return sorted((s for s in stats if s.pct >= threshold), key=lambda s: (-s.pct, s.topic))


def calibration(claimed: int | None, level: int) -> str:
    """Compare what the student claimed with what they demonstrated."""
    if claimed is None:
        return "no_claim"
    if claimed - level >= 2:
        return "overconfident"
    if level - claimed >= 2:
        return "underconfident"
    return "calibrated"


@dataclass(frozen=True)
class AssignmentOption:
    id: int
    slug: str
    ceiling: int
    attempts_used: int = 0
    best_pct: float | None = None


def recommend_next(options: Sequence[AssignmentOption], score: float, claimed: int | None = None):
    """Pick the single most useful next assignment for a skill (or None).

    1. Untried assignments that can still raise the level (ceiling > current level), easiest first.
       With no evidence yet, a student who claims level 3+ is started on the easiest task that could prove
       that level, so the first piece of evidence is informative.
    2. Otherwise retry the weakest one that has attempts left.
    """
    level = level_for(score)
    available = [o for o in options if o.attempts_used < MAX_ATTEMPTS]
    untried = sorted((o for o in available if o.attempts_used == 0 and o.ceiling > level),
                     key=lambda o: (o.ceiling, o.id))
    if untried:
        if score == 0 and claimed and claimed >= 3:
            # a strong claim: start with a task that COULD prove it (the claim itself is still not evidence)
            capable = [o for o in untried if o.ceiling >= claimed]
            if capable:
                return capable[0]
        return untried[0]
    retry = sorted((o for o in available if o.attempts_used > 0 and (o.best_pct or 0) < MASTERY_PCT and o.ceiling > level),
                   key=lambda o: (o.best_pct or 0, o.ceiling))
    return retry[0] if retry else None


def summarise_points(items: Sequence[Mapping]) -> tuple[float, float, float]:
    """(earned, possible, pct) for a list of breakdown items."""
    earned = sum(float(i.get("earned", 0)) for i in items)
    possible = sum(float(i.get("possible", 0)) for i in items)
    return earned, possible, (earned / possible if possible else 0.0)
