"""Coding challenges: students write functions; hidden tests run in the sandbox.

Hidden tests are NOT shown. Tests with visible=True reveal input/expected/got on failure so the student can debug.
"""
from . import Assignment, T


def code(slug, skill, title, summary, ceiling, minutes, instructions, starter, tests, reference, **spec_extra):
    return Assignment(slug=slug, skill=skill, kind="code", title=title, summary=summary, ceiling=ceiling, minutes=minutes,
                      instructions=instructions, starter=starter, spec={"tests": tests, **spec_extra}, reference=reference)


INTRO = ("Write the functions described in the starter code. Your code runs against hidden tests in a restricted sandbox "
         "(allowed modules: math, re, json, collections, itertools, functools, heapq, bisect, datetime, ipaddress, hashlib, hmac, "
         "html, base64, csv, random, decimal, fractions and a few others; no file or network access). Print statements are ignored. "
         "Edge cases count, and so does speed: slow solutions time out.")

# ----------------------------------------------------------------------------------------------- python
PY_BASICS_STARTER = '''import re


def word_counts(text):
    """Return a dict mapping each lowercase word in `text` to how many times it appears.
    A word is a run of letters or apostrophes (so "don't" is ONE word). Ignore everything else."""
    pass


def is_palindrome(s):
    """True if `s` reads the same forwards and backwards, ignoring case and any non-alphanumeric characters."""
    pass


def fizzbuzz(n):
    """Return a list of strings for 1..n: 'Fizz' for multiples of 3, 'Buzz' for multiples of 5,
    'FizzBuzz' for multiples of both, otherwise the number as a string. fizzbuzz(0) is []."""
    pass


def chunk(items, size):
    """Split the list `items` into consecutive lists of length `size` (the last one may be shorter).
    Raise ValueError if size is less than 1."""
    pass
'''
PY_BASICS_REF = '''import re

def word_counts(text):
    counts = {}
    for w in re.findall(r"[a-z']+", text.lower()):
        counts[w] = counts.get(w, 0) + 1
    return counts

def is_palindrome(s):
    cleaned = [c.lower() for c in s if c.isalnum()]
    return cleaned == cleaned[::-1]

def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        out.append("FizzBuzz" if i % 15 == 0 else "Fizz" if i % 3 == 0 else "Buzz" if i % 5 == 0 else str(i))
    return out

def chunk(items, size):
    if size < 1:
        raise ValueError("size must be at least 1")
    return [items[i:i + size] for i in range(0, len(items), size)]
'''
FB15 = ["1", "2", "Fizz", "4", "Buzz", "Fizz", "7", "8", "Fizz", "Buzz", "11", "Fizz", "13", "14", "FizzBuzz"]

PY_ORDERS_STARTER = '''def parse_orders(lines):
    """`lines` are CSV text lines: order_id,customer,amount,status  (the first line may be a header).
    Return a list of dicts {"id": int, "customer": str, "amount": float, "status": str} in input order.
    Skip: the header, blank lines, rows without exactly 4 columns, rows whose id is not an integer,
    and rows whose amount is not a number or is negative. Trim spaces around values; lowercase the status."""
    pass


def revenue_by_customer(orders):
    """Total `amount` of PAID orders (status == "paid") per customer, as a dict.
    Customers with no paid orders are left out."""
    pass


def top_customers(orders, n):
    """The n customers with the highest paid revenue, as a list of [customer, total] pairs,
    highest first; break ties by customer name A-Z. n larger than the number of customers returns all of them."""
    pass


def summarize(orders):
    """Return {"count": all orders, "paid_count": paid orders, "total_paid": sum of paid amounts rounded to 2 decimals,
    "average_paid": mean paid amount rounded to 2 decimals (0.0 if none), "largest_paid_id": id of the paid order
    with the biggest amount, or None if there are none}."""
    pass
'''
PY_ORDERS_REF = '''def parse_orders(lines):
    orders = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 4:
            continue
        try:
            oid = int(parts[0])
            amount = float(parts[2])
        except ValueError:
            continue
        if amount < 0:
            continue
        orders.append({"id": oid, "customer": parts[1], "amount": amount, "status": parts[3].lower()})
    return orders

def _paid(orders):
    return [o for o in orders if o["status"] == "paid"]

def revenue_by_customer(orders):
    totals = {}
    for o in _paid(orders):
        totals[o["customer"]] = totals.get(o["customer"], 0) + o["amount"]
    return totals

def top_customers(orders, n):
    ranked = sorted(revenue_by_customer(orders).items(), key=lambda kv: (-kv[1], kv[0]))
    return [[c, t] for c, t in ranked[:max(0, n)]]

def summarize(orders):
    paid = _paid(orders)
    total = sum(o["amount"] for o in paid)
    return {"count": len(orders), "paid_count": len(paid), "total_paid": round(total, 2),
            "average_paid": round(total / len(paid), 2) if paid else 0.0,
            "largest_paid_id": max(paid, key=lambda o: o["amount"])["id"] if paid else None}
'''
ORD = [{"id": 1, "customer": "Asha", "amount": 250.5, "status": "paid"}, {"id": 2, "customer": "Ravi", "amount": 100.0, "status": "pending"},
       {"id": 3, "customer": "Asha", "amount": 40.0, "status": "paid"}, {"id": 4, "customer": "Meena", "amount": 290.5, "status": "paid"},
       {"id": 5, "customer": "Ravi", "amount": 60.0, "status": "paid"}, {"id": 6, "customer": "Meena", "amount": 10.0, "status": "cancelled"}]
LINES = ["order_id,customer,amount,status", "1,Asha,250.50,PAID", "2, Ravi ,100,pending", "", "3,Asha,abc,paid",
         "4,Meena,75,paid,extra", "x,Ravi,10,paid", "5,Meena,-5,paid", "6,Asha,40,Paid"]

PY_EVAL_STARTER = '''def evaluate(expression):
    """Evaluate an arithmetic expression string WITHOUT using eval().
    Support + - * / , parentheses, unary minus, integers and decimals, spaces, and normal precedence
    (* and / before + and -, left to right). Return a number.
    Raise ValueError for anything malformed ("2 +", "(1", "abc", "", "2 3", "()").
    Division by zero should raise ZeroDivisionError."""
    pass


def rle_decode(encoded):
    """Run-length decode: '3a1b2c' -> 'aaabcc'. Counts can have several digits ('12x' is twelve x's).
    Raise ValueError if a letter has no count in front of it or the string ends with a count. '' decodes to ''."""
    pass


def longest_unique_substring(s):
    """Length of the longest substring of `s` that has no repeated characters.
    Must stay fast for strings of 100,000 characters."""
    pass
'''
PY_EVAL_REF = '''def evaluate(expression):
    tokens = []
    s = expression
    i = 0
    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
        elif c in "+-*/()":
            tokens.append(c)
            i += 1
        elif c.isdigit() or c == ".":
            j = i
            while j < len(s) and (s[j].isdigit() or s[j] == "."):
                j += 1
            try:
                tokens.append(float(s[i:j]))
            except ValueError:
                raise ValueError("bad number")
            i = j
        else:
            raise ValueError("unexpected character")
    if not tokens:
        raise ValueError("empty")
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def expr():
        v = term()
        while peek() in ("+", "-"):
            op = take()
            r = term()
            v = v + r if op == "+" else v - r
        return v

    def term():
        v = factor()
        while peek() in ("*", "/"):
            op = take()
            r = factor()
            v = v * r if op == "*" else v / r
        return v

    def factor():
        t = take()
        if t == "-":
            return -factor()
        if t == "(":
            v = expr()
            if take() != ")":
                raise ValueError("missing )")
            return v
        if isinstance(t, float):
            return t
        raise ValueError("unexpected token")

    value = expr()
    if pos[0] != len(tokens):
        raise ValueError("trailing tokens")
    return value

def rle_decode(encoded):
    out, num = [], ""
    for ch in encoded:
        if ch.isdigit():
            num += ch
        else:
            if not num:
                raise ValueError("count missing")
            out.append(ch * int(num))
            num = ""
    if num:
        raise ValueError("dangling count")
    return "".join(out)

def longest_unique_substring(s):
    last, start, best = {}, 0, 0
    for i, ch in enumerate(s):
        if ch in last and last[ch] >= start:
            start = last[ch] + 1
        last[ch] = i
        best = max(best, i - start + 1)
    return best
'''

# --------------------------------------------------------------------------------------------------- dsa
DSA_CORE_STARTER = '''def two_sum(nums, target):
    """Return [i, j] with i < j such that nums[i] + nums[j] == target, or None if there is no such pair.
    (Tests only use inputs with at most one valid pair.) Must handle 20,000 numbers quickly."""
    pass


def is_valid_parentheses(s):
    """True if every (, [, { in `s` is closed by the matching bracket in the right order. '' is valid."""
    pass


def binary_search(sorted_list, target):
    """Return the index of `target` in `sorted_list` (ascending, no duplicates) or -1 if it is absent."""
    pass


def merge_sorted(a, b):
    """Merge two ascending lists into one ascending list (keep duplicates)."""
    pass
'''
DSA_CORE_REF = '''def two_sum(nums, target):
    seen = {}
    for j, x in enumerate(nums):
        if target - x in seen:
            return [seen[target - x], j]
        seen[x] = j
    return None

def is_valid_parentheses(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack

def binary_search(sorted_list, target):
    lo, hi = 0, len(sorted_list) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if sorted_list[mid] == target:
            return mid
        if sorted_list[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1

def merge_sorted(a, b):
    out, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            out.append(a[i]); i += 1
        else:
            out.append(b[j]); j += 1
    return out + a[i:] + b[j:]
'''

DSA_ADV_STARTER = '''def merge_intervals(intervals):
    """Merge overlapping or touching [start, end] intervals (input may be unsorted).
    [[1,3],[2,6],[8,10]] -> [[1,6],[8,10]];  [[1,4],[4,5]] -> [[1,5]].  Return a sorted list."""
    pass


def top_k_frequent(words, k):
    """The k most frequent words, most frequent first; break ties alphabetically. If k is larger than the
    number of distinct words return them all. k = 0 returns []."""
    pass


def shortest_path(grid, start, end):
    """`grid` is a list of rows of 0 (free) / 1 (wall). Move up/down/left/right. `start` and `end` are [row, col].
    Return the minimum number of steps, or -1 if unreachable or if start/end is a wall. Must handle a 100x100 grid."""
    pass


def min_coins(coins, amount):
    """Fewest coins (unlimited supply of each value) that add up to `amount`, or -1 if impossible.
    min_coins([1,3,4], 6) is 2 (3+3), so a greedy approach is not enough. amount 0 needs 0 coins."""
    pass
'''
DSA_ADV_REF = '''from collections import Counter, deque

def merge_intervals(intervals):
    out = []
    for s, e in sorted(intervals):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out

def top_k_frequent(words, k):
    counts = Counter(words)
    ranked = sorted(counts, key=lambda w: (-counts[w], w))
    return ranked[:max(0, k)]

def shortest_path(grid, start, end):
    rows, cols = len(grid), len(grid[0]) if grid else 0
    sr, sc = start
    er, ec = end
    if not (0 <= sr < rows and 0 <= sc < cols and 0 <= er < rows and 0 <= ec < cols):
        return -1
    if grid[sr][sc] == 1 or grid[er][ec] == 1:
        return -1
    seen = {(sr, sc)}
    queue = deque([(sr, sc, 0)])
    while queue:
        r, c, d = queue.popleft()
        if (r, c) == (er, ec):
            return d
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0 and (nr, nc) not in seen:
                seen.add((nr, nc))
                queue.append((nr, nc, d + 1))
    return -1

def min_coins(coins, amount):
    INF = amount + 1
    dp = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a and dp[a - c] + 1 < dp[a]:
                dp[a] = dp[a - c] + 1
    return dp[amount] if dp[amount] != INF else -1
'''

# ---------------------------------------------------------------------------------------------- rest
REST_STARTER = '''def status_for(kind):
    """Map an outcome name to the right HTTP status code:
    ok 200, created 201, no_content 204, bad_request 400, unauthenticated 401, forbidden 403,
    not_found 404, conflict 409, validation 422, rate_limited 429, server_error 500. Unknown names -> 500."""
    pass


def paginate(items, page, per_page):
    """Return {"data": [...items on this page...],
               "meta": {"page", "per_page", "total", "total_pages"},
               "has_next": bool}.
    Pages start at 1: a page below 1 is treated as 1. per_page is clamped to the range 1..100.
    A page beyond the last returns empty data (keep the requested page number). total_pages is
    ceil(total / per_page), and 0 when there are no items."""
    pass


def validate_payload(payload, schema):
    """Validate a JSON body (dict) against `schema`, a dict like
    {"name": {"type": "str", "required": True, "min_len": 2, "max_len": 10},
     "age": {"type": "int", "min": 0, "max": 120}, "active": {"type": "bool"}}.
    Return a dict {field: code} with at most ONE code per field:
      "required"   missing or None and the field is required (a missing optional field is fine)
      "type"       wrong type (note: True/False are NOT valid ints)
      "too_short" / "too_long"    for str length, "too_small" / "too_large"    for int bounds
      "unknown"    a key in the payload that is not in the schema
    An empty dict means the payload is valid."""
    pass


def parse_bearer(header):
    """Extract the token from an Authorization header value like 'Bearer abc123'.
    The scheme is case-insensitive. Return None for None, '', other schemes (Basic ...),
    a missing token, or more than two parts."""
    pass
'''
REST_REF = '''import math

STATUS = {"ok": 200, "created": 201, "no_content": 204, "bad_request": 400, "unauthenticated": 401, "forbidden": 403,
          "not_found": 404, "conflict": 409, "validation": 422, "rate_limited": 429, "server_error": 500}

def status_for(kind):
    return STATUS.get(kind, 500)

def paginate(items, page, per_page):
    per_page = max(1, min(100, per_page))
    page = max(1, page)
    total = len(items)
    pages = math.ceil(total / per_page)
    start = (page - 1) * per_page
    return {"data": items[start:start + per_page],
            "meta": {"page": page, "per_page": per_page, "total": total, "total_pages": pages},
            "has_next": page < pages}

def validate_payload(payload, schema):
    errors = {}
    for field, rule in schema.items():
        value = payload.get(field)
        if value is None:
            if rule.get("required"):
                errors[field] = "required"
            continue
        kind = rule["type"]
        ok = (isinstance(value, str) if kind == "str" else isinstance(value, bool) if kind == "bool"
              else isinstance(value, int) and not isinstance(value, bool))
        if not ok:
            errors[field] = "type"
        elif kind == "str":
            if "min_len" in rule and len(value) < rule["min_len"]:
                errors[field] = "too_short"
            elif "max_len" in rule and len(value) > rule["max_len"]:
                errors[field] = "too_long"
        elif kind == "int":
            if "min" in rule and value < rule["min"]:
                errors[field] = "too_small"
            elif "max" in rule and value > rule["max"]:
                errors[field] = "too_large"
    for key in payload:
        if key not in schema:
            errors[key] = "unknown"
    return errors

def parse_bearer(header):
    if not header:
        return None
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]
'''
SCHEMA = {"name": {"type": "str", "required": True, "min_len": 2, "max_len": 10},
          "age": {"type": "int", "min": 0, "max": 120}, "active": {"type": "bool"}}

ASSIGNMENTS = [
    code("python-basics", "python", "Python warm-up: text, loops and lists", "Four small functions that test core Python.", 3, 20,
         INTRO, PY_BASICS_STARTER, [
        T("word_counts", ["The cat and the hat"], {"the": 2, "cat": 1, "and": 1, "hat": 1}, "word_counts counts repeated words", "dictionaries", visible=True),
        T("word_counts", ["Hello, hello! HELLO?"], {"hello": 3}, "word_counts ignores case and punctuation", "strings"),
        T("word_counts", [""], {}, "word_counts handles empty text", "edge cases"),
        T("word_counts", ["don't stop; don't"], {"don't": 2, "stop": 1}, "word_counts keeps apostrophes", "strings"),
        T("is_palindrome", ["A man, a plan, a canal: Panama"], True, "is_palindrome ignores punctuation and case", "strings", visible=True),
        T("is_palindrome", ["hello"], False, "is_palindrome rejects non-palindromes", "strings"),
        T("is_palindrome", [""], True, "is_palindrome of empty text", "edge cases"),
        T("is_palindrome", ["No 'x' in Nixon"], True, "is_palindrome with quotes", "strings"),
        T("is_palindrome", ["ab"], False, "is_palindrome of two different characters", "edge cases"),
        T("fizzbuzz", [5], ["1", "2", "Fizz", "4", "Buzz"], "fizzbuzz(5)", "control flow", visible=True),
        T("fizzbuzz", [15], FB15, "fizzbuzz(15) includes FizzBuzz", "control flow"),
        T("fizzbuzz", [0], [], "fizzbuzz(0) is empty", "edge cases"),
        T("chunk", [[1, 2, 3, 4, 5], 2], [[1, 2], [3, 4], [5]], "chunk leaves a shorter last piece", "lists", visible=True),
        T("chunk", [[], 3], [], "chunk of an empty list", "edge cases"),
        T("chunk", [[1, 2, 3], 5], [[1, 2, 3]], "chunk size larger than the list", "lists"),
        T("chunk", [[1, 2, 3], 0], label="chunk rejects size 0", topic="error handling", raises="ValueError"),
    ], PY_BASICS_REF),

    code("python-orders", "python", "Python data processing: order report", "Parse messy CSV lines and summarise orders.", 4, 35,
         INTRO, PY_ORDERS_STARTER, [
        T("parse_orders", [LINES], [{"id": 1, "customer": "Asha", "amount": 250.5, "status": "paid"},
                                    {"id": 2, "customer": "Ravi", "amount": 100.0, "status": "pending"},
                                    {"id": 6, "customer": "Asha", "amount": 40.0, "status": "paid"}],
          "parse_orders skips bad rows and normalises values", "parsing", weight=3, visible=True),
        T("parse_orders", [[]], [], "parse_orders of no lines", "edge cases"),
        T("parse_orders", [["7,Zed,0,paid"]], [{"id": 7, "customer": "Zed", "amount": 0.0, "status": "paid"}], "zero amounts are valid", "parsing"),
        T("revenue_by_customer", [ORD], {"Asha": 290.5, "Meena": 290.5, "Ravi": 60.0}, "revenue counts only paid orders", "aggregation", weight=2, visible=True, cmp="approx"),
        T("revenue_by_customer", [[]], {}, "revenue of no orders", "edge cases"),
        T("revenue_by_customer", [[ORD[1], ORD[5]]], {}, "customers without paid orders are omitted", "aggregation"),
        T("top_customers", [ORD, 2], [["Asha", 290.5], ["Meena", 290.5]], "top_customers breaks ties by name", "sorting", weight=2, cmp="approx"),
        T("top_customers", [ORD, 1], [["Asha", 290.5]], "top_customers n=1", "sorting", cmp="approx"),
        T("top_customers", [ORD, 10], [["Asha", 290.5], ["Meena", 290.5], ["Ravi", 60.0]], "top_customers with n above customer count", "edge cases", cmp="approx"),
        T("top_customers", [ORD, 0], [], "top_customers n=0", "edge cases"),
        T("summarize", [ORD], {"count": 6, "paid_count": 4, "total_paid": 641.0, "average_paid": 160.25, "largest_paid_id": 4},
          "summarize full example", "aggregation", weight=2, cmp="approx"),
        T("summarize", [[]], {"count": 0, "paid_count": 0, "total_paid": 0.0, "average_paid": 0.0, "largest_paid_id": None}, "summarize with no orders", "edge cases", cmp="approx"),
        T("summarize", [[{"id": 9, "customer": "A", "amount": 0.1, "status": "paid"}, {"id": 10, "customer": "A", "amount": 0.2, "status": "paid"}]],
          {"count": 2, "paid_count": 2, "total_paid": 0.3, "average_paid": 0.15, "largest_paid_id": 10}, "summarize rounds floating point sums", "numbers", cmp="approx"),
    ], PY_ORDERS_REF),

    code("python-challenge", "python", "Python challenge: parser, decoder and sliding window", "Harder problems: an expression evaluator, run-length decoding and an O(n) algorithm.", 5, 45,
         INTRO, PY_EVAL_STARTER, [
        T("evaluate", ["2+3*4"], 14, "precedence: * before +", "parsing", visible=True, cmp="approx"),
        T("evaluate", ["(2+3)*4"], 20, "parentheses", "parsing", cmp="approx"),
        T("evaluate", ["-3 + 5"], 2, "unary minus and spaces", "parsing", cmp="approx"),
        T("evaluate", ["10/4"], 2.5, "true division", "parsing", cmp="approx"),
        T("evaluate", ["2*(3+(4-1))"], 12, "nested parentheses", "parsing", cmp="approx"),
        T("evaluate", ["8/2/2"], 2, "division is left-associative", "parsing", cmp="approx"),
        T("evaluate", ["2-3-4"], -5, "subtraction is left-associative", "parsing", cmp="approx"),
        T("evaluate", ["3 * -2"], -6, "unary minus after an operator", "parsing", cmp="approx"),
        T("evaluate", ["1.5*4"], 6, "decimals", "parsing", cmp="approx"),
        T("evaluate", ["2 +"], label="evaluate rejects a dangling operator", topic="error handling", raises="ValueError"),
        T("evaluate", ["(1"], label="evaluate rejects an unclosed parenthesis", topic="error handling", raises="ValueError"),
        T("evaluate", ["abc"], label="evaluate rejects letters", topic="error handling", raises="ValueError"),
        T("evaluate", [""], label="evaluate rejects empty input", topic="error handling", raises="ValueError"),
        T("evaluate", ["2 3"], label="evaluate rejects two numbers in a row", topic="error handling", raises="ValueError"),
        T("evaluate", ["()"], label="evaluate rejects empty parentheses", topic="error handling", raises="ValueError"),
        T("evaluate", ["10/(5-5)"], label="evaluate raises ZeroDivisionError", topic="error handling", raises="ZeroDivisionError"),
        T("rle_decode", ["3a1b2c"], "aaabcc", "rle_decode basic", "strings", visible=True),
        T("rle_decode", ["12x"], "x" * 12, "rle_decode multi-digit counts", "strings"),
        T("rle_decode", [""], "", "rle_decode empty", "edge cases"),
        T("rle_decode", ["2a2a"], "aaaa", "rle_decode repeated letters", "strings"),
        T("rle_decode", ["a"], label="rle_decode rejects a letter without a count", topic="error handling", raises="ValueError"),
        T("rle_decode", ["3"], label="rle_decode rejects a trailing count", topic="error handling", raises="ValueError"),
        T("longest_unique_substring", ["abcabcbb"], 3, "longest_unique_substring classic", "algorithms", visible=True),
        T("longest_unique_substring", ["bbbbb"], 1, "all the same character", "edge cases"),
        T("longest_unique_substring", ["pwwkew"], 3, "window must not include repeats", "algorithms"),
        T("longest_unique_substring", ["dvdf"], 3, "restarting the window correctly", "algorithms"),
        T("longest_unique_substring", [""], 0, "empty string", "edge cases"),
        T("longest_unique_substring", ["ab" * 50000], 2, "100,000 characters stays fast", "performance", weight=2),
    ], PY_EVAL_REF),

    code("dsa-core", "dsa", "Algorithms: lookups, stacks and merging", "Classic interview-style problems with a speed requirement.", 3, 30,
         INTRO, DSA_CORE_STARTER, [
        T("two_sum", [[2, 7, 11, 15], 9], [0, 1], "two_sum basic", "hash maps", visible=True),
        T("two_sum", [[3, 2, 4], 6], [1, 2], "two_sum not using the same element twice", "hash maps"),
        T("two_sum", [[3, 3], 6], [0, 1], "two_sum with duplicates", "hash maps"),
        T("two_sum", [[-1, -2, -3, -4, -5], -8], [2, 4], "two_sum with negatives", "hash maps"),
        T("two_sum", [[1, 2, 3], 10], None, "two_sum with no answer", "edge cases"),
        T("two_sum", [[5], 5], None, "two_sum with one element", "edge cases"),
        T("two_sum", [list(range(20000)), 39997], [19998, 19999], "two_sum on 20,000 numbers stays fast", "performance", weight=2),
        T("is_valid_parentheses", ["()[]{}"], True, "valid mixed brackets", "stacks", visible=True),
        T("is_valid_parentheses", ["([)]"], False, "interleaved brackets", "stacks"),
        T("is_valid_parentheses", ["{[]}"], True, "nested brackets", "stacks"),
        T("is_valid_parentheses", [""], True, "empty string", "edge cases"),
        T("is_valid_parentheses", ["("], False, "unclosed bracket", "edge cases"),
        T("is_valid_parentheses", [")"], False, "closing bracket first", "edge cases"),
        T("is_valid_parentheses", ["(" * 50000 + ")" * 50000], True, "deeply nested input", "performance"),
        T("binary_search", [[1, 3, 5, 7, 9], 7], 3, "binary_search finds a middle item", "searching", visible=True),
        T("binary_search", [[1, 3, 5, 7, 9], 1], 0, "binary_search first item", "searching"),
        T("binary_search", [[1, 3, 5, 7, 9], 9], 4, "binary_search last item", "searching"),
        T("binary_search", [[1, 3, 5, 7, 9], 4], -1, "binary_search missing item", "searching"),
        T("binary_search", [[], 1], -1, "binary_search empty list", "edge cases"),
        T("binary_search", [[4], 4], 0, "binary_search single element", "edge cases"),
        T("binary_search", [list(range(0, 100000, 2)), 99998], 49999, "binary_search on 50,000 items", "searching"),
        T("merge_sorted", [[1, 3, 5], [2, 4, 6]], [1, 2, 3, 4, 5, 6], "merge_sorted interleaved", "merging", visible=True),
        T("merge_sorted", [[], []], [], "merge_sorted both empty", "edge cases"),
        T("merge_sorted", [[1], []], [1], "merge_sorted one empty", "edge cases"),
        T("merge_sorted", [[1, 1, 2], [1, 3]], [1, 1, 1, 2, 3], "merge_sorted keeps duplicates", "merging"),
        T("merge_sorted", [[-5, 0], [-3, 2]], [-5, -3, 0, 2], "merge_sorted with negatives", "merging"),
    ], DSA_CORE_REF),

    code("dsa-advanced", "dsa", "Algorithms: intervals, BFS and dynamic programming", "Harder problems where the obvious solution is too slow or wrong.", 5, 45,
         INTRO, DSA_ADV_STARTER, [
        T("merge_intervals", [[[1, 3], [2, 6], [8, 10], [15, 18]]], [[1, 6], [8, 10], [15, 18]], "merge_intervals basic", "intervals", visible=True),
        T("merge_intervals", [[[1, 4], [4, 5]]], [[1, 5]], "touching intervals merge", "intervals"),
        T("merge_intervals", [[[8, 10], [1, 3], [2, 6]]], [[1, 6], [8, 10]], "unsorted input", "intervals"),
        T("merge_intervals", [[[1, 10], [2, 3]]], [[1, 10]], "contained interval", "intervals"),
        T("merge_intervals", [[]], [], "no intervals", "edge cases"),
        T("top_k_frequent", [["a", "b", "a", "c", "b", "a"], 2], ["a", "b"], "top_k_frequent basic", "hash maps", visible=True),
        T("top_k_frequent", [["x", "y", "z", "y", "z"], 2], ["y", "z"], "ties broken alphabetically", "sorting"),
        T("top_k_frequent", [["a", "b"], 5], ["a", "b"], "k above distinct count", "edge cases"),
        T("top_k_frequent", [["a"], 0], [], "k = 0", "edge cases"),
        T("shortest_path", [[[0, 0, 0], [0, 0, 0], [0, 0, 0]], [0, 0], [2, 2]], 4, "open 3x3 grid", "graphs", visible=True),
        T("shortest_path", [[[0, 0, 0], [1, 1, 0], [0, 0, 0]], [0, 0], [2, 0]], 6, "path around a wall", "graphs"),
        T("shortest_path", [[[0, 1], [1, 0]], [0, 0], [1, 1]], -1, "unreachable target", "graphs"),
        T("shortest_path", [[[0]], [0, 0], [0, 0]], 0, "start equals end", "edge cases"),
        T("shortest_path", [[[0, 1]], [0, 0], [0, 1]], -1, "end is a wall", "edge cases"),
        T("shortest_path", [[[0] * 100 for _ in range(100)], [0, 0], [99, 99]], 198, "100x100 grid stays fast (use a visited set)", "performance", weight=2),
        T("min_coins", [[1, 2, 5], 11], 3, "min_coins basic", "dynamic programming", visible=True),
        T("min_coins", [[2], 3], -1, "impossible amount", "dynamic programming"),
        T("min_coins", [[1], 0], 0, "amount 0", "edge cases"),
        T("min_coins", [[1, 3, 4], 6], 2, "greedy fails here", "dynamic programming", weight=2),
        T("min_coins", [[186, 419, 83, 408], 6249], 20, "larger amount", "performance", weight=2),
        T("min_coins", [[1, 5, 10, 25], 63], 6, "US coins", "dynamic programming"),
    ], DSA_ADV_REF),

    code("rest-helpers", "rest-apis", "REST API helpers: status codes, pagination, validation", "Pure functions that every API needs.", 4, 30,
         INTRO, REST_STARTER, [
        T("status_for", ["created"], 201, "created -> 201", "status codes", visible=True),
        T("status_for", ["not_found"], 404, "not_found -> 404", "status codes"),
        T("status_for", ["unauthenticated"], 401, "unauthenticated -> 401", "status codes"),
        T("status_for", ["forbidden"], 403, "forbidden -> 403", "status codes"),
        T("status_for", ["validation"], 422, "validation -> 422", "status codes"),
        T("status_for", ["conflict"], 409, "conflict -> 409", "status codes"),
        T("status_for", ["no_content"], 204, "no_content -> 204", "status codes"),
        T("status_for", ["rate_limited"], 429, "rate_limited -> 429", "status codes"),
        T("status_for", ["teapot"], 500, "unknown outcome -> 500", "status codes"),
        T("paginate", [list(range(1, 26)), 2, 10], {"data": list(range(11, 21)), "meta": {"page": 2, "per_page": 10, "total": 25, "total_pages": 3}, "has_next": True},
          "paginate middle page", "pagination", visible=True, weight=2),
        T("paginate", [list(range(1, 26)), 3, 10], {"data": [21, 22, 23, 24, 25], "meta": {"page": 3, "per_page": 10, "total": 25, "total_pages": 3}, "has_next": False}, "paginate last page", "pagination"),
        T("paginate", [list(range(1, 26)), 4, 10], {"data": [], "meta": {"page": 4, "per_page": 10, "total": 25, "total_pages": 3}, "has_next": False}, "paginate beyond the end", "pagination"),
        T("paginate", [list(range(1, 6)), 0, 2], {"data": [1, 2], "meta": {"page": 1, "per_page": 2, "total": 5, "total_pages": 3}, "has_next": True}, "page below 1 becomes 1", "pagination"),
        T("paginate", [list(range(1, 6)), 1, 500], {"data": [1, 2, 3, 4, 5], "meta": {"page": 1, "per_page": 100, "total": 5, "total_pages": 1}, "has_next": False}, "per_page is capped at 100", "pagination"),
        T("paginate", [[], 1, 10], {"data": [], "meta": {"page": 1, "per_page": 10, "total": 0, "total_pages": 0}, "has_next": False}, "paginate an empty list", "pagination"),
        T("validate_payload", [{"name": "Asha", "age": 30, "active": True}, SCHEMA], {}, "valid payload", "validation", visible=True),
        T("validate_payload", [{"age": 30}, SCHEMA], {"name": "required"}, "required field missing", "validation"),
        T("validate_payload", [{"name": "A"}, SCHEMA], {"name": "too_short"}, "string too short", "validation"),
        T("validate_payload", [{"name": "Abcdefghijk"}, SCHEMA], {"name": "too_long"}, "string too long", "validation"),
        T("validate_payload", [{"name": "Asha", "age": -1}, SCHEMA], {"age": "too_small"}, "int below minimum", "validation"),
        T("validate_payload", [{"name": "Asha", "age": 121}, SCHEMA], {"age": "too_large"}, "int above maximum", "validation"),
        T("validate_payload", [{"name": "Asha", "age": True}, SCHEMA], {"age": "type"}, "bool is not an int", "validation", weight=2),
        T("validate_payload", [{"name": 5, "active": "yes"}, SCHEMA], {"name": "type", "active": "type"}, "wrong types", "validation"),
        T("validate_payload", [{"name": "Asha", "admin": True}, SCHEMA], {"admin": "unknown"}, "unknown fields are reported", "validation"),
        T("validate_payload", [{"name": None}, SCHEMA], {"name": "required"}, "None counts as missing", "validation"),
        T("parse_bearer", ["Bearer abc123"], "abc123", "parse_bearer basic", "authentication", visible=True),
        T("parse_bearer", ["bearer abc123"], "abc123", "scheme is case-insensitive", "authentication"),
        T("parse_bearer", ["Basic abc123"], None, "other schemes are rejected", "authentication"),
        T("parse_bearer", ["Bearer"], None, "missing token", "authentication"),
        T("parse_bearer", ["Bearer a b"], None, "too many parts", "authentication"),
        T("parse_bearer", [None], None, "header missing", "authentication"),
    ], REST_REF),
]

from . import coding_data  # noqa: E402  (second half of the coding challenges)
ASSIGNMENTS += coding_data.ASSIGNMENTS
