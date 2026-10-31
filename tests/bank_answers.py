"""Known-good answers for the command labs and rubric assignments (used only by tests, never served)."""

COMMANDS = {
    "git-command-lab": {"g1": "git checkout -b feature/login", "g2": "git add app.py", "g3": 'git commit -m "Add login form"',
                        "g4": "git reset --soft HEAD~1", "g5": "git push -u origin feature/login", "g6": "git log --oneline",
                        "g7": "git revert abc123", "g8": "git merge feature/login", "g9": "git diff"},
    "django-snippet-lab": {"d1": "title = models.CharField(max_length=200)", "d2": "path('posts/<int:pk>/', views.post_detail, name='post_detail'),",
                           "d3": "python manage.py makemigrations", "d4": "Post.objects.filter(published=True).order_by('-created')",
                           "d5": "{% for post in posts %}", "d6": "post = get_object_or_404(Post, pk=pk)", "d7": "{% csrf_token %}",
                           "d8": "admin.site.register(Post)"},
    "excel-formula-lab": {"x1": '=SUMIF(A2:A101, "North", C2:C101)', "x2": "=C2*D2", "x3": '=COUNTIF(C2:C101,">50")',
                          "x4": '=averageif(B2:B101,"Pen",D2:D101)', "x5": "=XLOOKUP(H1,$J$2:$J$20,$K$2:$K$20)", "x6": '=IF(C2>=100,"High","Low")',
                          "x7": "=COUNTA(UNIQUE(A2:A101))", "x8": "=SUMPRODUCT(C2:C101,D2:D101)"},
    "linux-command-lab": {"l1": 'grep -c "ERROR" app.log', "l2": 'find . -name "*.py"', "l3": "chmod u+x script.sh", "l4": "echo done >> log.txt",
                          "l5": "tail -n 20 -f server.log", "l6": "du -sh *", "l7": "sort -u names.txt", "l8": "lsof -i :8000",
                          "l9": "sed -i 's/foo/bar/g' config.txt"},
    "security-tools-lab": {"s1": "nmap -sV 192.168.1.10", "s2": "nmap -p- 10.0.0.5", "s3": "http && ip.src == 10.0.0.5",
                           "s4": "sudo tcpdump -i eth0 tcp port 443", "s5": "curl -I https://example.com", "s6": "nmap -sn 192.168.1.0/24",
                           "s7": "sha256sum file.iso", "s8": "grep 'Failed password' /var/log/auth.log"},
    "docker-cli-lab": {"k1": "docker build -t myapp:1.0 .", "k2": "docker run -d -p 8080:8000 myapp:1.0", "k3": "docker ps",
                       "k4": "docker logs -f web", "k5": "docker exec -it web sh", "k6": "docker run -v data:/var/lib/app myapp",
                       "k7": "docker container prune", "k8": "docker compose up -d"},
}
# Plausible WRONG answers that must be rejected (unsafe, reversed, or subtly different)
WRONG_COMMANDS = {
    "git-command-lab": {"g2": "git add .", "g4": "git reset --hard HEAD~1", "g7": "git reset --hard abc123", "g9": "git diff --staged"},
    "linux-command-lab": {"l4": "echo done > log.txt", "l9": "sed -i 's/foo/bar/' config.txt"},
    "excel-formula-lab": {"x5": "=VLOOKUP(H1,J2:K20,2)"},
    "docker-cli-lab": {"k2": "docker run -d -p 8000:8080 myapp:1.0"},
}

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bean There Cafe</title>
<style>
:root { --brand: #7c4a2d; --bg: #fffaf5; }
body { margin: 0; font-family: system-ui, sans-serif; background: var(--bg); color: #222; line-height: 1.6; }
header, footer { background: var(--brand); color: #fff; padding: 1rem 2rem; }
nav { display: flex; gap: 1.5rem; }
nav a { color: #fff; text-decoration: none; }
nav a:hover, nav a:focus { text-decoration: underline; }
main { max-width: 60rem; margin: 0 auto; padding: 2rem 1rem; }
.menu { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
img { max-width: 100%; }
@media (max-width: 40rem) { .menu { grid-template-columns: 1fr; } nav { flex-direction: column; } }
</style>
</head>
<body>
<header><nav aria-label="Main"><a href="#menu">Menu</a><a href="#contact">Contact</a></nav></header>
<main>
  <h1>Bean There Cafe</h1>
  <img src="cafe.jpg" alt="Inside the cafe with wooden tables">
  <section id="menu"><h2>Menu</h2>
    <ul class="menu"><li>Flat white</li><li>Cold brew</li><li>Almond croissant</li></ul></section>
  <section id="contact"><h2>Contact us</h2>
    <form action="/contact" method="post">
      <label for="name">Name</label><input id="name" name="name" type="text">
      <label for="email">Email</label><input id="email" name="email" type="email">
      <button type="submit">Send</button>
    </form></section>
</main>
<footer><p>Open daily 8am to 6pm</p></footer>
</body>
</html>
"""

JS = """const list = document.querySelector('#list');
const status = document.querySelector('#status');
const input = document.querySelector('#new-todo');
let todos = [];

function render(items) {
  list.textContent = '';
  items.forEach(item => {
    const li = document.createElement('li');
    li.textContent = `${item.text}${item.done ? ' (done)' : ''}`;
    li.addEventListener('click', () => toggle(item.id));
    list.appendChild(li);
  });
}

function toggle(id) {
  todos = todos.map(t => t.id === id ? { ...t, done: !t.done } : t);
  render(todos);
}

function remove(id) {
  todos = todos.filter(t => t.id !== id);
  render(todos);
}

function add(text) {
  if (text === '') return;
  todos.push({ id: Date.now(), text, done: false });
  render(todos);
}

async function load() {
  try {
    const response = await fetch('/api/todos');
    if (!response.ok) throw new Error(`Server said ${response.status}`);
    todos = await response.json();
    render(todos);
  } catch (err) {
    status.textContent = 'Could not load your to-dos: ' + err.message;
  }
}

document.querySelector('#add').addEventListener('click', () => { add(input.value.trim()); input.value = ''; });
load();
"""

DOCKERFILE = """FROM python:3.12-slim
LABEL maintainer="team@example.com"
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
"""

IAM = """{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": "arn:aws:s3:::reports-prod/*"},
    {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": "arn:aws:s3:::reports-prod"}
  ]
}"""
IAM_BAD = """{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"}]}"""

BUG_REPORT = """Summary:
Checkout shows a blank page on Safari 17 (iPhone) after tapping Pay now, since release 2.4.1.

Steps to reproduce:
1. Open the store on an iPhone using Safari 17.
2. Add any item to the cart and go to checkout.
3. Tap Pay now.

Expected result:
The payment form opens.

Actual result:
A blank white page appears. The console shows TypeError: undefined is not an object (evaluating 'cart.items.length') at checkout.js:88.

Environment:
Safari 17 on iOS. Chrome and Android are not affected. Started after release 2.4.1 on Tuesday.

Impact:
About 12% of orders in the last two days are affected, roughly 340 users cannot pay.

Suggested next step:
Roll back 2.4.1 as a workaround, then add a null check for cart.items in checkout.js.
"""

RUBRICS = {"responsive-landing-page": HTML, "js-todo-widget": JS, "dockerfile-review": DOCKERFILE,
           "iam-least-privilege": IAM, "bug-report-writing": BUG_REPORT}
