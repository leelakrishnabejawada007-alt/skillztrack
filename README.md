# SkillzTrack - Skill Gap & Career Roadmap

**Prove your skills. Close your gaps. Land your career.**

SkillzTrack is a full-stack career and skill-development platform built **without a web framework**: Python's standard library does the
backend (WSGI app, `sqlite3`, `hashlib`), Jinja2 renders the HTML, and a small hand-written design system (CSS, SVG icons and charts,
plain JavaScript) makes the front end. **There are no CDN dependencies for scripts, styles or icons**, so it also works on an offline
college network (only the optional Google Fonts need internet; the page falls back to system fonts without them).

Students pick a target career, prove their level with graded assignments, see their skill gaps, and get a personalised **rule-based**
roadmap (weekly milestones with study materials) to track. There is no AI: every recommendation comes from rules you can read in
`skillztrack/engine.py` and `skillztrack/insights.py`.

## Features
**Core:** register / log in / log out - career picker - evidence-based skill assessment (quizzes, sandboxed code, SQL, rubric projects) -
skill-gap analysis - generated roadmap with weekly milestones, dates and "why this milestone?" - study tracking - profile - admin panel.

**Added in SkillzTrack (all computed from real stored data):**
- **Premium dashboard**: time-aware greeting, readiness ring, progress tiles, interactive skill radar, per-skill level indicators,
  upcoming milestones with estimated dates, recent activity feed, badges and next-step recommendations.
- **Personalised career insights**: which single skill would raise your readiness the most (and by how many points), how your *verified*
  skills fit every other career ("career match"), and an estimated finish date from your weekly study hours.
- **What-if simulator** on the gap page: drag skills to the level you plan to reach and watch your projected readiness change.
- **Badges, XP, learner level and streaks**: 18 badges awarded only from stored evidence (mastery, comebacks, verified skills,
  milestones, study streaks, readiness). XP is recomputed from your results every time, so it cannot drift.
- **Activity feed and notifications**: every attempt, level-up, milestone, roadmap and badge is logged; a bell shows unread items and
  updates itself every minute.
- **Draft autosave** while taking an assignment (saved on the server every few seconds), a timer, and answered-questions progress.
- **Search and filters**: assessments (text, status, type), roadmap (status), admin tables.
- **Design system**: light and dark theme (remembers your choice), responsive app shell with a mobile drawer, toasts, confirm dialogs,
  loading states on every submit, inline form validation with a password-strength meter, designed empty states, keyboard and screen-reader
  support (skip link, labelled controls, live regions, reduced-motion support).

## Folder structure
```
skillztrack/
|-- run.py                  Dev server + commands (initdb, reseed, createadmin)
|-- wsgi.py                 Entry point for gunicorn (production)
|-- requirements.txt        Jinja2, gunicorn
|-- Procfile, render.yaml   Deployment config
|-- skillztrack/            The Python package (all backend code)
|   |-- config.py           Settings from environment variables
|   |-- db.py               SQLite schema (CREATE TABLE ...) + seeding
|   |-- seed_content.py     Careers, skills, requirements, resources, projects (edit me!)
|   |-- levels.py           The 0-5 scale labels
|   |-- engine.py           PURE rule engine: gaps, priority, milestones, resource choice
|   |-- services.py         Database logic that uses the engine
|   |-- assessments.py, assessment_engine.py, assessment_views.py, graders.py, sandbox.py, bank/   Graded assignments
|   |-- gamification.py     PURE badge / XP / level / streak rules + stats from the database
|   |-- insights.py         Rule-based insights: biggest levers, career match, next steps, dates
|   |-- events.py           Activity log, notifications, badge awarding (called after each action)
|   |-- security.py         Password hashing, session & CSRF tokens
|   |-- web.py              Mini web layer: routing, sessions, CSRF, headers, errors
|   |-- views.py            Student pages        admin_views.py  Admin panel
|   `-- app.py              Registers routes, exposes `application`
|-- templates/              Jinja2 HTML (base.html + one file per page; admin/, auth/)
|-- static/css, static/js   skillztrack.css (design system), main.js (interactions + SVG charts), boot.js (theme)
`-- tests/                  engine, app, assessment, bank, beginner-track and SkillzTrack feature tests
```

## Run it on Windows (VS Code terminal / PowerShell)
```powershell
cd path\to\skillztrack
py -m venv venv
.\venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python run.py createadmin            # optional: make your admin account
python run.py                        # open http://127.0.0.1:8000
```
The database file `skillztrack.db` and the starter catalogue are created automatically on first start.

## Skill assessments: evidence, not self-rating

Your level in a skill is **proven by graded assignments**. Self-ratings (the old `/assess` page) are still stored, but only to
show whether your confidence matches your results and to choose a first assignment; they never change gaps or roadmaps.

| Kind | How it is graded | Can prove up to |
|---|---|---|
| Quiz (24, one per skill) | 5 of 6 questions drawn, options shuffled per attempt, answer key stays on the server | level 3 |
| Coding challenge / debugging task | Your functions run against hidden test cases in a sandbox (per-test results, topics, timeouts) | level 5 |
| Testing challenge | You write tests; they must pass the correct code and **catch 7 hidden bugs** (mutation testing) | level 4 |
| SQL lab | Your queries run on a real SQLite database; results are compared with the reference query | level 5 |
| Command / formula lab | Git, Linux, Docker, Django, Excel, security-tool answers checked against accepted forms and unsafe alternatives | level 4 |
| Mini-project (HTML/CSS page, JavaScript, Dockerfile, IAM policy, bug report) | Parsed and checked against a rubric (static analysis: it is not rendered or run) | level 4 (3 for writing) |

**Scoring rules** (`skillztrack/assessment_engine.py`, fully unit-tested):
1. attempt score = ceiling x min(1, points% / 80%) x retake factor (attempts 1-2 count fully, each later one is 15% less; max 5 attempts);
2. a skill's score is its best assignment result; **one assignment can prove at most 3.5**, so levels 4-5 need two different assignments;
3. level = floor(score); confidence is low / medium / high (high needs 3 assignments including auto-tested code and no contradictions);
4. skills with no graded assignment count as level 0 (unverified).

Every attempt is stored in `attempts` (per-test breakdown with topic and feedback), the profile in `skill_scores`, and every change in
`skill_score_history`. Weak **topics** from your latest attempts flow into the roadmap ("Focus on: ..."). A milestone completes
automatically when your verified level reaches its target; ticking resources shows study progress but never raises a level.

**The bank** lives in `skillztrack/bank/` (plain Python data). `tests/test_bank.py` proves every task is fair: each reference solution must
score 100%, each untouched starter must not, and wrong or dangerous answers must lose points. Run `python run.py rescore` after
changing the bank or the rules.

### Code execution and safety (read before deploying publicly)
Submitted Python runs in a separate process with an AST allow-list (no `os`, `open`, `eval`, dunder or frame access), restricted builtins,
CPU/memory/file-size limits (Linux/macOS), per-test and overall time-outs, an empty environment, a temp directory, and **no expected answers
inside the process**. That is solid for coursework or a small community, but it is **not** container-grade isolation. On a public site either
run grading in an isolated container with no network or secrets, or set `SKILLZTRACK_CODE_EXEC=0` (the default in `render.yaml`): coding tasks
are then marked unavailable and everything else keeps working. On Windows the OS resource limits do not exist (time-outs and the screen still apply).
Honest limits: there is no proctoring, so a student can copy a solution from elsewhere; hidden tests, retake penalties, attempt caps and
corroboration across assignments reduce, but do not remove, that. Rubric-checked projects are static analysis and cannot judge visual quality.

## Run the tests
```powershell
python -m unittest discover -s tests -t . -v
```

## How the rules work (engine.py)
1. gap = max(0, required - your level)       2. priority = gap x importance (1-3)
3. mastered = gap 0, missing = verified level 0 (or unverified), to improve = verified level 1+ but below target
4. readiness % = sum(min(you, required) x importance) / sum(required x importance)
5. one milestone per skill with a gap, in the career's learning order (prerequisites first)
6. effort = gap x 12 hours; weeks come from your study hours per week
7. the 3 highest-priority gaps are flagged "Top priority"
8. resources: levels climbed map to difficulty bands; pick best (free, shorter) per band, up to 4
Every graded attempt recalculates the roadmap and keeps ticked resources and completed milestones. A milestone completes automatically
when your *verified* level reaches its target; ticking study materials never raises a level.

## Insights, badges and XP (new)
- **Biggest lever** = gap x importance / sum(required x importance) x 100: the readiness points you would gain by closing that one gap.
- **Career match** = the readiness formula applied to your verified levels for every career.
- **XP** = 10 per graded attempt + 40 per assignment mastered (80%+) + 25 per verified skill level + 30 per milestone + 3 per study material.
  Learner level n needs 50 x (n-1)^2 XP.
- **Streak** = consecutive days (UTC) with a graded attempt, a study tick or a completed milestone; it survives until the end of the next day.
- Badges are stored the first time the evidence supports them and are never taken away. Users with existing data get their badges
  back-filled the next time they open the dashboard.
- Not implemented on purpose: the original author removed the standalone Projects and Resource Library pages (a test documents this);
  SkillzTrack keeps them removed. Study materials appear inside each roadmap milestone.

## Security measures
PBKDF2-SHA256 password hashing (600k iterations, per-user salt) - server-side sessions (only a hash of
the token is stored) - HttpOnly + SameSite=Lax cookies (+ Secure in production) - CSRF token on every POST -
Jinja2 auto-escaping (XSS) - parameterised SQL only (SQL injection) - open-redirect protection on `next` -
login rate limiting - role checks on every admin route, ownership checks on every student record -
security headers incl. Content-Security-Policy - request size limit.

## Deployment (Render)
**Local vs production settings** (all environment variables, see `skillztrack/config.py`):

| Setting | Local | Production |
|---|---|---|
| `SKILLZTRACK_DB` | `./skillztrack.db` (default) | `/var/data/skillztrack.db` on a persistent disk |
| `SKILLZTRACK_SECURE_COOKIES` | `0` (http://localhost) | `1` (HTTPS only) |
| `SKILLZTRACK_PBKDF2_ITERATIONS` | 600000 | 600000 |
| Server | `python run.py` | `gunicorn wsgi:application` |

**Upgrading from CareerTrack:** the project was renamed. Old `CAREERTRACK_*` environment variables and an existing `careertrack.db` file are
still honoured (the new `SKILLZTRACK_*` names win when both are set; new installs create `skillztrack.db`). New tables are created
automatically on first start, so existing users, attempts and roadmaps are kept. Cookie and session formats are unchanged, so signed-in
students stay signed in.

Steps:
1. Push the project to GitHub (`.gitignore` already excludes `*.db`, `venv`, `.env`).
2. Render -> New -> Blueprint (uses `render.yaml`), or New -> Web Service with
   Build `pip install -r requirements.txt`, Start `gunicorn wsgi:application --workers 2 --threads 4 --bind 0.0.0.0:$PORT`.
3. Add environment variables from the table, plus `SKILLZTRACK_ADMIN_USERNAME/EMAIL/PASSWORD` for the first admin
   (delete the PASSWORD variable after the first successful start).
4. Open the URL, log in, visit `/admin`.

**Free-tier caveat:** Render's free web services have an *ephemeral* filesystem, so a SQLite file is wiped
on every redeploy/restart. Use a paid plan with a persistent disk (as in `render.yaml`), or port `db.py` to
PostgreSQL (the schema uses a few SQLite-specific bits: `datetime('now')`, `INSERT OR IGNORE`, `ON CONFLICT`).

**Deployment checklist**
- [ ] Tests pass locally  - [ ] `SKILLZTRACK_SECURE_COOKIES=1`  - [ ] disk mounted and `SKILLZTRACK_DB` points to it
- [ ] admin created, admin password variable removed  - [ ] HTTPS works, login works, `/admin` rejects students
- [ ] resource links spot-checked (they point to third-party sites and can change)

## Screenshot checklist
Landing (hero + features + careers) - register - login - dashboard (empty, then with a career) - assessment -
gap analysis (radar + simulator) - roadmap (with "Why this milestone?" open) - achievements - notifications -
profile - admin overview - dark mode - mobile view of dashboard & roadmap.

## Known limitations
- Login rate limiting is in memory, per server process.
- Resource URLs are well-known public pages but were not link-checked automatically.
- Google Fonts are optional and load from Google; offline the app uses system fonts (everything else is self-hosted).
- Streaks and activity timestamps use UTC, so a student far from UTC may see a day boundary at an unusual local time.
- Notifications refresh by polling once a minute (no WebSocket server), which fits the standard-library architecture.

## Beginner track (new)
- Every skill now starts with a **level-1 "First steps" quiz**; Python, DSA, Statistics and Testing also have easy step-by-step coding/debugging tasks (levels 1-2) with numbered steps, an example with expected output, and hints (`skillztrack/bank/beginner.py`).
- Difficulty badges (Beginner, Easy, Intermediate, Advanced, Expert); the recommended next task starts with the easiest one and climbs.
- Wrong answers show a **hint**, not the solution. Quiz explanations unlock after the second attempt.
- Beginner/Easy tasks allow 10 retries with no retry penalty. Harder tasks keep the old rules.
- Grading still uses hidden test cases and rubrics, gives a 0-5 skill score, and updates the skill profile and roadmap.
- Tests: `tests/test_beginner.py`.
#   s k i l l z t r a c k  
 