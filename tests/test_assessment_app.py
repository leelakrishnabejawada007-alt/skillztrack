"""End-to-end tests of the assessment flow: real requests, real grading, real database."""
import json
import re

from skillztrack import assessment_engine as ae
from skillztrack import bank, config, db
from tests.test_app import AppTestCase, Client


class AssessmentFlowCase(AppTestCase):
    def setUp(self):
        super().setUp()
        from skillztrack import assessment_views
        assessment_views._submits.clear()      # the per-user submit limiter is process-wide state
        self.register()
        self.client.post("/career", {"career_id": self.career_id()})      # Web Developer

    # ---- helpers
    def start(self, slug, client=None):
        r = (client or self.client).post(f"/assignments/{slug}/start")
        self.assertEqual(r.status, 303, r.text[:200])
        self.assertRegex(r.location, r"^/attempts/\d+$")
        return int(r.location.rsplit("/", 1)[1])

    def quiz_form(self, attempt_id, correct=True):
        row = self.query("SELECT payload, a.slug FROM attempts at JOIN assignments a ON a.id = at.assignment_id WHERE at.id = ?", attempt_id)[0]
        by_id = {q["id"]: q for q in bank.get(row["slug"]).spec["pool"]}
        form = {}
        for entry in json.loads(row["payload"])["questions"]:
            q = by_id[entry["id"]]
            wrong = next(i for i in range(len(q["options"])) if i != q["answer"])
            form[f"q_{q['id']}"] = str(q["answer"] if correct else wrong)
        return form

    def take_quiz(self, slug, correct=True, client=None):
        client = client or self.client
        aid = self.start(slug, client)
        r = client.post(f"/attempts/{aid}/submit", self.quiz_form(aid, correct))
        self.assertEqual(r.location, f"/attempts/{aid}", r.text[:200])
        return aid

    def submit_code(self, slug, code, client=None):
        client = client or self.client
        aid = self.start(slug, client)
        return aid, client.post(f"/attempts/{aid}/submit", {"code": code})

    def skill(self, slug="python"):
        return self.query("SELECT s.score, s.level, s.confidence, s.assignments_count FROM skill_scores s JOIN skills k ON k.id = s.skill_id "
                          "WHERE k.slug = ?", slug)


class QuizFlowTests(AssessmentFlowCase):
    def test_hub_lists_career_skills_and_recommends_a_starting_point(self):
        page = self.client.get("/assignments").text
        self.assertIn("Skill assessments", page)
        for name in ("HTML &amp; CSS", "JavaScript", "Python"):
            self.assertIn(name, page)
        self.assertIn("Recommended next", page)
        self.assertIn("0 of 8 skills verified", page)

    def test_the_answer_key_never_reaches_the_browser(self):
        aid = self.start("quiz-python")
        html = self.client.get(f"/attempts/{aid}").text
        spec = bank.get("quiz-python").spec
        for q in spec["pool"]:
            self.assertNotIn(q["why"], html)
        self.assertNotIn('"answer"', html)
        self.assertEqual(html.count('type="radio"') // 4, ae.MAX_ATTEMPTS and spec["draw"])

    def test_perfect_quiz_creates_a_verified_score_and_history(self):
        aid = self.take_quiz("quiz-python")
        page = self.client.get(f"/attempts/{aid}").text
        self.assertIn("100%", page)
        self.assertIn("First evidence for this skill", page)
        score, level, confidence, count = list(self.skill()[0])
        self.assertEqual((score, level, confidence, count), (3.0, 3, "low", 1))
        att = self.query("SELECT status, attempt_no, pct, skill_score, points, possible, duration_seconds FROM attempts WHERE id = ?", aid)[0]
        self.assertEqual((att["status"], att["attempt_no"], att["pct"], att["skill_score"]), ("graded", 1, 1.0, 3.0))
        self.assertEqual((att["points"], att["possible"]), (5, 5))
        self.assertIsNotNone(att["duration_seconds"])
        self.assertEqual(len(json.loads(self.query("SELECT breakdown FROM attempts WHERE id = ?", aid)[0]["breakdown"])), 5)
        self.assertEqual(self.query("SELECT COUNT(*) n FROM skill_score_history")[0]["n"], 1)

    def test_failing_quiz_gives_a_low_score_and_weak_topics(self):
        aid = self.take_quiz("quiz-python", correct=False)
        score, level, *_ = list(self.skill()[0])
        self.assertEqual((score, level), (0.0, 0))
        page = self.client.get(f"/attempts/{aid}").text
        self.assertIn("Topics to work on", page)
        self.assertIn("Not quite.", page)

    def test_partial_credit_follows_the_80_percent_mastery_rule(self):
        aid = self.start("quiz-python")
        form = self.quiz_form(aid, True)
        wrong = self.quiz_form(aid, False)
        first = sorted(form)[0]
        form[first] = wrong[first]                                    # 4 of 5 correct = 80% = full mastery of a level-3 quiz
        self.client.post(f"/attempts/{aid}/submit", form)
        self.assertEqual(self.skill()[0]["score"], 3.0)

    def test_unanswered_quiz_is_not_graded(self):
        aid = self.start("quiz-python")
        r = self.client.post(f"/attempts/{aid}/submit", {})
        self.assertEqual(self.query("SELECT status FROM attempts WHERE id = ?", aid)[0]["status"], "in_progress")
        self.assertEqual(self.query("SELECT COUNT(*) n FROM skill_scores")[0]["n"], 0)
        self.assertIn("Not graded", self.client.get(r.location).text)

    def test_self_rating_never_changes_the_verified_score(self):
        rows = self.query("SELECT cs.skill_id FROM career_skills cs JOIN users u ON u.target_career_id = cs.career_id")
        self.client.post("/assess", {f"skill_{r['skill_id']}": "5" for r in rows})
        self.assertEqual(self.query("SELECT COUNT(*) n FROM skill_scores")[0]["n"], 0)
        self.take_quiz("quiz-python", correct=False)
        self.assertEqual(self.skill()[0]["level"], 0)                  # claimed 5, proved 0

    def test_overconfidence_is_shown_next_to_the_evidence(self):
        rows = self.query("SELECT cs.skill_id FROM career_skills cs JOIN users u ON u.target_career_id = cs.career_id")
        self.client.post("/assess", {f"skill_{r['skill_id']}": "5" for r in rows})
        self.take_quiz("quiz-python")                                  # proves level 3
        profile = self.client.get("/skill-profile").text
        self.assertIn("You rated yourself 5, evidence shows 3", profile)
        self.assertIn("3.0/5", profile)

    def test_attempt_limit_and_retake_penalty(self):
        scores = []
        for _ in range(ae.MAX_ATTEMPTS):
            aid = self.take_quiz("quiz-python")
            scores.append(self.query("SELECT skill_score FROM attempts WHERE id = ?", aid)[0]["skill_score"])
        self.assertEqual(scores[:2], [3.0, 3.0])
        self.assertEqual(scores[2], 2.55)                              # 3 x 0.85
        self.assertTrue(scores[3] < scores[2] and scores[4] < scores[3])
        self.assertEqual(self.skill()[0]["score"], 3.0)                # best attempt still counts
        r = self.client.post("/assignments/quiz-python/start")
        self.assertEqual(self.query("SELECT COUNT(*) n FROM attempts WHERE status = 'in_progress'")[0]["n"], 0)
        self.assertIn("used all", self.client.get(r.location).text)

    def test_resuming_an_unfinished_attempt_keeps_the_same_questions(self):
        a = self.start("quiz-python")
        b = self.start("quiz-python")
        self.assertEqual(a, b)

    def test_double_submit_does_not_grade_twice(self):
        aid = self.take_quiz("quiz-python")
        r = self.client.post(f"/attempts/{aid}/submit", self.quiz_form(aid, False))
        self.assertEqual(r.location, f"/attempts/{aid}")
        self.assertEqual(self.query("SELECT COUNT(*) n FROM attempts WHERE status = 'graded'")[0]["n"], 1)
        self.assertEqual(self.skill()[0]["score"], 3.0)


class CodeFlowTests(AssessmentFlowCase):
    def test_correct_code_is_graded_by_running_it(self):
        ref = bank.get("python-basics").reference
        aid, r = self.submit_code("python-basics", ref)
        page = self.client.get(f"/attempts/{aid}").text
        self.assertIn("100%", page)
        self.assertEqual(self.skill()[0]["score"], 3.0)
        items = json.loads(self.query("SELECT breakdown FROM attempts WHERE id = ?", aid)[0]["breakdown"])
        self.assertEqual(len(items), 16)
        self.assertTrue(all(i["passed"] for i in items))

    def test_buggy_code_loses_points_per_hidden_test_with_topics(self):
        buggy = bank.get("python-basics").reference.replace("return cleaned == cleaned[::-1]", "return True")
        aid, _ = self.submit_code("python-basics", buggy)
        page = self.client.get(f"/attempts/{aid}").text
        self.assertIn("is_palindrome rejects non-palindromes", page)
        row = self.query("SELECT pct FROM attempts WHERE id = ?", aid)[0]
        self.assertTrue(0.5 < row["pct"] < 0.9)
        self.assertIn("strings", page)

    def test_visible_examples_show_input_expected_and_got_but_hidden_tests_do_not(self):
        buggy = bank.get("python-basics").reference.replace('c.lower() for c in s if c.isalnum()', 'c for c in s')
        aid, _ = self.submit_code("python-basics", buggy)
        page = self.client.get(f"/attempts/{aid}").text
        self.assertIn("expected:", page)                               # the visible example
        self.assertNotIn("No 'x' in Nixon", page)                      # a hidden test's input must not be revealed

    def test_syntax_error_is_rejected_and_the_draft_is_kept(self):
        aid, r = self.submit_code("python-basics", "def word_counts(:\n    pass\n")
        self.assertEqual(self.query("SELECT status FROM attempts WHERE id = ?", aid)[0]["status"], "in_progress")
        page = self.client.get(r.location).text
        self.assertIn("Syntax error", page)
        self.assertIn("def word_counts(:", page)                       # the student's work is not lost
        self.assertEqual(self.query("SELECT COUNT(*) n FROM skill_scores")[0]["n"], 0)

    def test_forbidden_code_is_rejected_without_running(self):
        marker = "/tmp/skillztrack_should_not_exist"
        code = f"import os\nos.system('touch {marker}')\n"
        aid, r = self.submit_code("python-basics", code)
        self.assertIn("not allowed", self.client.get(r.location).text)
        import os
        self.assertFalse(os.path.exists(marker))
        self.assertEqual(self.query("SELECT status FROM attempts WHERE id = ?", aid)[0]["status"], "in_progress")

    def test_infinite_loop_cannot_hang_grading_and_other_tests_still_count(self):
        ref = bank.get("python-basics").reference.replace(
            "def fizzbuzz(n):", "def fizzbuzz(n):\n    while True:\n        pass\n\ndef _unused(n):")
        aid, _ = self.submit_code("python-basics", ref)
        pct = self.query("SELECT pct FROM attempts WHERE id = ?", aid)[0]["pct"]
        self.assertTrue(0.5 < pct < 1.0)

    def test_two_assignments_are_needed_to_unlock_level_four(self):
        self.submit_code("python-orders", bank.get("python-orders").reference)
        row = self.skill()[0]
        self.assertEqual((row["score"], row["level"], row["assignments_count"]), (3.5, 3, 1))     # capped: one assignment
        self.take_quiz("quiz-python")
        row = self.skill()[0]
        self.assertEqual((row["score"], row["level"], row["assignments_count"]), (4.0, 4, 2))
        self.assertEqual(row["confidence"], "medium")
        self.submit_code("python-basics", bank.get("python-basics").reference)
        self.assertEqual(self.skill()[0]["confidence"], "high")

    def test_code_assignments_can_be_switched_off_while_quizzes_still_work(self):
        config.CODE_EXEC = False
        try:
            r = self.client.post("/assignments/python-basics/start")
            self.assertIn("switched off", self.client.get(r.location).text)
            self.assertEqual(self.query("SELECT COUNT(*) n FROM attempts")[0]["n"], 0)
            self.take_quiz("quiz-python")
            self.assertEqual(self.skill()[0]["level"], 3)
        finally:
            config.CODE_EXEC = True

    def test_other_kinds_are_graded_through_the_web_layer(self):
        sql = bank.get("sql-foundations")
        aid = self.start("sql-foundations")
        self.client.post(f"/attempts/{aid}/submit", {q["id"]: q["expected_sql"] for q in sql.spec["questions"]})
        self.assertEqual(self.query("SELECT pct FROM attempts WHERE id = ?", aid)[0]["pct"], 1.0)
        aid = self.start("git-command-lab")
        from tests.bank_answers import COMMANDS, RUBRICS
        self.client.post(f"/attempts/{aid}/submit", COMMANDS["git-command-lab"])
        self.assertEqual(self.query("SELECT pct FROM attempts WHERE id = ?", aid)[0]["pct"], 1.0)
        aid = self.start("dockerfile-review")
        self.client.post(f"/attempts/{aid}/submit", {"text": RUBRICS["dockerfile-review"]})
        self.assertEqual(self.query("SELECT pct FROM attempts WHERE id = ?", aid)[0]["pct"], 1.0)


class SecurityAndPrivacyTests(AssessmentFlowCase):
    def test_pages_require_login(self):
        anon = Client()
        for path in ("/assignments", "/assignments/quiz-python", "/attempts/1", "/skill-profile"):
            self.assertEqual(anon.get(path).location.split("?")[0], "/login", path)

    def test_students_cannot_view_or_submit_each_others_attempts(self):
        aid = self.start("quiz-python")
        other = Client()
        self.register(other, "mallory")
        self.assertEqual(other.get(f"/attempts/{aid}").status, 404)
        self.assertEqual(other.post(f"/attempts/{aid}/submit", self.quiz_form(aid)).status, 404)
        self.assertEqual(self.query("SELECT status FROM attempts WHERE id = ?", aid)[0]["status"], "in_progress")

    def test_submission_requires_a_csrf_token(self):
        aid = self.start("quiz-python")
        r = self.client.request("POST", f"/attempts/{aid}/submit", self.quiz_form(aid), send_csrf=False)
        self.assertEqual(r.status, 403)
        self.assertEqual(self.query("SELECT status FROM attempts WHERE id = ?", aid)[0]["status"], "in_progress")

    def test_unknown_assignment_and_attempt_are_404(self):
        self.assertEqual(self.client.get("/assignments/nope").status, 404)
        self.assertEqual(self.client.post("/assignments/nope/start").status, 404)
        self.assertEqual(self.client.get("/attempts/99999").status, 404)

    def test_student_input_is_escaped_when_shown_back(self):
        aid = self.start("responsive-landing-page")
        self.client.post(f"/attempts/{aid}/submit", {"text": "<script>alert('x')</script>" * 10})
        page = self.client.get(f"/attempts/{aid}").text
        self.assertNotIn("<script>alert('x')</script>", page)

    def test_each_students_scores_are_separate(self):
        self.take_quiz("quiz-python")
        other = Client()
        self.register(other, "mallory")
        other.post("/career", {"career_id": self.career_id()})
        self.assertIn("0 of 8 skills verified", other.get("/assignments").text)


class PlanIntegrationTests(AssessmentFlowCase):
    def test_gaps_and_roadmap_follow_the_evidence(self):
        self.assertEqual(self.client.get("/gaps").location, "/assignments")           # no evidence yet
        self.take_quiz("quiz-python")
        gaps = self.client.get("/gaps").text
        self.assertIn("Unverified", gaps)                                              # the other skills
        self.assertIn("Verified 3.0/5", gaps)
        r = self.client.post("/roadmap/generate", {"hours_per_week": "8"})
        self.assertEqual(r.location, "/roadmap")
        page = self.client.get("/roadmap").text
        self.assertIn("Prove it", page)
        self.assertIn("never raises your level", page)
        self.assertNotIn("Mark milestone complete", page)

    def test_weak_topics_flow_into_the_roadmap_milestone(self):
        self.client.post("/career", {"career_id": self.career_id("python-developer")})     # Python needs level 4 here
        broken = bank.get("python-orders").reference
        broken = broken.replace('"average_paid": round(total / len(paid), 2) if paid else 0.0', '"average_paid": 0.0')
        self.submit_code("python-orders", broken)
        self.client.post("/roadmap/generate", {"hours_per_week": "8"})
        m = self.query("SELECT focus_topics, reason FROM milestones m JOIN skills s ON s.id = m.skill_id WHERE s.slug = 'python'")
        self.assertEqual(len(m), 1)
        topics = json.loads(m[0]["focus_topics"])
        self.assertEqual(topics[0], "numbers")      # the topic with the failed tests, not the mostly-passing one
        self.assertNotIn("parsing", topics)
        self.assertIn("VERIFIED score", m[0]["reason"])
        self.assertIn("Weak topics", m[0]["reason"])
        self.assertIn("Focus on:", self.client.get("/roadmap").text)

    def test_passing_an_assignment_completes_the_milestone_and_updates_the_roadmap(self):
        self.take_quiz("quiz-python")
        self.client.post("/roadmap/generate", {"hours_per_week": "8"})
        git = self.query("SELECT m.id, m.status FROM milestones m JOIN skills s ON s.id = m.skill_id WHERE s.slug = 'git-github'")[0]
        self.assertEqual(git["status"], "not_started")
        self.take_quiz("quiz-git-github")                                              # proves level 3 = the target
        self.assertEqual(self.query("SELECT status FROM milestones m JOIN skills s ON s.id = m.skill_id WHERE s.slug = 'git-github' "
                                    "ORDER BY m.id DESC")[0]["status"], "completed")
        self.assertIn("Completed milestones (1)", self.client.get("/roadmap").text)
        self.assertEqual(self.query("SELECT COUNT(*) n FROM roadmaps WHERE is_active = 1")[0]["n"], 1)

    def test_dashboard_shows_verification_progress(self):
        self.take_quiz("quiz-python")
        page = self.client.get("/dashboard").text
        self.assertIn("skills verified by assignments", page)
        self.assertIn("1/8", page)

    def test_profile_page_shows_history_and_next_step(self):
        self.take_quiz("quiz-python")
        self.take_quiz("quiz-python")
        page = self.client.get("/skill-profile").text
        self.assertIn("Score history", page)
        self.assertIn("Python", page)

    def test_rebuild_recomputes_scores_from_raw_attempts(self):
        from skillztrack import assessments
        self.take_quiz("quiz-python")
        conn = db.connect()
        conn.execute("UPDATE skill_scores SET score = 0, level = 0")
        assessments.rebuild_scores(conn)
        conn.commit(); conn.close()
        self.assertEqual(self.skill()[0]["score"], 3.0)

    def test_migration_adds_the_new_column_to_an_old_database(self):
        conn = db.connect()
        conn.executescript("ALTER TABLE milestones DROP COLUMN focus_topics;")
        db.init_db(conn)
        self.assertIn("focus_topics", {r["name"] for r in conn.execute("PRAGMA table_info(milestones)")})
        conn.close()
