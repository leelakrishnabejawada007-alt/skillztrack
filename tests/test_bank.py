"""The bank checks itself: every task must be solvable (reference scores 100%), the untouched starter must not,
and a deliberately bad answer must lose points. This is what keeps hidden tests fair."""
import unittest

from skillztrack import bank, graders
from skillztrack import assessment_engine as ae
from tests import bank_answers as ans
from tests.test_app import AppTestCase  # noqa: F401  (also sets fast PBKDF2 for any DB use)


def pct(result):
    return ae.summarise_points(result.items)[2]


def all_passed(result):
    return all(i["passed"] for i in result.items)


class BankStructureTests(unittest.TestCase):
    def test_every_assignment_has_valid_metadata(self):
        items = bank.all_assignments()
        self.assertGreaterEqual(len(items), 50)
        for a in items:
            self.assertTrue(1 <= a.ceiling <= 5, a.slug)
            self.assertTrue(a.title and a.summary and a.minutes > 0, a.slug)
            if a.kind == "quiz":
                self.assertLessEqual(a.ceiling, 3, "quizzes alone must not prove advanced levels")
            if a.evidence == "static":
                self.assertLessEqual(a.ceiling, 4, a.slug)

    def test_every_skill_has_a_quiz_and_a_practical_assignment(self):
        from skillztrack.seed_content import SKILLS
        for skill in SKILLS:
            slug = skill[0]
            kinds = {a.kind for a in bank.for_skill(slug)}
            self.assertIn("quiz", kinds, slug)
            self.assertTrue(kinds - {"quiz"}, f"{slug} has only a quiz")

    def test_required_levels_are_reachable_and_need_two_assignments_for_level_4(self):
        from skillztrack.seed_content import REQUIREMENTS
        needed = {}
        for rows in REQUIREMENTS.values():
            for slug, level, *_ in rows:
                needed[slug] = max(needed.get(slug, 0), level)
        for slug, level in needed.items():
            ceilings = sorted((a.ceiling for a in bank.for_skill(slug)), reverse=True)
            self.assertGreaterEqual(ceilings[0], level, f"{slug} needs level {level} but no assignment can prove it")
            if level >= 4:
                self.assertGreaterEqual(len([c for c in ceilings if c >= 3]), 2, f"{slug}: level 4 needs two corroborating assignments")

    def test_quiz_pools_are_well_formed(self):
        for a in bank.all_assignments():
            if a.kind != "quiz":
                continue
            pool = a.spec["pool"]
            self.assertGreater(len(pool), a.spec["draw"], a.slug)
            self.assertEqual(len({q["id"] for q in pool}), len(pool))
            for q in pool:
                self.assertTrue(0 <= q["answer"] < len(q["options"]), q["id"])
                self.assertEqual(len(set(q["options"])), len(q["options"]), q["id"])

    def test_quiz_draw_shuffles_and_hides_answers(self):
        a = bank.get("quiz-python")
        payload = graders.make_quiz_payload(a.spec)
        shown = graders.present_quiz(a.spec, payload)
        self.assertEqual(len(shown), a.spec["draw"])
        for q in shown:
            self.assertNotIn("answer", q)
            self.assertNotIn("why", q)


class ExecutableAssignmentTests(unittest.TestCase):
    def test_reference_solutions_score_full_marks_and_starters_do_not(self):
        for a in bank.all_assignments():
            if a.kind not in {"code", "debug"}:
                continue
            with self.subTest(a.slug):
                ref = graders.grade_submission(a, None, {"code": a.reference})
                self.assertTrue(all_passed(ref), [i["label"] for i in ref.items if not i["passed"]])
                starter = graders.grade_submission(a, None, {"code": a.starter})
                self.assertLess(pct(starter), 1.0)

    def test_debug_starters_are_partly_correct(self):
        # "debug" tasks are meant to be partially working: some tests pass on the buggy code, some fail
        for slug in ("debug-pack", "config-loader-debug", "secure-code-fix"):
            r = graders.grade_submission(bank.get(slug), None, {"code": bank.get(slug).starter})
            self.assertTrue(0 < pct(r) < 1, slug)

    def test_every_hidden_test_is_checked_against_a_correct_expectation(self):
        # a test whose expectation is wrong would also fail the reference; the previous test covers it. Here: no
        # zero-weight (decorative) tests and every test has a label and topic.
        for a in bank.all_assignments():
            if a.kind in {"code", "debug"}:
                for t in a.spec["tests"]:
                    self.assertGreater(t["weight"], 0, (a.slug, t["label"]))
                    self.assertTrue(t["label"] and t["topic"])

    def test_wrong_but_plausible_solution_loses_points(self):
        a = bank.get("dsa-core")
        slow_and_wrong = a.reference.replace("if target - x in seen:", "if False:")
        self.assertLess(pct(graders.grade_submission(a, None, {"code": slow_and_wrong})), 0.8)

    def test_quadratic_two_sum_times_out_on_large_input(self):
        a = bank.get("dsa-core")
        quadratic = ("def two_sum(nums, target):\n    for i in range(len(nums)):\n        for j in range(i + 1, len(nums)):\n"
                     "            if nums[i] + nums[j] == target:\n                return [i, j]\n    return None\n"
                     + a.reference.split("def is_valid_parentheses", 1)[1].join(["def is_valid_parentheses", ""]))
        r = graders.grade_submission(a, None, {"code": quadratic})
        perf = [i for i in r.items if "20,000" in i["label"]][0]
        self.assertFalse(perf["passed"])
        self.assertIn("Timed out", perf["feedback"])

    def test_statistics_module_is_forbidden_where_the_task_is_to_implement_it(self):
        a = bank.get("statistics-from-scratch")
        with self.assertRaises(graders.SubmissionRejected):
            graders.grade_submission(a, None, {"code": "import statistics\n" + a.reference})

    def test_subclass_of_expected_exception_is_accepted(self):
        a = bank.get("network-calculations")  # ipaddress raises AddressValueError, a ValueError subclass
        r = graders.grade_submission(a, None, {"code": a.reference})
        self.assertTrue(all_passed(r))


class MutationTestingTests(unittest.TestCase):
    def setUp(self):
        self.a = bank.get("mutation-testing")

    def test_a_good_test_suite_catches_every_bug(self):
        r = graders.grade_submission(self.a, None, {"code": self.a.reference})
        self.assertTrue(all_passed(r), [i["label"] for i in r.items if not i["passed"]])
        self.assertEqual(len(r.items), 1 + len(self.a.spec["mutants"]))

    def test_weak_suite_misses_bugs(self):
        weak = "def test_cases():\n    return [[[2], 7.0], [[3], 9.0], [[5], 13.0], [[10], 5.0 + 2.0 * 9]]\n"
        r = graders.grade_submission(self.a, None, {"code": weak})
        killed = [i for i in r.items if i["id"].startswith("m") and i["passed"]]
        self.assertLess(len(killed), len(self.a.spec["mutants"]))
        self.assertLess(pct(r), 0.8)

    def test_incorrect_expectations_are_penalised(self):
        wrong = "def test_cases():\n    return [[[1], 99.0], [[2], 7.0], [[3], 9.0], [[4], 11.0]]\n"
        r = graders.grade_submission(self.a, None, {"code": wrong})
        valid = next(i for i in r.items if i["id"] == "valid")
        self.assertLess(valid["earned"], valid["possible"])
        self.assertIn("expect the wrong result", valid["feedback"])

    def test_malformed_or_too_few_tests_are_rejected(self):
        for code in ("def test_cases():\n    return [1, 2, 3, 4]\n", "def test_cases():\n    return [[[2], 7.0]]\n", "x = 1\n"):
            with self.assertRaises(graders.SubmissionRejected):
                graders.grade_submission(self.a, None, {"code": code})

    def test_tests_that_only_pass_on_the_wrong_code_are_not_rewarded(self):
        # expectations copied from a buggy mutant, not from the specification
        r = graders.grade_submission(self.a, None, {"code": "def test_cases():\n    return [[[1.2], 5.0], [[0], 5.0], [[2], 7.0], [[3], 9.0]]\n"})
        self.assertLess(pct(r), 0.7)


class SqlLabTests(unittest.TestCase):
    def test_reference_queries_score_full_marks(self):
        for slug in ("sql-foundations", "sql-analyst"):
            a = bank.get(slug)
            r = graders.grade_submission(a, None, {q["id"]: q["expected_sql"] for q in a.spec["questions"]})
            self.assertTrue(all_passed(r), slug)

    def test_equivalent_query_written_differently_passes(self):
        a = bank.get("sql-analyst")
        alt = {"q3": "SELECT c.name FROM customers c LEFT JOIN orders o ON o.customer_id = c.id WHERE o.id IS NULL"}
        r = graders.grade_submission(a, None, alt)
        self.assertTrue(next(i for i in r.items if i["id"] == "q3")["passed"])

    def test_wrong_filter_is_caught_by_the_data(self):
        a = bank.get("sql-analyst")
        no_status_filter = ("SELECT c.name, SUM(oi.quantity * p.price) AS revenue FROM customers c JOIN orders o ON o.customer_id = c.id "
                            "JOIN order_items oi ON oi.order_id = o.id JOIN products p ON p.id = oi.product_id "
                            "GROUP BY c.id HAVING revenue > 1000 ORDER BY revenue DESC")
        item = next(i for i in graders.grade_submission(a, None, {"q4": no_status_filter}).items if i["id"] == "q4")
        self.assertFalse(item["passed"])

    def test_right_rows_wrong_order_gets_half_credit(self):
        a = bank.get("sql-foundations")
        r = graders.grade_submission(a, None, {"q2": "SELECT name, price FROM products WHERE price > 500 ORDER BY price ASC"})
        item = next(i for i in r.items if i["id"] == "q2")
        self.assertEqual(item["earned"], item["possible"] * 0.5)

    def test_only_select_is_allowed(self):
        a = bank.get("sql-foundations")
        for evil in ("DROP TABLE customers", "DELETE FROM customers", "SELECT 1; DROP TABLE customers",
                     "ATTACH DATABASE 'x.db' AS x", "PRAGMA table_info(customers)", "UPDATE customers SET name='x'"):
            item = next(i for i in graders.grade_submission(a, None, {"q1": evil}).items if i["id"] == "q1")
            self.assertFalse(item["passed"], evil)

    def test_runaway_query_is_stopped(self):
        a = bank.get("sql-foundations")
        bomb = ("WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r) SELECT n FROM r")
        item = next(i for i in graders.grade_submission(a, None, {"q1": bomb}).items if i["id"] == "q1")
        self.assertFalse(item["passed"])


class PatternLabTests(unittest.TestCase):
    def test_known_good_answers_are_accepted(self):
        for slug, answers in ans.COMMANDS.items():
            a = bank.get(slug)
            self.assertEqual(set(answers), {p["id"] for p in a.spec["prompts"]}, slug)
            r = graders.grade_submission(a, None, answers)
            self.assertTrue(all_passed(r), (slug, [(i["id"], i["feedback"]) for i in r.items if not i["passed"]]))

    def test_wrong_or_dangerous_answers_are_rejected(self):
        for slug, wrong in ans.WRONG_COMMANDS.items():
            a = bank.get(slug)
            r = graders.grade_submission(a, None, {**ans.COMMANDS[slug], **wrong})
            failed = {i["id"] for i in r.items if not i["passed"]}
            self.assertEqual(failed, set(wrong), slug)

    def test_blank_answers_are_rejected(self):
        with self.assertRaises(graders.SubmissionRejected):
            graders.grade_submission(bank.get("git-command-lab"), None, {})


class RubricTests(unittest.TestCase):
    def test_good_submissions_pass_every_criterion(self):
        for slug, text in ans.RUBRICS.items():
            r = graders.grade_submission(bank.get(slug), None, {"text": text})
            self.assertTrue(all_passed(r), (slug, [(i["label"], i["feedback"]) for i in r.items if not i["passed"]]))

    def test_the_starter_templates_do_not_pass(self):
        for slug in ans.RUBRICS:
            a = bank.get(slug)
            if a.starter.strip():
                try:
                    r = graders.grade_submission(a, None, {"text": a.starter})
                except graders.SubmissionRejected:
                    continue
                self.assertLess(pct(r), 0.5, slug)

    def test_html_checks_find_real_problems(self):
        a = bank.get("responsive-landing-page")
        broken = ans.HTML.replace('alt="Inside the cafe with wooden tables"', "").replace('<label for="email">Email</label>', "") \
                         .replace("@media (max-width: 40rem)", "@supports (display: grid)").replace("</section>", "", 1)
        r = graders.grade_submission(a, None, {"text": broken})
        failed = {i["id"] for i in r.items if not i["passed"]}
        self.assertTrue({"h1", "h7", "h8", "c2"} <= failed, failed)

    def test_iam_wildcard_policy_is_penalised_but_still_parsed(self):
        r = graders.grade_submission(bank.get("iam-least-privilege"), None, {"text": ans.IAM_BAD})
        failed = {i["id"] for i in r.items if not i["passed"]}
        self.assertTrue({"i3", "i4", "i5", "i6"} <= failed)
        self.assertIn("i1", {i["id"] for i in r.items if i["passed"]})

    def test_invalid_json_is_reported(self):
        r = graders.grade_submission(bank.get("iam-least-privilege"), None, {"text": "{ \"Version\": 2012, this is not valid json at all"})
        self.assertEqual(sum(1 for i in r.items if i["passed"]), 0)

    def test_dockerfile_latest_tag_and_root_user_fail(self):
        bad = "FROM python:latest\nCOPY . .\nRUN pip install -r requirements.txt\nCMD python app.py\n"
        r = graders.grade_submission(bank.get("dockerfile-review"), None, {"text": bad})
        failed = {i["id"] for i in r.items if not i["passed"]}
        self.assertTrue({"d1", "d4", "d5", "d6", "d8"} <= failed, failed)

    def test_vague_bug_report_fails_most_criteria(self):
        r = graders.grade_submission(bank.get("bug-report-writing"), None, {"text": "Checkout is broken and the developers obviously did a terrible job. Please fix it right now or else."})
        self.assertLess(pct(r), 0.4)


if __name__ == "__main__":
    unittest.main()
