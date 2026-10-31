"""The code runner: hostile and broken submissions must be contained, honest ones must run."""
import os
import unittest

from skillztrack import config, sandbox


class ScreenTests(unittest.TestCase):
    def test_honest_code_passes_the_screen(self):
        ok = "import math\nfrom collections import Counter\nclass A:\n    def __init__(self):\n        self.x = 1\ndef f(n):\n    return [i * i for i in range(n)]\n"
        self.assertIsNone(sandbox.screen_source(ok))

    def test_dangerous_code_is_rejected_before_it_runs(self):
        attacks = {
            "import os": "import os\n",
            "import subprocess": "import subprocess\n",
            "from import": "from os import path\n",
            "socket": "import socket\n",
            "open": "def f():\n    return open('/etc/passwd').read()\n",
            "eval": "def f():\n    return eval('1+1')\n",
            "exec": "exec('x=1')\n",
            "__import__": "m = __import__('os')\n",
            "getattr": "def f():\n    return getattr(1, 'real')\n",
            "dunder class": "def f():\n    return ().__class__.__bases__\n",
            "subclasses": "def f():\n    return object.__subclasses__()\n",
            "globals": "def f():\n    return globals()\n",
            "builtins": "def f():\n    return __builtins__\n",
            "generator frame": "def f():\n    g = (i for i in [1])\n    return g.gi_frame\n",
            "format_map": "def f(o):\n    return '{a.__class__}'.format_map(o)\n",
            "relative import": "from . import x\n",
        }
        for name, code in attacks.items():
            self.assertIsNotNone(sandbox.screen_source(code), name)

    def test_syntax_errors_are_explained_with_a_line_number(self):
        msg = sandbox.screen_source("def f(:\n    pass\n")
        self.assertIn("Syntax error", msg)
        self.assertIn("line 1", msg)

    def test_empty_and_huge_submissions_are_rejected(self):
        self.assertIsNotNone(sandbox.screen_source("   \n"))
        self.assertIsNotNone(sandbox.screen_source("x = 1\n" * 10000))


class RunTests(unittest.TestCase):
    def run_one(self, code, fn="f", args=(), **kw):
        return sandbox.run_cases(code, [{"fn": fn, "args": list(args)}], **kw)[0]

    def test_returns_values_as_json(self):
        r = self.run_one("def f(a, b):\n    return {'sum': a + b, 'items': {3, 1, 2}}\n", args=(2, 3))
        self.assertEqual(r, {"ok": True, "value": {"sum": 5, "items": [1, 2, 3]}})

    def test_runtime_errors_are_reported_not_raised(self):
        r = self.run_one("def f():\n    return 1 / 0\n")
        self.assertFalse(r["ok"])
        self.assertIn("ZeroDivisionError", r["error"])
        self.assertIn("ArithmeticError", r["mro"])

    def test_each_case_is_isolated(self):
        out = sandbox.run_cases("def a():\n    return 1\ndef b():\n    raise ValueError('x')\ndef c():\n    return 3\n",
                                [{"fn": "a"}, {"fn": "b"}, {"fn": "c"}, {"fn": "missing"}])
        self.assertEqual([o["ok"] for o in out], [True, False, True, False])
        self.assertIn("not defined", out[3]["error"])

    def test_infinite_loop_times_out_without_hanging_the_server(self):
        out = sandbox.run_cases("def spin():\n    while True:\n        pass\ndef ok():\n    return 7\n",
                                [{"fn": "spin"}, {"fn": "ok"}], per_case=1.0)
        self.assertIn("Timed out", out[0]["error"])
        self.assertEqual(out[1], {"ok": True, "value": 7})     # later tests still run

    def test_memory_bomb_is_contained(self):
        r = self.run_one("def f():\n    return [0] * (10 ** 10)\n")
        self.assertFalse(r["ok"])

    def test_deep_recursion_is_contained(self):
        r = self.run_one("def f():\n    return f()\n")
        self.assertFalse(r["ok"])

    def test_print_cannot_corrupt_results(self):
        r = self.run_one("def f():\n    print('{\"ok\": true, \"value\": 999}')\n    return 1\n")
        self.assertEqual(r["value"], 1)

    def test_errors_at_import_time_fail_every_case(self):
        out = sandbox.run_cases("raise RuntimeError('boom')\ndef f():\n    return 1\n", [{"fn": "f"}, {"fn": "f"}])
        self.assertTrue(all(not o["ok"] and "failed while loading" in o["error"] for o in out))

    def test_the_child_process_never_sees_expected_answers(self):
        # run_cases takes no expected values at all: the signature itself guarantees this
        import inspect
        self.assertNotIn("expected", inspect.signature(sandbox.run_cases).parameters)

    def test_runs_in_a_clean_temporary_directory_and_leaves_nothing_behind(self):
        import glob, tempfile
        before = set(glob.glob(os.path.join(tempfile.gettempdir(), "pp_run_*")))
        self.run_one("def f():\n    return 1\n")
        self.assertEqual(set(glob.glob(os.path.join(tempfile.gettempdir(), "pp_run_*"))), before)

    def test_environment_secrets_are_not_visible(self):
        env = sandbox._child_env()
        os.environ["SKILLZTRACK_TEST_SECRET"] = "hunter2"
        try:
            self.assertNotIn("SKILLZTRACK_TEST_SECRET", sandbox._child_env())
            self.assertNotIn("hunter2", str(env))
        finally:
            del os.environ["SKILLZTRACK_TEST_SECRET"]

    def test_can_be_switched_off(self):
        old = config.CODE_EXEC
        config.CODE_EXEC = False
        try:
            with self.assertRaises(sandbox.SandboxUnavailable):
                self.run_one("def f():\n    return 1\n")
        finally:
            config.CODE_EXEC = old

    def test_users_db_fixture_denies_attach_and_pragma(self):
        code = "def f(conn):\n    conn.execute(\"ATTACH DATABASE 'x.db' AS x\")\n    return 1\n"
        r = sandbox.run_cases(code, [{"fn": "f", "fixture": "users_db"}])[0]
        self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
