"""Debugging and testing assignments: fix buggy code, or write tests that catch bugs."""
from . import Assignment, T

DEBUG_INTRO = ("The starter code is buggy. Fix it so it matches the description in each docstring. Your fixed code runs against hidden "
               "tests in a restricted sandbox (standard library only, no files or network). Some functions already work: don't break them.")


def debug(slug, skill, title, summary, ceiling, minutes, instructions, starter, tests, reference):
    return Assignment(slug=slug, skill=skill, kind="debug", title=title, summary=summary, ceiling=ceiling, minutes=minutes,
                      instructions=instructions, starter=starter, spec={"tests": tests}, reference=reference)


# --------------------------------------------------------------------------------------------- debug pack
PACK_STARTER = '''def average(numbers):
    """Return the mean of a list of numbers. An empty list returns 0."""
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)


def find_max(items):
    """Return the largest item, or None for an empty list. Must work for lists of negative numbers."""
    biggest = 0
    for x in items:
        if x > biggest:
            biggest = x
    return biggest


def count_vowels(text):
    """Count the vowels a, e, i, o, u in `text`, ignoring case."""
    count = 0
    for ch in text:
        if ch in "aeiou":
            count += 1
    return count


def remove_duplicates(items):
    """Remove duplicates but keep the FIRST occurrence of each item and the original order."""
    return list(set(items))


def last_n(items, n):
    """Return the last n items of the list. n = 0 returns []; n larger than the list returns the whole list."""
    return items[-n:]
'''
PACK_REF = '''def average(numbers):
    return sum(numbers) / len(numbers) if numbers else 0

def find_max(items):
    return max(items) if items else None

def count_vowels(text):
    return sum(1 for ch in text.lower() if ch in "aeiou")

def remove_duplicates(items):
    seen, out = set(), []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def last_n(items, n):
    return items[max(0, len(items) - n):] if n > 0 else []
'''

# ------------------------------------------------------------------------------------------ config loader
CONFIG_STARTER = '''def parse_bool(value):
    """'true', '1', 'yes', 'on' (any case, spaces ignored) -> True.  'false', '0', 'no', 'off', '' -> False.
    None -> False. Anything else raises ValueError."""
    return bool(value)


def load_config(env):
    """Build settings from a dict of environment variables (all values are strings):
      debug          bool, from DEBUG via parse_bool, default False
      port           int, from PORT, default 8000; ValueError if not an integer or outside 1..65535
      allowed_hosts  list of trimmed, non-empty names from comma-separated ALLOWED_HOSTS, default []
      database_url   from DATABASE_URL (trimmed); raise KeyError if it is missing or blank
    Return them in a dict with exactly those four keys."""
    return {
        "debug": env.get("DEBUG", True),
        "port": env.get("PORT", 8000),
        "allowed_hosts": env.get("ALLOWED_HOSTS", "").split(","),
        "database_url": env.get("DATABASE_URL"),
    }


def mask_secret(secret):
    """Show only the last 4 characters: 'supersecret123' -> '****t123'. Secrets of 4 characters or fewer become '****'."""
    return secret
'''
CONFIG_REF = '''def parse_bool(value):
    if value is None:
        return False
    v = str(value).strip().lower()
    if v in ("true", "1", "yes", "on"):
        return True
    if v in ("false", "0", "no", "off", ""):
        return False
    raise ValueError("not a boolean: %r" % value)

def load_config(env):
    raw = str(env.get("PORT", "8000")).strip()
    try:
        port = int(raw)
    except ValueError:
        raise ValueError("PORT must be an integer")
    if not 1 <= port <= 65535:
        raise ValueError("PORT out of range")
    hosts = [h.strip() for h in env.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
    db = env.get("DATABASE_URL")
    if db is None or not db.strip():
        raise KeyError("DATABASE_URL")
    return {"debug": parse_bool(env.get("DEBUG")), "port": port, "allowed_hosts": hosts, "database_url": db.strip()}

def mask_secret(secret):
    return "****" if len(secret) <= 4 else "****" + secret[-4:]
'''
DB = "postgres://u:p@db/app"

# ----------------------------------------------------------------------------------------- web security
SEC_STARTER = '''def find_user(conn, username):
    """Return the rows (id, username, role) of the user whose username matches EXACTLY.
    `conn` is an open sqlite3 connection with a table users(id, username, role, secret). Must be safe against SQL injection."""
    query = "SELECT id, username, role FROM users WHERE username = '" + username + "'"
    return conn.execute(query).fetchall()


def render_comment(text):
    """Return an HTML paragraph containing the user's comment: <p>...</p>. The comment is untrusted:
    it must not be able to inject HTML or scripts (escape < > & and quotes)."""
    return "<p>" + text + "</p>"


def safe_join(base, user_path):
    """Join `user_path` onto the directory `base` (use '/' separators) and return the normalised path.
    Raise ValueError if the result would be outside `base` (path traversal such as '../etc/passwd',
    'a/../../x' or an absolute path like '/etc/passwd'). 'a/../b' is fine and becomes '<base>/b'."""
    return base + "/" + user_path


def is_safe_redirect(url):
    """True only for relative paths on THIS site: they start with a single '/'. Reject '//host', 'http://...',
    'javascript:...', empty strings, paths without a leading '/', and anything containing a backslash."""
    return True
'''
SEC_REF = '''import html
import posixpath

def find_user(conn, username):
    return conn.execute("SELECT id, username, role FROM users WHERE username = ?", (username,)).fetchall()

def render_comment(text):
    return "<p>" + html.escape(text) + "</p>"

def safe_join(base, user_path):
    base_n = posixpath.normpath(base)
    if user_path.startswith("/"):
        raise ValueError("absolute path")
    joined = posixpath.normpath(posixpath.join(base_n, user_path))
    if joined != base_n and not joined.startswith(base_n + "/"):
        raise ValueError("path escapes base")
    return joined

def is_safe_redirect(url):
    return isinstance(url, str) and url.startswith("/") and not url.startswith("//") and "\\\\" not in url
'''
U = "users_db"

# ---------------------------------------------------------------------------------------------- mutation
SHIP_REF = '''import math

def shipping_cost(weight_kg, express=False):
    if weight_kg <= 0:
        raise ValueError("weight must be positive")
    extra = max(0, math.ceil(weight_kg) - 1)
    cost = min(20.0, 5.0 + 2.0 * extra)
    if express:
        cost = cost * 1.5
    return round(cost, 2)
'''
SHIP_CAP_AFTER = SHIP_REF.replace("cost = min(20.0, 5.0 + 2.0 * extra)", "cost = 5.0 + 2.0 * extra").replace(
    "    return round(cost, 2)", "    return round(min(cost, 20.0), 2)")
MUTANTS = [
    {"id": "m1", "label": "Bug: a weight of exactly 0 is accepted", "topic": "boundary values", "hint": "what should happen at exactly 0 kg?",
     "src": SHIP_REF.replace("weight_kg <= 0", "weight_kg < 0")},
    {"id": "m2", "label": "Bug: partial kilograms are not charged as a started kilogram", "topic": "equivalence classes", "hint": "try a fractional weight such as 1.2.",
     "src": SHIP_REF.replace("math.ceil(weight_kg)", "int(weight_kg)")},
    {"id": "m3", "label": "Bug: the 20.00 cap is wrong", "topic": "boundary values", "hint": "test a very heavy parcel.",
     "src": SHIP_REF.replace("min(20.0,", "min(25.0,")},
    {"id": "m4", "label": "Bug: wrong express surcharge", "topic": "business rules", "hint": "test an express parcel.",
     "src": SHIP_REF.replace("cost * 1.5", "cost * 1.25")},
    {"id": "m5", "label": "Bug: exactly 1 kg is charged as 2 kg", "topic": "boundary values", "hint": "test the exact boundary of the first kilogram.",
     "src": SHIP_REF.replace("math.ceil(weight_kg) - 1", "math.ceil(weight_kg)")},
    {"id": "m6", "label": "Bug: express price is truncated instead of rounded to cents", "topic": "numeric precision", "hint": "an express 1 kg parcel costs a fractional amount.",
     "src": SHIP_REF.replace("round(cost, 2)", "int(cost)")},
    {"id": "m7", "label": "Bug: the cap is applied after the express surcharge", "topic": "business rules", "hint": "combine express with a heavy parcel.",
     "src": SHIP_CAP_AFTER},
]
MUTATION_STARTER = '''def test_cases():
    """Return a list of [args, expected] pairs for this function (shown for reference, you do not write it):

        def shipping_cost(weight_kg, express=False):
            # Standard: 5.00 for up to 1 kg, plus 2.00 for every further STARTED kilogram, never more than 20.00.
            # Express adds 50% on top of that price (the 20.00 cap is applied BEFORE the express surcharge).
            # The result is rounded to 2 decimals. weight_kg <= 0 raises ValueError.

    `args` is the list of positional arguments, `expected` the result, or {"raises": "ValueError"} when the call
    should raise. Example: [[2], 7.0] means shipping_cost(2) == 7.0, and [[0], {"raises": "ValueError"}].
    Your tests must be CORRECT (they pass on the real function) and SHARP (they fail on buggy versions)."""
    return [
        [[2], 7.0],
    ]
'''
MUTATION_REF = '''def test_cases():
    return [
        [[0.5], 5.0], [[1], 5.0], [[1.2], 7.0], [[2], 7.0], [[3.5], 11.0], [[20], 20.0],
        [[1, True], 7.5], [[20, True], 30.0], [[0], {"raises": "ValueError"}], [[-1], {"raises": "ValueError"}],
    ]
'''

ASSIGNMENTS = [
    debug("debug-pack", "testing", "Debugging: five small bugs", "Find and fix one bug in each of five functions.", 3, 25, DEBUG_INTRO, PACK_STARTER, [
        T("average", [[1, 2, 3]], 2, "average of a normal list", "arithmetic", visible=True, cmp="approx"),
        T("average", [[]], 0, "average of an empty list is 0", "edge cases", cmp="approx"),
        T("average", [[-4, 4, 10]], 10 / 3, "average with negatives", "arithmetic", cmp="approx"),
        T("find_max", [[3, 9, 2]], 9, "find_max of positives", "comparisons", visible=True),
        T("find_max", [[-5, -2, -9]], -2, "find_max of all-negative numbers", "comparisons", weight=2),
        T("find_max", [[]], None, "find_max of an empty list is None", "edge cases"),
        T("find_max", [[0]], 0, "find_max of a single zero", "edge cases"),
        T("count_vowels", ["hello"], 2, "lowercase vowels", "strings", visible=True),
        T("count_vowels", ["HELLO World"], 3, "uppercase vowels count too", "strings", weight=2),
        T("count_vowels", [""], 0, "empty string", "edge cases"),
        T("remove_duplicates", [[3, 1, 3, 2, 1]], [3, 1, 2], "first occurrences, original order", "ordering", weight=2, visible=True),
        T("remove_duplicates", [["b", "a", "b"]], ["b", "a"], "strings keep their order", "ordering"),
        T("remove_duplicates", [[]], [], "empty list", "edge cases"),
        T("last_n", [[1, 2, 3, 4], 2], [3, 4], "last two items", "slicing", visible=True),
        T("last_n", [[1, 2, 3, 4], 0], [], "n = 0 returns an empty list", "slicing", weight=2),
        T("last_n", [[1, 2, 3, 4], 10], [1, 2, 3, 4], "n larger than the list", "slicing"),
        T("last_n", [[], 3], [], "empty list", "edge cases"),
    ], PACK_REF),

    debug("config-loader-debug", "deployment-basics", "Debugging a deployment config loader", "Fix environment-variable parsing bugs that break real deployments.", 4, 30,
          DEBUG_INTRO + " Environment variables are always strings, which is the source of most of these bugs.", CONFIG_STARTER, [
        T("parse_bool", ["true"], True, "'true' is True", "environment variables", visible=True),
        T("parse_bool", ["FALSE"], False, "'FALSE' is False (non-empty strings are truthy in Python!)", "environment variables", weight=2),
        T("parse_bool", ["0"], False, "'0' is False", "environment variables", weight=2),
        T("parse_bool", ["Yes"], True, "'Yes' is True", "environment variables"),
        T("parse_bool", [" on "], True, "spaces are ignored", "environment variables"),
        T("parse_bool", ["off"], False, "'off' is False", "environment variables"),
        T("parse_bool", [""], False, "empty string is False", "environment variables"),
        T("parse_bool", [None], False, "None is False", "environment variables"),
        T("parse_bool", ["maybe"], label="unknown text is an error", topic="validation", raises="ValueError"),
        T("load_config", [{"DATABASE_URL": DB}], {"debug": False, "port": 8000, "allowed_hosts": [], "database_url": DB},
          "defaults: debug off, port 8000, no hosts", "defaults", visible=True, weight=3),
        T("load_config", [{"DATABASE_URL": DB, "DEBUG": "true", "PORT": "5000", "ALLOWED_HOSTS": " a.com, b.com ,,"}],
          {"debug": True, "port": 5000, "allowed_hosts": ["a.com", "b.com"], "database_url": DB}, "parses and trims everything", "parsing", weight=3),
        T("load_config", [{"DATABASE_URL": DB, "DEBUG": "false"}], {"debug": False, "port": 8000, "allowed_hosts": [], "database_url": DB}, "DEBUG=false really means off", "environment variables", weight=2),
        T("load_config", [{"PORT": "5000"}], label="a missing DATABASE_URL is an error", topic="validation", raises="KeyError", weight=2),
        T("load_config", [{"DATABASE_URL": "   "}], label="a blank DATABASE_URL is an error", topic="validation", raises="KeyError"),
        T("load_config", [{"DATABASE_URL": DB, "PORT": "abc"}], label="a non-numeric PORT is an error", topic="validation", raises="ValueError"),
        T("load_config", [{"DATABASE_URL": DB, "PORT": "70000"}], label="PORT above 65535 is an error", topic="validation", raises="ValueError"),
        T("load_config", [{"DATABASE_URL": DB, "PORT": "0"}], label="PORT 0 is an error", topic="validation", raises="ValueError"),
        T("mask_secret", ["supersecret123"], "****t123", "mask_secret hides all but the last 4", "secrets", visible=True, weight=2),
        T("mask_secret", ["abc"], "****", "short secrets are fully masked", "secrets"),
        T("mask_secret", ["abcd"], "****", "4-character secrets are fully masked", "secrets"),
        T("mask_secret", ["abcde"], "****bcde", "5 characters", "secrets"),
    ], CONFIG_REF),

    debug("secure-code-fix", "web-security", "Fix the vulnerabilities", "Repair SQL injection, XSS, path traversal and an open redirect.", 4, 35,
          DEBUG_INTRO + " Each function contains a real security flaw. Your fix is tested with attack payloads, not just normal input.", SEC_STARTER, [
        T("find_user", ["alice"], [[1, "alice", "admin"]], "find_user works for a normal username", "SQL injection", fixture=U, visible=True),
        T("find_user", ["bob"], [[2, "bob", "user"]], "find_user works for another user", "SQL injection", fixture=U),
        T("find_user", ["nobody"], [], "find_user returns nothing for an unknown user", "SQL injection", fixture=U),
        T("find_user", ["' OR '1'='1"], [], "classic ' OR '1'='1 injection returns nothing", "SQL injection", fixture=U, weight=3),
        T("find_user", ["alice' --"], [], "comment-based injection returns nothing", "SQL injection", fixture=U, weight=2),
        T("find_user", ["x'; DROP TABLE users; --"], [], "stacked-query injection returns nothing", "SQL injection", fixture=U, weight=2),
        T("find_user", ["O'Brien"], [], "an apostrophe in a name must not break the query", "SQL injection", fixture=U),
        T("render_comment", ["hello"], "<p>hello</p>", "plain comments are unchanged", "XSS", visible=True),
        T("render_comment", ["<script>alert(1)</script>"], "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>", "script tags are neutralised", "XSS", weight=3),
        T("render_comment", ['Tom & "Jerry"'], "<p>Tom &amp; &quot;Jerry&quot;</p>", "ampersands and quotes are escaped", "XSS", weight=2),
        T("render_comment", ['<img src=x onerror="steal()">'], "<p>&lt;img src=x onerror=&quot;steal()&quot;&gt;</p>", "attribute-based payloads are escaped", "XSS", weight=2),
        T("safe_join", ["/var/www", "img/a.png"], "/var/www/img/a.png", "safe_join normal path", "path traversal", visible=True),
        T("safe_join", ["/var/www", "a/../b"], "/var/www/b", "safe_join normalises harmless '..'", "path traversal"),
        T("safe_join", ["/var/www", "../etc/passwd"], label="'../etc/passwd' is rejected", topic="path traversal", raises="ValueError", weight=3),
        T("safe_join", ["/var/www", "a/../../x"], label="a sneaky '..' chain is rejected", topic="path traversal", raises="ValueError", weight=2),
        T("safe_join", ["/var/www", "/etc/passwd"], label="an absolute path is rejected", topic="path traversal", raises="ValueError", weight=2),
        T("is_safe_redirect", ["/dashboard"], True, "a local path is allowed", "open redirect", visible=True),
        T("is_safe_redirect", ["//evil.com"], False, "protocol-relative URL is rejected", "open redirect", weight=2),
        T("is_safe_redirect", ["https://evil.com"], False, "absolute URL is rejected", "open redirect", weight=2),
        T("is_safe_redirect", ["javascript:alert(1)"], False, "javascript: URL is rejected", "open redirect"),
        T("is_safe_redirect", ["/\\evil.com"], False, "backslash trick is rejected", "open redirect", weight=2),
        T("is_safe_redirect", [""], False, "empty string is rejected", "open redirect"),
        T("is_safe_redirect", ["dashboard"], False, "a path without a leading slash is rejected", "open redirect"),
    ], SEC_REF),

    Assignment(slug="mutation-testing", skill="testing", kind="mutation", title="Write tests that catch bugs",
               summary="Write a test suite for a shipping-cost function. It is graded on whether it catches 7 hidden bugs.", ceiling=4, minutes=30,
               instructions=("You are the tester. Edit test_cases() so it returns [args, expected] pairs. Your tests are run against the CORRECT "
                             "function (every expected value must be right) and then against seven deliberately broken versions: each bug your "
                             "tests catch earns points. Think about boundaries, equivalence classes and combinations of options. "
                             "Provide between 4 and 30 tests."),
               starter=MUTATION_STARTER, reference=MUTATION_REF,
               spec={"function": "shipping_cost", "reference": SHIP_REF, "mutants": MUTANTS, "min_tests": 4, "max_tests": 30}),
]
