"""SQL labs (queries are really executed) and command/formula labs (answers checked against accepted patterns)."""
from . import Assignment

SCHEMA = """
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, city TEXT, signup_date TEXT);
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, status TEXT);
CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, quantity INTEGER);
INSERT INTO customers VALUES (1,'Asha','Pune','2023-03-14'),(2,'Ravi','Delhi','2023-11-02'),(3,'Meena','Pune','2024-01-20'),
  (4,'Karan','Mumbai','2024-02-11'),(5,'Divya','Delhi','2024-05-30'),(6,'Imran','Pune','2024-07-08'),
  (7,'Sara','Chennai','2024-09-01'),(8,'Tej','Mumbai','2022-12-25');
INSERT INTO products VALUES (1,'Laptop','Electronics',55000),(2,'Phone','Electronics',22000),(3,'Headphones','Electronics',2500),
  (4,'Desk','Furniture',8500),(5,'Chair','Furniture',4200),(6,'Notebook','Stationery',120),(7,'Pen','Stationery',25),
  (8,'Backpack','Accessories',1800);
INSERT INTO orders VALUES (1,1,'2024-01-05','completed'),(2,1,'2024-02-10','completed'),(3,2,'2024-02-15','cancelled'),
  (4,3,'2024-03-01','completed'),(5,4,'2024-03-12','pending'),(6,5,'2024-06-02','completed'),(7,6,'2024-07-20','completed'),
  (8,3,'2024-08-14','pending'),(9,2,'2024-09-09','completed'),(10,1,'2024-10-01','completed');
INSERT INTO order_items VALUES (1,1,1,1),(2,1,3,2),(3,2,6,10),(4,2,7,20),(5,3,2,1),(6,4,4,1),(7,4,5,2),(8,5,8,1),(9,5,6,5),
  (10,6,2,1),(11,6,3,1),(12,7,5,1),(13,7,7,10),(14,8,1,1),(15,9,3,3),(16,9,8,2),(17,10,4,1),(18,10,6,4);
"""
SCHEMA_TEXT = """Tables (SQLite):
  customers(id, name, city, signup_date)        signup_date is text like '2024-01-20'
  products(id, name, category, price)
  orders(id, customer_id, order_date, status)    status: completed | pending | cancelled
  order_items(id, order_id, product_id, quantity)

Write ONE SELECT statement per question. Column ORDER matters (names do not). Only SELECT queries are allowed."""


def Qs(id_, topic, label, expected_sql, ordered=False, weight=1):
    return {"id": id_, "topic": topic, "label": label, "expected_sql": expected_sql, "ordered": ordered, "weight": weight}


def sql_lab(slug, title, summary, ceiling, minutes, questions):
    prompts = "\n".join(f"{q['id'].upper()}. {q['label']}" for q in questions)
    return Assignment(slug=slug, skill="sql-databases", kind="sql", title=title, summary=summary, ceiling=ceiling, minutes=minutes,
                      instructions=SCHEMA_TEXT, spec={"schema": SCHEMA, "questions": questions, "prompt_text": prompts})


def P(id_, topic, label, accept, hint, reject=(), ci=False, strip=False, weight=1):
    return {"id": id_, "topic": topic, "label": label, "accept": accept, "hint": hint, "reject": list(reject), "ci": ci,
            "strip_spaces": strip, "weight": weight}


def lab(slug, skill, title, summary, ceiling, minutes, instructions, prompts):
    return Assignment(slug=slug, skill=skill, kind="commands", title=title, summary=summary, ceiling=ceiling, minutes=minutes,
                      instructions=instructions, spec={"prompts": prompts})


def rng(col, a=2, b=101):
    return rf"\$?{col}\$?{a}:\$?{col}\$?{b}"


A_, B_, C_, D_ = rng("A"), rng("B"), rng("C"), rng("D")
J_, K_ = rng("J", 2, 20), rng("K", 2, 20)
CMD_INTRO = ("Type the exact command (one line) for each prompt. Answers are checked against the accepted forms, including common equivalent "
             "variants, and against dangerous or wrong alternatives. {extra}")

ASSIGNMENTS = [
    sql_lab("sql-foundations", "SQL foundations lab", "Filter, sort, count and average on a small shop database.", 3, 20, [
        Qs("q1", "filtering", "List the name and city of every customer who lives in 'Pune', alphabetically by name.",
           "SELECT name, city FROM customers WHERE city = 'Pune' ORDER BY name", ordered=True),
        Qs("q2", "sorting", "Show the name and price of products costing more than 500, most expensive first.",
           "SELECT name, price FROM products WHERE price > 500 ORDER BY price DESC", ordered=True),
        Qs("q3", "aggregation", "How many orders are there for each status? Columns: status, count.",
           "SELECT status, COUNT(*) FROM orders GROUP BY status"),
        Qs("q4", "aggregation", "Average product price per category rounded to 2 decimals. Columns: category, average.",
           "SELECT category, ROUND(AVG(price), 2) FROM products GROUP BY category"),
        Qs("q5", "dates", "Customers who signed up on or after 2024-01-01: name and signup_date, newest signup first.",
           "SELECT name, signup_date FROM customers WHERE signup_date >= '2024-01-01' ORDER BY signup_date DESC", ordered=True),
    ]),
    sql_lab("sql-analyst", "SQL analyst lab", "Joins, grouping, anti-joins, HAVING, CASE and top-N on the same database.", 5, 40, [
        Qs("q1", "joins", "Every order with its customer's name: order id, customer name, status. Sorted by order id.",
           "SELECT o.id, c.name, o.status FROM orders o JOIN customers c ON c.id = o.customer_id ORDER BY o.id", ordered=True),
        Qs("q2", "joins + aggregation", "Total quantity sold per product that has been sold: product name, total quantity. Highest first; ties by name A-Z.",
           "SELECT p.name, SUM(oi.quantity) AS q FROM products p JOIN order_items oi ON oi.product_id = p.id GROUP BY p.id ORDER BY q DESC, p.name",
           ordered=True, weight=2),
        Qs("q3", "anti-join", "Names of customers who have never placed an order.",
           "SELECT name FROM customers WHERE id NOT IN (SELECT customer_id FROM orders)", weight=2),
        Qs("q4", "having", "Revenue (quantity x price) per customer counting only 'completed' orders, keeping customers above 1000: name, revenue. Highest first.",
           "SELECT c.name, SUM(oi.quantity * p.price) AS revenue FROM customers c JOIN orders o ON o.customer_id = c.id "
           "JOIN order_items oi ON oi.order_id = o.id JOIN products p ON p.id = oi.product_id WHERE o.status = 'completed' "
           "GROUP BY c.id HAVING revenue > 1000 ORDER BY revenue DESC", ordered=True, weight=3),
        Qs("q5", "top-N", "The single product category with the highest total revenue over ALL order items: category, revenue.",
           "SELECT p.category, SUM(oi.quantity * p.price) AS revenue FROM order_items oi JOIN products p ON p.id = oi.product_id "
           "GROUP BY p.category ORDER BY revenue DESC LIMIT 1", weight=2),
        Qs("q6", "CASE", "Label each product's price tier: 'budget' under 500, 'standard' from 500 up to 9999, 'premium' from 10000. Columns: name, tier.",
           "SELECT name, CASE WHEN price < 500 THEN 'budget' WHEN price < 10000 THEN 'standard' ELSE 'premium' END FROM products", weight=2),
    ]),

    lab("git-command-lab", "git-github", "Git command lab", "Nine everyday and recovery situations, answered with the right command.", 4, 15,
        CMD_INTRO.format(extra="Assume you are inside a repository on branch main."), [
        P("g1", "branching", "Create and switch to a new branch called feature/login.", [r"^git (checkout -b|switch -c) feature/login$"], "one command can create and switch."),
        P("g2", "staging", "Stage ONLY the file app.py.", [r"^git add app\.py$"], "name the file; do not stage everything.",
          reject=[(r"^git add (\.|-A|--all|\*)", "That stages everything; the task asks for only app.py.")]),
        P("g3", "committing", 'Commit the staged changes with the message "Add login form".', [r"^git commit (-a )?-m ?[\"']Add login form[\"']$", r"^git commit -am ?[\"']Add login form[\"']$"], "use -m with the message in quotes."),
        P("g4", "undoing", "Undo the last commit but keep its changes staged.", [r"^git reset --soft (HEAD~1|HEAD~|HEAD\^)$"], "a reset mode that keeps the index.",
          reject=[(r"--hard", "--hard discards your changes; the task wants to keep them.")], weight=2),
        P("g5", "remotes", "Push the current new branch feature/login to origin and set it as upstream.", [r"^git push (-u|--set-upstream) origin feature/login$"], "push with an upstream flag."),
        P("g6", "history", "Show the history with one line per commit.", [r"^git log (--oneline|--pretty=oneline)$"], "git log has a compact mode."),
        P("g7", "undoing", "Commit abc123 is already pushed to the shared main branch and is bad. Undo it WITHOUT rewriting history.", [r"^git revert abc123$"], "create a new commit that reverses it.",
          reject=[(r"reset|--force|push -f", "Rewriting shared history is not safe; use a command that adds a new commit.")], weight=2),
        P("g8", "merging", "Merge feature/login into the branch you are on.", [r"^git merge feature/login$"], "merge the named branch into the current one."),
        P("g9", "inspecting", "Show the changes in your working tree that are NOT staged yet.", [r"^git diff$"], "plain diff, no staging flags.",
          reject=[(r"--(staged|cached)", "That shows staged changes.")]),
    ]),

    lab("django-snippet-lab", "django", "Django snippet lab", "Write the Django line that does each job (models, URLs, ORM, templates, security).", 4, 15,
        CMD_INTRO.format(extra="Whitespace and quote style (' or \") do not matter. Assume a blog app with a Post model."), [
        P("d1", "models", "Model field: a CharField named title with max length 200.", [r"^title\s*=\s*models\.CharField\(\s*max_length\s*=\s*200\s*\)$"], "models.CharField with max_length."),
        P("d2", "urls", "URL pattern: path 'posts/<int:pk>/' to views.post_detail, named 'post_detail'.", [r"^path\(\s*['\"]posts/<int:pk>/['\"]\s*,\s*views\.post_detail\s*,\s*name\s*=\s*['\"]post_detail['\"]\s*\)\s*,?$"], "path(route, view, name=...).", weight=2),
        P("d3", "migrations", "Command that creates migration files after changing models.", [r"^(python3?|py) manage\.py makemigrations$"], "manage.py has a command for this."),
        P("d4", "ORM", "Query: all published Posts (published=True), newest first by the created field.", [r"^Post\.objects\.filter\(\s*published\s*=\s*True\s*\)\.order_by\(\s*['\"]-created['\"]\s*\)$"], "filter, then order_by with a minus for descending.", weight=2),
        P("d5", "templates", "Template tag that starts a loop over a variable posts, naming each item post.", [r"^\{%\s*for post in posts\s*%\}$"], "{% for ... in ... %}"),
        P("d6", "views", "In a view: fetch the Post with primary key pk, or return a 404 (use the shortcut).", [r"^(post\s*=\s*)?get_object_or_404\(\s*Post\s*,\s*pk\s*=\s*pk\s*\)$"], "a shortcut from django.shortcuts."),
        P("d7", "security", "Template tag that protects a POST form against CSRF.", [r"^\{%\s*csrf_token\s*%\}$"], "a built-in template tag."),
        P("d8", "admin", "Register the Post model with the admin site.", [r"^admin\.site\.register\(\s*Post\s*\)$"], "admin.site.register(...)"),
    ]),

    lab("excel-formula-lab", "excel", "Excel formula lab", "Eight formulas over a sales table (spaces in formulas are ignored).", 4, 20,
        CMD_INTRO.format(extra="Data: Region in A2:A101, Product in B2:B101, Units in C2:C101, Price in D2:D101. A product price table is in J2:K20 (name in J, price in K) and the product to find is in H1."), [
        P("x1", "conditional sums", 'Total units for Region "North".', [rf'^=SUMIF\({A_},"North",{C_}\)$', rf'^=SUMIFS\({C_},{A_},"North"\)$'], "SUMIF / SUMIFS.", ci=True, strip=True),
        P("x2", "arithmetic", "In E2: revenue for the row (units x price).", [r"^=(\$?C\$?2\*\$?D\$?2|\$?D\$?2\*\$?C\$?2|PRODUCT\(C2,D2\))$"], "multiply the two cells.", ci=True, strip=True),
        P("x3", "counting", "Count the rows where Units is greater than 50.", [rf'^=COUNTIF\({C_},">50"\)$', rf'^=COUNTIFS\({C_},">50"\)$'], "COUNTIF with a criteria string.", ci=True, strip=True),
        P("x4", "conditional averages", 'Average price of the product "Pen".', [rf'^=AVERAGEIF\({B_},"Pen",{D_}\)$', rf'^=AVERAGEIFS\({D_},{B_},"Pen"\)$'], "AVERAGEIF / AVERAGEIFS.", ci=True, strip=True),
        P("x5", "lookups", "Exact-match lookup: the price (column K) of the product named in H1 (column J).",
          [rf"^=XLOOKUP\(H1,{J_},{K_}\)$", rf"^=VLOOKUP\(H1,\$?J\$?2:\$?K\$?20,2,(FALSE|0)\)$", rf"^=INDEX\({K_},MATCH\(H1,{J_},0\)\)$"],
          "XLOOKUP, or INDEX/MATCH, or VLOOKUP with exact match.", reject=[(r"^=VLOOKUP\([^,]+,[^,]+,2\)$|,(TRUE|1)\)$", "VLOOKUP without FALSE/0 does an approximate match; ask for an exact match.")], ci=True, strip=True, weight=2),
        P("x6", "logic", 'In G2: "High" if Units >= 100, otherwise "Low".', [r'^=IF\(C2>=100,"High","Low"\)$'], "IF(test, then, else).", ci=True, strip=True),
        P("x7", "unique values", "Count how many DIFFERENT regions there are.", [rf"^=COUNTA\(UNIQUE\({A_}\)\)$", rf"^=SUMPRODUCT\(1/COUNTIF\({A_},{A_}\)\)$"], "count the distinct values.", ci=True, strip=True, weight=2),
        P("x8", "array maths", "Total revenue in ONE formula without a helper column (sum of units x price).", [rf"^=SUMPRODUCT\({C_},{D_}\)$"], "a function that multiplies arrays and adds.", ci=True, strip=True, weight=2),
    ]),

    lab("linux-command-lab", "linux-cli", "Linux command-line lab", "Nine real-world shell tasks (search, permissions, redirection, monitoring).", 4, 20,
        CMD_INTRO.format(extra="Assume Bash on Linux and that you are in the right directory."), [
        P("l1", "searching", "Count the lines containing ERROR in app.log.", [r"^grep -c ['\"]?ERROR['\"]? app\.log$", r"^grep ['\"]?ERROR['\"]? app\.log \| wc -l$", r"^cat app\.log \| grep ['\"]?ERROR['\"]? \| wc -l$"], "grep has a count flag, or use a pipe."),
        P("l2", "searching", "Find all .py files under the current directory.", [r"^find \.?/? (-type f )?-name ['\"]?\*\.py['\"]?( -type f)?$"], "find <where> -name <pattern>."),
        P("l3", "permissions", "Make script.sh executable for its owner.", [r"^chmod (u\+x|700|744|755) script\.sh$"], "chmod with u+x or an octal mode."),
        P("l4", "redirection", "Append the text done to log.txt.", [r"^echo ['\"]?done['\"]? >> log\.txt$"], "use the append operator.", reject=[(r"(?<!>)>(?!>)", "A single > overwrites the file; use the append operator.")]),
        P("l5", "monitoring", "Show the last 20 lines of server.log and keep following new lines.", [r"^tail (-n ?20 -f|-f -n ?20|-fn ?20|-n20 -f|-f -n20|-20 -f|-f -20|-F -n ?20|-n ?20 -F) server\.log$"], "tail with a line count and a follow flag.", weight=2),
        P("l6", "disk", "Show the disk usage of every item in the current directory in human-readable form (summarised per item).", [r"^du (-sh|-hs|-h -s|-s -h) (\*|\./\*)$"], "du with summarise and human-readable flags."),
        P("l7", "text processing", "Print names.txt sorted with duplicate lines removed.", [r"^sort -u names\.txt$", r"^sort names\.txt \| uniq$", r"^sort -u < names\.txt$"], "sort has a unique flag, or pipe to uniq."),
        P("l8", "networking", "Find which process is listening on port 8000.", [r"^(sudo )?lsof -i :?8000$", r"^(sudo )?lsof -i tcp:8000$", r"^(sudo )?(ss|netstat) -[a-z]+ \| grep :?8000$"], "lsof -i, or ss/netstat piped to grep.", weight=2),
        P("l9", "text processing", "Replace every foo with bar everywhere in config.txt, editing the file in place.", [r"^sed -i(\.bak)? ['\"]s/foo/bar/g['\"] config\.txt$"], "sed -i with s///g.", weight=2),
    ]),

    lab("security-tools-lab", "security-tools", "Security tools command lab", "Scanning, packet capture, headers and log triage (only against systems you are authorised to test).", 4, 20,
        CMD_INTRO.format(extra="Assume you have permission to test the example systems."), [
        P("s1", "nmap", "Detect service versions on 192.168.1.10.", [r"^(sudo )?nmap -sV 192\.168\.1\.10$"], "nmap has a version-detection flag."),
        P("s2", "nmap", "Scan ALL 65535 TCP ports of 10.0.0.5.", [r"^(sudo )?nmap (-p- |-p 1-65535 )10\.0\.0\.5$", r"^(sudo )?nmap 10\.0\.0\.5 (-p-|-p 1-65535)$"], "the port flag accepts a full range.", weight=2),
        P("s3", "Wireshark", "Wireshark display filter: only HTTP traffic whose source IP is 10.0.0.5.", [r"^http (&&|and) ip\.src ?== ?10\.0\.0\.5$", r"^ip\.src ?== ?10\.0\.0\.5 (&&|and) http$"], "combine two conditions with && / and.", weight=2),
        P("s4", "tcpdump", "Capture only TCP port 443 traffic on interface eth0.", [r"^(sudo )?tcpdump -i eth0 (tcp )?port 443$", r"^(sudo )?tcpdump (tcp )?port 443 -i eth0$"], "tcpdump -i <iface> <filter>."),
        P("s5", "HTTP", "Show only the response headers for https://example.com.", [r"^curl (-I|--head|-sI|-Is) https://example\.com/?$"], "curl can send a HEAD request."),
        P("s6", "nmap", "Host discovery (ping sweep) of 192.168.1.0/24 without scanning ports.", [r"^(sudo )?nmap -s[nP] 192\.168\.1\.0/24$"], "nmap has a no-port-scan mode."),
        P("s7", "integrity", "Compute the SHA-256 checksum of file.iso to verify a download.", [r"^sha256sum file\.iso$", r"^shasum -a 256 file\.iso$", r"^openssl dgst -sha256 file\.iso$"], "a checksum tool with sha256."),
        P("s8", "log triage", "List the failed SSH password attempts in /var/log/auth.log.", [r"^grep ['\"]Failed password['\"] /var/log/auth\.log$", r"^cat /var/log/auth\.log \| grep ['\"]Failed password['\"]$"], "search for the failure message text."),
    ]),

    lab("docker-cli-lab", "docker", "Docker CLI lab", "Build, run, inspect and clean up containers.", 3, 15,
        CMD_INTRO.format(extra="Assume Docker is installed and a Dockerfile is in the current directory."), [
        P("k1", "images", "Build an image from the current directory tagged myapp:1.0.", [r"^docker build -t myapp:1\.0 \.$", r"^docker build \. -t myapp:1\.0$", r"^docker build --tag myapp:1\.0 \.$"], "docker build with a tag and a context."),
        P("k2", "running", "Run myapp:1.0 in the background, publishing host port 8080 to container port 8000.", [r"^docker run -d -p 8080:8000 myapp:1\.0$", r"^docker run -p 8080:8000 -d myapp:1\.0$", r"^docker run --detach --publish 8080:8000 myapp:1\.0$"], "ports are host:container.", reject=[(r"8000:8080", "Ports are host:container; yours is reversed.")], weight=2),
        P("k3", "inspecting", "List the running containers.", [r"^docker ps$", r"^docker container ls$"], "a short ps-style command."),
        P("k4", "inspecting", "Follow the logs of the container named web.", [r"^docker logs -f web$", r"^docker logs --follow web$"], "docker logs with a follow flag."),
        P("k5", "debugging", "Open an interactive shell inside the running container web.", [r"^docker exec -(it|ti) web (sh|bash)$"], "exec with interactive and tty flags."),
        P("k6", "storage", "Run myapp with the named volume data mounted at /var/lib/app.", [r"^docker run( -d)? -v data:/var/lib/app myapp$"], "-v name:path.", weight=2),
        P("k7", "cleanup", "Remove all stopped containers.", [r"^docker container prune( -f)?$", r"^docker rm \$\(docker ps -aq -f status=exited\)$"], "there is a prune command."),
        P("k8", "compose", "Start the services defined in docker-compose.yml in the background.", [r"^docker(-| )compose up (-d|--detach)$"], "compose up with detach."),
    ]),
]
