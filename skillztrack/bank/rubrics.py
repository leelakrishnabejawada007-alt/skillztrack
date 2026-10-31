"""Rubric assignments: the submission is analysed by named checks (see skillztrack/rubric_checks.py).

These are STATIC: they parse and inspect the work but cannot run it or judge how it looks. That is why they are
capped at level 4 (3 for communication) and why they never count as stronger evidence than auto-tested code.
"""
from . import Assignment


def C(id_, topic, label, check, weight=1, **args):
    return {"id": id_, "topic": topic, "label": label, "check": check, "weight": weight, "args": args}


def rubric(slug, skill, title, summary, ceiling, minutes, instructions, starter, criteria, min_chars=60):
    return Assignment(slug=slug, skill=skill, kind="rubric", title=title, summary=summary, ceiling=ceiling, minutes=minutes,
                      instructions=instructions, starter=starter, spec={"criteria": criteria, "min_chars": min_chars})


HTML_STARTER = """<!DOCTYPE html>
<html>
<head>
  <title></title>
  <style>
    /* your CSS here */
  </style>
</head>
<body>
  <!-- your page here -->
</body>
</html>
"""
JS_STARTER = """// Starter HTML (already on the page):
//   <input id="new-todo"> <button id="add">Add</button>
//   <ul id="list"></ul>   <p id="status"></p>
// The server exposes GET /api/todos -> [{"id": 1, "text": "Buy milk", "done": false}, ...]
//
// Write the JavaScript below.

"""
DOCKER_STARTER = """# Write your Dockerfile here
"""
IAM_STARTER = """{
  "Version": "",
  "Statement": []
}
"""
BUG_STARTER = """Summary:

Steps to reproduce:
1.

Expected result:

Actual result:

Environment:

Impact:

Suggested next step:
"""

ASSIGNMENTS = [
    rubric("responsive-landing-page", "html-css", "Build a responsive café landing page", "One HTML file, checked for structure, accessibility and responsive CSS.", 4, 45,
           "Write ONE self-contained HTML file (CSS inside a <style> block) for a small café website. Required: a header with navigation links, a main area with a "
           "hero heading, a list of at least three menu items, at least one image (use any src) , a contact form with at least two labelled fields and a submit button, "
           "and a footer. It must work on phones: use a viewport meta tag, a media query, flexbox or grid and relative units. Use semantic elements, "
           "keep one <h1> with no skipped heading levels, and add hover/focus styles. Your page is parsed and checked against a rubric; it is not rendered.",
           HTML_STARTER, [
        C("h1", "HTML validity", "Tags are properly nested and closed", "html.well_formed"),
        C("h2", "HTML basics", "DOCTYPE and <html lang>", "html.doctype_lang"),
        C("h3", "HTML basics", "Non-empty <title>", "html.title"),
        C("h4", "responsive design", "Viewport meta tag", "html.viewport", weight=2),
        C("h5", "semantics", "header, nav, main and footer are used", "html.landmarks", weight=2),
        C("h6", "semantics", "One <h1>, no skipped heading levels", "html.heading_outline", weight=2),
        C("h7", "accessibility", "Images have alt text", "html.img_alt", min_images=1, weight=2),
        C("h8", "forms", "Every form field has a label", "html.form_labels", min_fields=2, weight=2),
        C("h9", "forms", "Form has a submit button", "html.form_submit"),
        C("h10", "content", "A list with at least three items", "html.list", min_items=3),
        C("h11", "content", "At least two real links", "html.links", min_links=2),
        C("h12", "best practice", "No deprecated tags", "html.no_deprecated"),
        C("h13", "best practice", "Styling lives in CSS, not inline attributes", "html.no_inline_style_overuse"),
        C("c1", "CSS layout", "Uses flexbox or grid", "css.modern_layout", weight=2),
        C("c2", "responsive design", "Has a responsive @media query", "css.media_query", weight=3),
        C("c3", "responsive design", "Uses relative units", "css.relative_units"),
        C("c4", "CSS interaction", "Hover/focus styles", "css.interaction_states"),
        C("c5", "CSS maintainability", "CSS custom properties (variables)", "css.variables"),
        C("c6", "CSS", "A real stylesheet (6+ rules)", "css.nonempty"),
    ], min_chars=200),

    rubric("js-todo-widget", "javascript", "JavaScript: a to-do widget that loads data", "Static checks on DOM handling, array methods, fetch and error handling.", 4, 45,
           "Write the JavaScript for a to-do list widget (starter HTML is described in the editor). It must: load the initial items from GET /api/todos with fetch, "
           "check the response and handle failures (show a message in #status), render items into #list, let the user add an item from #new-todo, toggle done and delete, "
           "and filter to show only unfinished items. Use modern JavaScript (const/let, ===, template literals, array methods, small functions) and insert user text "
           "safely (textContent, not innerHTML). Your code is analysed against a rubric; it is not executed.",
           JS_STARTER, [
        C("j0", "completeness", "Enough code to assess", "js.not_empty"),
        C("j1", "DOM", "Selects DOM elements", "js.dom_select"),
        C("j2", "events", "Uses addEventListener", "js.events", weight=2),
        C("j3", "DOM", "Creates or updates DOM nodes", "js.dom_create"),
        C("j4", "modern JavaScript", "const/let, no var", "js.modern_vars"),
        C("j5", "modern JavaScript", "Strict equality (===)", "js.strict_equality"),
        C("j6", "modern JavaScript", "Array methods (map/filter/reduce/...)", "js.array_methods"),
        C("j7", "code structure", "At least three small functions", "js.arrow_or_functions"),
        C("j8", "modern JavaScript", "Template literals", "js.template_literals"),
        C("j9", "async", "Calls fetch()", "js.async_fetch", weight=2),
        C("j10", "async", "Handles the promise (await/.then)", "js.await_or_then", weight=2),
        C("j11", "error handling", "Handles failures (try/catch or .catch)", "js.error_handling", weight=2),
        C("j12", "error handling", "Checks response.ok / status", "js.response_ok", weight=2),
        C("j13", "async", "Parses JSON", "js.json"),
        C("j14", "security", "Inserts text with textContent (XSS-safe)", "js.safe_text", weight=2),
        C("j15", "security", "No eval / document.write", "js.no_eval"),
        C("j16", "state", "Keeps items in an array", "js.state_array"),
    ], min_chars=150),

    rubric("dockerfile-review", "docker", "Write a production-minded Dockerfile", "A Dockerfile for a Flask app, checked against container best practices.", 4, 25,
           "Write a Dockerfile for a Python (Flask) app that has requirements.txt and app.py in the build context and is served with gunicorn on port 8000 "
           "(module app, object app). Apply container best practices: pinned slim base image, WORKDIR, good layer caching (install dependencies BEFORE copying the source), "
           "no pip cache, a non-root user, EXPOSE, exec-form CMD, no secrets in the image, and a HEALTHCHECK.",
           DOCKER_STARTER, [
        C("d1", "base image", "Base image pinned to a version tag (not :latest)", "docker.from_pinned", weight=2),
        C("d2", "image size", "Slim/alpine base image", "docker.small_base"),
        C("d3", "structure", "WORKDIR is set", "docker.workdir"),
        C("d4", "layer caching", "requirements copied and installed before the source", "docker.layer_caching", weight=3),
        C("d5", "image size", "pip install --no-cache-dir", "docker.no_cache_pip"),
        C("d6", "security", "Runs as a non-root USER", "docker.non_root", weight=3),
        C("d7", "documentation", "EXPOSE documents the port", "docker.expose"),
        C("d8", "runtime", "CMD in exec (JSON array) form", "docker.cmd_exec_form", weight=2),
        C("d9", "security", "No secrets in ENV/ARG", "docker.no_secrets", weight=2),
        C("d10", "operations", "HEALTHCHECK or LABEL present", "docker.healthcheck_or_labels"),
    ], min_chars=40),

    rubric("iam-least-privilege", "cloud-basics", "Write a least-privilege IAM policy", "An AWS-style JSON policy checked for correctness and least privilege.", 4, 20,
           "A reporting service must be able to READ objects from the S3 bucket reports-prod and LIST that bucket. It must not be able to write, delete or touch any other "
           "resource. Write the IAM policy as JSON (Version 2012-10-17). Remember: object actions (s3:GetObject) apply to object ARNs (bucket/*), "
           "while s3:ListBucket applies to the bucket ARN itself. Avoid wildcard actions and \"*\" resources.",
           IAM_STARTER, [
        C("i1", "policy syntax", "Valid JSON with Version and Statement", "iam.valid_json", weight=2),
        C("i2", "permissions", "Allows s3:GetObject", "iam.allows_get_object", weight=2),
        C("i3", "least privilege", "No wildcard actions", "iam.no_wildcards", weight=2),
        C("i4", "least privilege", "Every resource is scoped to reports-prod", "iam.specific_resource", weight=2),
        C("i5", "resource ARNs", "GetObject targets objects (bucket/*)", "iam.object_arn_for_get", weight=2),
        C("i6", "resource ARNs", "ListBucket targets the bucket ARN", "iam.list_bucket_separate", weight=2),
        C("i7", "least privilege", "Read-only (no write/delete actions)", "iam.read_only", weight=2),
    ], min_chars=30),

    rubric("bug-report-writing", "communication", "Write a clear bug report", "Turn raw notes into a report an engineer can act on.", 3, 20,
           "Scenario: customers using Safari 17 on iPhone report that tapping 'Pay now' on the checkout page shows a blank white page. It started after release 2.4.1 "
           "went out on Tuesday. About 12% of orders in the last two days are affected (roughly 340 users). The browser console shows: "
           "TypeError: undefined is not an object (evaluating 'cart.items.length') at checkout.js:88. Chrome and Android are fine. "
           "Write the bug report you would file. Use the labelled sections, numbered steps, concrete details from the scenario, say who is affected, and "
           "suggest a next step (workaround or fix). Keep a neutral tone and short sentences (80-450 words).",
           BUG_STARTER, [
        C("b1", "structure", "Clearly labelled sections", "text.sections", weight=2, need=5),
        C("b2", "reproducibility", "Numbered reproduction steps", "text.numbered_steps", weight=2),
        C("b3", "specificity", "Uses concrete details (versions, errors, numbers)", "text.concrete_details", weight=2),
        C("b4", "scenario facts", "Mentions the key facts: Safari, 2.4.1 and the TypeError", "text.mentions", weight=2,
          patterns=[r"safari", r"2\.4\.1", r"typeerror|cart\.items"], need=3),
        C("b5", "impact", "States who/what is affected", "text.states_impact"),
        C("b6", "next steps", "Suggests a workaround, fix or next step", "text.next_step"),
        C("b7", "tone", "Neutral, professional tone", "text.tone"),
        C("b8", "readability", "Short, readable sentences", "text.sentence_length"),
        C("b9", "length", "Right length (80-450 words)", "text.length", low=80, high=450),
    ], min_chars=80),
]
