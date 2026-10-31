"""Tests for what SkillzTrack added: badges/XP/streaks, activity, notifications, insights, draft autosave, branding."""
import json
import re
import unittest
from datetime import date, timedelta
from pathlib import Path

from skillztrack import bank, config, events, gamification, insights
from tests.test_app import AppTestCase, Client

ROOT = Path(__file__).resolve().parent.parent


class GamificationRuleTests(unittest.TestCase):
    def test_streaks(self):
        today = date(2026, 5, 10)
        self.assertEqual(gamification.streaks(set(), today), (0, 0))
        run = {today - timedelta(days=i) for i in range(3)}
        self.assertEqual(gamification.streaks(run, today), (3, 3))
        self.assertEqual(gamification.streaks({today - timedelta(days=1)}, today), (1, 1))      # yesterday still counts
        self.assertEqual(gamification.streaks({today - timedelta(days=2)}, today), (0, 1))      # broken
        gap = {today, today - timedelta(days=1), today - timedelta(days=5), today - timedelta(days=6), today - timedelta(days=7)}
        self.assertEqual(gamification.streaks(gap, today), (2, 3))

    def test_xp_and_level_thresholds(self):
        stats = {"attempts": 2, "mastered": 1, "level_sum": 4, "milestones": 1, "study": 5}
        self.assertEqual(gamification.xp_total(stats), 20 + 40 + 100 + 30 + 15)
        self.assertEqual(gamification.level_info(0)["level"], 1)
        self.assertEqual(gamification.level_info(49)["level"], 1)
        self.assertEqual(gamification.level_info(50)["level"], 2)
        self.assertEqual(gamification.level_info(200)["level"], 3)
        info = gamification.level_info(125)
        self.assertEqual((info["floor"], info["next_at"], info["percent"]), (50, 200, 50))

    def test_badge_progress_and_codes_are_unique(self):
        self.assertEqual(len({b[0] for b in gamification.BADGES}), len(gamification.BADGES))
        out = {b["code"]: b for b in gamification.evaluate({"study": 4, "attempts": 1})}
        self.assertTrue(out["first_steps"]["earned"])
        self.assertFalse(out["scholar"]["earned"])
        self.assertEqual(out["scholar"]["percent"], 40)
        # a stored badge stays earned even when the live metric drops (e.g. the career changed)
        kept = {b["code"]: b for b in gamification.evaluate({"readiness": 10}, {"career_ready": "2026-01-01 00:00:00"})}
        self.assertTrue(kept["career_ready"]["earned"])


class InsightRuleTests(unittest.TestCase):
    def test_finish_date_and_schedule(self):
        d, weeks = insights.finish_date(40, 8, today=date(2026, 1, 1))
        self.assertEqual((weeks, d), (5, date(2026, 2, 5)))
        self.assertEqual(insights.finish_date(0, 8, today=date(2026, 1, 1))[1], 0)
        start, end = insights.schedule("2026-01-01 10:00:00", 3, 4)
        self.assertEqual((start, end), (date(2026, 1, 15), date(2026, 1, 28)))
        self.assertEqual(insights.fmt_date(date(2026, 3, 9)), "9 Mar")


class FeatureFlowTests(AppTestCase):
    def setUp(self):
        super().setUp()
        from skillztrack import assessment_views
        assessment_views._submits.clear()
        assessment_views._drafts.clear()
        self.register()
        self.client.post("/career", {"career_id": self.career_id()})

    # helpers
    def start(self, slug, client=None):
        r = (client or self.client).post(f"/assignments/{slug}/start")
        self.assertEqual(r.status, 303, r.text[:200])
        return int(r.location.rsplit("/", 1)[1])

    def quiz(self, slug, correct=True, client=None):
        client = client or self.client
        aid = self.start(slug, client)
        row = self.query("SELECT payload FROM attempts WHERE id = ?", aid)[0]
        pool = {q["id"]: q for q in bank.get(slug).spec["pool"]}
        form = {}
        for e in json.loads(row["payload"])["questions"]:
            q = pool[e["id"]]
            wrong = next(i for i in range(len(q["options"])) if i != q["answer"])
            form[f"q_{q['id']}"] = str(q["answer"] if correct else wrong)
        r = client.post(f"/attempts/{aid}/submit", form)
        self.assertEqual(r.status, 303, r.text[:300])
        return aid

    def quiz_slug(self, name="python"):
        return next(a.slug for a in bank.all_assignments() if a.kind == "quiz" and name in a.slug)

    # ---------------------------------------------------------------- events, badges, notifications
    def test_graded_attempt_logs_activity_awards_badges_and_notifies(self):
        self.quiz(self.quiz_slug())
        codes = {r["code"] for r in self.query("SELECT code FROM achievements")}
        self.assertTrue({"first_steps", "mastery", "flawless"} <= codes)
        kinds = {r["kind"] for r in self.query("SELECT kind FROM activity_log")}
        self.assertTrue({"attempt", "badge", "level"} <= kinds)
        titles = [r["title"] for r in self.query("SELECT title FROM notifications")]
        self.assertTrue(any(t.startswith("New badge") for t in titles))
        self.assertTrue(any("level" in t.lower() for t in titles))

    def test_badges_are_awarded_only_once(self):
        slug = self.quiz_slug()
        self.quiz(slug)
        badges = self.query("SELECT COUNT(*) AS n FROM achievements")[0]["n"]
        first_steps = lambda: self.query("SELECT COUNT(*) AS n FROM notifications WHERE title = 'New badge: First Steps'")[0]["n"]
        self.assertEqual(first_steps(), 1)
        self.quiz(slug)                                                  # the same evidence again must not re-award
        events.after_change(__import__("skillztrack.db", fromlist=["connect"]).connect(), 1)
        self.assertEqual(self.query("SELECT COUNT(*) AS n FROM achievements")[0]["n"], badges)
        self.assertEqual(first_steps(), 1)

    def test_comeback_badge_needs_a_failure_then_mastery(self):
        slug = self.quiz_slug("javascript")
        self.quiz(slug, correct=False)
        self.assertNotIn("comeback", {r["code"] for r in self.query("SELECT code FROM achievements")})
        self.quiz(slug, correct=True)
        self.assertIn("comeback", {r["code"] for r in self.query("SELECT code FROM achievements")})

    def test_study_tick_is_logged_once_per_material(self):
        self.quiz(self.quiz_slug())
        self.client.post("/roadmap/generate", {"hours_per_week": "8"})
        item = self.query("SELECT id FROM milestone_resources ORDER BY id LIMIT 1")[0]["id"]
        self.client.post(f"/item/{item}/toggle", {"done": "1"})
        self.client.post(f"/item/{item}/toggle", {"done": "0"})
        self.client.post(f"/item/{item}/toggle", {"done": "1"})
        self.assertEqual(self.query("SELECT COUNT(*) AS n FROM activity_log WHERE kind = 'study'")[0]["n"], 1)

    def test_roadmap_generation_is_logged_and_earns_pathfinder(self):
        self.quiz(self.quiz_slug())
        self.client.post("/roadmap/generate", {"hours_per_week": "6"})
        self.assertIn("pathfinder", {r["code"] for r in self.query("SELECT code FROM achievements")})
        self.assertEqual(self.query("SELECT COUNT(*) AS n FROM activity_log WHERE kind = 'roadmap'")[0]["n"], 1)

    # ------------------------------------------------------------------------------------- pages
    def test_new_pages_require_login(self):
        anon = Client()
        for path in ("/achievements", "/notifications", "/api/unread"):
            r = anon.get(path)
            self.assertEqual(r.status, 303, path)
            self.assertTrue(r.location.startswith("/login"), path)
        self.assertEqual(anon.post("/notifications/clear").status, 303)

    def test_achievements_page_lists_all_badges_with_progress(self):
        self.quiz(self.quiz_slug())
        r = self.client.get("/achievements")
        self.assertEqual(r.status, 200)
        for b in gamification.BADGES:
            self.assertIn(b[1], r.text)
        self.assertIn("Level 2", r.text)
        self.assertIn("XP", r.text)

    def test_notifications_unread_count_and_mark_read_on_view(self):
        self.quiz(self.quiz_slug())
        unread = json.loads(self.client.get("/api/unread").text)["unread"]
        self.assertGreater(unread, 0)
        page = self.client.get("/notifications")
        self.assertIn("New badge:", page.text)
        self.assertEqual(json.loads(self.client.get("/api/unread").text)["unread"], 0)
        self.client.post("/notifications/clear")
        self.assertEqual(self.query("SELECT COUNT(*) AS n FROM notifications")[0]["n"], 0)
        self.assertIn("all caught up", self.client.get("/notifications").text.lower())

    def test_notifications_are_private_to_their_owner(self):
        self.quiz(self.quiz_slug())
        other = Client()
        self.register(other, username="ravi")
        self.assertEqual(json.loads(other.get("/api/unread").text)["unread"], 0)
        self.assertNotIn("New badge:", other.get("/notifications").text)

    def test_dashboard_shows_real_data_not_samples(self):
        empty = self.client.get("/dashboard").text
        self.assertIn("0-day streak", empty)
        self.assertIn("Start with", empty)                                # next step for a user with no evidence
        slug = self.quiz_slug()
        self.quiz(slug)
        page = self.client.get("/dashboard").text
        self.assertIn("Scored 100%", page)                                # recent activity from the log
        self.assertIn("1-day streak", page)
        self.assertIn("Level 2", page)
        self.assertRegex(page, r"data-chart='\{[^']*&#34;|data-chart='\{")
        self.assertIn("Mastery", page)

    def test_dashboard_next_steps_rank_biggest_lever_and_resume_open_attempt(self):
        self.quiz(self.quiz_slug())
        page = self.client.get("/dashboard").text
        self.assertRegex(page, r"readiness\)")                            # "Raise X (+N% readiness)"
        self.start(self.quiz_slug("javascript"))
        self.assertIn("Continue:", self.client.get("/dashboard").text)

    def test_career_match_ranks_all_careers_by_verified_skills(self):
        self.quiz(self.quiz_slug())
        conn = __import__("skillztrack.db", fromlist=["connect"]).connect()
        try:
            user = conn.execute("SELECT id, target_career_id FROM users WHERE username = 'asha'").fetchone()
            match = insights.career_match(conn, user["id"], user["target_career_id"])
        finally:
            conn.close()
        self.assertEqual(len(match), 6)
        self.assertEqual([m["readiness"] for m in match], sorted((m["readiness"] for m in match), reverse=True))
        self.assertTrue(any(m["is_target"] for m in match))
        self.assertTrue(all(0 <= m["readiness"] <= 100 for m in match))
        self.assertIn("Career match", self.client.get("/skill-profile").text)

    def test_career_detail_shows_personal_match_when_signed_in(self):
        self.quiz(self.quiz_slug())
        self.assertIn("Your match", self.client.get("/careers/web-developer").text)
        self.assertIn("Sign up to start this path", Client().get("/careers/web-developer").text)

    def test_roadmap_milestones_have_estimated_dates(self):
        self.quiz(self.quiz_slug())
        self.client.post("/roadmap/generate", {"hours_per_week": "8"})
        self.assertRegex(self.client.get("/roadmap").text, r"\d{1,2} [A-Z][a-z]{2} &ndash; \d{1,2} [A-Z][a-z]{2}")

    # --------------------------------------------------------------------------------- autosave
    def test_draft_autosave_persists_and_is_restored(self):
        slug = next(a.slug for a in bank.all_assignments() if a.kind == "quiz")
        aid = self.start(slug)
        first = json.loads(self.query("SELECT payload FROM attempts WHERE id = ?", aid)[0]["payload"])["questions"][0]["id"]
        r = self.client.post(f"/attempts/{aid}/draft", {f"q_{first}": "2"})
        self.assertEqual(r.status, 200)
        self.assertTrue(json.loads(r.text)["saved"])
        html = self.client.get(f"/attempts/{aid}").text
        self.assertRegex(html, rf'name="q_{first}" id="q{first}-2" value="2" checked')

    def test_draft_autosave_rejects_other_users_graded_attempts_and_floods(self):
        aid = self.start(self.quiz_slug("javascript"))                   # an attempt that stays open
        other = Client()
        self.register(other, username="ravi")
        self.assertEqual(other.post(f"/attempts/{aid}/draft", {"q_x": "1"}).status, 404)
        done = self.quiz(self.quiz_slug())
        r = self.client.post(f"/attempts/{done}/draft", {"q_x": "1"})
        self.assertEqual(r.status, 409)
        statuses = [self.client.post(f"/attempts/{aid}/draft", {"q_x": "1"}).status for _ in range(45)]
        self.assertIn(429, statuses)

    def test_draft_autosave_needs_csrf(self):
        slug = next(a.slug for a in bank.all_assignments() if a.kind == "quiz")
        aid = self.start(slug)
        self.assertEqual(self.client.request("POST", f"/attempts/{aid}/draft", {"q_x": "1"}, send_csrf=False).status, 403)


class BrandingAndConfigTests(AppTestCase):
    def test_no_legacy_branding_in_source_templates_or_static_files(self):
        legacy = re.compile(r"career\s*-?_?\s*track", re.I)
        allowed = {"skillztrack/config.py", "README.md", "tests/test_skillztrack_features.py"}   # config keeps legacy env/db fallbacks
        offenders = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".db", ".png", ".pyc", ".zip"}:
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel in allowed or rel.startswith(".git/"):
                continue
            if legacy.search(path.read_text(errors="ignore")) or legacy.search(rel):
                offenders.append(rel)
        self.assertEqual(offenders, [])

    def test_every_public_page_uses_the_new_name_and_no_cdn(self):
        for path in ("/", "/login", "/register", "/careers/web-developer", "/missing-page"):
            html = self.client.get(path).text
            self.assertIn("SkillzTrack", html, path)
            self.assertNotRegex(html, r"(?i)career\s*track", path)
            self.assertNotIn("cdn.jsdelivr", html, path)
            self.assertNotIn("bootstrap", html.lower(), path)

    def test_signed_in_pages_have_no_legacy_branding_or_dead_assets(self):
        self.register()
        self.client.post("/career", {"career_id": self.career_id()})
        slug = next(a.slug for a in bank.all_assignments() if a.kind == "quiz" and "python" in a.slug)
        aid = int(self.client.post(f"/assignments/{slug}/start").location.rsplit("/", 1)[1])
        pool = {q["id"]: q for q in bank.get(slug).spec["pool"]}
        form = {f"q_{e['id']}": str(pool[e["id"]]["answer"]) for e in json.loads(self.query("SELECT payload FROM attempts WHERE id = ?", aid)[0]["payload"])["questions"]}
        self.client.post(f"/attempts/{aid}/submit", form)            # gives the user evidence, so /gaps and /roadmap pages open
        for path in ("/dashboard", "/assignments", "/skill-profile", "/gaps", "/roadmap", "/achievements", "/notifications", "/profile", "/assess"):
            r = self.client.get(path)
            self.assertEqual(r.status, 200, path)
            self.assertNotRegex(r.text, r"(?i)career\s*track", path)
            for href in set(re.findall(r'(?:href|src)="(/static/[^"#?]+)', r.text)):
                self.assertTrue((ROOT / href.lstrip("/")).is_file(), f"{path} references missing {href}")

    def test_legacy_environment_variables_and_database_still_work(self):
        import os
        os.environ["CAREERTRACK_PBKDF2_ITERATIONS"] = "1234"
        try:
            self.assertEqual(config._env("PBKDF2_ITERATIONS"), "1234")
            os.environ["SKILLZTRACK_PBKDF2_ITERATIONS"] = "99"
            self.assertEqual(config._env("PBKDF2_ITERATIONS"), "99")           # new name wins
        finally:
            os.environ.pop("CAREERTRACK_PBKDF2_ITERATIONS", None)
            os.environ.pop("SKILLZTRACK_PBKDF2_ITERATIONS", None)

    def test_default_database_prefers_an_existing_legacy_file(self):
        import tempfile
        old = config.BASE_DIR
        with tempfile.TemporaryDirectory() as d:
            config.BASE_DIR = Path(d)
            try:
                self.assertTrue(config._default_db().endswith("skillztrack.db"))          # fresh install
                (Path(d) / "careertrack.db").write_bytes(b"")
                self.assertTrue(config._default_db().endswith("careertrack.db"))          # upgrade: keep the user's data
                (Path(d) / "skillztrack.db").write_bytes(b"")
                self.assertTrue(config._default_db().endswith("skillztrack.db"))          # both exist: the new name wins
            finally:
                config.BASE_DIR = old

    def test_schema_upgrade_adds_new_tables_and_keeps_existing_rows(self):
        self.register()
        conn = __import__("skillztrack.db", fromlist=["connect"]).connect()
        try:
            for table in ("activity_log", "notifications", "achievements"):          # pretend this is a pre-rename database
                conn.execute(f"DROP TABLE {table}")
            conn.commit()
            from skillztrack import db as database
            database.init_db(conn)
            conn.commit()
            names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            self.assertTrue({"activity_log", "notifications", "achievements"} <= names)
            self.assertEqual(conn.execute("SELECT COUNT(*) AS n FROM users WHERE username = 'asha'").fetchone()["n"], 1)
        finally:
            conn.close()

    def test_security_headers_no_longer_allow_a_cdn(self):
        csp = self.client.get("/").header("Content-Security-Policy")
        self.assertIn("script-src 'self';", csp)
        self.assertNotIn("jsdelivr", csp)


if __name__ == "__main__":
    unittest.main()
