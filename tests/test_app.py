"""End-to-end tests: real requests go through the WSGI app, a real SQLite file and real templates."""
import io
import json
import os
import re
import tempfile
import unittest
from http.cookies import SimpleCookie
from urllib.parse import urlencode

from skillztrack import config

config.PBKDF2_ITERATIONS = 1000  # fast hashing for tests only

from skillztrack import db, services, web  # noqa: E402
from skillztrack.app import application  # noqa: E402,F401  (registers routes)


class Response:
    def __init__(self, status, headers, body):
        self.status, self.headers, self.text = status, headers, body.decode("utf-8", "replace")

    def header(self, name):
        return next((v for k, v in self.headers if k.lower() == name.lower()), None)

    @property
    def location(self):
        return self.header("Location")


class Client:
    def __init__(self):
        self.cookies = {}

    def request(self, method, path, data=None, headers=None, send_csrf=True):
        path, _, query = path.partition("?")
        if method == "POST" and send_csrf and "pp_csrf" in self.cookies:
            data = {"csrf_token": self.cookies["pp_csrf"], **(data or {})}
        body = urlencode(data or {}).encode()
        environ = {
            "REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query, "REMOTE_ADDR": "127.0.0.1",
            "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body),
            "HTTP_COOKIE": "; ".join(f"{k}={v}" for k, v in self.cookies.items()),
        }
        environ.update(headers or {})
        captured = {}
        chunks = application(environ, lambda s, h: captured.update(status=s, headers=h))
        for k, v in captured["headers"]:
            if k == "Set-Cookie":
                cookie = SimpleCookie(v)
                for name, morsel in cookie.items():
                    if morsel.value == "" or morsel["max-age"] == "0":
                        self.cookies.pop(name, None)
                    else:
                        self.cookies[name] = morsel.value
        return Response(int(captured["status"].split()[0]), captured["headers"], b"".join(chunks))

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, data=None, **kw):
        if "pp_csrf" not in self.cookies:
            self.get("/login")  # visiting any page hands out a CSRF cookie
        return self.request("POST", path, data, **kw)


class AppTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self._old = config.DB_PATH
        config.DB_PATH = self.path
        web.bootstrap()
        web._attempts.clear()
        self.client = Client()

    def tearDown(self):
        config.DB_PATH = self._old
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.path + suffix)
            except FileNotFoundError:
                pass

    # helpers
    def query(self, sql, *args):
        conn = db.connect()
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def register(self, client=None, username="asha", email=None, name="Asha Rao"):
        client = client or self.client
        r = client.post("/register", {"username": username, "full_name": name, "email": email or f"{username}@example.com",
                                      "password": "s3cret-pass", "password2": "s3cret-pass"})
        self.assertEqual(r.status, 303, r.text[:300])
        return r

    def career_id(self, slug="web-developer"):
        return self.query("SELECT id FROM careers WHERE slug = ?", slug)[0]["id"]

    def rate_all(self, client, level_for):
        """level_for(skill name, required level) -> level"""
        rows = self.query("SELECT cs.skill_id, cs.required_level, s.name FROM career_skills cs JOIN skills s ON s.id = cs.skill_id "
                          "JOIN users u ON u.target_career_id = cs.career_id WHERE u.username = 'asha'")
        data = {f"skill_{r['skill_id']}": level_for(r["name"], r["required_level"]) for r in rows}
        return client.post("/assess", data)

    def verify_all(self, level_for, username="asha"):
        """TEST FIXTURE: store verified skill scores as if graded assignments had produced them.
        (The real grading pipeline is exercised end-to-end in tests/test_assessment_app.py.)"""
        rows = self.query("SELECT cs.skill_id, cs.required_level, s.name FROM career_skills cs JOIN skills s ON s.id = cs.skill_id "
                          "JOIN users u ON u.target_career_id = cs.career_id WHERE u.username = ?", username)
        uid = self.query("SELECT id FROM users WHERE username = ?", username)[0]["id"]
        conn = db.connect()
        for r in rows:
            level = level_for(r["name"], r["required_level"])
            conn.execute("INSERT INTO skill_scores (user_id, skill_id, score, level, confidence, assignments_count) VALUES (?,?,?,?,?,2) "
                         "ON CONFLICT(user_id, skill_id) DO UPDATE SET score=excluded.score, level=excluded.level",
                         (uid, r["skill_id"], float(level), level, "medium"))
        conn.commit(); conn.close()

    def make_roadmap(self, hours=8):
        self.register()
        self.client.post("/career", {"career_id": self.career_id()})
        self.verify_all(lambda n, req: req if n in ("HTML & CSS", "Git & GitHub") else 1)
        return self.client.post("/roadmap/generate", {"hours_per_week": hours})

    def make_admin(self, username="boss"):
        c = Client()
        self.register(c, username, name="Big Boss")
        conn = db.connect(); conn.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (username,)); conn.commit(); conn.close()
        return c


class PublicPageTests(AppTestCase):
    def test_landing_page_lists_careers_from_database(self):
        r = self.client.get("/")
        self.assertEqual(r.status, 200)
        for title in ("Web Developer", "Python Developer", "Cloud Engineer", "Data Analyst"):
            self.assertIn(title, r.text)
        self.assertIn("Rule-based", r.text)

    def test_career_detail_and_static(self):
        self.assertIn("HTML &amp; CSS", self.client.get("/careers/web-developer").text)
        self.assertEqual(self.client.get("/careers/nope").status, 404)
        self.assertEqual(self.client.get("/static/css/skillztrack.css").status, 200)

    def test_projects_and_resources_pages_are_removed(self):
        for path in ("/projects", "/resources"):
            self.assertEqual(self.client.get(path).status, 404, path)
        self.assertNotIn('href="/resources"', self.client.get("/").text)

    def test_static_path_traversal_blocked(self):
        self.assertEqual(self.client.get("/static/../skillztrack/config.py").status, 404)
        self.assertEqual(self.client.get("/static/%2e%2e/run.py").status, 404)

    def test_unknown_url_404_and_wrong_method_405(self):
        self.assertEqual(self.client.get("/nothing-here").status, 404)
        self.assertEqual(self.client.get("/logout").status, 405)

    def test_security_headers(self):
        r = self.client.get("/")
        self.assertEqual(r.header("X-Frame-Options"), "DENY")
        self.assertIn("default-src 'self'", r.header("Content-Security-Policy"))
        self.assertEqual(r.header("X-Content-Type-Options"), "nosniff")


class AuthTests(AppTestCase):
    def test_register_logs_in_and_stores_hashed_password(self):
        r = self.register()
        self.assertEqual(r.location, "/dashboard")
        row = self.query("SELECT password_hash FROM users WHERE username = 'asha'")[0]
        self.assertTrue(row["password_hash"].startswith("pbkdf2_sha256$"))
        self.assertNotIn("s3cret-pass", row["password_hash"])
        self.assertEqual(self.client.get("/dashboard").status, 200)

    def test_register_validation_errors(self):
        r = self.client.post("/register", {"username": "a", "full_name": "", "email": "bad", "password": "123", "password2": "x"})
        self.assertEqual(r.status, 400)
        for msg in ("3-30 letters", "enter your name", "valid email", "at least 8"):
            self.assertIn(msg, r.text)
        self.assertEqual(self.query("SELECT COUNT(*) n FROM users")[0]["n"], 0)

    def test_duplicate_username_and_email_rejected(self):
        self.register()
        other = Client()
        r = other.post("/register", {"username": "ASHA", "full_name": "X", "email": "ASHA@example.com",
                                     "password": "s3cret-pass", "password2": "s3cret-pass"})
        self.assertEqual(r.status, 400)
        self.assertIn("already taken", r.text)
        self.assertIn("already exists", r.text)

    def test_password_mismatch(self):
        r = self.client.post("/register", {"username": "bob", "full_name": "Bob", "email": "b@x.io", "password": "abcdefgh1", "password2": "different1"})
        self.assertIn("do not match", r.text)

    def test_login_logout_cycle(self):
        self.register()
        self.client.post("/logout")
        self.assertEqual(self.client.get("/dashboard").status, 303)
        r = self.client.post("/login", {"identifier": "asha@example.com", "password": "s3cret-pass"})
        self.assertEqual(r.location, "/dashboard")
        self.client.post("/logout")
        self.assertNotIn("pp_session", self.client.cookies)

    def test_wrong_password_and_unknown_user_same_message(self):
        self.register(); self.client.post("/logout")
        a = self.client.post("/login", {"identifier": "asha", "password": "wrong-pass"})
        b = self.client.post("/login", {"identifier": "ghost", "password": "wrong-pass"})
        self.assertEqual((a.status, b.status), (400, 400))
        self.assertIn("Incorrect username/email or password", a.text)
        self.assertIn("Incorrect username/email or password", b.text)

    def test_login_rate_limit(self):
        for _ in range(web.MAX_ATTEMPTS):
            self.client.post("/login", {"identifier": "victim", "password": "nope-nope"})
        self.assertEqual(self.client.post("/login", {"identifier": "victim", "password": "nope-nope"}).status, 429)

    def test_login_next_is_restricted_to_local_paths(self):
        self.register(); self.client.post("/logout")
        r = self.client.post("/login", {"identifier": "asha", "password": "s3cret-pass", "next": "https://evil.example"})
        self.assertEqual(r.location, "/dashboard")
        self.client.post("/logout")
        r = self.client.post("/login", {"identifier": "asha", "password": "s3cret-pass", "next": "//evil.example"})
        self.assertEqual(r.location, "/dashboard")
        self.client.post("/logout")
        r = self.client.post("/login", {"identifier": "asha", "password": "s3cret-pass", "next": "/roadmap"})
        self.assertEqual(r.location, "/roadmap")

    def test_protected_pages_redirect_anonymous_users(self):
        for path in ("/dashboard", "/assess", "/gaps", "/roadmap", "/profile", "/admin"):
            r = self.client.get(path)
            self.assertEqual(r.status, 303, path)
            self.assertTrue(r.location.startswith("/login"), path)

    def test_csrf_blocks_posts_without_valid_token(self):
        self.register()
        r = self.client.request("POST", "/career", {"career_id": 1}, send_csrf=False)
        self.assertEqual(r.status, 403)
        r = self.client.request("POST", "/career", {"career_id": 1, "csrf_token": "forged"}, send_csrf=False)
        self.assertEqual(r.status, 403)

    def test_html_is_escaped(self):
        self.client.post("/register", {"username": "xss", "full_name": "<script>alert(1)</script>", "email": "x@x.io",
                                       "password": "s3cret-pass", "password2": "s3cret-pass"})
        page = self.client.get("/dashboard").text
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)


class PlannerFlowTests(AppTestCase):
    def test_empty_dashboard_prompts_for_career(self):
        self.register()
        self.assertIn("choose your target career", self.client.get("/dashboard").text.lower())
        self.assertEqual(self.client.get("/assess").location, "/dashboard")

    def test_full_journey(self):
        r = self.make_roadmap()
        self.assertEqual(r.location, "/roadmap")
        page = self.client.get("/roadmap").text
        self.assertIn("Why this milestone?", page)
        self.assertIn("JavaScript: reach Advanced", page)
        self.assertNotIn("HTML &amp; CSS: reach", page)  # mastered skills get no milestone
        gaps = self.client.get("/gaps").text
        self.assertIn("Mastered skills", gaps)
        self.assertIn("Skills to improve", gaps)
        self.assertIn("data-chart=", gaps)
        self.assertIn("Roadmap progress", self.client.get("/dashboard").text)

    def test_missing_skills_group_for_zero_scores(self):
        self.register(); self.client.post("/career", {"career_id": self.career_id()})
        self.verify_all(lambda n, req: 0)
        gaps = self.client.get("/gaps")
        self.assertEqual(gaps.status, 200)
        self.assertIn("Missing skills", gaps.text)
        self.assertEqual(len(services.classify_for_display(
            services.analyze(db.connect(), self.query("SELECT id FROM users")[0]["id"], self.career_id()))["missing"]), 8)

    def test_assessment_requires_every_rating(self):
        self.register(); self.client.post("/career", {"career_id": self.career_id()})
        r = self.client.post("/assess", {})
        self.assertEqual(r.status, 400)
        self.assertIn("Please rate every skill", r.text)
        r = self.client.post("/assess", {"skill_1": "9"})
        self.assertEqual(r.status, 400)

    def test_gaps_requires_assessment_first(self):
        self.register(); self.client.post("/career", {"career_id": self.career_id()})
        self.assertEqual(self.client.get("/gaps").location, "/assignments")
        # self-ratings alone are NOT evidence: rating everything 5 must not unlock gaps or a roadmap
        self.rate_all(self.client, lambda n, req: 5)
        self.assertEqual(self.client.get("/gaps").location, "/assignments")
        self.assertEqual(self.client.post("/roadmap/generate", {"hours_per_week": "8"}).location, "/assignments")
        self.assertEqual(self.query("SELECT COUNT(*) n FROM roadmaps")[0]["n"], 0)

    def test_generate_validates_hours(self):
        self.register(); self.client.post("/career", {"career_id": self.career_id()})
        self.verify_all(lambda n, req: 1)
        self.client.post("/roadmap/generate", {"hours_per_week": "1"})
        self.assertEqual(self.query("SELECT COUNT(*) n FROM roadmaps")[0]["n"], 0)
        self.client.post("/roadmap/generate", {"hours_per_week": "abc"})
        self.assertEqual(self.query("SELECT COUNT(*) n FROM roadmaps")[0]["n"], 0)

    def test_no_roadmap_when_requirements_met(self):
        self.register(); self.client.post("/career", {"career_id": self.career_id()})
        self.verify_all(lambda n, req: req)
        r = self.client.post("/roadmap/generate", {"hours_per_week": "8"})
        self.assertEqual(r.location, "/gaps")
        self.assertEqual(self.query("SELECT COUNT(*) n FROM roadmaps")[0]["n"], 0)
        self.assertIn("meet every requirement", self.client.get("/gaps").text)

    def test_ajax_item_toggle_updates_progress(self):
        self.make_roadmap()
        item = self.query("SELECT mr.id, mr.milestone_id FROM milestone_resources mr ORDER BY mr.id")[0]
        r = self.client.post(f"/item/{item['id']}/toggle", {"done": "1"}, headers={"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"})
        data = json.loads(r.text)
        self.assertTrue(data["completed_now"])
        self.assertEqual(data["status"], "in_progress")
        self.assertGreater(data["resource_percent"], 0)
        r = self.client.post(f"/item/{item['id']}/toggle", {"done": "0"}, headers={"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"})
        self.assertFalse(json.loads(r.text)["completed_now"])

    def test_milestone_cannot_be_self_completed_without_evidence(self):
        self.make_roadmap()
        m = self.query("SELECT id, skill_id, target_level FROM milestones ORDER BY sequence")[0]
        r = self.client.post(f"/milestone/{m['id']}/status", {"action": "complete"})
        self.assertEqual(r.status, 303)
        self.assertEqual(self.query("SELECT status FROM milestones WHERE id = ?", m["id"])[0]["status"], "not_started")
        self.assertEqual(self.query("SELECT COUNT(*) n FROM assessments")[0]["n"], 0)       # no rating was written
        self.assertEqual(self.query("SELECT level FROM skill_scores WHERE skill_id = ?", m["skill_id"])[0]["level"], 1)  # level unchanged
        # ticking every resource shows study progress but still does not complete or level up
        for item in self.query("SELECT id FROM milestone_resources WHERE milestone_id = ?", m["id"]):
            self.client.post(f"/item/{item['id']}/toggle", {"done": "1"})
        self.assertNotEqual(self.query("SELECT status FROM milestones WHERE id = ?", m["id"])[0]["status"], "completed")

    def test_milestone_completes_once_verified_level_reaches_target(self):
        self.make_roadmap()
        m = self.query("SELECT id, skill_id, target_level FROM milestones ORDER BY sequence")[0]
        conn = db.connect()
        conn.execute("UPDATE skill_scores SET level = ?, score = ? WHERE skill_id = ?", (m["target_level"], float(m["target_level"]), m["skill_id"]))
        conn.commit(); conn.close()
        self.client.post(f"/milestone/{m['id']}/status", {"action": "complete"})
        self.assertIn("Completed milestones (1)", self.client.get("/roadmap").text)
        self.client.post(f"/milestone/{m['id']}/status", {"action": "reopen"})
        self.assertEqual(self.query("SELECT status FROM milestones WHERE id = ?", m["id"])[0]["status"], "in_progress")

    def test_new_evidence_recalculates_but_keeps_completed_work(self):
        self.make_roadmap()
        first = self.query("SELECT id, skill_id, target_level FROM milestones ORDER BY sequence")[0]
        uid = self.query("SELECT id FROM users")[0]["id"]
        conn = db.connect()
        conn.execute("UPDATE skill_scores SET level = ?, score = ? WHERE skill_id = ?", (first["target_level"], float(first["target_level"]), first["skill_id"]))
        conn.commit()
        services.refresh_after_assessment(conn, uid, first["skill_id"])   # what grading calls
        conn.commit(); conn.close()
        self.assertEqual(self.query("SELECT status FROM milestones WHERE skill_id = ? ORDER BY id DESC", first["skill_id"])[0]["status"], "completed")
        before = self.query("SELECT COUNT(*) n FROM milestones m JOIN roadmaps r ON r.id = m.roadmap_id WHERE r.is_active = 1 AND m.status != 'completed'")[0]["n"]
        self.verify_all(lambda n, req: req)           # evidence now covers everything
        conn = db.connect(); services.refresh_after_assessment(conn, uid, first["skill_id"]); conn.commit(); conn.close()
        self.assertEqual(self.query("SELECT COUNT(*) n FROM roadmaps WHERE is_active = 1")[0]["n"], 1)
        active = self.query("SELECT m.status FROM milestones m JOIN roadmaps r ON r.id = m.roadmap_id WHERE r.is_active = 1")
        self.assertTrue(before > 0 and all(row["status"] == "completed" for row in active))

    def test_changing_career_retires_roadmap(self):
        self.make_roadmap()
        self.client.post("/career", {"career_id": self.career_id("cloud-engineer")})
        self.assertEqual(self.query("SELECT COUNT(*) n FROM roadmaps WHERE is_active = 1")[0]["n"], 0)
        self.assertIn("No roadmap yet", self.client.get("/roadmap").text)

    def test_users_cannot_touch_each_others_data(self):
        self.make_roadmap()
        item = self.query("SELECT id FROM milestone_resources")[0]["id"]
        milestone = self.query("SELECT id FROM milestones")[0]["id"]
        other = Client(); self.register(other, "mallory")
        self.assertEqual(other.post(f"/item/{item}/toggle", {"done": "1"}).status, 404)
        self.assertEqual(other.post(f"/milestone/{milestone}/status", {"action": "complete"}).status, 404)
        self.assertEqual(self.query("SELECT done FROM milestone_resources WHERE id = ?", item)[0]["done"], 0)

    def test_dashboard_progress_counts_only_milestones(self):
        self.make_roadmap()
        page = self.client.get("/dashboard").text
        self.assertIn("0/", page)
        self.assertNotIn("projects", page.lower().split("<main")[1])

    def test_profile_update_and_password_change(self):
        self.register()
        r = self.client.post("/profile", {"full_name": "Asha R", "email": "new@example.com", "hours_per_week": "12", "target_career_id": self.career_id("data-analyst")})
        self.assertEqual(r.location, "/assignments")
        row = self.query("SELECT full_name, email, hours_per_week, target_career_id FROM users")[0]
        self.assertEqual((row["full_name"], row["hours_per_week"], row["target_career_id"]), ("Asha R", 12, self.career_id("data-analyst")))
        bad = self.client.post("/profile", {"full_name": "", "email": "nope", "hours_per_week": "99", "target_career_id": "0"})
        self.assertEqual(bad.status, 400)
        self.client.post("/profile/password", {"current_password": "s3cret-pass", "new_password": "brand-new-pass", "new_password2": "brand-new-pass"})
        self.client.post("/logout")
        self.assertEqual(self.client.post("/login", {"identifier": "asha", "password": "brand-new-pass"}).location, "/dashboard")


class RenderedHtmlTests(AppTestCase):
    """Every page must produce well-formed HTML (balanced tags) after real data is rendered into it."""

    VOID = {"meta", "link", "input", "br", "hr", "img"}

    def check_balanced(self, path, html):
        from html.parser import HTMLParser
        problems, stack = [], []

        class P(HTMLParser):
            def handle_starttag(s, tag, attrs):
                if tag not in RenderedHtmlTests.VOID:
                    stack.append(tag)

            def handle_endtag(s, tag):
                if tag in RenderedHtmlTests.VOID:
                    return
                if not stack or stack[-1] != tag:
                    problems.append(f"unexpected </{tag}> (open: {stack[-3:]})")
                else:
                    stack.pop()
        P().feed(html)
        self.assertEqual(problems + [f"unclosed {stack}"] * bool(stack), [], path)

    def test_all_pages_are_well_formed(self):
        self.make_roadmap()
        self.client.post("/milestone/1/status", {"action": "complete"})
        paths = ["/", "/careers/web-developer", "/dashboard", "/assess", "/gaps", "/roadmap",
                 "/profile", "/assignments", "/skill-profile", "/assignments/quiz-python", "/assignments/python-basics"]
        for path in paths:
            r = self.client.get(path)
            self.assertEqual(r.status, 200, path)
            self.check_balanced(path, r.text)
        admin = self.make_admin()
        for path in ("/admin", "/admin/users", "/admin/skills", "/admin/resources/new", "/admin/resources/1/edit"):
            r = admin.get(path)
            self.assertEqual(r.status, 200, path)
            self.check_balanced(path, r.text)
        for path in ("/login", "/register", "/nothing"):
            self.check_balanced(path, Client().get(path).text)


class AdminTests(AppTestCase):
    def test_students_cannot_open_admin(self):
        self.register()
        self.assertEqual(self.client.get("/admin").status, 403)
        self.assertEqual(self.client.get("/admin/skills").status, 403)
        self.assertEqual(self.client.post("/admin/skills/new", {"name": "x"}).status, 403)

    def test_admin_pages_render(self):
        admin = self.make_admin()
        for path in ("/admin", "/admin/users", "/admin/careers", "/admin/skills", "/admin/career_skills", "/admin/resources",
                     "/admin/skills/new", "/admin/resources/new", "/admin/career_skills/new"):
            self.assertEqual(admin.get(path).status, 200, path)
        self.assertEqual(admin.get("/admin/hackers").status, 404)
        self.assertEqual(admin.get("/admin/skills/99999/edit").status, 404)

    def test_admin_crud_on_resources_with_validation(self):
        admin = self.make_admin()
        skill = self.query("SELECT id FROM skills WHERE slug = 'python'")[0]["id"]
        good = {"skill_id": skill, "title": "Learn Python the Hard Way", "provider": "Zed", "url": "https://learnpythonthehardway.org/",
                "rtype": "book", "difficulty": "beginner", "hours": 20, "is_free": "1"}
        self.assertEqual(admin.post("/admin/resources/new", good).status, 303)
        rid = self.query("SELECT id FROM resources WHERE title = 'Learn Python the Hard Way'")[0]["id"]
        bad = admin.post("/admin/resources/new", {**good, "url": "javascript:alert(1)", "hours": 9999, "difficulty": "godlike"})
        self.assertEqual(bad.status, 400)
        self.assertIn("http://", bad.text); self.assertIn("1 to 500", bad.text); self.assertIn("Choose one of the options", bad.text)
        self.assertEqual(admin.post("/admin/resources/new", good).status, 400)  # duplicate (skill, url)
        self.assertEqual(admin.post(f"/admin/resources/{rid}/edit", {**good, "title": "Renamed"}).status, 303)
        self.assertEqual(self.query("SELECT title FROM resources WHERE id = ?", rid)[0]["title"], "Renamed")
        self.assertEqual(admin.post(f"/admin/resources/{rid}/delete").status, 303)
        self.assertEqual(self.query("SELECT COUNT(*) n FROM resources WHERE id = ?", rid)[0]["n"], 0)

    def test_admin_can_add_career_requirements(self):
        admin = self.make_admin()
        r = admin.post("/admin/careers/new", {"title": "QA Engineer", "slug": "qa-engineer", "tagline": "Break things", "description": "", "icon": "bi-bug"})
        self.assertEqual(r.status, 303)
        cid = self.career_id("qa-engineer")
        skill = self.query("SELECT id FROM skills WHERE slug = 'testing'")[0]["id"]
        self.assertEqual(admin.post("/admin/career_skills/new", {"career_id": cid, "skill_id": skill, "required_level": 4, "importance": 3, "sequence": 1}).status, 303)
        self.assertEqual(admin.post("/admin/career_skills/new", {"career_id": cid, "skill_id": skill, "required_level": 4, "importance": 3, "sequence": 1}).status, 400)
        self.assertEqual(admin.get("/admin/projects").status, 404)  # project ideas section removed
        self.assertEqual(admin.post("/admin/careers/new", {"title": "Bad Slug", "slug": "Bad Slug!", "icon": "x"}).status, 400)
        self.assertIn("QA Engineer", self.client.get("/").text)  # new career shows on the landing page immediately

    def test_user_management_rules(self):
        admin = self.make_admin("boss")
        self.register(Client(), "student1")
        sid = self.query("SELECT id FROM users WHERE username = 'student1'")[0]["id"]
        bid = self.query("SELECT id FROM users WHERE username = 'boss'")[0]["id"]
        self.assertEqual(admin.post(f"/admin/users/{sid}/toggle-admin").status, 303)
        self.assertEqual(self.query("SELECT is_admin FROM users WHERE id = ?", sid)[0]["is_admin"], 1)
        admin.post(f"/admin/users/{bid}/delete")  # cannot delete yourself
        self.assertEqual(self.query("SELECT COUNT(*) n FROM users WHERE id = ?", bid)[0]["n"], 1)
        admin.post(f"/admin/users/{sid}/delete")
        self.assertEqual(self.query("SELECT COUNT(*) n FROM users WHERE id = ?", sid)[0]["n"], 0)


class SecurityUnitTests(unittest.TestCase):
    def test_password_hash_roundtrip(self):
        from skillztrack import security
        stored = security.hash_password("hello-world", iterations=1000)
        self.assertTrue(security.verify_password("hello-world", stored))
        self.assertFalse(security.verify_password("Hello-world", stored))
        self.assertFalse(security.verify_password("x", "garbage"))
        self.assertNotEqual(stored, security.hash_password("hello-world", iterations=1000))  # random salt

    def test_safe_next(self):
        self.assertEqual(web.safe_next("/roadmap"), "/roadmap")
        for bad in ("http://x.io", "//x.io", "javascript:1", "/\\evil", "", None):
            self.assertEqual(web.safe_next(bad, "/dashboard"), "/dashboard")


if __name__ == "__main__":
    unittest.main()
