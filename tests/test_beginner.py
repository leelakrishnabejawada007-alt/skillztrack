"""Beginner track: easy tasks first, hints without spoilers, free retries, skill score + roadmap update."""
import unittest

from skillztrack import assessment_engine as ae
from skillztrack import bank, graders
from tests.test_assessment_app import AssessmentFlowCase


class BeginnerRulesTests(unittest.TestCase):
    def test_every_skill_has_a_level_1_starting_task(self):
        from skillztrack.seed_content import SKILLS
        for skill in SKILLS:
            self.assertEqual(min(a.ceiling for a in bank.for_skill(skill[0])), 1, skill[0])

    def test_beginner_tasks_have_steps_example_and_hints(self):
        for a in bank.all_assignments():
            if a.kind in {"code", "debug"} and a.ceiling <= 2:
                self.assertTrue(a.steps and a.example and a.hints, a.slug)
                self.assertTrue(all(t.get("hint") for t in a.spec["tests"]), a.slug)

    def test_beginner_retries_are_free_and_allow_10_attempts(self):
        self.assertEqual(ae.max_attempts(1), 10)
        self.assertEqual(ae.max_attempts(3), 5)
        self.assertEqual(ae.attempt_score(2, 1.0, attempt_no=6), 2.0)
        self.assertLess(ae.attempt_score(3, 1.0, attempt_no=3), 3.0)

    def test_wrong_quiz_answer_shows_hint_not_explanation(self):
        a = bank.get("first-steps-python")
        payload = graders.make_quiz_payload(a.spec)
        by_id = {q["id"]: q for q in a.spec["pool"]}
        answers = {e["id"]: str((by_id[e["id"]]["answer"] + 1) % 4) for e in payload["questions"]}
        for item in graders.grade_quiz(a.spec, payload, answers).items:
            q = by_id[item["id"]]
            self.assertIn(q["hint"], item["feedback"])
            self.assertNotIn(q["why"], item["feedback"])

    def test_wrong_code_shows_test_hint(self):
        a = bank.get("py-first-functions")
        r = graders.grade_submission(a, None, {"code": a.starter})
        self.assertTrue(all("Hint:" in i["feedback"] for i in r.items if not i["passed"]))


class BeginnerFlowTests(AssessmentFlowCase):
    def test_retry_after_mistakes_then_pass_updates_skill_score(self):
        a = bank.get("py-first-functions")
        aid, _ = self.submit_code("py-first-functions", a.starter)
        page = self.client.get(f"/attempts/{aid}").text
        self.assertIn("Hint:", page)
        self.assertNotIn(a.reference.splitlines()[1].strip(), page)  # solution not revealed
        self.submit_code("py-first-functions", a.reference)
        self.assertEqual(self.skill("python")[0]["score"], 1.0)

    def test_beginner_detail_page_shows_steps_and_expected_output(self):
        page = self.client.get("/assignments/py-first-functions").text
        for text in ("Step by step", "Example and expected output", "Show hints", "Beginner"):
            self.assertIn(text, page)
