"""
Runs student Python code against test inputs, in a separate, restricted process.

DEFENCE IN DEPTH (read this before deploying to the public internet)
    1. Static screen (ast): only allow-listed imports; no eval/exec/open/getattr/...; no dunder or
       frame/generator attribute access (the usual ways out of a Python "sandbox").
    2. Restricted builtins + a guarded __import__ inside the child process.
    3. A SEPARATE process started with `python -I -B -S`, an empty environment, a throw-away
       working directory, and (on Linux/macOS) hard CPU / memory / file-size limits.
    4. Per-test and overall time-outs.
    5. The child only ever receives test INPUTS. Expected answers stay in the parent process, so
       submitted code cannot read them, and the child cannot "print the answer key".

    This is a solid layer for a coursework / small-community deployment. It is NOT a replacement
    for real isolation: a determined attacker can still hurt a pure-Python sandbox. For a public
    site, run grading in a container or worker with no network and no secrets, or set
    SKILLZTRACK_CODE_EXEC=0 to disable code execution entirely (code assignments then show as
    unavailable and the rest of the system keeps working).
    Windows: resource limits (RLIMIT_*) do not exist there; the screen, restricted builtins and
    time-outs still apply.
"""
from __future__ import annotations

import ast
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

from . import config

MAX_SOURCE_CHARS = 20_000
OVERALL_TIMEOUT = 12.0
PER_CASE_TIMEOUT = 2.0
RESULT_CHAR_LIMIT = 4000

ALLOWED_MODULES = frozenset({
    "math", "re", "json", "collections", "itertools", "functools", "heapq", "bisect", "statistics",
    "string", "datetime", "ipaddress", "hashlib", "hmac", "html", "base64", "csv", "textwrap",
    "operator", "random", "decimal", "fractions", "typing", "dataclasses", "secrets", "copy",
    "enum", "abc", "urllib.parse", "posixpath", "numbers", "array", "binascii", "struct", "zlib",
})

FORBIDDEN_NAMES = frozenset({
    "eval", "exec", "compile", "open", "input", "breakpoint", "globals", "locals", "vars", "getattr",
    "setattr", "delattr", "__import__", "exit", "quit", "help", "dir", "memoryview", "__builtins__",
    "__loader__", "__spec__",
})
SAFE_DUNDER_ATTRS = frozenset({"__init__", "__name__", "__doc__", "__eq__", "__lt__", "__repr__", "__str__",
                               "__len__", "__hash__"})
FORBIDDEN_ATTR_PREFIXES = ("gi_", "cr_", "ag_", "tb_", "f_", "co_")
FORBIDDEN_ATTRS = frozenset({"format_map", "func_globals", "mro"})


class SandboxUnavailable(RuntimeError):
    pass


# ------------------------------------------------------------------ static screen
def screen_source(source: str):
    """Return None if the code may run, otherwise a short human-readable reason."""
    if not isinstance(source, str) or not source.strip():
        return "Your submission is empty."
    if len(source) > MAX_SOURCE_CHARS:
        return f"Submission is too long (limit {MAX_SOURCE_CHARS} characters)."
    if "\x00" in source:
        return "Submission contains invalid characters."
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        where = f" (line {exc.lineno})" if exc.lineno else ""
        return f"Syntax error{where}: {exc.msg}"
    except (ValueError, RecursionError, MemoryError):
        return "This code could not be parsed."

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in ALLOWED_MODULES:
                    return f"Line {node.lineno}: importing '{alias.name}' is not allowed in assignments."
        elif isinstance(node, ast.ImportFrom):
            if node.level or (node.module or "") not in ALLOWED_MODULES:
                return f"Line {node.lineno}: importing from '{node.module or '.'}' is not allowed in assignments."
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES or (node.id.startswith("__") and node.id.endswith("__") and node.id != "__name__"):
                return f"Line {node.lineno}: '{node.id}' is not allowed in assignments."
        elif isinstance(node, ast.Attribute):
            attr = node.attr
            if attr.startswith("__") and attr.endswith("__") and attr not in SAFE_DUNDER_ATTRS:
                return f"Line {node.lineno}: access to '{attr}' is not allowed in assignments."
            if attr in FORBIDDEN_ATTRS or attr.startswith(FORBIDDEN_ATTR_PREFIXES):
                return f"Line {node.lineno}: access to '.{attr}' is not allowed in assignments."
    return None


# --------------------------------------------------------------------- the child
_HARNESS = r'''
import builtins, json, os, sys

def _limits():
    try:
        import resource
    except ImportError:          # Windows
        return
    for name, value in (("RLIMIT_CPU", 10), ("RLIMIT_AS", 768 << 20), ("RLIMIT_FSIZE", 2 << 20),
                        ("RLIMIT_NOFILE", 64), ("RLIMIT_CORE", 0)):
        try:
            resource.setrlimit(getattr(resource, name), (value, value))
        except (ValueError, OSError):
            pass

_limits()
work = sys.argv[1]
with open(os.path.join(work, "spec.json"), encoding="utf-8") as fh:
    spec = json.load(fh)
with open(os.path.join(work, "submission.py"), encoding="utf-8") as fh:
    source = fh.read()
_real_import = builtins.__import__
_out_path = os.path.join(work, "results.json")
_devnull = open(os.devnull, "w")
sys.stdout = _devnull
sys.stderr = _devnull
sys.setrecursionlimit(1500)

ALLOWED = set(spec["allowed_modules"])
def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name not in ALLOWED:
        raise ImportError("import of %r is not allowed" % name)
    return _real_import(name, globals, locals, fromlist, level)

SAFE = {n: getattr(builtins, n) for n in (
    "abs all any ascii bin bool bytearray bytes callable chr complex dict divmod enumerate filter float "
    "format frozenset hash hex id int isinstance issubclass iter len list map max min next object oct ord "
    "pow print property range repr reversed round set slice sorted staticmethod classmethod str sum super "
    "tuple type zip __build_class__ Exception ValueError TypeError KeyError IndexError ZeroDivisionError "
    "StopIteration AttributeError RuntimeError NotImplementedError ArithmeticError LookupError AssertionError "
    "OverflowError NotImplemented Ellipsis BaseException UnicodeError").split()}
SAFE["__import__"] = _guarded_import
namespace = {"__builtins__": SAFE, "__name__": "submission"}

class _Timeout(BaseException):
    pass

def _alarm(seconds):
    try:
        import signal
        def handler(signum, frame):
            raise _Timeout()
        signal.signal(signal.SIGALRM, handler)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        return signal
    except (ImportError, AttributeError, ValueError):
        return None

def _default(o):
    if isinstance(o, (set, frozenset)):
        try:
            return sorted(o)
        except TypeError:
            return sorted(map(repr, o))
    return "<" + type(o).__name__ + ">"

def _fixture(name):
    if name == "users_db":
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, role TEXT, secret TEXT)")
        conn.executemany("INSERT INTO users (username, role, secret) VALUES (?,?,?)",
                         [("alice", "admin", "a-secret"), ("bob", "user", "b-secret"), ("carol", "user", "c-secret")])
        conn.commit()
        deny = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA}
        conn.set_authorizer(lambda action, *rest: sqlite3.SQLITE_DENY if action in deny else sqlite3.SQLITE_OK)
        return conn
    return None

results = []
def _flush():
    with open(_out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, default=_default)

try:
    try:
        exec(compile(source, "<submission>", "exec"), namespace)
    except _Timeout:
        raise
    except BaseException as exc:
        for _ in spec["cases"]:
            results.append({"ok": False, "error": "Your code failed while loading: %s: %s" % (type(exc).__name__, str(exc)[:200])})
        _flush()
        raise SystemExit(0)
    for case in spec["cases"]:
        fn = namespace.get(case["fn"])
        if not callable(fn):
            results.append({"ok": False, "error": "Function '%s' is not defined." % case["fn"]})
            continue
        args = list(case.get("args", []))
        fixture = _fixture(case.get("fixture"))
        if fixture is not None:
            args.insert(0, fixture)
        sig = _alarm(spec["per_case"])
        try:
            value = fn(*args, **case.get("kwargs", {}))
            if sig: sig.setitimer(sig.ITIMER_REAL, 0)
            text = json.dumps(value, default=_default)
            if len(text) > spec["result_limit"]:
                results.append({"ok": False, "error": "Result is too large."})
            else:
                results.append({"ok": True, "value": json.loads(text)})
        except _Timeout:
            results.append({"ok": False, "error": "Timed out (likely an infinite loop or very slow code)."})
        except RecursionError:
            if sig: sig.setitimer(sig.ITIMER_REAL, 0)
            results.append({"ok": False, "error": "RecursionError: maximum recursion depth exceeded."})
        except MemoryError:
            if sig: sig.setitimer(sig.ITIMER_REAL, 0)
            results.append({"ok": False, "error": "MemoryError: your code used too much memory."})
        except BaseException as exc:
            if sig: sig.setitimer(sig.ITIMER_REAL, 0)
            results.append({"ok": False, "error": type(exc).__name__ + ": " + str(exc)[:200], "exc": type(exc).__name__,
                            "mro": [c.__name__ for c in type(exc).__mro__]})
    _flush()
except SystemExit:
    pass
except BaseException:
    _flush()
'''

_slots = threading.BoundedSemaphore(2)


def code_execution_enabled() -> bool:
    return bool(getattr(config, "CODE_EXEC", True))


def _child_env():
    env = {"PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8", "PATH": "/usr/bin:/bin"}
    if os.name == "nt":
        env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", r"C:\Windows")
    return env


def run_cases(source: str, cases: list, *, overall_timeout: float = OVERALL_TIMEOUT, per_case: float = PER_CASE_TIMEOUT):
    """Run `cases` (each: {fn, args, kwargs, fixture}) against `source`.

    Returns a list of result dicts aligned with `cases`: {"ok": True, "value": ...} or
    {"ok": False, "error": "..."}. The caller must call screen_source() first.
    """
    if not code_execution_enabled():
        raise SandboxUnavailable("Code execution is switched off on this server.")
    if not _slots.acquire(timeout=15):
        raise SandboxUnavailable("The code runner is busy. Please try again in a moment.")
    work = tempfile.mkdtemp(prefix="pp_run_")
    try:
        safe_cases = [{"fn": c["fn"], "args": copy.deepcopy(c.get("args") or []), "kwargs": copy.deepcopy(c.get("kwargs") or {}),
                       "fixture": c.get("fixture")} for c in cases]
        spec = {"cases": safe_cases, "allowed_modules": sorted(ALLOWED_MODULES), "per_case": per_case,
                "result_limit": RESULT_CHAR_LIMIT}
        with open(os.path.join(work, "spec.json"), "w", encoding="utf-8") as fh:
            json.dump(spec, fh)
        with open(os.path.join(work, "submission.py"), "w", encoding="utf-8") as fh:
            fh.write(source)
        with open(os.path.join(work, "harness.py"), "w", encoding="utf-8") as fh:
            fh.write(_HARNESS)
        kwargs = {"start_new_session": True} if os.name != "nt" else {}
        try:
            subprocess.run([sys.executable, "-I", "-B", "-S", os.path.join(work, "harness.py"), work], cwd=work,
                           env=_child_env(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=overall_timeout, **kwargs)
        except subprocess.TimeoutExpired:
            return [{"ok": False, "error": "Timed out (the whole run took too long)."} for _ in cases]
        try:
            with open(os.path.join(work, "results.json"), encoding="utf-8") as fh:
                results = json.load(fh)
        except (OSError, ValueError):
            return [{"ok": False, "error": "Your code crashed the runner (out of memory, or a fatal error)."} for _ in cases]
        while len(results) < len(cases):
            results.append({"ok": False, "error": "No result (the run stopped early)."})
        return results[:len(cases)]
    finally:
        shutil.rmtree(work, ignore_errors=True)
        _slots.release()
