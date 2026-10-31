"""SQLite connection, schema and seeding.

We open ONE short-lived connection per request. SQLite handles this well for a
small app, and it avoids sharing a connection between threads.
"""
import sqlite3

from . import config, seed_content as content

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS careers (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL UNIQUE,
    tagline TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    icon TEXT NOT NULL DEFAULT 'bi-compass'
);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL DEFAULT 'programming',
    description TEXT NOT NULL DEFAULT ''
);

-- "Career X needs skill Y at level N" (target proficiency)
CREATE TABLE IF NOT EXISTS career_skills (
    id INTEGER PRIMARY KEY,
    career_id INTEGER NOT NULL REFERENCES careers(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    required_level INTEGER NOT NULL DEFAULT 3 CHECK (required_level BETWEEN 1 AND 5),
    importance INTEGER NOT NULL DEFAULT 2 CHECK (importance BETWEEN 1 AND 3),
    sequence INTEGER NOT NULL DEFAULT 1,
    UNIQUE (career_id, skill_id)
);

CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    rtype TEXT NOT NULL DEFAULT 'course',
    difficulty TEXT NOT NULL DEFAULT 'beginner' CHECK (difficulty IN ('beginner','intermediate','advanced')),
    hours INTEGER NOT NULL DEFAULT 5,
    is_free INTEGER NOT NULL DEFAULT 1,
    UNIQUE (skill_id, url)
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    career_id INTEGER NOT NULL REFERENCES careers(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    difficulty TEXT NOT NULL DEFAULT 'beginner' CHECK (difficulty IN ('beginner','intermediate','advanced')),
    hours INTEGER NOT NULL DEFAULT 10,
    UNIQUE (career_id, title)
);

CREATE TABLE IF NOT EXISTS project_skills (
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, skill_id)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    full_name TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    target_career_id INTEGER REFERENCES careers(id) ON DELETE SET NULL,
    hours_per_week INTEGER NOT NULL DEFAULT 8 CHECK (hours_per_week BETWEEN 2 AND 40),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL
);

-- The student's self-assessment: one level (0-5) per skill
CREATE TABLE IF NOT EXISTS assessments (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    level INTEGER NOT NULL CHECK (level BETWEEN 0 AND 5),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, skill_id)
);

CREATE TABLE IF NOT EXISTS roadmaps (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    career_id INTEGER NOT NULL REFERENCES careers(id) ON DELETE CASCADE,
    hours_per_week INTEGER NOT NULL,
    readiness REAL NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
-- at most ONE active roadmap per user
CREATE UNIQUE INDEX IF NOT EXISTS one_active_roadmap ON roadmaps(user_id) WHERE is_active = 1;

CREATE TABLE IF NOT EXISTS milestones (
    id INTEGER PRIMARY KEY,
    roadmap_id INTEGER NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    title TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    from_level INTEGER NOT NULL,
    target_level INTEGER NOT NULL,
    hours INTEGER NOT NULL,
    start_week INTEGER NOT NULL,
    end_week INTEGER NOT NULL,
    is_priority INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started','in_progress','completed')),
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS milestone_resources (
    id INTEGER PRIMARY KEY,
    milestone_id INTEGER NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
    resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    done INTEGER NOT NULL DEFAULT 0,
    UNIQUE (milestone_id, resource_id)
);

-- ---------------------------------------------------------------- evidence-based assessment
-- One row per bank assignment (metadata only; hidden tests/rubrics stay in skillztrack/bank and are never sent to a browser).
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('quiz','code','debug','mutation','sql','commands','rubric')),
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    ceiling INTEGER NOT NULL CHECK (ceiling BETWEEN 1 AND 5),
    evidence TEXT NOT NULL CHECK (evidence IN ('executed','static','quiz')),
    minutes INTEGER NOT NULL DEFAULT 20,
    is_active INTEGER NOT NULL DEFAULT 1
);

-- Every attempt a student makes, with the full per-test/per-criterion evidence.
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    attempt_no INTEGER NOT NULL DEFAULT 0,          -- set when graded: 1 = first graded attempt on this assignment
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress','graded')),
    payload TEXT NOT NULL DEFAULT '{}',             -- server-side only: which quiz questions, in which option order
    submission TEXT NOT NULL DEFAULT '{}',          -- what the student submitted (JSON)
    points REAL,                                    -- rubric/test points earned
    possible REAL,
    pct REAL,                                       -- points / possible (0..1)
    skill_score REAL,                               -- this attempt on the 0-5 scale (ceiling x mastery x retake factor)
    breakdown TEXT NOT NULL DEFAULT '[]',           -- JSON: [{label, topic, earned, possible, passed, feedback}]
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    graded_at TEXT,
    duration_seconds INTEGER
);
CREATE INDEX IF NOT EXISTS attempts_user ON attempts(user_id, assignment_id);

-- The student's VERIFIED skill profile: derived only from graded attempts, never from self-ratings.
CREATE TABLE IF NOT EXISTS skill_scores (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    score REAL NOT NULL CHECK (score BETWEEN 0 AND 5),
    level INTEGER NOT NULL CHECK (level BETWEEN 0 AND 5),
    confidence TEXT NOT NULL CHECK (confidence IN ('low','medium','high')),
    assignments_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, skill_id)
);

-- Progress over time: one row each time a graded attempt changes a skill score.
CREATE TABLE IF NOT EXISTS skill_score_history (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    attempt_id INTEGER REFERENCES attempts(id) ON DELETE SET NULL,
    score REAL NOT NULL,
    level INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS score_history_user ON skill_score_history(user_id, skill_id, id);

-- Project progress belongs to the student (it survives roadmap regeneration)
CREATE TABLE IF NOT EXISTS project_progress (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started','in_progress','completed')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, project_id)
);
-- ---------------------------------------------------------------- engagement (activity, notifications, badges)
-- Everything the student did, newest first on the dashboard; also feeds the streak.
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,                      -- attempt | study | milestone | roadmap | career | badge | level
    title TEXT NOT NULL,
    link TEXT NOT NULL DEFAULT '',
    ref TEXT NOT NULL DEFAULT '',            -- optional de-duplication key (e.g. the skill id of a milestone)
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS activity_user ON activity_log(user_id, id);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL DEFAULT 'info',       -- badge | level | milestone | roadmap | info
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    link TEXT NOT NULL DEFAULT '',
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS notifications_user ON notifications(user_id, is_read, id);

-- Badges are earned once and kept, even if the roadmap or career later changes.
CREATE TABLE IF NOT EXISTS achievements (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    earned_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, code)
);
"""


def connect(path=None):
    conn = sqlite3.connect(path or config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _columns(conn, table):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def migrate(conn):
    """Small, idempotent upgrades for databases created by earlier versions."""
    if "focus_topics" not in _columns(conn, "milestones"):
        conn.execute("ALTER TABLE milestones ADD COLUMN focus_topics TEXT NOT NULL DEFAULT '[]'")


def init_db(conn):
    conn.executescript(SCHEMA)
    migrate(conn)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.commit()


def seed_assignments(conn):
    """Sync assignment metadata from the bank. Safe to run on every start (upsert by slug)."""
    from . import bank
    skill_id = {r["slug"]: r["id"] for r in conn.execute("SELECT id, slug FROM skills")}
    for a in bank.all_assignments():
        if a.skill not in skill_id:
            continue
        conn.execute(
            "INSERT INTO assignments (slug, skill_id, kind, title, summary, ceiling, evidence, minutes) VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(slug) DO UPDATE SET skill_id=excluded.skill_id, kind=excluded.kind, title=excluded.title, "
            "summary=excluded.summary, ceiling=excluded.ceiling, evidence=excluded.evidence, minutes=excluded.minutes",
            (a.slug, skill_id[a.skill], a.kind, a.title, a.summary, a.ceiling, a.evidence, a.minutes))
    conn.commit()


def seed(conn):
    """Load the starter catalogue. Safe to run repeatedly (upserts by slug / unique keys)."""
    for slug, name, category, description in content.SKILLS:
        conn.execute(
            "INSERT INTO skills (slug,name,category,description) VALUES (?,?,?,?) "
            "ON CONFLICT(slug) DO UPDATE SET name=excluded.name, category=excluded.category, description=excluded.description",
            (slug, name, category, description),
        )
    skill_id = {r["slug"]: r["id"] for r in conn.execute("SELECT id, slug FROM skills")}

    for slug, title, tagline, icon, description in content.CAREERS:
        conn.execute(
            "INSERT INTO careers (slug,title,tagline,icon,description) VALUES (?,?,?,?,?) "
            "ON CONFLICT(slug) DO UPDATE SET title=excluded.title, tagline=excluded.tagline, icon=excluded.icon, description=excluded.description",
            (slug, title, tagline, icon, description),
        )
    career_id = {r["slug"]: r["id"] for r in conn.execute("SELECT id, slug FROM careers")}

    for career_slug, rows in content.REQUIREMENTS.items():
        for skill_slug, level, importance, sequence in rows:
            conn.execute(
                "INSERT INTO career_skills (career_id,skill_id,required_level,importance,sequence) VALUES (?,?,?,?,?) "
                "ON CONFLICT(career_id,skill_id) DO UPDATE SET required_level=excluded.required_level, "
                "importance=excluded.importance, sequence=excluded.sequence",
                (career_id[career_slug], skill_id[skill_slug], level, importance, sequence),
            )

    for skill_slug, title, provider, url, rtype, difficulty, hours, free in content.RESOURCES:
        conn.execute(
            "INSERT INTO resources (skill_id,title,provider,url,rtype,difficulty,hours,is_free) VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(skill_id,url) DO UPDATE SET title=excluded.title, provider=excluded.provider, rtype=excluded.rtype, "
            "difficulty=excluded.difficulty, hours=excluded.hours, is_free=excluded.is_free",
            (skill_id[skill_slug], title, provider, url, rtype, difficulty, hours, int(free)),
        )

    for career_slug, title, description, difficulty, hours, skill_slugs in content.PROJECTS:
        conn.execute(
            "INSERT INTO projects (career_id,title,description,difficulty,hours) VALUES (?,?,?,?,?) "
            "ON CONFLICT(career_id,title) DO UPDATE SET description=excluded.description, difficulty=excluded.difficulty, hours=excluded.hours",
            (career_id[career_slug], title, description, difficulty, hours),
        )
        pid = conn.execute(
            "SELECT id FROM projects WHERE career_id=? AND title=?", (career_id[career_slug], title)
        ).fetchone()["id"]
        for s in skill_slugs:
            conn.execute("INSERT OR IGNORE INTO project_skills (project_id,skill_id) VALUES (?,?)", (pid, skill_id[s]))
    conn.commit()
    seed_assignments(conn)
