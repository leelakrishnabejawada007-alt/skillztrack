"""
Named rubric checks used by the "rubric" assignments (HTML/CSS pages, JavaScript, Dockerfiles, IAM
policies, written communication).

Each check is a small function  check(text, **args) -> (passed: bool, detail: str).
They analyse the submission for real (HTML is parsed, JSON is loaded, Dockerfile instructions are
split) but they are STATIC: they cannot judge visual quality or run the code. That is why static
assignments have a lower ceiling than auto-tested ones (see assessment_engine.py).
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser

CHECKS = {}


def check(name):
    def deco(fn):
        CHECKS[name] = fn
        return fn
    return deco


def run_check(name, text, **args):
    try:
        passed, detail = CHECKS[name](text, **args)
    except Exception as exc:  # a bad submission must never crash the grader
        return False, f"Could not analyse this part ({type(exc).__name__})."
    return bool(passed), detail


# ====================================================================== HTML / CSS
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class _Doc(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags, self.stack, self.problems = [], [], []
        self.doctype = False
        self.style, self._in_style = [], False
        self.text, self.title = [], ""
        self._in_title = False
        self.label_for, self.wrapped_inputs = set(), 0
        self._label_depth = 0

    def handle_decl(self, decl):
        if decl.lower().startswith("doctype"):
            self.doctype = True

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        self.tags.append((tag, a))
        if tag == "style":
            self._in_style = True
        if tag == "title":
            self._in_title = True
        if tag == "label":
            self._label_depth += 1
            if a.get("for"):
                self.label_for.add(a["for"])
        if tag in {"input", "select", "textarea"} and self._label_depth:
            self.wrapped_inputs += 1
            a["_wrapped"] = "1"
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        self.tags.append((tag, a))

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False
        if tag == "title":
            self._in_title = False
        if tag == "label":
            self._label_depth = max(0, self._label_depth - 1)
        if tag in VOID:
            return
        if tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.problems.append(f"<{self.stack.pop()}> was not closed before </{tag}>")
            self.stack.pop()
        else:
            self.problems.append(f"stray </{tag}>")

    def handle_data(self, data):
        if self._in_style:
            self.style.append(data)
        elif self._in_title:
            self.title += data
        else:
            self.text.append(data)

    def close(self):
        super().close()
        for tag in self.stack:
            if tag not in {"html", "body", "head", "p", "li"}:
                self.problems.append(f"<{tag}> is never closed")


def _doc(text):
    d = _Doc()
    d.feed(text)
    d.close()
    return d


def _css(text):
    d = _doc(text)
    blocks = "\n".join(d.style)
    return re.sub(r"/\*.*?\*/", "", blocks, flags=re.S)


@check("html.well_formed")
def _(text):
    d = _doc(text)
    return (not d.problems, "Tags are balanced." if not d.problems else "Problem: " + d.problems[0])


@check("html.doctype_lang")
def _(text):
    d = _doc(text)
    html_attrs = next((a for t, a in d.tags if t == "html"), None)
    ok = d.doctype and html_attrs is not None and bool(html_attrs.get("lang"))
    return ok, "DOCTYPE and <html lang> present." if ok else "Add <!DOCTYPE html> and <html lang=\"en\">."


@check("html.title")
def _(text):
    d = _doc(text)
    return bool(d.title.strip()), "Page has a title." if d.title.strip() else "Add a non-empty <title>."


@check("html.viewport")
def _(text):
    d = _doc(text)
    ok = any(t == "meta" and a.get("name", "").lower() == "viewport" and "width=device-width" in a.get("content", "") for t, a in d.tags)
    return ok, "Viewport meta tag found." if ok else "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">."


@check("html.landmarks")
def _(text, need=("header", "nav", "main", "footer")):
    present = {t for t, _ in _doc(text).tags}
    missing = [n for n in need if n not in present]
    return not missing, "All landmarks used." if not missing else "Missing semantic elements: " + ", ".join(missing)


@check("html.heading_outline")
def _(text):
    levels = [int(t[1]) for t, _ in _doc(text).tags if re.fullmatch(r"h[1-6]", t)]
    if levels.count(1) != 1:
        return False, f"Use exactly one <h1> (found {levels.count(1)})."
    for prev, cur in zip(levels, levels[1:]):
        if cur - prev > 1:
            return False, f"Heading levels skip from h{prev} to h{cur}."
    return True, "Single h1 and no skipped heading levels."


@check("html.img_alt")
def _(text, min_images=1):
    imgs = [a for t, a in _doc(text).tags if t == "img"]
    if len(imgs) < min_images:
        return False, f"Include at least {min_images} image(s) with alt text."
    missing = [a for a in imgs if "alt" not in a]
    return not missing, "Every image has alt text." if not missing else f"{len(missing)} image(s) have no alt attribute."


@check("html.form_labels")
def _(text, min_fields=2):
    d = _doc(text)
    fields = [a for t, a in d.tags if t in {"input", "select", "textarea"} and a.get("type", "text") not in {"hidden", "submit", "button", "reset"}]
    if len(fields) < min_fields:
        return False, f"The form needs at least {min_fields} fields."
    unlabeled = [a for a in fields if not (a.get("id") in d.label_for or a.get("_wrapped") or a.get("aria-label"))]
    return not unlabeled, "Every field has a label." if not unlabeled else f"{len(unlabeled)} field(s) have no <label for=...>, wrapping label or aria-label."


@check("html.form_submit")
def _(text):
    tags = _doc(text).tags
    has_form = any(t == "form" for t, _ in tags)
    submit = any((t == "button" and a.get("type", "submit") == "submit") or (t == "input" and a.get("type") == "submit") for t, a in tags)
    return has_form and submit, "Form with a submit control." if has_form and submit else "Add a <form> containing a submit button."


@check("html.list")
def _(text, min_items=3):
    d = _doc(text)
    items = sum(1 for t, _ in d.tags if t == "li")
    lists = any(t in {"ul", "ol"} for t, _ in d.tags)
    return lists and items >= min_items, f"Found a list with {items} items." if lists and items >= min_items else f"Use a <ul>/<ol> with at least {min_items} <li> items."


@check("html.links")
def _(text, min_links=2):
    links = [a for t, a in _doc(text).tags if t == "a"]
    good = [a for a in links if a.get("href", "").strip() not in {"", "#"}]
    return len(good) >= min_links, f"{len(good)} meaningful link(s)." if len(good) >= min_links else f"Include at least {min_links} links with real href values."


@check("html.no_deprecated")
def _(text):
    bad = {"font", "center", "marquee", "blink", "big", "strike"} & {t for t, _ in _doc(text).tags}
    return not bad, "No deprecated tags." if not bad else "Deprecated tags used: " + ", ".join(sorted(bad))


@check("html.no_inline_style_overuse")
def _(text, limit=3):
    n = sum(1 for _, a in _doc(text).tags if a.get("style"))
    return n <= limit, "Styling lives in CSS, not style=\"\" attributes." if n <= limit else f"{n} inline style attributes; move them into the <style> block."


@check("css.media_query")
def _(text):
    ok = bool(re.search(r"@media[^{]*\((?:max|min)-width", _css(text)))
    return ok, "Responsive @media query found." if ok else "Add an @media (max-width / min-width) rule."


@check("css.modern_layout")
def _(text):
    ok = bool(re.search(r"display\s*:\s*(flex|grid|inline-flex|inline-grid)", _css(text)))
    return ok, "Flexbox/Grid layout used." if ok else "Use display:flex or display:grid for layout."


@check("css.relative_units")
def _(text):
    css = _css(text)
    ok = len(re.findall(r"\d(?:rem|em|%|vw|vh|ch)\b", css)) >= 3
    return ok, "Relative units used." if ok else "Use relative units (rem, em, %, vw) in at least three places."


@check("css.interaction_states")
def _(text):
    ok = bool(re.search(r":(hover|focus|focus-visible)", _css(text)))
    return ok, "Hover/focus styles present." if ok else "Add :hover and :focus styles for links or buttons."


@check("css.variables")
def _(text):
    css = _css(text)
    ok = bool(re.search(r"--[\w-]+\s*:", css)) and "var(--" in css
    return ok, "CSS custom properties used." if ok else "Define and use CSS variables (--name: ...; var(--name))."


@check("css.nonempty")
def _(text, min_rules=6):
    n = len(re.findall(r"\{", _css(text)))
    return n >= min_rules, f"{n} CSS blocks." if n >= min_rules else f"Write at least {min_rules} CSS rules."


# ================================================================= JavaScript (static)
def _js(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(^|[^:\\])//.*", r"\1", text)


def _js_pattern(pattern, ok_msg, bad_msg, flags=re.S):
    def fn(text):
        found = bool(re.search(pattern, _js(text), flags))
        return found, ok_msg if found else bad_msg
    return fn


CHECKS["js.not_empty"] = lambda t: (len(_js(t).strip()) >= 150, "Enough code to assess." if len(_js(t).strip()) >= 150 else "Submission looks too short to be a working solution.")
CHECKS["js.dom_select"] = _js_pattern(r"(querySelector(All)?|getElementById|getElementsBy\w+)\s*\(", "Selects DOM elements.", "Select elements with querySelector / getElementById.")
CHECKS["js.events"] = _js_pattern(r"addEventListener\s*\(", "Uses addEventListener.", "Attach behaviour with addEventListener (not inline onclick).")
CHECKS["js.dom_create"] = _js_pattern(r"(createElement|textContent|append(Child)?|insertAdjacent)", "Builds/updates DOM nodes.", "Create or update DOM nodes (createElement, textContent, append).")
CHECKS["js.modern_vars"] = lambda t: (bool(re.search(r"\b(const|let)\b", _js(t))) and not re.search(r"\bvar\s+\w", _js(t)), "Uses const/let and avoids var." if (re.search(r"\b(const|let)\b", _js(t)) and not re.search(r"\bvar\s+\w", _js(t))) else "Use const/let instead of var.")
CHECKS["js.strict_equality"] = lambda t: (not re.search(r"[^=!<>]==[^=]|!=[^=]", _js(t)) and "===" in _js(t), "Uses === / !==." if (not re.search(r"[^=!<>]==[^=]|!=[^=]", _js(t)) and "===" in _js(t)) else "Prefer === and !== over == and !=.")
CHECKS["js.array_methods"] = _js_pattern(r"\.(map|filter|reduce|find|some|every|forEach)\s*\(", "Uses array methods.", "Use array methods such as map/filter/reduce.")
CHECKS["js.arrow_or_functions"] = lambda t: (len(re.findall(r"=>|\bfunction\b", _js(t))) >= 3, "Several functions defined." if len(re.findall(r"=>|\bfunction\b", _js(t))) >= 3 else "Break the logic into at least three small functions.")
CHECKS["js.template_literals"] = _js_pattern(r"`[^`]*\$\{", "Template literals used.", "Use a template literal (`...${value}...`) when building strings.")
CHECKS["js.async_fetch"] = _js_pattern(r"\bfetch\s*\(", "Calls fetch().", "Load data with fetch().")
CHECKS["js.await_or_then"] = _js_pattern(r"(\bawait\b|\.then\s*\()", "Handles promises (await/.then).", "Handle the promise with async/await or .then().")
CHECKS["js.error_handling"] = _js_pattern(r"(\btry\s*\{.*\bcatch\b|\.catch\s*\()", "Handles errors.", "Handle failures with try/catch or .catch().")
CHECKS["js.response_ok"] = _js_pattern(r"(\.ok\b|\.status\b)", "Checks response.ok/status.", "Check response.ok before using the data (fetch does not throw on 404/500).")
CHECKS["js.json"] = _js_pattern(r"(\.json\s*\(|JSON\.(parse|stringify))", "Parses/serialises JSON.", "Use response.json() or JSON.parse.")
CHECKS["js.no_eval"] = lambda t: (not re.search(r"\beval\s*\(|document\.write\s*\(|new Function\s*\(", _js(t)), "No eval/document.write." if not re.search(r"\beval\s*\(|document\.write\s*\(|new Function\s*\(", _js(t)) else "Avoid eval(), document.write() and new Function().")
CHECKS["js.safe_text"] = lambda t: ("textContent" in _js(t) or "innerText" in _js(t), "Inserts text safely." if ("textContent" in _js(t) or "innerText" in _js(t)) else "Insert user-provided text with textContent (not innerHTML) to avoid XSS.")
CHECKS["js.state_array"] = _js_pattern(r"(\b(const|let)\s+\w+\s*=\s*\[|\.push\s*\(|\.splice\s*\(|\.filter\s*\()", "Keeps state in an array.", "Keep the to-do items in an array (push/filter).")


# ====================================================================== Dockerfile
def _docker_lines(text):
    joined = re.sub(r"\\\s*\n", " ", text)
    out = []
    for raw in joined.splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            op, _, rest = line.partition(" ")
            out.append((op.upper(), rest.strip()))
    return out


@check("docker.from_pinned")
def _(text):
    froms = [r for op, r in _docker_lines(text) if op == "FROM"]
    if not froms:
        return False, "Start with a FROM instruction."
    image = froms[0].split()[0]
    pinned = ":" in image.split("/")[-1] and not image.endswith(":latest")
    return pinned, "Base image is pinned to a version tag." if pinned else "Pin the base image to a specific tag (e.g. python:3.12-slim), not :latest."


@check("docker.small_base")
def _(text):
    froms = [r for op, r in _docker_lines(text) if op == "FROM"]
    ok = bool(froms) and bool(re.search(r"slim|alpine|distroless", froms[0]))
    return ok, "Small base image." if ok else "Use a -slim or -alpine base image to keep the image small."


@check("docker.workdir")
def _(text):
    ok = any(op == "WORKDIR" for op, _ in _docker_lines(text))
    return ok, "WORKDIR set." if ok else "Set a WORKDIR instead of cd-ing inside RUN."


@check("docker.layer_caching")
def _(text):
    lines = _docker_lines(text)
    copies = [(i, r) for i, (op, r) in enumerate(lines) if op in {"COPY", "ADD"}]
    req = [i for i, r in copies if re.search(r"requirements|package(-lock)?\.json|pyproject", r)]
    full = [i for i, r in copies if re.match(r"\.\s+\S+|\.\/?\s", r + " ") and not re.search(r"requirements|package", r)]
    run_install = [i for i, (op, r) in enumerate(lines) if op == "RUN" and re.search(r"pip install|npm (ci|install)|poetry install", r)]
    ok = bool(req and full and run_install and req[0] < run_install[0] < full[0])
    return ok, "Dependencies are installed before the source is copied (good layer caching)." if ok else "COPY requirements.txt, RUN pip install, and only THEN COPY the rest, so rebuilds reuse the dependency layer."


@check("docker.no_cache_pip")
def _(text):
    installs = [r for op, r in _docker_lines(text) if op == "RUN" and "pip install" in r]
    ok = bool(installs) and all("--no-cache-dir" in r for r in installs)
    return ok, "pip cache disabled." if ok else "Use pip install --no-cache-dir to avoid storing the download cache in the image."


@check("docker.non_root")
def _(text):
    users = [r.split()[0] for op, r in _docker_lines(text) if op == "USER" and r.split()]
    ok = bool(users) and users[-1] not in {"root", "0"}
    return ok, "Runs as a non-root user." if ok else "Add a USER instruction so the container does not run as root."


@check("docker.expose")
def _(text):
    ok = any(op == "EXPOSE" and re.search(r"\d{2,5}", r) for op, r in _docker_lines(text))
    return ok, "Port documented with EXPOSE." if ok else "Document the port with EXPOSE."


@check("docker.cmd_exec_form")
def _(text):
    cmds = [r for op, r in _docker_lines(text) if op in {"CMD", "ENTRYPOINT"}]
    ok = bool(cmds) and all(c.lstrip().startswith("[") for c in cmds)
    return ok, "CMD uses exec form." if ok else "Use exec form: CMD [\"gunicorn\", \"app:app\"] (JSON array), so signals reach your app."


@check("docker.no_secrets")
def _(text):
    bad = [r for op, r in _docker_lines(text) if op in {"ENV", "ARG"} and re.search(r"(PASSWORD|SECRET|TOKEN|API_?KEY)\s*[= ]\s*\S+", r, re.I)]
    return not bad, "No secrets baked into the image." if not bad else "Do not bake secrets into ENV/ARG; inject them at runtime."


@check("docker.healthcheck_or_labels")
def _(text):
    ok = any(op in {"HEALTHCHECK", "LABEL"} for op, _ in _docker_lines(text))
    return ok, "HEALTHCHECK/LABEL present." if ok else "Add a HEALTHCHECK (or LABELs) so the platform can monitor the container."


# ================================================================ IAM policy (JSON)
def _policy(text):
    return json.loads(text)


def _statements(doc):
    st = doc.get("Statement", [])
    return st if isinstance(st, list) else [st]


def _as_list(v):
    return v if isinstance(v, list) else [v]


@check("iam.valid_json")
def _(text):
    try:
        doc = _policy(text)
    except ValueError as exc:
        return False, f"Not valid JSON: {exc}"
    ok = isinstance(doc, dict) and doc.get("Version") == "2012-10-17" and bool(_statements(doc))
    return ok, "Valid policy document." if ok else "Include \"Version\": \"2012-10-17\" and a non-empty \"Statement\"."


@check("iam.allows_get_object")
def _(text):
    doc = _policy(text)
    ok = any(s.get("Effect") == "Allow" and "s3:GetObject" in _as_list(s.get("Action", [])) for s in _statements(doc))
    return ok, "Allows s3:GetObject." if ok else "Add an Allow statement for s3:GetObject."


@check("iam.no_wildcards")
def _(text):
    doc = _policy(text)
    acts = [a for s in _statements(doc) for a in _as_list(s.get("Action", []))]
    bad = [a for a in acts if a == "*" or a.endswith(":*")]
    return not bad, "No wildcard actions." if not bad else f"Wildcard action(s) {bad}: grant only the actions needed."


@check("iam.specific_resource")
def _(text, bucket="reports-prod"):
    doc = _policy(text)
    res = [r for s in _statements(doc) if s.get("Effect") == "Allow" for r in _as_list(s.get("Resource", []))]
    ok = bool(res) and all(r != "*" and r.startswith("arn:aws:s3:::" + bucket) for r in res)
    return ok, f"Scoped to the {bucket} bucket." if ok else f"Scope every Resource to arn:aws:s3:::{bucket} (never \"*\")."


@check("iam.object_arn_for_get")
def _(text, bucket="reports-prod"):
    doc = _policy(text)
    ok = any(s.get("Effect") == "Allow" and "s3:GetObject" in _as_list(s.get("Action", []))
             and any(r == f"arn:aws:s3:::{bucket}/*" for r in _as_list(s.get("Resource", []))) for s in _statements(doc))
    return ok, "GetObject targets objects (bucket/*)." if ok else f"s3:GetObject applies to objects: use arn:aws:s3:::{bucket}/*."


@check("iam.list_bucket_separate")
def _(text, bucket="reports-prod"):
    doc = _policy(text)
    ok = any(s.get("Effect") == "Allow" and "s3:ListBucket" in _as_list(s.get("Action", []))
             and any(r == f"arn:aws:s3:::{bucket}" for r in _as_list(s.get("Resource", []))) for s in _statements(doc))
    return ok, "ListBucket targets the bucket ARN." if ok else f"s3:ListBucket applies to the bucket itself: arn:aws:s3:::{bucket} (no /*)."


@check("iam.read_only")
def _(text):
    doc = _policy(text)
    acts = [a for s in _statements(doc) for a in _as_list(s.get("Action", []))]
    bad = [a for a in acts if re.search(r"Put|Delete|Create|Update|Restore|Replicate", a)]
    return not bad, "Read-only policy." if not bad else f"Remove write/delete actions: {bad}."


# =================================================================== written text
def _words(text):
    return re.findall(r"[A-Za-z0-9'’-]+", text)


@check("text.length")
def _(text, low=80, high=450):
    n = len(_words(text))
    return low <= n <= high, f"{n} words." if low <= n <= high else f"{n} words: aim for {low}-{high} (clear but complete)."


@check("text.sections")
def _(text, names=("summary", "steps", "expected", "actual", "environment"), need=4):
    low = text.lower()
    found = [n for n in names if re.search(rf"(^|\n)\s*[#*_\-]*\s*{n}\b", low)]
    return len(found) >= need, f"Sections found: {', '.join(found)}." if len(found) >= need else f"Use clearly labelled sections ({', '.join(names)}); found {len(found)} of {need} needed."


@check("text.numbered_steps")
def _(text, minimum=3):
    n = len(re.findall(r"(?m)^\s*(?:\d+[.)]|[-*])\s+\S", text))
    return n >= minimum, f"{n} list items." if n >= minimum else f"Write the reproduction steps as a numbered list (at least {minimum})."


@check("text.concrete_details")
def _(text, minimum=3):
    signals = [r"\b\d+(\.\d+){1,2}\b", r"https?://\S+|/[\w./-]{3,}", r"\b(error|exception|status|http)\s*[:=]?\s*\w*\d{3}\b|\bTraceback\b|\b[A-Z][a-zA-Z]+Error\b",
               r"\b(chrome|firefox|safari|edge|windows|macos|linux|ubuntu|android|ios|python|node)\b", r"\b\d+\s?(ms|s|seconds|minutes|users|requests|%)\b"]
    hits = sum(1 for s in signals if re.search(s, text, re.I))
    return hits >= minimum, f"{hits} kinds of concrete detail." if hits >= minimum else "Add specifics: versions, URLs, exact error text, environment, counts or timings."


@check("text.states_impact")
def _(text):
    ok = bool(re.search(r"\b(impact|affect(s|ed|ing)?|users?|customers?|blocked|unable|cannot|can't|severity|priority)\b", text, re.I))
    return ok, "Explains the impact." if ok else "Say who or what is affected (impact/severity)."


@check("text.next_step")
def _(text):
    ok = bool(re.search(r"\b(workaround|mitigat\w+|suggest\w*|propos\w+|recommend\w*|next step|fix|rollback|roll back)\b", text, re.I))
    return ok, "Proposes a next step." if ok else "Suggest a workaround, fix or next step."


@check("text.tone")
def _(text):
    bad = re.search(r"\b(stupid|idiot|obviously|useless|garbage|incompetent|your fault|lazy)\b", text, re.I)
    return not bad, "Neutral, professional tone." if not bad else "Keep the tone neutral: describe the problem, not people."


@check("text.sentence_length")
def _(text, limit=26):
    sentences = [s for s in re.split(r"[.!?]\s+|\n+", text) if len(_words(s)) > 2]
    if not sentences:
        return False, "Write complete sentences."
    avg = sum(len(_words(s)) for s in sentences) / len(sentences)
    return avg <= limit, f"Average sentence length {avg:.0f} words." if avg <= limit else f"Sentences average {avg:.0f} words: shorten them (aim for under {limit})."


@check("text.mentions")
def _(text, patterns=(), need=None):
    need = len(patterns) if need is None else need
    hits = [p for p in patterns if re.search(p, text, re.I)]
    missing = len(patterns) - len(hits)
    return len(hits) >= need, "Mentions the key facts from the scenario." if len(hits) >= need else f"Include the key facts from the scenario ({missing} still missing)."
