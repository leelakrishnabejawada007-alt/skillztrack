"""Beginner track: very easy, step-by-step assignments for students with little or no experience.

Every skill gets a level-1 "First steps" quiz (3 of 4 questions drawn). Core skills also get small practical
tasks at level 1-2 with numbered steps, a worked example, the expected output and hints. Beginner tasks
(ceiling <= 2) can be retried more often and retries are never penalised (see assessment_engine.max_attempts).
Harder assignments (levels 3-5) in the other modules are unchanged, so difficulty grows step by step.
"""
from . import Assignment, Q, T

QUIZ_INTRO = ("A short, friendly warm-up. Read each question slowly and pick the best answer. "
              "If you get one wrong you will see a hint (not the answer) so you can think again and retry. "
              "After your second attempt the full explanation is unlocked.")


def first_quiz(skill, name, questions):
    pool = [Q(f"b-{skill}-{i}", topic, q, opts, ans, why, hint=hint) for i, (topic, q, opts, ans, why, hint) in enumerate(questions, 1)]
    return Assignment(
        slug=f"first-steps-{skill}", skill=skill, kind="quiz", title=f"First steps: {name}",
        summary=f"Beginner warm-up for {name}. No experience needed.", ceiling=1, minutes=5,
        instructions=QUIZ_INTRO, spec={"pool": pool, "draw": 3},
        steps=("Read the question and all options.", "Pick the answer you think fits best.",
               "Submit. Wrong answers show a hint, so you can retry and learn."),
    )


# (topic, question, options, answer index, explanation, hint)
QUIZZES = {
    "python": ("Python", [
        ("printing", "What does print(2 + 3) show?", ["5", "2 + 3", "23", "Error"], 0, "print shows the value of the expression; 2 + 3 is 5.", "Python works out the maths before printing."),
        ("variables", "After x = 4 and x = x + 1, what is x?", ["4", "5", "x + 1", "1"], 1, "The right side is computed first (4 + 1) and stored back in x.", "Compute the right side using the old value of x."),
        ("types", "Which value is a string?", ["42", "3.5", "\"hello\"", "True"], 2, "Text in quotes is a string.", "Look for quotes."),
        ("lists", "What is [10, 20, 30][0]?", ["10", "20", "30", "0"], 0, "Python counts positions from 0, so index 0 is the first item.", "Counting starts at zero."),
    ]),
    "javascript": ("JavaScript", [
        ("variables", "Which keyword declares a variable that can change?", ["let", "const", "print", "var()"], 0, "let declares a reassignable variable; const cannot be reassigned.", "One of them means 'constant'."),
        ("output", "Where does console.log('hi') print?", ["The browser console", "A popup", "The page title", "Nowhere"], 0, "console.log writes to the developer console.", "Think of the developer tools."),
        ("types", "What is typeof 5?", ["\"number\"", "\"string\"", "\"int\"", "\"five\""], 0, "JavaScript has a single number type.", "JS has no separate int type."),
        ("strings", "What is 'Hi' + ' there'?", ["'Hi there'", "'Hithere'", "Error", "NaN"], 0, "+ joins strings; the second string starts with a space.", "Look at the space inside the quotes."),
    ]),
    "html-css": ("HTML & CSS", [
        ("html", "Which tag makes the biggest heading?", ["<h1>", "<h6>", "<head>", "<big>"], 0, "h1 is the top-level heading.", "Headings are numbered by importance."),
        ("html", "Which tag creates a link?", ["<a>", "<link>", "<url>", "<p>"], 0, "<a href=...> is an anchor (link).", "Think 'anchor'."),
        ("css", "Which CSS property changes text colour?", ["color", "font", "background", "text-style"], 0, "color sets the text colour.", "It is the simplest word for colour."),
        ("css", "How do you select class=\"card\" in CSS?", [".card", "#card", "card", "*card"], 0, "A dot selects a class; # selects an id.", "Classes and ids use different symbols."),
    ]),
    "git-github": ("Git & GitHub", [
        ("basics", "What does git do?", ["Tracks changes to files", "Hosts websites", "Writes code for you", "Runs tests"], 0, "Git is a version control system.", "Think 'history of changes'."),
        ("commands", "Which command saves a snapshot of staged changes?", ["git commit", "git push", "git clone", "git status"], 0, "commit records a snapshot locally.", "push sends; this one saves."),
        ("commands", "Which command shows what changed and what is staged?", ["git status", "git log", "git init", "git merge"], 0, "status summarises the working tree.", "It tells you the current state."),
        ("github", "What does git push do?", ["Uploads commits to a remote like GitHub", "Deletes a branch", "Undoes a commit", "Creates a repo"], 0, "push sends local commits to the remote.", "Direction: from your computer outward."),
    ]),
    "django": ("Django", [
        ("basics", "Django is a web framework for which language?", ["Python", "JavaScript", "Java", "PHP"], 0, "Django is written in Python.", "Same language as SkillzTrack's backend."),
        ("structure", "Which file maps URLs to views?", ["urls.py", "models.py", "settings.py", "admin.py"], 0, "urls.py holds URL patterns.", "The file name says it."),
        ("models", "What does a model usually represent?", ["A database table", "A web page style", "A URL", "A test"], 0, "Each model class maps to a table.", "Models describe stored data."),
        ("commands", "Which command starts the dev server?", ["python manage.py runserver", "django start", "pip run", "python server.py"], 0, "runserver starts the development server.", "It uses manage.py."),
    ]),
    "rest-apis": ("REST APIs", [
        ("http", "Which HTTP method is used to read data?", ["GET", "POST", "DELETE", "PATCH"], 0, "GET retrieves data without changing it.", "Think 'get me something'."),
        ("http", "Which method usually creates a new item?", ["POST", "GET", "HEAD", "OPTIONS"], 0, "POST sends data to create a resource.", "You 'post' a new letter."),
        ("status", "What does status code 404 mean?", ["Not found", "OK", "Server error", "Created"], 0, "404 = resource not found.", "You have seen it on broken links."),
        ("format", "Which data format do most APIs return?", ["JSON", "MP3", "PNG", "DOCX"], 0, "JSON is the common text format for APIs.", "It looks like Python dicts."),
    ]),
    "sql-databases": ("SQL", [
        ("select", "Which keyword reads rows from a table?", ["SELECT", "GET", "READ", "FETCH ALL"], 0, "SELECT columns FROM table.", "It is how you 'select' data."),
        ("filter", "Which clause filters rows?", ["WHERE", "ORDER BY", "FROM", "GROUP"], 0, "WHERE keeps rows that match a condition.", "It answers 'which rows?'."),
        ("sort", "Which clause sorts results?", ["ORDER BY", "SORT", "WHERE", "LIMIT"], 0, "ORDER BY col sorts the output.", "Two words, about order."),
        ("basics", "A table is made of...", ["Rows and columns", "Pages and links", "Files and folders", "Classes"], 0, "Like a spreadsheet: rows are records, columns are fields.", "Think spreadsheet."),
    ]),
    "deployment-basics": ("Deployment", [
        ("basics", "What does deploying an app mean?", ["Putting it online for users", "Deleting it", "Writing tests", "Designing a logo"], 0, "Deployment makes the app available on a server.", "Users need to reach it."),
        ("config", "Where should secret keys be stored?", ["Environment variables", "In the HTML", "In a public README", "In the URL"], 0, "Env variables keep secrets out of code.", "Never in places others can read."),
        ("http", "What does HTTPS add over HTTP?", ["Encryption", "Colours", "Speed only", "Images"], 0, "The S means secure (TLS encryption).", "S stands for..."),
        ("logs", "Your live app crashes. What do you check first?", ["The server logs", "The logo", "The font", "Your browser history"], 0, "Logs show the error message and stack trace.", "Where do errors get written?"),
    ]),
    "dsa": ("Data Structures & Algorithms", [
        ("arrays", "How many items are in [3, 7, 1]?", ["3", "2", "11", "1"], 0, "Count the items: 3, 7, 1.", "Count, don't add."),
        ("search", "To find the largest number in an unsorted list you must...", ["Look at every item", "Look at the first item", "Look at the last item", "Sort it backwards"], 0, "Any item could be the max, so check all.", "Could the max be hiding anywhere?"),
        ("stack", "A stack is like...", ["A pile of plates (last in, first out)", "A queue at a shop", "A dictionary", "A random bag"], 0, "Stacks are LIFO.", "Which plate do you take first?"),
        ("dict", "Which Python type stores key: value pairs?", ["dict", "list", "tuple", "str"], 0, "dict maps keys to values.", "Like a real dictionary: word -> meaning."),
    ]),
    "excel": ("Excel", [
        ("formulas", "Every Excel formula starts with...", ["=", "#", "@", "$"], 0, "Formulas begin with =.", "It looks like the start of an equation."),
        ("functions", "Which function adds a range of cells?", ["SUM", "ADD", "TOTAL", "PLUS"], 0, "=SUM(A1:A5) adds the range.", "Think 'sum'."),
        ("functions", "Which function gives the mean?", ["AVERAGE", "MEAN()", "MID", "COUNT"], 0, "=AVERAGE(range).", "The everyday word for mean."),
        ("refs", "What is cell B3?", ["Column B, row 3", "Row B, column 3", "Sheet 3", "Book B"], 0, "Letter = column, number = row.", "Letters go across the top."),
    ]),
    "statistics": ("Statistics", [
        ("mean", "What is the mean of 2, 4, 6?", ["4", "6", "12", "2"], 0, "(2+4+6)/3 = 4.", "Add them, then divide by how many."),
        ("median", "What is the median of 1, 3, 9?", ["3", "9", "4.3", "1"], 0, "Middle value after sorting.", "Middle position."),
        ("mode", "The mode of 2, 2, 5 is...", ["2", "5", "3", "9"], 0, "Most frequent value.", "Which appears most?"),
        ("range", "The range of 3, 8, 10 is...", ["7", "10", "21", "3"], 0, "max - min = 10 - 3.", "Largest minus smallest."),
    ]),
    "pandas-numpy": ("Pandas & NumPy", [
        ("pandas", "A pandas table is called a...", ["DataFrame", "Sheet", "Array", "Grid"], 0, "pandas.DataFrame.", "Data + frame."),
        ("io", "Which function reads a CSV file?", ["pd.read_csv", "pd.open", "pd.csv()", "np.load_csv"], 0, "pd.read_csv('file.csv').", "read_ + file type."),
        ("pandas", "df.head() shows...", ["The first 5 rows", "Column names only", "The last row", "A chart"], 0, "head shows the top rows.", "Head = top."),
        ("numpy", "np.array([1, 2]) * 2 gives...", ["[2, 4]", "[1, 2, 1, 2]", "Error", "[1, 2, 2]"], 0, "NumPy multiplies element by element.", "Unlike lists, NumPy does maths on each item."),
    ]),
    "data-visualization": ("Data Visualization", [
        ("charts", "Best chart to show change over time?", ["Line chart", "Pie chart", "Table", "Word cloud"], 0, "Lines show trends.", "Time flows along a line."),
        ("charts", "Best chart to compare categories?", ["Bar chart", "Line chart", "Scatter", "Map"], 0, "Bars compare sizes.", "Side-by-side heights."),
        ("labels", "Every chart should have...", ["Clear axis labels and a title", "Lots of 3D effects", "No labels", "Random colours"], 0, "Labels tell the reader what they see.", "Readers must understand it."),
        ("library", "Which is a Python plotting library?", ["matplotlib", "flask", "requests", "sqlite3"], 0, "matplotlib draws charts.", "It has 'plot' in it."),
    ]),
    "machine-learning": ("Machine Learning", [
        ("basics", "Machine learning means...", ["Learning patterns from data", "Writing every rule by hand", "Building robots only", "Fixing hardware"], 0, "Models learn from examples.", "Where do the rules come from?"),
        ("data", "Data with known answers is called...", ["Labelled data", "Random data", "Empty data", "Code"], 0, "Labels are the correct answers.", "Each example has a label."),
        ("split", "Why keep a test set?", ["To check the model on unseen data", "To make training faster", "To store code", "No reason"], 0, "Testing on unseen data measures real performance.", "Would a student grade their own exam?"),
        ("tasks", "Predicting a house price is...", ["Regression", "Classification", "Clustering", "Sorting"], 0, "Predicting a number = regression.", "Is the answer a number or a category?"),
    ]),
    "deep-learning": ("Deep Learning", [
        ("basics", "Deep learning uses...", ["Neural networks with many layers", "Only spreadsheets", "Just if-statements", "Databases"], 0, "Deep = many layers.", "'Deep' refers to layers."),
        ("training", "One full pass over the training data is an...", ["Epoch", "Era", "Batch file", "Loop error"], 0, "An epoch = one pass.", "Starts with 'E'."),
        ("uses", "A common deep learning use is...", ["Recognising images", "Adding two numbers", "Renaming files", "Sorting a small list"], 0, "Image recognition is a classic task.", "Something hard to write rules for."),
        ("hardware", "Which hardware speeds up training?", ["GPU", "Mouse", "Printer", "Speaker"], 0, "GPUs do many calculations in parallel.", "The graphics card."),
    ]),
    "networking": ("Networking", [
        ("ip", "An IP address identifies...", ["A device on a network", "A website's colour", "A file", "A user's password"], 0, "Like a postal address for devices.", "Address."),
        ("dns", "DNS converts...", ["Names like google.com into IP addresses", "Images to text", "HTTP to HTTPS", "Files to folders"], 0, "DNS is the internet's phone book.", "Humans like names, computers like numbers."),
        ("ports", "Default port for HTTPS?", ["443", "80", "22", "21"], 0, "HTTPS uses 443; HTTP uses 80.", "Not 80, that's plain HTTP."),
        ("tools", "Which command checks if a host is reachable?", ["ping", "ls", "cd", "cat"], 0, "ping sends echo requests.", "It sounds like sonar."),
    ]),
    "linux-cli": ("Linux command line", [
        ("files", "Which command lists files?", ["ls", "cd", "rm", "pwd"], 0, "ls = list.", "Short for 'list'."),
        ("nav", "Which command changes folder?", ["cd", "ls", "mv", "cp"], 0, "cd = change directory.", "Change directory."),
        ("nav", "Which command shows the current folder?", ["pwd", "whoami", "ls", "dir -x"], 0, "pwd = print working directory.", "Print working directory."),
        ("files", "Which command copies a file?", ["cp", "mv", "rm", "touch"], 0, "cp = copy.", "Short for copy."),
    ]),
    "web-security": ("Web security", [
        ("passwords", "How should apps store passwords?", ["Hashed", "Plain text", "In cookies", "In the URL"], 0, "Store a salted hash, never the password.", "So even admins can't read them."),
        ("https", "Why use HTTPS?", ["To encrypt traffic", "To make pages colourful", "To speed up images", "To skip login"], 0, "TLS encrypts data in transit.", "Protects data on the way."),
        ("input", "User input should be...", ["Validated and never trusted", "Always trusted", "Ignored", "Shown as HTML directly"], 0, "Untrusted input causes XSS and injection.", "Attackers type things too."),
        ("phishing", "A fake login email trying to steal passwords is...", ["Phishing", "Debugging", "Caching", "Hosting"], 0, "Phishing tricks users.", "Sounds like fishing."),
    ]),
    "cryptography": ("Cryptography", [
        ("basics", "Encryption turns readable data into...", ["Unreadable ciphertext", "A picture", "A shorter word", "HTML"], 0, "Only someone with the key can read it.", "Cipher..."),
        ("keys", "To decrypt you need...", ["The right key", "A faster computer only", "The file name", "Nothing"], 0, "Keys unlock ciphertext.", "Like a lock."),
        ("hash", "A hash function is...", ["One-way: you can't get the input back", "Easily reversible", "A type of chart", "A database"], 0, "Hashes are one-way fingerprints.", "Fingerprint, not a lockbox."),
        ("classic", "The Caesar cipher shifts...", ["Letters by a fixed number", "Words randomly", "Numbers only", "Nothing"], 0, "e.g. shift 3: A -> D.", "A -> D is a shift of 3."),
    ]),
    "security-tools": ("Security tools", [
        ("scanning", "nmap is used to...", ["Scan networks for open ports", "Edit photos", "Write Python", "Send email"], 0, "nmap = network mapper.", "Network mapper."),
        ("traffic", "Wireshark lets you...", ["Inspect network packets", "Design websites", "Store passwords", "Compile code"], 0, "Wireshark captures packets.", "It 'listens' to the wire."),
        ("ethics", "Before scanning a system you need...", ["Written permission", "A fast laptop", "Nothing", "A VPN only"], 0, "Unauthorised scanning is illegal.", "Ethics and law."),
        ("passwords", "A password manager helps you...", ["Use strong unique passwords", "Share passwords", "Remove passwords", "Hack accounts"], 0, "It stores strong, unique passwords.", "Unique per site."),
    ]),
    "testing": ("Software testing", [
        ("basics", "Why write tests?", ["To catch bugs early", "To make code longer", "To slow down", "To replace users"], 0, "Tests prove code works and stays working.", "Bugs."),
        ("unit", "A unit test checks...", ["One small piece of code", "The whole company", "Only the UI colours", "The server hardware"], 0, "Unit = smallest testable part.", "Unit = small."),
        ("assert", "assert 2 + 2 == 4 ...", ["Passes silently", "Fails", "Prints 4", "Deletes code"], 0, "A true assertion does nothing.", "Is the statement true?"),
        ("tools", "A popular Python test tool is...", ["pytest", "photoshop", "nginx", "excel"], 0, "pytest runs test functions.", "It has 'test' in the name."),
    ]),
    "docker": ("Docker", [
        ("basics", "Docker packages apps into...", ["Containers", "Spreadsheets", "Emails", "Fonts"], 0, "Containers bundle app + dependencies.", "Shipping metaphor."),
        ("files", "Which file describes how to build an image?", ["Dockerfile", "package.json", "README", "index.html"], 0, "The Dockerfile has build steps.", "Named after the tool."),
        ("commands", "Which command runs a container?", ["docker run", "docker go", "docker open", "docker exec-all"], 0, "docker run IMAGE.", "Run."),
        ("why", "Main benefit of containers?", ["Same environment everywhere", "Prettier UI", "No code needed", "Free hosting"], 0, "'Works on my machine' everywhere.", "Consistency."),
    ]),
    "cloud-basics": ("Cloud basics", [
        ("basics", "Cloud computing means...", ["Using servers over the internet", "Weather prediction", "Only storing photos", "Offline software"], 0, "Rent computing on demand.", "Someone else's computers."),
        ("providers", "Which is a cloud provider?", ["AWS", "Excel", "Chrome", "Linux"], 0, "Amazon Web Services.", "Amazon."),
        ("storage", "Cloud object storage is used for...", ["Files like images and backups", "Running CSS", "Typing code", "Email only"], 0, "e.g. S3 stores files.", "Files."),
        ("pricing", "Most cloud services charge...", ["For what you use", "A one-time fee forever", "Nothing ever", "Per keyboard"], 0, "Pay-as-you-go.", "Like electricity."),
    ]),
    "communication": ("Communication", [
        ("email", "A good work email starts with...", ["A clear subject line", "No subject", "All caps", "Emojis only"], 0, "Subject tells the reader what it's about.", "What appears first in an inbox?"),
        ("listening", "Active listening means...", ["Paying attention and asking questions", "Waiting to talk", "Checking your phone", "Interrupting"], 0, "Show you understand.", "Engage."),
        ("updates", "When you're stuck on a task you should...", ["Ask for help early with details", "Say nothing", "Quit", "Blame others"], 0, "Early, specific questions save time.", "Sooner is better."),
        ("clarity", "Clear writing uses...", ["Short sentences and simple words", "Long jargon", "No punctuation", "Random order"], 0, "Simple is clear.", "Easy to read."),
    ]),
}

ASSIGNMENTS = [first_quiz(skill, name, qs) for skill, (name, qs) in QUIZZES.items()]


# ------------------------------------------------------------------- practical beginner tasks
def code(slug, skill, kind, title, summary, ceiling, minutes, instructions, starter, tests, reference, steps, example, hints):
    return Assignment(slug=slug, skill=skill, kind=kind, title=title, summary=summary, ceiling=ceiling, minutes=minutes,
                      instructions=instructions, starter=starter, spec={"tests": tests}, reference=reference,
                      steps=steps, example=example, hints=hints)


ASSIGNMENTS += [
    code("py-first-functions", "python", "code", "Python step 1: your first functions",
         "Write three tiny functions. Perfect if you have never coded before.", 1, 15,
         "Fill in each function so it returns (not prints) the right value. Replace the word `pass` with your code.",
         'def greet(name):\n    """Return "Hello, <name>!"  e.g. greet("Asha") -> "Hello, Asha!" """\n    pass\n\n\n'
         'def add(a, b):\n    """Return the sum of a and b."""\n    pass\n\n\n'
         'def is_even(n):\n    """Return True if n is even, otherwise False."""\n    pass\n',
         [T("greet", ["Asha"], "Hello, Asha!", "greet('Asha')", "strings", visible=True, hint="Join the pieces: \"Hello, \" + name + \"!\". Check the comma, space and !"),
          T("greet", ["Ravi"], "Hello, Ravi!", "greet another name", "strings", hint="Use the name parameter, don't type a fixed name."),
          T("add", [2, 3], 5, "add(2, 3)", "numbers", visible=True, hint="Use the + operator and `return` the result."),
          T("add", [-4, 10], 6, "add with a negative", "numbers", hint="+ works for negative numbers too."),
          T("is_even", [4], True, "is_even(4)", "conditions", visible=True, hint="n % 2 gives the remainder after dividing by 2."),
          T("is_even", [7], False, "is_even(7)", "conditions", hint="An odd number leaves remainder 1.")],
         'def greet(name):\n    return "Hello, " + name + "!"\n\ndef add(a, b):\n    return a + b\n\ndef is_even(n):\n    return n % 2 == 0\n',
         ("Look at the docstring (the text in triple quotes) to see what each function must do.",
          "Delete `pass` and write a `return` line.", "Use the example below to check your thinking.",
          "Submit. Failed tests show a hint; fix and retry as often as you like."),
         {"input": 'greet("Asha")\nadd(2, 3)\nis_even(4)', "output": '"Hello, Asha!"\n5\nTrue'},
         ("`return` sends a value back; `print` only shows it. The grader needs `return`.",
          "Strings are joined with +.", "The % operator gives a remainder: 7 % 2 is 1.")),

    code("py-loops-lists", "python", "code", "Python step 2: loops and lists",
         "Practise for-loops on lists with small, clear tasks.", 2, 20,
         "Each function receives a list. Loop over it (or use a built-in) and return the answer.",
         'def total(numbers):\n    """Return the sum of all numbers. total([]) -> 0"""\n    pass\n\n\n'
         'def count_positive(numbers):\n    """Return how many numbers are greater than 0."""\n    pass\n\n\n'
         'def longest_word(words):\n    """Return the longest word. If there is a tie, return the first one. Empty list -> "" """\n    pass\n',
         [T("total", [[1, 2, 3]], 6, "total([1, 2, 3])", "loops", visible=True, hint="Start with result = 0 and add each number in a for-loop."),
          T("total", [[]], 0, "total of an empty list", "edge cases", hint="What should the starting value be if there is nothing to add?"),
          T("count_positive", [[3, -1, 0, 5]], 2, "count_positive([3, -1, 0, 5])", "conditions", visible=True, hint="0 is not greater than 0."),
          T("count_positive", [[-2, -3]], 0, "no positives", "conditions", hint="Count only when n > 0."),
          T("longest_word", [["hi", "hello", "hey"]], "hello", "longest_word basic", "strings", visible=True, hint="Compare len(word) with the best so far."),
          T("longest_word", [["cat", "dog"]], "cat", "tie keeps the first", "edge cases", hint="Only replace the best when the new word is strictly longer (>, not >=)."),
          T("longest_word", [[]], "", "empty list", "edge cases", hint="Start with best = \"\".")],
         'def total(numbers):\n    return sum(numbers)\n\ndef count_positive(numbers):\n    return sum(1 for n in numbers if n > 0)\n\n'
         'def longest_word(words):\n    best = ""\n    for w in words:\n        if len(w) > len(best):\n            best = w\n    return best\n',
         ("Create a variable to hold the answer before the loop.", "Write `for item in the_list:` and update the variable inside.",
          "Return the variable after the loop.", "Think about the empty list case."),
         {"input": "total([1, 2, 3])\ncount_positive([3, -1, 0, 5])\nlongest_word([\"hi\", \"hello\"])", "output": "6\n2\n\"hello\""},
         ("Indentation matters: the loop body is indented 4 spaces.", "len(word) gives the number of letters.")),

    code("py-fix-the-bugs", "python", "debug", "Python step 3: find and fix 3 small bugs",
         "Basic debugging: each function has one small mistake.", 2, 15,
         "Every function below has exactly ONE bug. Read the docstring, compare it with the code, and fix the line that is wrong.",
         'def double(n):\n    """Return n multiplied by 2."""\n    return n + 2\n\n\n'
         'def first_item(items):\n    """Return the first item of the list."""\n    return items[1]\n\n\n'
         'def can_vote(age):\n    """Return True if age is 18 or more."""\n    return age > 18\n',
         [T("double", [5], 10, "double(5)", "operators", visible=True, hint="Is the code adding or multiplying?"),
          T("double", [0], 0, "double(0)", "operators", hint="0 doubled is still 0."),
          T("first_item", [["a", "b", "c"]], "a", "first_item(['a','b','c'])", "indexing", visible=True, hint="Python list positions start at 0."),
          T("can_vote", [18], True, "can_vote(18)", "comparisons", visible=True, hint="'18 or more' includes 18 itself. Which operator means 'greater than or equal'?"),
          T("can_vote", [30], True, "can_vote(30)", "comparisons", hint="Older people can vote too."),
          T("can_vote", [10], False, "can_vote(10)", "comparisons", hint="Under 18 must return False.")],
         'def double(n):\n    return n * 2\n\ndef first_item(items):\n    return items[0]\n\ndef can_vote(age):\n    return age >= 18\n',
         ("Read the docstring: it is the truth.", "Try the example in your head: what does the current code return?",
          "Change only the wrong symbol or number.", "Submit and read the hints for any failing check."),
         {"input": "double(5)\nfirst_item([\"a\", \"b\"])\ncan_vote(18)", "output": "10\n\"a\"\nTrue"},
         ("Bugs are often one character: + vs *, 1 vs 0, > vs >=.",)),

    code("dsa-first-steps", "dsa", "code", "DSA step 1: search and count",
         "Small real-world tasks on lists and dictionaries.", 2, 20,
         "A shop keeps a list of sold items. Write helpers to answer simple questions about it.",
         'def find_index(items, target):\n    """Return the position of target in items, or -1 if it is missing."""\n    pass\n\n\n'
         'def count_items(items):\n    """Return a dict: item -> how many times it appears.  ["tea","tea","milk"] -> {"tea": 2, "milk": 1}"""\n    pass\n',
         [T("find_index", [["pen", "book", "bag"], "book"], 1, "find 'book'", "search", visible=True, hint="Loop with enumerate(items) to get position and value."),
          T("find_index", [["pen"], "cup"], -1, "missing item", "search", hint="If the loop ends without finding it, return -1."),
          T("count_items", [["tea", "tea", "milk"]], {"tea": 2, "milk": 1}, "count sales", "dictionaries", visible=True, hint="Start with an empty dict {} and add 1 for each item: d[x] = d.get(x, 0) + 1."),
          T("count_items", [[]], {}, "no sales", "edge cases", hint="An empty list gives an empty dict.")],
         'def find_index(items, target):\n    for i, x in enumerate(items):\n        if x == target:\n            return i\n    return -1\n\n'
         'def count_items(items):\n    d = {}\n    for x in items:\n        d[x] = d.get(x, 0) + 1\n    return d\n',
         ("Solve find_index first with a simple loop.", "For count_items, create an empty dictionary.",
          "Update the count for each item.", "Return the result."),
         {"input": 'find_index(["pen", "book"], "book")\ncount_items(["tea", "tea", "milk"])', "output": '1\n{"tea": 2, "milk": 1}'},
         ("dict.get(key, 0) returns 0 when the key isn't there yet.",)),

    code("stats-first-steps", "statistics", "code", "Statistics step 1: mean and range",
         "Compute simple statistics for a class's test marks.", 2, 15,
         "Write functions that summarise a list of marks. Use only plain Python (no libraries).",
         'def mean(marks):\n    """Return the average mark. Empty list -> 0"""\n    pass\n\n\n'
         'def value_range(marks):\n    """Return highest minus lowest. Empty list -> 0"""\n    pass\n',
         [T("mean", [[50, 70, 90]], 70, "mean([50, 70, 90])", "mean", visible=True, cmp="approx", hint="sum(marks) / len(marks)."),
          T("mean", [[]], 0, "mean of nothing", "edge cases", hint="Check `if not marks:` first to avoid dividing by zero."),
          T("value_range", [[40, 95, 60]], 55, "range of marks", "spread", visible=True, hint="max(marks) - min(marks)."),
          T("value_range", [[]], 0, "range of nothing", "edge cases", hint="max() of an empty list raises an error; handle it first.")],
         'def mean(marks):\n    return sum(marks) / len(marks) if marks else 0\n\ndef value_range(marks):\n    return max(marks) - min(marks) if marks else 0\n',
         ("Handle the empty list first.", "Use sum, len, max and min.", "Return the number."),
         {"input": "mean([50, 70, 90])\nvalue_range([40, 95, 60])", "output": "70.0\n55"},
         ("Dividing by len([]) crashes: return 0 early for an empty list.",)),

    code("testing-first-bugs", "testing", "debug", "Testing step 1: fix a shopping cart",
         "A small real-world debugging task with clear expected outputs.", 2, 15,
         "A shopping cart's helper functions have bugs. Fix them so they match the docstrings.",
         'def cart_total(prices):\n    """Return the total of all prices."""\n    total = 0\n    for p in prices:\n        total = p\n    return total\n\n\n'
         'def apply_discount(total, percent):\n    """Return total reduced by percent. apply_discount(200, 10) -> 180"""\n    return total - percent\n',
         [T("cart_total", [[10, 20, 5]], 35, "cart_total([10, 20, 5])", "loops", visible=True, hint="Is the loop adding to total, or replacing it?"),
          T("cart_total", [[]], 0, "empty cart", "edge cases", hint="An empty cart costs 0."),
          T("apply_discount", [200, 10], 180, "10% off 200", "percentages", visible=True, cmp="approx", hint="10% of 200 is 200 * 10 / 100 = 20."),
          T("apply_discount", [50, 0], 50, "0% off", "percentages", cmp="approx", hint="No discount keeps the total.")],
         'def cart_total(prices):\n    return sum(prices)\n\ndef apply_discount(total, percent):\n    return total - total * percent / 100\n',
         ("Run the example in your head with the current code.", "Find where the result goes wrong.", "Fix that one line."),
         {"input": "cart_total([10, 20, 5])\napply_discount(200, 10)", "output": "35\n180.0"},
         ("total += p adds; total = p replaces.", "A percent of x is x * percent / 100.")),
]
