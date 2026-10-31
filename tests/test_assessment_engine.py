"""Unit tests for the pure scoring rules (no database, no web)."""
import unittest

from skillztrack import assessment_engine as ae
from skillztrack.assessment_engine import AttemptEvidence as E


class AttemptScoreTests(unittest.TestCase):
    def test_ceiling_limits_what_an_assignment_can_prove(self):
        self.assertEqual(ae.attempt_score(3, 1.0), 3.0)      # a quiz can never give more than 3
        self.assertEqual(ae.attempt_score(5, 1.0), 5.0)

    def test_eighty_percent_counts_as_full_mastery(self):
        self.assertEqual(ae.attempt_score(4, 0.8), 4.0)
        self.assertEqual(ae.attempt_score(4, 0.4), 2.0)
        self.assertEqual(ae.attempt_score(4, 0.0), 0.0)

    def test_retakes_are_discounted_after_two_free_attempts(self):
        self.assertEqual(ae.attempt_score(4, 1.0, 1), 4.0)
        self.assertEqual(ae.attempt_score(4, 1.0, 2), 4.0)
        self.assertEqual(ae.attempt_score(4, 1.0, 3), 3.4)
        self.assertLess(ae.attempt_score(4, 1.0, 5), ae.attempt_score(4, 1.0, 3))

    def test_out_of_range_pct_is_clamped(self):
        self.assertEqual(ae.attempt_score(3, 7.0), 3.0)
        self.assertEqual(ae.attempt_score(3, -1.0), 0.0)


class SkillScoreTests(unittest.TestCase):
    def test_no_evidence_means_no_score(self):
        self.assertIsNone(ae.skill_score([]))

    def test_best_attempt_per_assignment_counts(self):
        r = ae.skill_score([E(1, 3, "quiz", 0.2, 1), E(1, 3, "quiz", 1.0, 2)])
        self.assertEqual(r.score, 3.0)
        self.assertEqual(r.assignments, 1)

    def test_a_worse_retry_never_lowers_the_score(self):
        first_only = ae.skill_score([E(1, 4, "executed", 0.8, 1)])
        with_bad_retry = ae.skill_score([E(1, 4, "executed", 0.8, 1), E(1, 4, "executed", 0.1, 2)])
        self.assertEqual(first_only.score, with_bad_retry.score)

    def test_one_assignment_is_capped_at_three_and_a_half(self):
        r = ae.skill_score([E(1, 5, "executed", 1.0, 1)])
        self.assertEqual(r.score, 3.5)
        self.assertEqual(r.level, 3)
        self.assertTrue(r.capped)

    def test_two_assignments_unlock_advanced_levels(self):
        r = ae.skill_score([E(1, 5, "executed", 1.0, 1), E(2, 3, "quiz", 1.0, 1)])
        self.assertEqual(r.score, 5.0)
        self.assertEqual(r.level, 5)
        self.assertFalse(r.capped)

    def test_quiz_only_evidence_can_never_exceed_level_three(self):
        r = ae.skill_score([E(1, 3, "quiz", 1.0, 1), E(2, 3, "quiz", 1.0, 1), E(3, 3, "quiz", 1.0, 1)])
        self.assertEqual(r.level, 3)

    def test_level_is_the_floor_of_the_score(self):
        r = ae.skill_score([E(1, 4, "executed", 0.7, 1), E(2, 3, "quiz", 1.0, 1)])
        self.assertAlmostEqual(r.score, 3.5)
        self.assertEqual(r.level, 3)
        self.assertEqual(r.progress_to_next, 50)

    def test_failing_a_hard_task_does_not_erase_easy_evidence(self):
        r = ae.skill_score([E(1, 3, "quiz", 1.0, 1), E(2, 5, "executed", 0.1, 1)])
        self.assertEqual(r.score, 3.0)

    def test_confidence_levels(self):
        self.assertEqual(ae.skill_score([E(1, 3, "quiz", 1.0, 1)]).confidence, "low")
        self.assertEqual(ae.skill_score([E(1, 3, "quiz", 1.0, 1), E(2, 4, "static", 1.0, 1)]).confidence, "medium")
        high = ae.skill_score([E(1, 3, "quiz", 1.0, 1), E(2, 4, "static", 1.0, 1), E(3, 5, "executed", 1.0, 1)])
        self.assertEqual(high.confidence, "high")
        no_exec = ae.skill_score([E(1, 3, "quiz", 1.0, 1), E(2, 4, "static", 1.0, 1), E(3, 4, "static", 1.0, 1)])
        self.assertEqual(no_exec.confidence, "medium")   # high needs auto-tested evidence

    def test_contradictory_evidence_lowers_confidence(self):
        r = ae.skill_score([E(1, 2, "quiz", 0.2, 1), E(2, 5, "executed", 1.0, 1), E(3, 4, "static", 1.0, 1)])
        self.assertTrue(r.contradictory)
        self.assertEqual(r.confidence, "medium")        # would have been high


class InsightTests(unittest.TestCase):
    ITEMS = [{"topic": "loops", "earned": 1, "possible": 1}, {"topic": "loops", "earned": 1, "possible": 1},
             {"topic": "recursion", "earned": 0, "possible": 2}, {"topic": "edge cases", "earned": 1, "possible": 3}]

    def test_topic_stats_and_weak_topics(self):
        stats = ae.topic_stats([self.ITEMS])
        weak = ae.weak_topics(stats)
        self.assertEqual([t.topic for t in weak], ["recursion", "edge cases"])
        self.assertEqual([t.topic for t in ae.strong_topics(stats)], ["loops"])

    def test_calibration(self):
        self.assertEqual(ae.calibration(5, 2), "overconfident")
        self.assertEqual(ae.calibration(1, 4), "underconfident")
        self.assertEqual(ae.calibration(3, 2), "calibrated")
        self.assertEqual(ae.calibration(None, 2), "no_claim")

    def test_recommend_next_prefers_untried_easier_assignments(self):
        opts = [ae.AssignmentOption(1, "quiz", 3), ae.AssignmentOption(2, "hard", 5), ae.AssignmentOption(3, "mid", 4)]
        self.assertEqual(ae.recommend_next(opts, 0.0).slug, "quiz")
        self.assertEqual(ae.recommend_next(opts, 0.0, claimed=4).slug, "mid")   # a strong claim starts higher, still not evidence
        opts[0] = ae.AssignmentOption(1, "quiz", 3, 1, 1.0)
        self.assertEqual(ae.recommend_next(opts, 3.0).slug, "mid")

    def test_recommend_next_retries_weakest_when_all_tried(self):
        opts = [ae.AssignmentOption(1, "a", 4, 1, 0.3), ae.AssignmentOption(2, "b", 4, 2, 0.6)]
        self.assertEqual(ae.recommend_next(opts, 1.0).slug, "a")

    def test_recommend_next_is_none_when_nothing_can_help(self):
        opts = [ae.AssignmentOption(1, "a", 3, 1, 1.0)]
        self.assertIsNone(ae.recommend_next(opts, 3.0))
        self.assertIsNone(ae.recommend_next([ae.AssignmentOption(1, "a", 4, ae.MAX_ATTEMPTS, 0.1)], 0.0))


if __name__ == "__main__":
    unittest.main()
