"""Local development server and small admin commands.

    python run.py                    start the site on http://127.0.0.1:8000
    python run.py initdb             create tables and load starter data (also happens automatically)
    python run.py createadmin        create an administrator account (asks for details)
    python run.py reseed             re-load/refresh the starter careers, skills, resources, projects
    python run.py rescore            recompute every verified skill score from the stored attempts
"""
import getpass
import os
import sys
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from skillztrack import config, db, security, services
from skillztrack.app import application


class ThreadingServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class QuietHandler(WSGIRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def create_admin():
    conn = db.connect()
    username = input("Admin username: ").strip()
    email = input("Admin email: ").strip()
    password = getpass.getpass("Password (min 8 chars): ")
    if len(password) < 8 or not username or "@" not in email:
        sys.exit("Invalid details (username, a valid email, and an 8+ character password are required).")
    uid = services.create_user(conn, username, email, username, password)
    conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (uid,))
    conn.commit()
    print(f"Admin '{username}' created. Log in, then open /admin.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "serve"
    if command == "createadmin":
        create_admin()
    elif command == "rescore":
        from skillztrack import assessments
        conn = db.connect(); db.init_db(conn); db.seed_assignments(conn); assessments.rebuild_scores(conn); conn.commit(); conn.close()
        print("Skill scores recomputed from attempts.")
    elif command in {"initdb", "reseed"}:
        conn = db.connect(); db.init_db(conn); db.seed(conn); conn.close()
        print("Database ready at", config.DB_PATH)
    else:
        port = int(os.environ.get("PORT", "8000"))
        print(f"SkillzTrack running at http://127.0.0.1:{port}  (Ctrl+C to stop)")
        with make_server("127.0.0.1", port, application, server_class=ThreadingServer, handler_class=QuietHandler) as httpd:
            httpd.serve_forever()
