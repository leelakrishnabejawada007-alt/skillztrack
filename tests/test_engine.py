"""Unit tests for the pure rule engine (no database needed)."""
import unittest

from skillztrack import engine
from skillztrack.engine import Requirement, ResourceInfo

REQS = [
    Requirement(1, "HTML & CSS", required_level=4, importance=3, sequence=1),
    Requirement(2, "JavaScript", required_level=4, importance=3, sequence=2),
    Requirement(3, "Git", required_level=3, importance=2, sequence=3),
    Requirement(4, "Deployment", required_level=2, importance=1, sequence=4),
]


class AnalyzeTests(unittest.TestCase):
    def test_gap_priority_and_severity(self):
        result = engine.analyze(REQS, {1: 4, 2: 1, 3: 2})  # skill 4 unrated -> 0
        by_id = {g.skill_id: g for g in result.gaps}
        self.assertEqual(by_id[1].gap, 0)
        self.assertEqual(by_id[1].severity, "strong")
        self.assertEqual(by_id[2].gap, 3)
        self.assertEqual(by_id[2].priority, 9)
        self.assertEqual(by_id[2].severity, "critical")
        self.assertEqual(by_id[3].severity, "minor")
        self.assertEqual(by_id[4].current_level, 0)
        self.assertEqual(by_id[4].severity, "moderate")

    def test_weaknesses_sorted_by_priority(self):
        result = engine.analyze(REQS, {1: 4, 2: 1, 3: 2})
        self.assertEqual([g.skill_id for g in result.weaknesses], [2, 3, 4])

    def test_readiness_bounds(self):
        none = engine.analyze(REQS, {})
        full = engine.analyze(REQS, {1: 5, 2: 5, 3: 5, 4: 5})
        self.assertEqual(none.readiness_percent, 0.0)
        self.assertEqual(full.readiness_percent, 100.0)
        self.assertEqual(full.weaknesses, [])

    def test_readiness_weighted_value(self):
        # achieved = 4*3 + 1*3 + 2*2 + 0 = 19 ; total = 4*3 + 4*3 + 3*2 + 2*1 = 32
        result = engine.analyze(REQS, {1: 4, 2: 1, 3: 2})
        self.assertEqual(result.readiness_percent, round(100 * 19 / 32, 1))

    def test_levels_are_clamped(self):
        result = engine.analyze(REQS, {1: 99, 2: -5})
        by_id = {g.skill_id: g for g in result.gaps}
        self.assertEqual(by_id[1].current_level, 5)
        self.assertEqual(by_id[2].current_level, 0)

    def test_empty_requirements_is_ready(self):
        self.assertEqual(engine.analyze([], {}).readiness_percent, 100.0)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.weak = engine.analyze(REQS, {1: 4, 2: 1, 3: 2}).weaknesses

    def test_only_gaps_become_milestones_in_sequence_order(self):
        plans = engine.plan_milestones(self.weak, hours_per_week=10)
        self.assertEqual([p.skill_id for p in plans], [2, 3, 4])
        self.assertEqual([p.sequence for p in plans], [1, 2, 3])

    def test_hours_and_weeks(self):
        plans = engine.plan_milestones(self.weak, hours_per_week=10)
        self.assertEqual([p.estimated_hours for p in plans], [36, 12, 24])
        self.assertEqual((plans[0].start_week, plans[0].end_week), (1, 4))  # 36h -> 3.6 weeks
        self.assertEqual((plans[1].start_week, plans[1].end_week), (4, 5))  # 36..48h
        self.assertEqual((plans[2].start_week, plans[2].end_week), (5, 8))  # 48..72h
        for p in plans:
            self.assertGreaterEqual(p.end_week, p.start_week)

    def test_top_three_priorities_flagged(self):
        reqs = REQS + [Requirement(5, "SQL", 4, 3, 5)]
        weak = engine.analyze(reqs, {}).weaknesses
        plans = engine.plan_milestones(weak, 8)
        flagged = {p.skill_id for p in plans if p.is_priority}
        self.assertEqual(len(flagged), 3)
        self.assertNotIn(4, flagged)  # lowest priority (gap 2 x importance 1)

    def test_invalid_hours_per_week_is_safe(self):
        plans = engine.plan_milestones(self.weak, hours_per_week=0)
        self.assertTrue(all(p.end_week >= 1 for p in plans))


class ResourceTests(unittest.TestCase):
    def test_bands_for_range(self):
        self.assertEqual(engine.bands_for_range(0, 1), ("beginner",))
        self.assertEqual(engine.bands_for_range(1, 4), ("intermediate", "advanced"))
        self.assertEqual(engine.bands_for_range(0, 5), ("beginner", "intermediate", "advanced"))

    def test_one_per_band_then_free_first(self):
        pool = [
            ResourceInfo(1, "beginner", 10, True),
            ResourceInfo(2, "beginner", 3, False),
            ResourceInfo(3, "intermediate", 8, True),
            ResourceInfo(4, "advanced", 6, True),
            ResourceInfo(5, "advanced", 2, True),
        ]
        picked = engine.pick_resources(pool, ("beginner", "intermediate", "advanced"), limit=3)
        self.assertEqual(picked, [1, 3, 5])  # free beats paid; shorter free advanced wins

    def test_limit_and_missing_bands(self):
        pool = [ResourceInfo(i, "beginner") for i in range(1, 9)]
        picked = engine.pick_resources(pool, ("beginner", "advanced"), limit=4)
        self.assertEqual(len(picked), 4)
        self.assertEqual(engine.pick_resources([], ("beginner",)), [])

    def test_progress_percent(self):
        self.assertEqual(engine.progress_percent(0, 0), 0)
        self.assertEqual(engine.progress_percent(1, 3), 33)
        self.assertEqual(engine.progress_percent(3, 3), 100)


if __name__ == "__main__":
    unittest.main()
