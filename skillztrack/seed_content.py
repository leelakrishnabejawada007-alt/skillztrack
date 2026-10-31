"""Starter catalogue. Edit freely, then re-run:  python manage.py seed_data

Safe to run many times: rows are matched by slug / (skill, url) and updated.
NOTE: web links change over time - check them occasionally (or fix them in /admin).
"""

SKILLS = [
    # slug, name, category, description
    ("python", "Python", "programming", "General-purpose language used in web, data, ML and security."),
    ("javascript", "JavaScript", "web", "The language of the browser; adds interactivity to web pages."),
    ("html-css", "HTML & CSS", "web", "Structure and style of every web page, including responsive layouts."),
    ("git-github", "Git & GitHub", "programming", "Version control and collaboration."),
    ("django", "Django", "web", "A batteries-included Python web framework."),
    ("rest-apis", "REST APIs", "web", "Designing and consuming HTTP/JSON interfaces."),
    ("sql-databases", "Databases & SQL", "data", "Storing, querying and modelling data."),
    ("deployment-basics", "Deployment Basics", "web", "Putting an app online: servers, env vars, HTTPS."),
    ("dsa", "Data Structures & Algorithms", "programming", "Core problem-solving toolkit."),
    ("excel", "Excel & Spreadsheets", "data", "Formulas, pivot tables and quick analysis."),
    ("statistics", "Statistics", "data", "Describing data and drawing sound conclusions."),
    ("pandas-numpy", "Pandas & NumPy", "data", "Python libraries for data wrangling."),
    ("data-visualization", "Data Visualization", "data", "Charts and dashboards that tell a story."),
    ("machine-learning", "Machine Learning", "data", "Training models that learn from data."),
    ("deep-learning", "Deep Learning", "data", "Neural networks for images, text and more."),
    ("networking", "Networking Basics", "security", "TCP/IP, DNS, HTTP and how data moves."),
    ("linux-cli", "Linux & Command Line", "security", "Working fluently in a Linux shell."),
    ("web-security", "Web Application Security", "security", "OWASP Top 10 and secure coding."),
    ("cryptography", "Cryptography Basics", "security", "Hashing, encryption and key exchange."),
    ("security-tools", "Security Tools", "security", "Nmap, Wireshark and friends."),
    ("testing", "Testing & Debugging", "programming", "Writing automated tests and finding bugs systematically."),
    ("docker", "Docker & Containers", "web", "Packaging apps so they run the same everywhere."),
    ("cloud-basics", "Cloud Fundamentals", "web", "Core cloud ideas: compute, storage, networking, IAM, pricing."),
    ("communication", "Communication", "professional", "Writing and presenting technical ideas clearly."),
]

# slug, title, tagline, icon, description
CAREERS = [
    # slug, title, tagline, icon name (bi-* names are mapped to the built-in SVG icon set), description
    ("web-developer", "Web Developer", "Build complete web apps, front to back.", "bi-globe2",
     "Web developers design interfaces, write server logic and manage databases. This path takes you from HTML/CSS to a deployed Python web application."),
    ("python-developer", "Python Developer", "Use Python to build apps, tools and services.", "bi-filetype-py",
     "Python developers write clean, tested code for back-end services, automation and tooling. Core language skill, testing and APIs come first."),
    ("data-analyst", "Data Analyst", "Turn raw numbers into decisions.", "bi-bar-chart-line",
     "Data analysts clean data, query databases, find patterns and present insights. Strong SQL, statistics and storytelling are the core."),
    ("cloud-engineer", "Cloud Engineer", "Run reliable systems on the cloud.", "bi-cloud",
     "Cloud engineers deploy and operate applications on cloud platforms. Linux, networking, containers and cloud fundamentals are the foundation."),
    ("cybersecurity-analyst", "Cybersecurity Analyst", "Defend systems and find weaknesses first.", "bi-shield-lock",
     "Security analysts monitor, test and harden systems. Networking, Linux and web security knowledge come first."),
    ("machine-learning-engineer", "Machine Learning Engineer", "Teach computers to learn from data.", "bi-cpu",
     "ML engineers build and ship predictive models. You need solid Python, maths and a feel for the whole modelling workflow."),
]

# career slug -> [(skill slug, required level 1-5, importance 1-3, learning sequence)]
REQUIREMENTS = {
    "web-developer": [
        ("html-css", 4, 3, 1), ("javascript", 4, 3, 2), ("git-github", 3, 2, 3), ("python", 3, 2, 4),
        ("sql-databases", 3, 3, 5), ("django", 3, 3, 6), ("rest-apis", 3, 2, 7), ("deployment-basics", 3, 2, 8),
    ],
    "python-developer": [
        ("python", 4, 3, 1), ("git-github", 3, 2, 2), ("dsa", 3, 2, 3), ("testing", 3, 2, 4),
        ("sql-databases", 3, 2, 5), ("rest-apis", 3, 2, 6), ("django", 3, 2, 7),
    ],
    "data-analyst": [
        ("excel", 4, 2, 1), ("statistics", 3, 3, 2), ("sql-databases", 4, 3, 3), ("python", 3, 3, 4),
        ("pandas-numpy", 4, 3, 5), ("data-visualization", 4, 2, 6), ("communication", 3, 2, 7),
    ],
    "cloud-engineer": [
        ("linux-cli", 4, 3, 1), ("networking", 3, 3, 2), ("python", 3, 2, 3), ("git-github", 3, 1, 4),
        ("docker", 3, 3, 5), ("cloud-basics", 4, 3, 6), ("deployment-basics", 3, 2, 7),
    ],
    "cybersecurity-analyst": [
        ("networking", 4, 3, 1), ("linux-cli", 4, 3, 2), ("python", 3, 2, 3), ("web-security", 4, 3, 4),
        ("cryptography", 3, 2, 5), ("security-tools", 3, 2, 6), ("communication", 2, 1, 7),
    ],
    "machine-learning-engineer": [
        ("python", 4, 3, 1), ("statistics", 4, 3, 2), ("pandas-numpy", 4, 2, 3), ("git-github", 3, 1, 4),
        ("sql-databases", 2, 1, 5), ("dsa", 3, 2, 6), ("machine-learning", 4, 3, 7), ("deep-learning", 3, 2, 8),
    ],
}

B, I, A = "beginner", "intermediate", "advanced"
# skill slug, title, provider, url, type, difficulty, hours, free
RESOURCES = [
    ("html-css", "Learn Web Development (MDN)", "MDN", "https://developer.mozilla.org/en-US/docs/Learn_web_development", "docs", B, 20, True),
    ("html-css", "A Complete Guide to Flexbox", "CSS-Tricks", "https://css-tricks.com/snippets/css/a-guide-to-flexbox/", "article", I, 2, True),
    ("html-css", "Learn CSS", "web.dev", "https://web.dev/learn/css", "course", I, 12, True),
    ("html-css", "freeCodeCamp Curriculum", "freeCodeCamp", "https://www.freecodecamp.org/learn/", "practice", B, 30, True),
    ("javascript", "The Modern JavaScript Tutorial", "javascript.info", "https://javascript.info/", "article", B, 30, True),
    ("javascript", "JavaScript Guide", "MDN", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "docs", I, 15, True),
    ("javascript", "Eloquent JavaScript", "Marijn Haverbeke", "https://eloquentjavascript.net/", "book", A, 25, True),
    ("python", "The Python Tutorial", "python.org", "https://docs.python.org/3/tutorial/", "docs", B, 10, True),
    ("python", "CS50's Introduction to Programming with Python", "Harvard", "https://cs50.harvard.edu/python/", "course", B, 25, True),
    ("python", "Automate the Boring Stuff with Python", "Al Sweigart", "https://automatetheboringstuff.com/", "book", I, 20, True),
    ("python", "Real Python Tutorials", "Real Python", "https://realpython.com/", "article", A, 10, False),
    ("git-github", "Learn Git Branching", "Peter Cottle", "https://learngitbranching.js.org/", "practice", B, 4, True),
    ("git-github", "GitHub Skills", "GitHub", "https://skills.github.com/", "course", I, 6, True),
    ("git-github", "Pro Git (book)", "git-scm.com", "https://git-scm.com/book/en/v2", "book", A, 12, True),
    ("django", "Django Girls Tutorial", "Django Girls", "https://tutorial.djangogirls.org/", "course", B, 10, True),
    ("django", "Writing your first Django app", "Django docs", "https://docs.djangoproject.com/en/stable/intro/tutorial01/", "docs", I, 8, True),
    ("django", "Django Web Framework Tutorial", "MDN", "https://developer.mozilla.org/en-US/docs/Learn_web_development/Extensions/Server-side/Django", "course", I, 15, True),
    ("django", "Django Deployment Checklist", "Django docs", "https://docs.djangoproject.com/en/stable/howto/deployment/checklist/", "docs", A, 2, True),
    ("rest-apis", "What is REST?", "restfulapi.net", "https://restfulapi.net/", "article", B, 3, True),
    ("rest-apis", "Django REST framework Quickstart", "DRF", "https://www.django-rest-framework.org/tutorial/quickstart/", "docs", I, 5, True),
    ("sql-databases", "SQLBolt: Learn SQL", "SQLBolt", "https://sqlbolt.com/", "practice", B, 5, True),
    ("sql-databases", "SQL Tutorial", "Mode", "https://mode.com/sql-tutorial", "course", I, 8, True),
    ("sql-databases", "PostgreSQL Tutorial", "PostgreSQL docs", "https://www.postgresql.org/docs/current/tutorial.html", "docs", A, 6, True),
    ("deployment-basics", "Deploy a Django app", "Render docs", "https://render.com/docs/deploy-django", "docs", B, 2, True),
    ("deployment-basics", "Django Deployment Checklist", "Django docs", "https://docs.djangoproject.com/en/stable/howto/deployment/checklist/", "docs", I, 2, True),
    ("dsa", "CS50x: Introduction to Computer Science", "Harvard", "https://cs50.harvard.edu/x/", "course", B, 40, True),
    ("dsa", "VisuAlgo", "VisuAlgo", "https://visualgo.net/", "practice", I, 8, True),
    ("dsa", "Data Structures Tutorial", "GeeksforGeeks", "https://www.geeksforgeeks.org/data-structures/", "article", A, 20, True),
    ("excel", "Excel help & learning", "Microsoft", "https://support.microsoft.com/en-us/excel", "docs", B, 6, True),
    ("excel", "Excel Formulas & Functions", "Exceljet", "https://exceljet.net/", "article", I, 8, True),
    ("statistics", "Statistics and Probability", "Khan Academy", "https://www.khanacademy.org/math/statistics-probability", "course", B, 30, True),
    ("statistics", "OpenIntro Statistics", "OpenIntro", "https://www.openintro.org/book/os/", "book", I, 25, True),
    ("pandas-numpy", "10 Minutes to pandas", "pandas docs", "https://pandas.pydata.org/docs/user_guide/10min.html", "docs", B, 2, True),
    ("pandas-numpy", "Kaggle Learn: Pandas", "Kaggle", "https://www.kaggle.com/learn/pandas", "course", I, 4, True),
    ("pandas-numpy", "NumPy Quickstart", "NumPy docs", "https://numpy.org/doc/stable/user/quickstart.html", "docs", I, 3, True),
    ("data-visualization", "Kaggle Learn: Data Visualization", "Kaggle", "https://www.kaggle.com/learn/data-visualization", "course", B, 4, True),
    ("data-visualization", "Matplotlib Tutorials", "Matplotlib docs", "https://matplotlib.org/stable/tutorials/index.html", "docs", I, 6, True),
    ("data-visualization", "Tableau Training", "Tableau", "https://www.tableau.com/learn/training", "video", A, 8, True),
    ("machine-learning", "Kaggle Learn: Intro to Machine Learning", "Kaggle", "https://www.kaggle.com/learn/intro-to-machine-learning", "course", B, 4, True),
    ("machine-learning", "Machine Learning Specialization", "Coursera / DeepLearning.AI", "https://www.coursera.org/specializations/machine-learning-introduction", "course", I, 60, False),
    ("machine-learning", "scikit-learn User Guide", "scikit-learn", "https://scikit-learn.org/stable/user_guide.html", "docs", A, 15, True),
    ("deep-learning", "Kaggle Learn: Intro to Deep Learning", "Kaggle", "https://www.kaggle.com/learn/intro-to-deep-learning", "course", B, 4, True),
    ("deep-learning", "Practical Deep Learning for Coders", "fast.ai", "https://course.fast.ai/", "course", I, 40, True),
    ("deep-learning", "PyTorch Tutorials", "PyTorch", "https://pytorch.org/tutorials/", "docs", A, 15, True),
    ("networking", "Cloudflare Learning Center", "Cloudflare", "https://www.cloudflare.com/learning/", "article", B, 6, True),
    ("networking", "Pre Security path", "TryHackMe", "https://tryhackme.com/path/outline/presecurity", "practice", B, 20, True),
    ("networking", "Cisco Networking Academy", "Cisco", "https://www.netacad.com/", "course", I, 40, True),
    ("linux-cli", "Linux Journey", "Linux Journey", "https://linuxjourney.com/", "course", B, 15, True),
    ("linux-cli", "The Linux Command Line", "William Shotts", "https://linuxcommand.org/tlcl.php", "book", I, 20, True),
    ("linux-cli", "OverTheWire: Bandit", "OverTheWire", "https://overthewire.org/wargames/bandit/", "practice", A, 12, True),
    ("web-security", "OWASP Top 10", "OWASP", "https://owasp.org/www-project-top-ten/", "docs", B, 4, True),
    ("web-security", "Web Security Academy", "PortSwigger", "https://portswigger.net/web-security", "course", I, 40, True),
    ("web-security", "OWASP Juice Shop", "OWASP", "https://owasp.org/www-project-juice-shop/", "practice", A, 20, True),
    ("cryptography", "Journey into Cryptography", "Khan Academy", "https://www.khanacademy.org/computing/computer-science/cryptography", "course", B, 8, True),
    ("cryptography", "Cryptography I", "Coursera (Stanford)", "https://www.coursera.org/learn/crypto", "course", I, 30, True),
    ("cryptography", "The Cryptopals Crypto Challenges", "Cryptopals", "https://cryptopals.com/", "practice", A, 30, True),
    ("security-tools", "Nmap Network Scanning (book)", "nmap.org", "https://nmap.org/book/", "book", B, 10, True),
    ("security-tools", "Wireshark User's Guide", "Wireshark", "https://www.wireshark.org/docs/wsug_html_chunked/", "docs", I, 8, True),
    ("security-tools", "TryHackMe", "TryHackMe", "https://tryhackme.com/", "practice", A, 30, False),
    ("communication", "Technical Writing Courses", "Google", "https://developers.google.com/tech-writing", "course", B, 6, True),
    ("communication", "Toastmasters", "Toastmasters", "https://www.toastmasters.org/", "practice", I, 20, False),
]

RESOURCES += [
    ("testing", "unittest - Unit testing framework", "python.org", "https://docs.python.org/3/library/unittest.html", "docs", B, 4, True),
    ("testing", "pytest: Get Started", "pytest", "https://docs.pytest.org/en/stable/getting-started.html", "docs", I, 5, True),
    ("testing", "Real Python: Getting Started With Testing in Python", "Real Python", "https://realpython.com/python-testing/", "article", I, 3, True),
    ("docker", "Docker: Get started", "Docker docs", "https://docs.docker.com/get-started/", "docs", B, 4, True),
    ("docker", "Play with Docker", "Docker", "https://labs.play-with-docker.com/", "practice", I, 5, True),
    ("docker", "Building best practices", "Docker docs", "https://docs.docker.com/build/building/best-practices/", "docs", A, 3, True),
    ("cloud-basics", "AWS Cloud Practitioner Essentials", "AWS", "https://aws.amazon.com/training/learn-about/cloud-practitioner/", "course", B, 10, True),
    ("cloud-basics", "Azure Fundamentals: Cloud concepts", "Microsoft Learn", "https://learn.microsoft.com/en-us/training/paths/azure-fundamentals-describe-cloud-concepts/", "course", I, 8, True),
    ("cloud-basics", "Google Cloud Skills Boost", "Google Cloud", "https://www.cloudskillsboost.google/", "practice", A, 20, False),
]

# career slug, title, description, difficulty, hours, [skill slugs practised]
PROJECTS = [
    ("web-developer", "Personal Portfolio Website", "Design a responsive portfolio with HTML, CSS and a little JavaScript, and publish it with GitHub Pages.", B, 15, ["html-css", "javascript", "git-github"]),
    ("web-developer", "Task Manager Web App", "A to-do app with user accounts, a database and a clean interface.", I, 30, ["javascript", "python", "sql-databases", "django"]),
    ("web-developer", "Deployed Blog with a REST API", "Build a blog with a JSON API and deploy it to a free host.", A, 40, ["django", "rest-apis", "deployment-basics"]),
    ("python-developer", "Command-Line Expense Tracker", "Track spending from the terminal, saving data to a file; practise functions, lists and dictionaries.", B, 12, ["python", "dsa", "git-github"]),
    ("python-developer", "Unit-Tested Utility Package", "Write a small reusable package with a full test suite and a README.", I, 20, ["python", "testing", "git-github"]),
    ("python-developer", "Library REST API", "Create an API for books and borrowers backed by a SQL database.", I, 30, ["python", "rest-apis", "sql-databases", "django"]),
    ("data-analyst", "Spreadsheet Budget Dashboard", "Clean a personal-finance sheet and add pivot tables and charts.", B, 10, ["excel", "data-visualization"]),
    ("data-analyst", "SQL Sales Analysis", "Answer ten business questions from a sample sales database using SQL.", I, 20, ["sql-databases", "statistics"]),
    ("data-analyst", "Exploratory Analysis of a Public Dataset", "Use pandas to clean, explore and present findings from an open dataset.", I, 25, ["python", "pandas-numpy", "data-visualization", "statistics", "communication"]),
    ("cloud-engineer", "Containerise a Web App", "Write a Dockerfile for a small app and run it locally in a container.", B, 12, ["docker", "linux-cli"]),
    ("cloud-engineer", "Host a Static Site in the Cloud", "Publish a site on a cloud provider's free tier with HTTPS.", B, 10, ["cloud-basics", "networking", "deployment-basics"]),
    ("cloud-engineer", "Automated Deploy Script", "Script a repeatable deployment of a containerised app using Python and Git.", A, 30, ["python", "git-github", "linux-cli", "docker", "cloud-basics"]),
    ("cybersecurity-analyst", "Home Lab Network Scan Report", "Scan your own lab network, document the findings and suggest fixes.", B, 12, ["networking", "security-tools", "communication"]),
    ("cybersecurity-analyst", "Vulnerable Web App Write-up", "Exploit and then fix three OWASP Top 10 issues in a practice app and write it up.", I, 25, ["web-security", "security-tools"]),
    ("cybersecurity-analyst", "Password Hashing Demo", "Show why salted hashing beats plain hashing, using Python.", B, 8, ["cryptography", "python"]),
    ("machine-learning-engineer", "House Price Predictor", "Train and evaluate a regression model on a public housing dataset.", I, 25, ["python", "pandas-numpy", "machine-learning", "statistics"]),
    ("machine-learning-engineer", "Image Classifier", "Train a small neural network to classify images.", A, 35, ["deep-learning", "python"]),
    ("machine-learning-engineer", "Reproducible ML Notebook on GitHub", "Publish a clean, documented ML experiment with version control.", B, 10, ["git-github", "machine-learning"]),
]
