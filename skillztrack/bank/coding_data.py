"""Coding challenges, part 2: data, ML, networking and crypto."""
from . import Assignment, T


def code(slug, skill, title, summary, ceiling, minutes, instructions, starter, tests, reference, **spec_extra):
    return Assignment(slug=slug, skill=skill, kind="code", title=title, summary=summary, ceiling=ceiling, minutes=minutes,
                      instructions=instructions, starter=starter, spec={"tests": tests, **spec_extra}, reference=reference)


INTRO = ("Write the functions described in the starter code. They run against hidden tests in a restricted sandbox "
         "(standard-library modules such as math, re, json, collections, itertools, hashlib, hmac, ipaddress are available; "
         "no files or network). Edge cases count. Floating-point answers are compared with a small tolerance.")
A = dict(cmp="approx")

# -------------------------------------------------------------------------------------------- statistics
STATS_STARTER = '''def median(xs):
    """Middle value (mean of the two middle values for an even count). ValueError for an empty list."""
    pass


def mode(xs):
    """Sorted list of ALL most-frequent values ([1,1,2] -> [1]; [1,2,3] -> [1,2,3]). ValueError if empty."""
    pass


def variance(xs, sample=True):
    """Sample variance (divide by n-1) by default, population variance (divide by n) if sample=False.
    ValueError if empty, or if sample=True and there is only one value."""
    pass


def stdev(xs, sample=True):
    """Square root of variance(xs, sample)."""
    pass


def percentile(xs, p):
    """The p-th percentile (0-100) using LINEAR INTERPOLATION between closest ranks:
    position = p/100 * (n-1) on the sorted data. ValueError for empty xs or p outside 0..100."""
    pass


def pearson(xs, ys):
    """Pearson correlation coefficient. ValueError if the lengths differ, there are fewer than 2 points,
    or either series is constant."""
    pass


def zscores(xs):
    """Z-score of each value using the POPULATION standard deviation. ValueError if xs is empty or constant."""
    pass


def iqr_outliers(xs):
    """Values below Q1 - 1.5*IQR or above Q3 + 1.5*IQR (Q1/Q3 from percentile()), returned in ascending order."""
    pass
'''
STATS_REF = '''import math

def median(xs):
    if not xs:
        raise ValueError("empty")
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

def mode(xs):
    if not xs:
        raise ValueError("empty")
    counts = {}
    for x in xs:
        counts[x] = counts.get(x, 0) + 1
    top = max(counts.values())
    return sorted(k for k, v in counts.items() if v == top)

def variance(xs, sample=True):
    n = len(xs)
    if n == 0 or (sample and n < 2):
        raise ValueError("not enough data")
    m = sum(xs) / n
    return sum((x - m) ** 2 for x in xs) / (n - 1 if sample else n)

def stdev(xs, sample=True):
    return math.sqrt(variance(xs, sample))

def percentile(xs, p):
    if not xs or p < 0 or p > 100:
        raise ValueError("bad input")
    s = sorted(xs)
    pos = p / 100 * (len(s) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)

def pearson(xs, ys):
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("bad lengths")
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        raise ValueError("constant series")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy)

def zscores(xs):
    if not xs:
        raise ValueError("empty")
    sd = stdev(xs, sample=False)
    if sd == 0:
        raise ValueError("constant")
    m = sum(xs) / len(xs)
    return [(x - m) / sd for x in xs]

def iqr_outliers(xs):
    q1, q3 = percentile(xs, 25), percentile(xs, 75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return sorted(x for x in xs if x < lo or x > hi)
'''
D8 = [2, 4, 4, 4, 5, 5, 7, 9]

# ----------------------------------------------------------------------------------- pandas-style wrangling
WRANGLE_STARTER = '''def drop_missing(rows, columns):
    """`rows` is a list of dicts. Keep (in order) only rows where EVERY column in `columns` is present,
    not None, and not an empty / blank string."""
    pass


def fill_missing(rows, column, strategy):
    """Return NEW rows (do not modify the input) where missing values (None, or '' / blank text, or a missing key)
    in `column` are replaced: strategy 'mean' or 'median' of the non-missing numbers in that column, or 'zero' (0).
    ValueError for an unknown strategy, or for mean/median when no values exist."""
    pass


def group_agg(rows, key, value, how):
    """Group rows by row[key] and aggregate row[value] with how = 'sum', 'mean', 'count', 'max' or 'min'.
    Ignore rows where the value is None. Return {group: result}. 'count' counts non-None values.
    ValueError for an unknown `how`."""
    pass


def merge_left(left, right, on):
    """Left join two lists of dicts on the column `on`. Every left row appears at least once, with the right row's
    other columns added; if several right rows match, output one row per match (in right order); if none match, the
    right columns are present with value None. Right columns = all keys in `right` rows except `on`."""
    pass


def rolling_mean(values, window):
    """Moving average: a list the same length as `values`; the first window-1 entries are None.
    ValueError if window < 1."""
    pass


def min_max_scale(values):
    """Scale to the range 0..1: (v - min) / (max - min). A constant list becomes all 0.0. Empty -> []."""
    pass
'''
WRANGLE_REF = '''def _blank(v):
    return v is None or (isinstance(v, str) and not v.strip())

def drop_missing(rows, columns):
    return [r for r in rows if all(not _blank(r.get(c)) for c in columns)]

def fill_missing(rows, column, strategy):
    if strategy not in ("mean", "median", "zero"):
        raise ValueError("strategy")
    present = sorted(float(r[column]) for r in rows if not _blank(r.get(column)))
    if strategy == "zero":
        fill = 0
    else:
        if not present:
            raise ValueError("no values")
        n = len(present)
        fill = sum(present) / n if strategy == "mean" else (present[n // 2] if n % 2 else (present[n // 2 - 1] + present[n // 2]) / 2)
    out = []
    for r in rows:
        new = dict(r)
        if _blank(new.get(column)):
            new[column] = fill
        out.append(new)
    return out

def group_agg(rows, key, value, how):
    if how not in ("sum", "mean", "count", "max", "min"):
        raise ValueError("how")
    groups = {}
    for r in rows:
        if r.get(value) is not None:
            groups.setdefault(r[key], []).append(r[value])
    fn = {"sum": sum, "count": len, "max": max, "min": min, "mean": lambda v: sum(v) / len(v)}[how]
    return {k: fn(v) for k, v in groups.items()}

def merge_left(left, right, on):
    cols = []
    for r in right:
        for k in r:
            if k != on and k not in cols:
                cols.append(k)
    out = []
    for l in left:
        matches = [r for r in right if r.get(on) == l.get(on)]
        if matches:
            for m in matches:
                row = dict(l)
                for c in cols:
                    row[c] = m.get(c)
                out.append(row)
        else:
            row = dict(l)
            for c in cols:
                row[c] = None
            out.append(row)
    return out

def rolling_mean(values, window):
    if window < 1:
        raise ValueError("window")
    return [None if i + 1 < window else sum(values[i + 1 - window:i + 1]) / window for i in range(len(values))]

def min_max_scale(values):
    if not values:
        return []
    lo, hi = min(values), max(values)
    return [0.0 if hi == lo else (v - lo) / (hi - lo) for v in values]
'''
ROWS = [{"id": 1, "city": "Pune", "sales": 10}, {"id": 2, "city": "Pune", "sales": None}, {"id": 3, "city": "", "sales": 30},
        {"id": 4, "city": "Delhi", "sales": 50}]

# -------------------------------------------------------------------------------------------- data visualisation
VIZ_STARTER = '''def bar_heights(values, chart_height):
    """Scale non-negative values so the LARGEST bar is `chart_height` pixels tall, zero baseline, each rounded to
    2 decimals. All zeros -> all 0.0. Empty -> []. ValueError if any value is negative."""
    pass


def histogram(values, bins):
    """Counts per equal-width bin between min(values) and max(values). The maximum belongs to the LAST bin.
    ValueError if bins < 1. Empty values -> [0] * bins. If all values are equal they all go in the first bin."""
    pass


def percent_change_series(values):
    """Percent change of every value relative to the FIRST value, rounded to 2 decimals:
    [100, 110, 99] -> [0.0, 10.0, -1.0]. Empty -> []. ValueError if the first value is 0."""
    pass


def scale_linear(value, domain, range_, clamp=False):
    """Map `value` from domain [d0, d1] to range [r0, r1] linearly (the range may be reversed, like SVG y-axes).
    With clamp=True the result stays between r0 and r1. ValueError if d0 == d1."""
    pass
'''
VIZ_REF = '''import math

def bar_heights(values, chart_height):
    if any(v < 0 for v in values):
        raise ValueError("negative")
    top = max(values) if values else 0
    return [0.0 if top == 0 else round(v / top * chart_height, 2) for v in values]

def histogram(values, bins):
    if bins < 1:
        raise ValueError("bins")
    counts = [0] * bins
    if not values:
        return counts
    lo, hi = min(values), max(values)
    if hi == lo:
        counts[0] = len(values)
        return counts
    width = (hi - lo) / bins
    for v in values:
        counts[min(bins - 1, int((v - lo) / width))] += 1
    return counts

def percent_change_series(values):
    if not values:
        return []
    if values[0] == 0:
        raise ValueError("zero base")
    return [round((v - values[0]) / values[0] * 100, 2) for v in values]

def scale_linear(value, domain, range_, clamp=False):
    d0, d1 = domain
    r0, r1 = range_
    if d0 == d1:
        raise ValueError("empty domain")
    t = (value - d0) / (d1 - d0)
    if clamp:
        t = max(0.0, min(1.0, t))
    return r0 + t * (r1 - r0)
'''

# ------------------------------------------------------------------------------------------------------ ML
ML_STARTER = '''import math


def confusion_counts(y_true, y_pred, positive=1):
    """Return {"tp": .., "fp": .., "tn": .., "fn": ..} treating `positive` as the positive class."""
    pass


def precision_recall_f1(y_true, y_pred, positive=1):
    """Return [precision, recall, f1]. Use 0.0 whenever a denominator is zero."""
    pass


def k_fold_indices(n, k):
    """Split indices 0..n-1 into k contiguous folds whose sizes differ by at most 1 (earlier folds get the extra item):
    k_fold_indices(10, 3) -> [[0,1,2,3],[4,5,6],[7,8,9]]. ValueError if k < 2 or k > n."""
    pass


def knn_predict(train_x, train_y, x, k):
    """k-nearest-neighbours classification. Euclidean distance; if distances tie, the EARLIER training point wins;
    the label with most votes among the k neighbours wins; if votes tie, the smallest label wins (sorted order)."""
    pass


def linear_fit(xs, ys):
    """Least-squares line y = slope * x + intercept. Return [slope, intercept].
    ValueError if fewer than 2 points, lengths differ, or all xs are equal."""
    pass


def gradient_step(w, b, xs, ys, lr):
    """One gradient-descent step for y_hat = w*x + b with mean squared error loss:
    dw = (2/n) * sum((y_hat - y) * x),  db = (2/n) * sum(y_hat - y).  Return [w - lr*dw, b - lr*db]."""
    pass
'''
ML_REF = '''import math

def confusion_counts(y_true, y_pred, positive=1):
    c = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for t, p in zip(y_true, y_pred):
        if p == positive:
            c["tp" if t == positive else "fp"] += 1
        else:
            c["fn" if t == positive else "tn"] += 1
    return c

def precision_recall_f1(y_true, y_pred, positive=1):
    c = confusion_counts(y_true, y_pred, positive)
    p = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else 0.0
    r = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return [p, r, f]

def k_fold_indices(n, k):
    if k < 2 or k > n:
        raise ValueError("k")
    base, extra = divmod(n, k)
    folds, start = [], 0
    for i in range(k):
        size = base + (1 if i < extra else 0)
        folds.append(list(range(start, start + size)))
        start += size
    return folds

def knn_predict(train_x, train_y, x, k):
    dists = sorted((math.dist(t, x), i) for i, t in enumerate(train_x))
    votes = {}
    for _, i in dists[:k]:
        votes[train_y[i]] = votes.get(train_y[i], 0) + 1
    top = max(votes.values())
    return sorted(l for l, v in votes.items() if v == top)[0]

def linear_fit(xs, ys):
    if len(xs) < 2 or len(xs) != len(ys):
        raise ValueError("data")
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        raise ValueError("constant x")
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return [slope, my - slope * mx]

def gradient_step(w, b, xs, ys, lr):
    n = len(xs)
    errs = [w * x + b - y for x, y in zip(xs, ys)]
    dw = 2 / n * sum(e * x for e, x in zip(errs, xs))
    db = 2 / n * sum(errs)
    return [w - lr * dw, b - lr * db]
'''
KX = [[0, 0], [0, 1], [1, 0], [5, 5], [5, 6], [6, 5]]
KY = ["a", "a", "a", "b", "b", "b"]

# ------------------------------------------------------------------------------------------- deep learning
DL_STARTER = '''import math


def relu(xs):
    """Apply ReLU to every element of the list: max(0, x)."""
    pass


def sigmoid(x):
    """1 / (1 + e^-x). Must not overflow for very large positive or negative x (e.g. -1000 and 1000)."""
    pass


def softmax(xs):
    """Probabilities that sum to 1. Must be numerically stable (softmax([1000, 1000]) is [0.5, 0.5]). [] -> []."""
    pass


def dense_forward(x, weights, bias, activation):
    """One dense layer. `weights[i]` is the row of weights for output i, so output_i = sum(weights[i][j] * x[j]) + bias[i].
    `activation` is "relu", "sigmoid" or "none". Return the list of outputs."""
    pass


def cross_entropy(probs, true_index):
    """Loss = -ln(p) of the true class, with p clamped to at least 1e-12 so the loss is finite."""
    pass


def sigmoid_neuron_step(w, b, x, y, lr):
    """One gradient-descent step for a single sigmoid neuron with binary cross-entropy loss.
    a = sigmoid(w . x + b); grad = a - y; each w_i -= lr * grad * x_i; b -= lr * grad.
    Return [new_w_list, new_b]."""
    pass
'''
DL_REF = '''import math

def relu(xs):
    return [x if x > 0 else 0 for x in xs]

def sigmoid(x):
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)

def softmax(xs):
    if not xs:
        return []
    m = max(xs)
    exps = [math.exp(x - m) for x in xs]
    total = sum(exps)
    return [e / total for e in exps]

def dense_forward(x, weights, bias, activation):
    out = [sum(w * v for w, v in zip(row, x)) + b for row, b in zip(weights, bias)]
    if activation == "relu":
        return relu(out)
    if activation == "sigmoid":
        return [sigmoid(v) for v in out]
    return out

def cross_entropy(probs, true_index):
    return -math.log(max(probs[true_index], 1e-12))

def sigmoid_neuron_step(w, b, x, y, lr):
    a = sigmoid(sum(wi * xi for wi, xi in zip(w, x)) + b)
    g = a - y
    return [[wi - lr * g * xi for wi, xi in zip(w, x)], b - lr * g]
'''

# -------------------------------------------------------------------------------------------------- networking
NET_STARTER = '''import ipaddress


def subnet_info(cidr):
    """For an IPv4 CIDR like "192.168.1.77/24" return a dict of strings/ints:
    {"network": "192.168.1.0", "broadcast": "192.168.1.255", "netmask": "255.255.255.0",
     "first_host": "192.168.1.1", "last_host": "192.168.1.254", "usable_hosts": 254}.
    Host bits in the input are ignored. Support prefixes /0 to /30; raise ValueError for /31, /32 or invalid input."""
    pass


def same_subnet(ip_a, ip_b, mask):
    """True if both IPv4 addresses are in the same subnet for the dotted-decimal `mask` (e.g. "255.255.252.0")."""
    pass


def parse_request_line(line):
    """Parse an HTTP request line like "GET /index.html?x=1 HTTP/1.1" into
    {"method": "GET", "path": "/index.html?x=1", "version": "HTTP/1.1"}.
    Exactly three parts separated by single spaces; method must be UPPERCASE letters; path must start with "/";
    version must look like HTTP/1.1, HTTP/1.0 or HTTP/2. Otherwise raise ValueError."""
    pass


def classify_port(port):
    """"well-known" for 1-1023, "registered" for 1024-49151, "dynamic" for 49152-65535. ValueError otherwise."""
    pass


def is_private_ip(ip):
    """True for the RFC 1918 private ranges only: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16.
    (127.0.0.1 and public addresses are False.) ValueError for an invalid IPv4 address."""
    pass
'''
NET_REF = '''import ipaddress
import re

def subnet_info(cidr):
    net = ipaddress.IPv4Network(cidr, strict=False)
    if net.prefixlen > 30:
        raise ValueError("unsupported prefix")
    return {"network": str(net.network_address), "broadcast": str(net.broadcast_address), "netmask": str(net.netmask),
            "first_host": str(net.network_address + 1), "last_host": str(net.broadcast_address - 1),
            "usable_hosts": net.num_addresses - 2}

def same_subnet(ip_a, ip_b, mask):
    m = int(ipaddress.IPv4Address(mask))
    return int(ipaddress.IPv4Address(ip_a)) & m == int(ipaddress.IPv4Address(ip_b)) & m

def parse_request_line(line):
    parts = line.split(" ")
    if len(parts) != 3:
        raise ValueError("parts")
    method, path, version = parts
    if not re.fullmatch(r"[A-Z]+", method) or not path.startswith("/") or not re.fullmatch(r"HTTP/(1\\.[01]|2)", version):
        raise ValueError("malformed")
    return {"method": method, "path": path, "version": version}

def classify_port(port):
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise ValueError("port")
    return "well-known" if port <= 1023 else "registered" if port <= 49151 else "dynamic"

def is_private_ip(ip):
    addr = ipaddress.IPv4Address(ip)
    return any(addr in ipaddress.IPv4Network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
'''

# ------------------------------------------------------------------------------------------------- cryptography
CRYPTO_STARTER = '''import hashlib
import hmac


def caesar(text, shift):
    """Shift letters by `shift` places (negative and >26 allowed), keeping case; leave other characters alone."""
    pass


def vigenere_encrypt(text, key):
    """Vigenere cipher: shift each LETTER by the matching key letter (a=0 ... z=25), keeping case. The key advances
    only on letters. ValueError if the key is empty or contains non-letters."""
    pass


def xor_hex(data_hex, key_hex):
    """XOR the bytes of `data_hex` with the repeating key `key_hex` (both hex strings). Return lowercase hex.
    ValueError for invalid hex or an empty key."""
    pass


def hmac_sha256_hex(key, message):
    """HMAC-SHA256 of the UTF-8 `message` under the UTF-8 `key`, as lowercase hex."""
    pass


def verify_mac(key, message, tag_hex):
    """True if `tag_hex` is the correct HMAC-SHA256 tag. Compare in CONSTANT TIME (not with ==)."""
    pass


def pbkdf2_hex(password, salt, iterations):
    """PBKDF2-HMAC-SHA256 (32-byte output) of the UTF-8 password and salt, as lowercase hex."""
    pass


def modinv(a, m):
    """Modular inverse of a modulo m (extended Euclid). ValueError if it does not exist."""
    pass


def rsa_toy(p, q, e, message):
    """Textbook RSA with small primes: n = p*q, phi = (p-1)*(q-1), d = modinv(e, phi).
    Return [ciphertext, decrypted] where ciphertext = message^e mod n and decrypted = ciphertext^d mod n."""
    pass
'''
CRYPTO_REF = '''import hashlib
import hmac

def _shift(ch, n):
    if ch.isascii() and ch.isalpha():
        base = ord("A") if ch.isupper() else ord("a")
        return chr((ord(ch) - base + n) % 26 + base)
    return ch

def caesar(text, shift):
    return "".join(_shift(c, shift) for c in text)

def vigenere_encrypt(text, key):
    if not key or not all(c.isascii() and c.isalpha() for c in key):
        raise ValueError("key")
    out, i = [], 0
    for ch in text:
        if ch.isascii() and ch.isalpha():
            out.append(_shift(ch, ord(key[i % len(key)].lower()) - 97))
            i += 1
        else:
            out.append(ch)
    return "".join(out)

def xor_hex(data_hex, key_hex):
    data, key = bytes.fromhex(data_hex), bytes.fromhex(key_hex)
    if not key:
        raise ValueError("empty key")
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data)).hex()

def hmac_sha256_hex(key, message):
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()

def verify_mac(key, message, tag_hex):
    return hmac.compare_digest(hmac_sha256_hex(key, message), tag_hex)

def pbkdf2_hex(password, salt, iterations):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations, 32).hex()

def modinv(a, m):
    g, x0, x1, b = m, 0, 1, a % m
    r0, r1 = m, b
    while r1:
        q = r0 // r1
        r0, r1 = r1, r0 - q * r1
        x0, x1 = x1, x0 - q * x1
    if r0 != 1:
        raise ValueError("no inverse")
    return x0 % m

def rsa_toy(p, q, e, message):
    n, phi = p * q, (p - 1) * (q - 1)
    d = modinv(e, phi)
    c = pow(message, e, n)
    return [c, pow(c, d, n)]
'''
FOX = "The quick brown fox jumps over the lazy dog"
FOX_TAG = "f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8"

ASSIGNMENTS = [
    code("statistics-from-scratch", "statistics", "Statistics from scratch", "Implement the core descriptive statistics yourself.", 4, 35,
         INTRO + " The `statistics` module is not allowed here: the point is to implement it yourself.", STATS_STARTER, [
        T("median", [[3, 1, 2]], 2, "median of an odd count", "centre", visible=True, **A),
        T("median", [[4, 1, 3, 2]], 2.5, "median of an even count", "centre", **A),
        T("median", [[5]], 5, "median of one value", "edge cases", **A),
        T("median", [[]], label="median rejects an empty list", topic="error handling", raises="ValueError"),
        T("mode", [[1, 2, 2, 3, 3]], [2, 3], "mode returns every most-frequent value", "centre", visible=True),
        T("mode", [[1, 1, 2]], [1], "mode with a single winner", "centre"),
        T("mode", [[1, 2, 3]], [1, 2, 3], "mode when all tie", "centre"),
        T("variance", [D8, False], 4.0, "population variance", "spread", visible=True, **A),
        T("variance", [D8, True], 32 / 7, "sample variance divides by n-1", "spread", weight=2, **A),
        T("variance", [D8], 32 / 7, "sample is the default", "spread", **A),
        T("variance", [[5], True], label="sample variance needs two values", topic="error handling", raises="ValueError"),
        T("variance", [[5], False], 0.0, "population variance of one value", "edge cases", **A),
        T("stdev", [D8, False], 2.0, "population standard deviation", "spread", **A),
        T("percentile", [[1, 2, 3, 4, 5], 50], 3, "percentile 50 of odd list", "percentiles", visible=True, **A),
        T("percentile", [[1, 2, 3, 4], 50], 2.5, "percentile interpolates between ranks", "percentiles", weight=2, **A),
        T("percentile", [[10, 20, 30, 40, 50], 90], 46.0, "percentile 90 interpolates", "percentiles", **A),
        T("percentile", [[5, 1, 3], 0], 1, "percentile 0 is the minimum (unsorted input)", "percentiles", **A),
        T("percentile", [[5, 1, 3], 100], 5, "percentile 100 is the maximum", "percentiles", **A),
        T("percentile", [[1, 2], 101], label="percentile rejects p above 100", topic="error handling", raises="ValueError"),
        T("pearson", [[1, 2, 3, 4, 5], [2, 4, 6, 8, 10]], 1.0, "perfect positive correlation", "correlation", visible=True, **A),
        T("pearson", [[1, 2, 3], [3, 2, 1]], -1.0, "perfect negative correlation", "correlation", **A),
        T("pearson", [[1, 2, 3, 4], [1, 3, 2, 4]], 0.8, "partial correlation", "correlation", weight=2, **A),
        T("pearson", [[1, 1, 1], [1, 2, 3]], label="pearson rejects a constant series", topic="error handling", raises="ValueError"),
        T("pearson", [[1, 2], [1, 2, 3]], label="pearson rejects mismatched lengths", topic="error handling", raises="ValueError"),
        T("zscores", [D8], [-1.5, -0.5, -0.5, -0.5, 0, 0, 1, 2], "zscores use the population standard deviation", "standardisation", weight=2, **A),
        T("zscores", [[3, 3, 3]], label="zscores reject a constant list", topic="error handling", raises="ValueError"),
        T("iqr_outliers", [[1, 2, 3, 4, 5, 6, 7, 8, 9, 100]], [100], "high outlier", "outliers", visible=True),
        T("iqr_outliers", [[-50, 1, 2, 3, 4, 5, 6, 7, 8, 9, 100]], [-50, 100], "outliers on both sides, ascending", "outliers", weight=2),
        T("iqr_outliers", [[1, 2, 3, 4, 5]], [], "no outliers", "outliers"),
    ], STATS_REF, forbidden_imports=["statistics"]),

    code("data-wrangling", "pandas-numpy", "Data wrangling the pandas way", "Clean, group, merge and scale tabular data (implemented with plain Python so every step is visible).", 4, 40,
         INTRO + " Rows are dicts, like records in a DataFrame; each function mirrors a pandas operation (dropna, fillna, groupby.agg, merge, rolling.mean, scaling).",
         WRANGLE_STARTER, [
        T("drop_missing", [ROWS, ["sales"]], [ROWS[0], ROWS[2], ROWS[3]], "drop_missing removes None values", "missing data", visible=True),
        T("drop_missing", [ROWS, ["sales", "city"]], [ROWS[0], ROWS[3]], "drop_missing treats blank text as missing", "missing data", weight=2),
        T("drop_missing", [[{"a": 1}, {"b": 2}], ["a"]], [{"a": 1}], "drop_missing treats a missing key as missing", "missing data"),
        T("drop_missing", [[], ["a"]], [], "drop_missing of no rows", "edge cases"),
        T("fill_missing", [[{"v": 1}, {"v": None}, {"v": 3}], "v", "mean"], [{"v": 1}, {"v": 2.0}, {"v": 3}], "fill with the mean", "missing data", visible=True, **A),
        T("fill_missing", [[{"v": 1}, {"v": ""}, {"v": 2}, {"v": 10}], "v", "median"], [{"v": 1}, {"v": 2.0}, {"v": 2}, {"v": 10}], "fill with the median", "missing data", **A),
        T("fill_missing", [[{"v": None}, {"v": 4}], "v", "zero"], [{"v": 0}, {"v": 4}], "fill with zero", "missing data"),
        T("fill_missing", [[{"v": None}], "v", "mean"], label="mean of nothing is an error", topic="error handling", raises="ValueError"),
        T("fill_missing", [[{"v": 1}], "v", "mode"], label="unknown strategy is an error", topic="error handling", raises="ValueError"),
        T("group_agg", [ROWS, "city", "sales", "sum"], {"Pune": 10, "": 30, "Delhi": 50}, "groupby sum ignores None values", "aggregation", visible=True),
        T("group_agg", [[{"k": "a", "v": 1}, {"k": "a", "v": 4}, {"k": "b", "v": 3}], "k", "v", "mean"], {"a": 2.5, "b": 3.0}, "groupby mean", "aggregation", **A),
        T("group_agg", [[{"k": "a", "v": 1}, {"k": "a", "v": None}], "k", "v", "count"], {"a": 1}, "count skips None", "aggregation"),
        T("group_agg", [[{"k": "a", "v": 1}, {"k": "a", "v": 7}], "k", "v", "max"], {"a": 7}, "groupby max", "aggregation"),
        T("group_agg", [[{"k": "a", "v": 1}], "k", "v", "median"], label="unknown aggregation is an error", topic="error handling", raises="ValueError"),
        T("merge_left", [[{"id": 1, "n": "a"}, {"id": 2, "n": "b"}], [{"id": 1, "score": 9}], "id"],
          [{"id": 1, "n": "a", "score": 9}, {"id": 2, "n": "b", "score": None}], "left join keeps unmatched rows with None", "joins", weight=2, visible=True),
        T("merge_left", [[{"id": 1}], [{"id": 1, "x": "p"}, {"id": 1, "x": "q"}], "id"], [{"id": 1, "x": "p"}, {"id": 1, "x": "q"}], "several matches give several rows", "joins", weight=2),
        T("merge_left", [[{"id": 5}], [], "id"], [{"id": 5}], "joining with an empty right side", "edge cases"),
        T("rolling_mean", [[1, 2, 3, 4], 2], [None, 1.5, 2.5, 3.5], "rolling mean window 2", "windows", visible=True, **A),
        T("rolling_mean", [[1, 2, 3, 4, 5], 3], [None, None, 2.0, 3.0, 4.0], "rolling mean window 3", "windows", **A),
        T("rolling_mean", [[5, 7], 1], [5.0, 7.0], "window of 1", "windows", **A),
        T("rolling_mean", [[1, 2], 0], label="window below 1 is an error", topic="error handling", raises="ValueError"),
        T("min_max_scale", [[10, 20, 30]], [0.0, 0.5, 1.0], "min-max scaling", "scaling", visible=True, **A),
        T("min_max_scale", [[5, 5, 5]], [0.0, 0.0, 0.0], "constant list scales to zeros", "edge cases", **A),
        T("min_max_scale", [[]], [], "empty list", "edge cases"),
    ], WRANGLE_REF),

    code("chart-maths", "data-visualization", "Chart maths: scales, bins and baselines", "The calculations behind honest charts.", 4, 30,
         INTRO, VIZ_STARTER, [
        T("bar_heights", [[10, 20, 40], 100], [25.0, 50.0, 100.0], "bars scale from a zero baseline", "scales", visible=True, **A),
        T("bar_heights", [[1, 2, 3], 10], [3.33, 6.67, 10.0], "heights are rounded to 2 decimals", "scales", **A),
        T("bar_heights", [[0, 0], 50], [0.0, 0.0], "all zeros", "edge cases", **A),
        T("bar_heights", [[], 50], [], "no values", "edge cases"),
        T("bar_heights", [[1, -2], 10], label="negative values are rejected", topic="error handling", raises="ValueError"),
        T("histogram", [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 3], [3, 3, 4], "equal-width bins, max in the last bin", "binning", visible=True, weight=2),
        T("histogram", [[0, 5, 10], 2], [1, 2], "boundary values", "binning"),
        T("histogram", [[3, 3, 3], 3], [3, 0, 0], "all values equal", "edge cases"),
        T("histogram", [[], 4], [0, 0, 0, 0], "no values", "edge cases"),
        T("histogram", [[1, 2], 0], label="zero bins is an error", topic="error handling", raises="ValueError"),
        T("percent_change_series", [[100, 110, 99]], [0.0, 10.0, -1.0], "percent change vs the first value", "normalisation", visible=True, **A),
        T("percent_change_series", [[200, 100, 300]], [0.0, -50.0, 50.0], "decreases and increases", "normalisation", **A),
        T("percent_change_series", [[]], [], "no values", "edge cases"),
        T("percent_change_series", [[0, 5]], label="a zero base is an error", topic="error handling", raises="ValueError"),
        T("scale_linear", [5, [0, 10], [0, 100]], 50.0, "scale_linear midpoint", "scales", visible=True, **A),
        T("scale_linear", [2, [0, 10], [100, 0]], 80.0, "reversed range (SVG y axis)", "scales", weight=2, **A),
        T("scale_linear", [15, [0, 10], [0, 100]], 150.0, "values outside the domain extrapolate", "scales", **A),
        T("scale_linear", [15, [0, 10], [0, 100], True], 100.0, "clamp high", "scales", **A),
        T("scale_linear", [-5, [0, 10], [0, 100], True], 0.0, "clamp low", "scales", **A),
        T("scale_linear", [1, [3, 3], [0, 1]], label="an empty domain is an error", topic="error handling", raises="ValueError"),
    ], VIZ_REF),

    code("ml-from-scratch", "machine-learning", "Machine learning from scratch", "Metrics, cross-validation splits, k-NN and regression without libraries.", 4, 40,
         INTRO, ML_STARTER, [
        T("confusion_counts", [[1, 0, 1, 1, 0, 0], [1, 0, 0, 1, 1, 0]], {"tp": 2, "fp": 1, "tn": 2, "fn": 1}, "confusion matrix counts", "evaluation", visible=True, weight=2),
        T("confusion_counts", [["spam", "ham", "spam"], ["spam", "spam", "ham"], "spam"], {"tp": 1, "fp": 1, "tn": 0, "fn": 1}, "custom positive label", "evaluation"),
        T("precision_recall_f1", [[1, 0, 1, 1, 0, 0], [1, 0, 0, 1, 1, 0]], [2 / 3, 2 / 3, 2 / 3], "precision, recall and F1", "evaluation", visible=True, weight=2, **A),
        T("precision_recall_f1", [[1, 1], [0, 0]], [0.0, 0.0, 0.0], "no positive predictions gives zeros, not an error", "evaluation", **A),
        T("precision_recall_f1", [[1, 1, 0, 0], [1, 0, 0, 0]], [1.0, 0.5, 2 / 3], "high precision, low recall", "evaluation", **A),
        T("k_fold_indices", [10, 3], [[0, 1, 2, 3], [4, 5, 6], [7, 8, 9]], "uneven folds", "validation", visible=True, weight=2),
        T("k_fold_indices", [6, 3], [[0, 1], [2, 3], [4, 5]], "even folds", "validation"),
        T("k_fold_indices", [5, 5], [[0], [1], [2], [3], [4]], "leave-one-out", "validation"),
        T("k_fold_indices", [5, 1], label="k below 2 is an error", topic="error handling", raises="ValueError"),
        T("k_fold_indices", [3, 4], label="k above n is an error", topic="error handling", raises="ValueError"),
        T("knn_predict", [KX, KY, [0.5, 0.5], 3], "a", "k-NN near cluster a", "k-NN", visible=True),
        T("knn_predict", [KX, KY, [5, 5.5], 3], "b", "k-NN near cluster b", "k-NN"),
        T("knn_predict", [KX, KY, [3, 3], 1], "b", "k=1 picks the nearest point", "k-NN"),
        T("knn_predict", [KX, KY, [0, 0], 6], "a", "vote ties go to the smallest label", "k-NN", weight=2),
        T("knn_predict", [[[1, 0], [-1, 0]], ["z", "a"], [0, 0], 1], "z", "distance ties go to the earlier training point", "k-NN", weight=2),
        T("linear_fit", [[1, 2, 3, 4], [2, 4, 6, 8]], [2.0, 0.0], "perfect line", "regression", visible=True, **A),
        T("linear_fit", [[0, 1, 2], [1, 3, 5]], [2.0, 1.0], "line with an intercept", "regression", **A),
        T("linear_fit", [[1, 2, 3, 4, 5], [2.2, 2.8, 3.6, 4.5, 5.1]], [0.75, 1.39], "noisy data", "regression", weight=2, **A),
        T("linear_fit", [[2, 2, 2], [1, 2, 3]], label="constant x is an error", topic="error handling", raises="ValueError"),
        T("gradient_step", [0, 0, [1, 2, 3], [2, 4, 6], 0.1], [1.8666666666666667, 0.8], "one gradient descent step", "optimisation", visible=True, weight=2, **A),
        T("gradient_step", [2, 0, [1, 2, 3], [2, 4, 6], 0.1], [2.0, 0.0], "no change at the optimum", "optimisation", **A),
    ], ML_REF),

    code("neural-net-basics", "deep-learning", "Neural network building blocks", "Activations, a dense layer, cross-entropy and a gradient step, in pure Python.", 4, 40,
         INTRO, DL_STARTER, [
        T("relu", [[-1, 0, 2.5]], [0, 0, 2.5], "relu", "activations", visible=True, **A),
        T("sigmoid", [0], 0.5, "sigmoid(0)", "activations", visible=True, **A),
        T("sigmoid", [2], 0.8807970779778823, "sigmoid(2)", "activations", **A),
        T("sigmoid", [-1000], 0.0, "sigmoid of a huge negative number must not overflow", "numerical stability", weight=2, tol=1e-9, cmp="approx"),
        T("sigmoid", [1000], 1.0, "sigmoid of a huge positive number", "numerical stability", **A),
        T("softmax", [[1, 2, 3]], [0.09003057317038046, 0.24472847105479764, 0.6652409557748219], "softmax", "activations", visible=True, **A),
        T("softmax", [[1000, 1000]], [0.5, 0.5], "softmax must be numerically stable", "numerical stability", weight=2, **A),
        T("softmax", [[0, 0, 0, 0]], [0.25, 0.25, 0.25, 0.25], "uniform softmax", "activations", **A),
        T("softmax", [[]], [], "softmax of nothing", "edge cases"),
        T("dense_forward", [[1, 2], [[1, 0], [0, 1], [1, 1]], [0, 0, -5], "relu"], [1, 2, 0], "dense layer with relu", "layers", visible=True, weight=2, **A),
        T("dense_forward", [[1, 2], [[1, 0], [0, 1], [1, 1]], [0, 0, -5], "none"], [1, 2, -2], "dense layer without activation", "layers", **A),
        T("dense_forward", [[1, 2], [[0, 0]], [0], "sigmoid"], [0.5], "dense layer with sigmoid", "layers", **A),
        T("cross_entropy", [[0.7, 0.2, 0.1], 0], 0.35667494393873245, "cross-entropy loss", "loss", visible=True, **A),
        T("cross_entropy", [[0.0, 1.0], 0], 27.631021115928547, "a zero probability is clamped", "numerical stability", weight=2, **A),
        T("cross_entropy", [[1.0], 0], 0.0, "perfect prediction", "loss", **A),
        T("sigmoid_neuron_step", [[0, 0], 0, [1, 2], 1, 0.5], [[0.25, 0.5], 0.25], "one neuron training step", "backpropagation", visible=True, weight=2, **A),
        T("sigmoid_neuron_step", [[1], 0, [1], 0, 1], [[0.2689414213699951], -0.7310585786300049], "step when the target is 0", "backpropagation", weight=2, **A),
    ], DL_REF),

    code("network-calculations", "networking", "Networking calculations", "Subnets, HTTP request lines, ports and private ranges.", 4, 30,
         INTRO, NET_STARTER, [
        T("subnet_info", ["192.168.1.0/24"], {"network": "192.168.1.0", "broadcast": "192.168.1.255", "netmask": "255.255.255.0", "first_host": "192.168.1.1", "last_host": "192.168.1.254", "usable_hosts": 254},
          "/24 subnet", "subnetting", visible=True, weight=2),
        T("subnet_info", ["10.0.0.77/30"], {"network": "10.0.0.76", "broadcast": "10.0.0.79", "netmask": "255.255.255.252", "first_host": "10.0.0.77", "last_host": "10.0.0.78", "usable_hosts": 2},
          "host bits are ignored", "subnetting", weight=2),
        T("subnet_info", ["172.16.5.130/25"], {"network": "172.16.5.128", "broadcast": "172.16.5.255", "netmask": "255.255.255.128", "first_host": "172.16.5.129", "last_host": "172.16.5.254", "usable_hosts": 126},
          "/25 subnet", "subnetting"),
        T("subnet_info", ["10.0.0.0/8"], {"network": "10.0.0.0", "broadcast": "10.255.255.255", "netmask": "255.0.0.0", "first_host": "10.0.0.1", "last_host": "10.255.255.254", "usable_hosts": 16777214},
          "/8 subnet", "subnetting"),
        T("subnet_info", ["10.0.0.1/32"], label="/32 is rejected", topic="error handling", raises="ValueError"),
        T("subnet_info", ["not-a-cidr"], label="garbage is rejected", topic="error handling", raises="ValueError"),
        T("same_subnet", ["192.168.1.10", "192.168.1.200", "255.255.255.0"], True, "same /24", "subnetting", visible=True),
        T("same_subnet", ["192.168.1.10", "192.168.2.10", "255.255.255.0"], False, "different /24", "subnetting"),
        T("same_subnet", ["10.0.0.5", "10.0.3.9", "255.255.252.0"], True, "same /22", "subnetting", weight=2),
        T("same_subnet", ["10.0.0.5", "10.0.4.9", "255.255.252.0"], False, "different /22", "subnetting"),
        T("parse_request_line", ["GET /index.html HTTP/1.1"], {"method": "GET", "path": "/index.html", "version": "HTTP/1.1"}, "basic request line", "HTTP", visible=True),
        T("parse_request_line", ["POST /api/items?id=3 HTTP/1.0"], {"method": "POST", "path": "/api/items?id=3", "version": "HTTP/1.0"}, "query string and HTTP/1.0", "HTTP"),
        T("parse_request_line", ["GET / HTTP/2"], {"method": "GET", "path": "/", "version": "HTTP/2"}, "HTTP/2", "HTTP"),
        T("parse_request_line", ["GET /index.html"], label="missing version", topic="error handling", raises="ValueError"),
        T("parse_request_line", ["get / HTTP/1.1"], label="lowercase method", topic="error handling", raises="ValueError"),
        T("parse_request_line", ["GET index.html HTTP/1.1"], label="path must start with /", topic="error handling", raises="ValueError"),
        T("parse_request_line", ["GET  / HTTP/1.1"], label="double space", topic="error handling", raises="ValueError"),
        T("parse_request_line", ["GET / HTTP/9.9"], label="unknown version", topic="error handling", raises="ValueError"),
        T("classify_port", [80], "well-known", "port 80", "ports", visible=True),
        T("classify_port", [1023], "well-known", "port 1023", "ports"),
        T("classify_port", [1024], "registered", "port 1024", "ports"),
        T("classify_port", [49151], "registered", "port 49151", "ports"),
        T("classify_port", [49152], "dynamic", "port 49152", "ports"),
        T("classify_port", [65535], "dynamic", "port 65535", "ports"),
        T("classify_port", [0], label="port 0 is invalid", topic="error handling", raises="ValueError"),
        T("classify_port", [65536], label="port 65536 is invalid", topic="error handling", raises="ValueError"),
        T("is_private_ip", ["10.1.2.3"], True, "10/8", "addressing", visible=True),
        T("is_private_ip", ["172.16.0.1"], True, "172.16/12 start", "addressing"),
        T("is_private_ip", ["172.31.255.255"], True, "172.16/12 end", "addressing", weight=2),
        T("is_private_ip", ["172.32.0.1"], False, "just outside 172.16/12", "addressing", weight=2),
        T("is_private_ip", ["192.168.0.1"], True, "192.168/16", "addressing"),
        T("is_private_ip", ["8.8.8.8"], False, "public address", "addressing"),
        T("is_private_ip", ["127.0.0.1"], False, "loopback is not RFC 1918", "addressing"),
        T("is_private_ip", ["999.1.1.1"], label="invalid address", topic="error handling", raises="ValueError"),
    ], NET_REF),

    code("crypto-workshop", "cryptography", "Cryptography workshop", "Classical ciphers, XOR, MACs, key derivation and toy RSA.", 4, 40,
         INTRO, CRYPTO_STARTER, [
        T("caesar", ["Hello, World!", 3], "Khoor, Zruog!", "caesar basic", "classical ciphers", visible=True),
        T("caesar", ["xyz", 3], "abc", "caesar wraps around", "classical ciphers"),
        T("caesar", ["abc", -1], "zab", "caesar negative shift", "classical ciphers"),
        T("caesar", ["abc", 29], "def", "caesar shift above 26", "classical ciphers"),
        T("caesar", ["", 5], "", "caesar empty", "edge cases"),
        T("vigenere_encrypt", ["ATTACKATDAWN", "LEMON"], "LXFOPVEFRNHR", "vigenere classic example", "classical ciphers", visible=True, weight=2),
        T("vigenere_encrypt", ["Attack at dawn!", "lemon"], "Lxfopv ef rnhr!", "case, spaces and punctuation; key advances on letters only", "classical ciphers", weight=2),
        T("vigenere_encrypt", ["abc", ""], label="empty key", topic="error handling", raises="ValueError"),
        T("vigenere_encrypt", ["abc", "a1"], label="non-letter key", topic="error handling", raises="ValueError"),
        T("xor_hex", ["48656c6c6f", "01"], "49646d6d6e", "xor with a one-byte key", "symmetric", visible=True),
        T("xor_hex", ["00000000", "ff00"], "ff00ff00", "xor with a repeating key", "symmetric", weight=2),
        T("xor_hex", ["zz", "01"], label="invalid hex", topic="error handling", raises="ValueError"),
        T("xor_hex", ["00", ""], label="empty key", topic="error handling", raises="ValueError"),
        T("hmac_sha256_hex", ["key", FOX], FOX_TAG, "HMAC-SHA256 known answer", "message authentication", visible=True, weight=2),
        T("verify_mac", ["key", FOX, FOX_TAG], True, "valid tag", "message authentication"),
        T("verify_mac", ["key", FOX, FOX_TAG[:-1] + ("0" if FOX_TAG[-1] != "0" else "1")], False, "tampered tag", "message authentication"),
        T("verify_mac", ["key2", FOX, FOX_TAG], False, "wrong key", "message authentication"),
        T("pbkdf2_hex", ["password", "salt", 1], "120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b", "PBKDF2 known answer", "password hashing", visible=True, weight=2),
        T("pbkdf2_hex", ["correct horse", "NaCl", 1000], "cba50afb9ece1b6c899d921b4b7139139f7d2258b02086c1764c441575c66253", "PBKDF2 with more iterations and a different salt", "password hashing"),
        T("modinv", [3, 11], 4, "modinv(3, 11)", "number theory", visible=True),
        T("modinv", [10, 17], 12, "modinv(10, 17)", "number theory"),
        T("modinv", [17, 3120], 2753, "modinv with RSA numbers", "number theory"),
        T("modinv", [6, 9], label="no inverse exists", topic="error handling", raises="ValueError"),
        T("rsa_toy", [61, 53, 17, 65], [2790, 65], "textbook RSA example", "public key", visible=True, weight=2),
        T("rsa_toy", [11, 13, 7, 42], [81, 42], "round trip with different primes", "public key", weight=2),
    ], CRYPTO_REF),
]
