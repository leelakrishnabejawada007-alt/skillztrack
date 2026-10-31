"""Recording what a student does: activity feed, notifications and badge awards.

Views call `after_change(conn, user_id)` once an action has been saved. It awards any badge the stored evidence now
supports (each exactly once) and tells the student. Everything runs inside the request's own transaction, so a failed
request records nothing.
"""

MAX_FEED = 200


def record(conn, user_id, kind, title, link="", ref=""):
    conn.execute("INSERT INTO activity_log (user_id, kind, title, link, ref) VALUES (?,?,?,?,?)",
                 (user_id, kind, title[:200], link, str(ref)))


def notify(conn, user_id, kind, title, body="", link=""):
    conn.execute("INSERT INTO notifications (user_id, kind, title, body, link) VALUES (?,?,?,?,?)",
                 (user_id, kind, title[:160], body[:400], link))


def record_once(conn, user_id, kind, title, link="", ref=""):
    """Like record(), but skip when the same (kind, ref) was already logged (used for milestones and study items)."""
    if conn.execute("SELECT 1 FROM activity_log WHERE user_id = ? AND kind = ? AND ref = ?", (user_id, kind, str(ref))).fetchone():
        return False
    record(conn, user_id, kind, title, link, ref)
    return True


def after_change(conn, user_id):
    """Award newly earned badges. Returns their names (so a page can mention them in its success message)."""
    from . import gamification as g
    stats = g.collect(conn, user_id)
    have = g.earned_map(conn, user_id)
    new = []
    for badge in g.evaluate(stats, have):
        if badge["earned"] and badge["code"] not in have:
            conn.execute("INSERT OR IGNORE INTO achievements (user_id, code) VALUES (?,?)", (user_id, badge["code"]))
            record(conn, user_id, "badge", f"Earned the {badge['name']} badge", "/achievements", badge["code"])
            notify(conn, user_id, "badge", f"New badge: {badge['name']}", badge["description"], "/achievements")
            new.append(badge["name"])
    return new


def unread_count(conn, user_id):
    return conn.execute("SELECT COUNT(*) AS n FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,)).fetchone()["n"]


def recent_activity(conn, user_id, limit=8):
    return conn.execute("SELECT kind, title, link, created_at FROM activity_log WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                        (user_id, limit)).fetchall()
