"""
SkillzTrack's rule-based engine: skill-gap analysis + roadmap planning.

WHY A SEPARATE, "PURE" MODULE?
    Nothing here imports Django or touches the database. It takes plain Python
    values in and returns plain Python values out. That makes the rules easy to
    read, easy to unit-test, and easy to explain in a viva:

        requirements + your ratings  --analyze()-->  gaps + readiness %
        gaps + hours per week        --plan_milestones()-->  ordered milestones
        resources + difficulty bands --pick_resources()-->   the best resources

THE RULES (all of them, in plain English)
    1. Skills are rated on a 0-5 scale (0 = no experience, 5 = expert).
    2. gap        = max(required_level - your_level, 0)
    3. priority   = gap x importance          (importance: 1 nice, 2 important, 3 core)
    4. severity   : gap 0 strong, 1 minor, 2 moderate, 3+ critical
    5. readiness% = sum(min(you, required) x importance) / sum(required x importance)
    6. A milestone is created ONLY for skills with a gap. Milestones follow the
       career's learning sequence (prerequisites first, e.g. HTML before Django).
    7. Estimated effort = gap x 12 hours; weeks come from your hours per week.
    8. The three highest-priority gaps are flagged "focus".
    9. Resources: levels climbed map to difficulty bands
       (1 -> beginner, 2-3 -> intermediate, 4-5 -> advanced). We pick the best
       resource per band (free + shorter first), then fill up to 4.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from .levels import MAX_LEVEL, MIN_LEVEL, level_label

HOURS_PER_LEVEL = 12
TOP_PRIORITY_COUNT = 3
MAX_RESOURCES_PER_MILESTONE = 4
DIFFICULTY_ORDER = ("beginner", "intermediate", "advanced")

SEVERITY_LABELS = {
    "strong": "On target",
    "minor": "Small gap",
    "moderate": "Moderate gap",
    "critical": "Big gap",
}


# --------------------------------------------------------------------------- data
@dataclass(frozen=True)
class Requirement:
    skill_id: int
    name: str
    required_level: int
    importance: int = 2
    sequence: int = 0


@dataclass(frozen=True)
class SkillGap:
    skill_id: int
    name: str
    current_level: int
    required_level: int
    importance: int
    sequence: int
    gap: int
    priority: int
    severity: str

    @property
    def current_percent(self) -> int:
        return round(100 * self.current_level / MAX_LEVEL)

    @property
    def required_percent(self) -> int:
        return round(100 * self.required_level / MAX_LEVEL)

    @property
    def current_label(self) -> str:
        return level_label(self.current_level)

    @property
    def required_label(self) -> str:
        return level_label(self.required_level)

    @property
    def severity_label(self) -> str:
        return SEVERITY_LABELS[self.severity]


@dataclass(frozen=True)
class AnalysisResult:
    gaps: tuple
    readiness_percent: float

    @property
    def strengths(self):
        return [g for g in self.gaps if g.gap == 0]

    @property
    def weaknesses(self):
        """Skills with a gap, most urgent first."""
        return sorted(
            (g for g in self.gaps if g.gap > 0),
            key=lambda g: (-g.priority, g.sequence, g.skill_id),
        )

    @property
    def total_gap_levels(self) -> int:
        return sum(g.gap for g in self.gaps)

    @property
    def estimated_hours(self) -> int:
        return self.total_gap_levels * HOURS_PER_LEVEL

    @property
    def readiness_label(self) -> str:
        return readiness_label(self.readiness_percent)


@dataclass(frozen=True)
class MilestonePlan:
    sequence: int
    skill_id: int
    name: str
    from_level: int
    target_level: int
    estimated_hours: int
    start_week: int
    end_week: int
    is_priority: bool
    severity: str
    difficulty_bands: tuple


@dataclass(frozen=True)
class ResourceInfo:
    id: int
    difficulty: str
    estimated_hours: int = 5
    is_free: bool = True


# ------------------------------------------------------------------------ helpers
def clamp_level(value) -> int:
    return max(MIN_LEVEL, min(MAX_LEVEL, int(value)))


def classify_gap(gap: int) -> str:
    if gap <= 0:
        return "strong"
    if gap == 1:
        return "minor"
    if gap == 2:
        return "moderate"
    return "critical"


def readiness_label(percent: float) -> str:
    if percent < 35:
        return "Just starting out"
    if percent < 60:
        return "Building foundations"
    if percent < 85:
        return "Almost there"
    return "Job-ready"


def difficulty_for_level(level: int) -> str:
    """Difficulty of material needed to *reach* this level."""
    if level <= 1:
        return "beginner"
    if level <= 3:
        return "intermediate"
    return "advanced"


def bands_for_range(from_level: int, target_level: int) -> tuple:
    bands = []
    for level in range(from_level + 1, target_level + 1):
        band = difficulty_for_level(level)
        if band not in bands:
            bands.append(band)
    return tuple(bands)


def progress_percent(done: int, total: int) -> int:
    return 0 if total <= 0 else round(100 * done / total)


# -------------------------------------------------------------------------- rules
def analyze(requirements: Sequence[Requirement], ratings: Mapping[int, int]) -> AnalysisResult:
    """Rules 2-5: compare required levels with the student's self-ratings."""
    gaps = []
    for req in requirements:
        current = clamp_level(ratings.get(req.skill_id, 0))
        required = clamp_level(req.required_level)
        gap = max(required - current, 0)
        gaps.append(
            SkillGap(
                skill_id=req.skill_id,
                name=req.name,
                current_level=current,
                required_level=required,
                importance=req.importance,
                sequence=req.sequence,
                gap=gap,
                priority=gap * req.importance,
                severity=classify_gap(gap),
            )
        )
    total = sum(g.required_level * g.importance for g in gaps)
    achieved = sum(min(g.current_level, g.required_level) * g.importance for g in gaps)
    readiness = round(100 * achieved / total, 1) if total else 100.0
    return AnalysisResult(gaps=tuple(gaps), readiness_percent=readiness)


def plan_milestones(weaknesses: Sequence[SkillGap], hours_per_week: int) -> list:
    """Rules 6-8: turn gaps into an ordered, time-boxed list of milestones."""
    hours_per_week = max(1, int(hours_per_week))
    focus_ids = {
        g.skill_id
        for g in sorted(weaknesses, key=lambda g: (-g.priority, g.sequence, g.skill_id))[
            :TOP_PRIORITY_COUNT
        ]
    }
    plans = []
    cumulative_hours = 0
    for index, gap in enumerate(sorted(weaknesses, key=lambda g: (g.sequence, g.skill_id)), start=1):
        hours = gap.gap * HOURS_PER_LEVEL
        start_week = cumulative_hours // hours_per_week + 1
        cumulative_hours += hours
        end_week = max(start_week, math.ceil(cumulative_hours / hours_per_week))
        plans.append(
            MilestonePlan(
                sequence=index,
                skill_id=gap.skill_id,
                name=gap.name,
                from_level=gap.current_level,
                target_level=gap.required_level,
                estimated_hours=hours,
                start_week=start_week,
                end_week=end_week,
                is_priority=gap.skill_id in focus_ids,
                severity=gap.severity,
                difficulty_bands=bands_for_range(gap.current_level, gap.required_level),
            )
        )
    return plans


def pick_resources(
    resources: Sequence[ResourceInfo],
    bands: Sequence[str],
    limit: int = MAX_RESOURCES_PER_MILESTONE,
) -> list:
    """Rule 9: choose resource ids - one per difficulty band first, then fill."""
    by_band = {
        band: sorted(
            (r for r in resources if r.difficulty == band),
            key=lambda r: (not r.is_free, r.estimated_hours, r.id),
        )
        for band in bands
    }
    chosen = [items[0] for items in by_band.values() if items]
    for items in by_band.values():
        for resource in items[1:]:
            if len(chosen) >= limit:
                break
            chosen.append(resource)
    chosen = chosen[:limit]
    order = {band: i for i, band in enumerate(bands)}
    chosen.sort(key=lambda r: (order[r.difficulty], not r.is_free, r.estimated_hours, r.id))
    return [r.id for r in chosen]
