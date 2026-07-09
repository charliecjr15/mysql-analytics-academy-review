"""Structural and analytical checks for the generated browser course."""
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from collections import defaultdict
from datetime import date
import json, re

ROOT = Path(__file__).resolve().parent
payload = (ROOT / "source-lessons.js").read_text(encoding="utf-8")
segments = json.loads(payload.removeprefix("window.SOURCE_SEGMENTS = ").removesuffix(";\n"))
errors = []

class LessonParser(HTMLParser):
    void = {"br", "hr", "img", "input", "meta", "link"}
    def __init__(self, label):
        super().__init__(); self.label = label; self.stack = []; self.tables = []
    def handle_starttag(self, tag, attrs):
        if tag not in self.void: self.stack.append(tag)
        if tag == "table": self.tables.append([])
        if tag == "tr" and self.tables: self.tables[-1].append(0)
        if tag in ("th", "td") and self.tables and self.tables[-1]:
            span = dict(attrs).get("colspan", "1")
            self.tables[-1][-1] += int(span) if span.isdigit() else 1
    def handle_endtag(self, tag):
        if tag in self.void: return
        if not self.stack or self.stack[-1] != tag:
            errors.append(f"{self.label}: mismatched closing tag {tag}")
            return
        self.stack.pop()

assertions = [
    (len(segments) == 13, "course must contain exactly thirteen segments"),
    ([s["title"] for s in segments] == ["MySQL Basics", "Build the Database", "Keys & Database Design", "Data Cleaning", "CASE, Dates & Text", "Orders & KPIs", "JOINS", "GROUP BY", "HAVING", "Views & Reporting", "Subqueries & CTEs", "Window Functions", "Query Performance"], "segment order is incorrect"),
]
for passed, message in assertions:
    if not passed: errors.append(message)

expected_lessons = {1: 7, 2: 8, 3: 9, 4: 7, 5: 6, 6: 9, 7: 10, 8: 7, 9: 7, 10: 6, 11: 8, 12: 8, 13: 6}

for si, segment in enumerate(segments, 1):
    if not segment["lessons"]: errors.append(f"S{si}: no lessons")
    if len(segment["lessons"]) != expected_lessons[si]:
        errors.append(f"S{si}: expected {expected_lessons[si]} lessons, found {len(segment['lessons'])}")
    for li, lesson in enumerate(segment["lessons"], 1):
        label = f"S{si}L{li} {lesson['title']}"
        body = lesson["body"]
        parser = LessonParser(label); parser.feed(body)
        if parser.stack: errors.append(f"{label}: unclosed tags {parser.stack}")
        for table in parser.tables:
            if table and len(set(table)) != 1: errors.append(f"{label}: inconsistent table widths {table}")
        for pattern, message in [
            (r"Absolutely, Charlie|uploaded course notes|Say [“\"]?next segment", "assistant/source chatter"),
            (r"```|\*\*|<tbody></tbody>|<td>Practice \d+</td>", "unrendered formatting artifact"),
            (r"\btotal_orders\b", "COUNT(*) mislabeled as total orders"),
        ]:
            if re.search(pattern, body, re.I): errors.append(f"{label}: {message}")
        if "<th></th>" in body:
            errors.append(f"{label}: table contains an unlabeled header")
        valid_sql_start = re.compile(r"^(SELECT|WITH|EXPLAIN|SHOW\s+INDEX|CREATE|ALTER|UPDATE|DELETE\s+FROM|START|COMMIT|ROLLBACK|USE|DROP|INSERT|VALUES|DESCRIBE|WHERE\s+[a-z_]|GROUP BY\s+[a-z_]|ORDER BY\s+[a-z_]|LIMIT\s+\d|SUM\(|AVG\(|COUNT\()", re.I)
        for code in re.findall(r"<pre><code>(.*?)</code></pre>", body, re.S):
            if not valid_sql_start.match(unescape(code).strip()):
                errors.append(f"{label}: non-SQL prose is incorrectly formatted as a code block")
        code_blocks = body.count('class="code-block"')
        result_cards = body.count('<aside class="expected-result')
        if code_blocks != result_cards:
            errors.append(f"{label}: expected one result card per SQL block, found {result_cards} for {code_blocks}")
        if lesson["title"].startswith("Mini-project: ") and 'class="expected-result error"' in body:
            errors.append(f"{label}: reference project SQL produces an expected error")

visual_dir = ROOT / "assets" / "lesson-visuals"
for segment_number, segment in enumerate(segments, 1):
    overview = segment["lessons"][0]["body"]
    images = re.findall(r'<img src="([^"]+)" alt="([^"]+)"', overview)
    if len(images) != 1:
        errors.append(f"S{segment_number}: expected one overview visual, found {len(images)}")
        continue
    source, alt = images[0]
    if not alt.strip(): errors.append(f"S{segment_number}: overview visual has no alt text")
    asset = ROOT / source
    if not asset.is_file(): errors.append(f"S{segment_number}: missing visual asset {source}")

if any('class="statement-scene"' in lesson["body"] for segment in segments for lesson in segment["lessons"]):
    errors.append("legacy hard-coded statement scenes remain in generated lessons")
generated_html = "\n".join(lesson["body"] for segment in segments for lesson in segment["lessons"])
for stale_scene_phrase in ("Candidate value A", "CTEs turn a complex query into named intermediate results"):
    if stale_scene_phrase in generated_html:
        errors.append(f"stale generic statement visual remains: {stale_scene_phrase}")

# Textbook sections must preserve every original topic and now include an
# explicit explanation layer so learners understand purpose, grain, validation,
# and mental model instead of copying isolated examples.
lesson_total = sum(len(segment["lessons"]) for segment in segments)
if lesson_total != 98:
    errors.append(f"expected 98 textbook sections, found {lesson_total}")
source_topic_total = 0
teaching_context_count = 0
query_teaching_count = 0
concept_teaching_count = 0
for segment_number, segment in enumerate(segments, 1):
    for lesson_number, lesson in enumerate(segment["lessons"], 1):
        body = lesson["body"]
        if 'class="learning-brief"' not in body:
            errors.append(f"S{segment_number}L{lesson_number}: missing learning goal / why it matters panel")
        else:
            teaching_context_count += 1
        query_teaching_count += body.count('class="query-teaching')
        concept_teaching_count += body.count('class="concept-teaching"')
        if lesson["title"] == "Section knowledge check" or lesson["title"].startswith("Mini-project:"):
            continue
        for required in ('class="chapter-label"', 'class="chapter-lead"', 'class="chapter-reading"', 'class="textbook-subsection"'):
            if required not in body:
                errors.append(f"S{segment_number}L{lesson_number}: textbook section is missing {required}")
        titles = lesson.get("source_titles", [])
        source_topic_total += len(titles)
        if body.count('class="textbook-subsection"') != len(titles):
            errors.append(f"S{segment_number}L{lesson_number}: source-topic count does not match rendered subsections")
if source_topic_total != 362:
    errors.append(f"expected 359 original/enriched topics plus two join supplements and one setup supplement, found {source_topic_total}")
if teaching_context_count != lesson_total:
    errors.append(f"expected learning context on all {lesson_total} lessons, found {teaching_context_count}")
if query_teaching_count < 60:
    errors.append(f"expected substantial query explanation coverage, found {query_teaching_count} query-teaching panels")
if concept_teaching_count < 4:
    errors.append(f"expected mental-model coverage for non-query topics, found {concept_teaching_count} concept-teaching panels")

# A statement visual must mention at least one real table/object identifier from
# the SQL it accompanies; this prevents generic or unrelated animations.
for segment_number, segment in enumerate(segments, 1):
    for lesson_number, lesson in enumerate(segment["lessons"], 1):
        body = lesson["body"]
        if "STATEMENT IN ACTION" not in body:
            continue
        code_blocks = re.findall(r"<pre><code>(.*?)</code></pre>", body, re.S)
        if not code_blocks:
            continue
        sql = unescape(code_blocks[0])
        identifiers = []
        for pattern in (r"(?i)\bFROM\s+([a-z_]\w*)", r"(?i)\bJOIN\s+([a-z_]\w*)", r"(?i)\b(?:UPDATE|INTO|TABLE)\s+([a-z_]\w*)"):
            identifiers.extend(re.findall(pattern, sql))
        if identifiers:
            visual = unescape(body[body.find("STATEMENT IN ACTION"):]).lower()
            if not any(identifier.lower() in visual for identifier in identifiers):
                errors.append(f"S{segment_number}L{lesson_number}: statement visual omits its SQL identifiers {identifiers}")

expected_results_path = ROOT / "expected-results.json"
if not expected_results_path.is_file():
    errors.append("missing captured expected-results.json")
else:
    captured_results = json.loads(expected_results_path.read_text(encoding="utf-8"))
    if len(captured_results) < 230:
        errors.append(f"expected at least 230 captured MySQL result sets, found {len(captured_results)}")

# Every section ends with assessed retrieval practice and an applied project.
for segment_number, segment in enumerate(segments, 1):
    checks = [lesson for lesson in segment["lessons"] if lesson["title"] == "Section knowledge check"]
    projects = [lesson for lesson in segment["lessons"] if lesson["title"].startswith("Mini-project: ")]
    if len(checks) != 1:
        errors.append(f"S{segment_number}: expected one section knowledge check, found {len(checks)}")
    elif checks[0]["body"].count('class="quiz"') != 3:
        errors.append(f"S{segment_number}: knowledge check must contain exactly three questions")
    if len(projects) != 1:
        errors.append(f"S{segment_number}: expected one mini-project, found {len(projects)}")
    else:
        project_body = projects[0]["body"]
        for required in ("Business brief", "Deliverables", "Acceptance criteria", "starting hint", "REFERENCE SQL", "Self-assessment rubric"):
            if required not in project_body:
                errors.append(f"S{segment_number}: mini-project is missing {required}")
        if '<details class="project-solution">' not in project_body:
            errors.append(f"S{segment_number}: project solution is not deliberately hidden")

expected_practices = {1: 6, 2: 7, 3: 6, 4: 6, 5: 4, 6: 10, 7: 5, 8: 4, 9: 4, 10: 4, 11: 4, 12: 5, 13: 5}
for segment_number, expected_count in expected_practices.items():
    practice_topics = [title for lesson in segments[segment_number - 1]["lessons"] for title in lesson.get("source_titles", []) if title.startswith("Practice ")]
    if len(practice_topics) != expected_count:
        errors.append(f"S{segment_number}: expected {expected_count} preserved practice topics, found {len(practice_topics)}")

# Verify the fixed teaching dataset and headline KPIs used throughout the course.
orders = [
    ("Iced Latte", "Coffee", 2, 2.750, "2026-06-20"), ("Cold Brew", "Coffee", 1, 3.000, "2026-06-20"),
    ("Croissant", "Pastry", 3, 1.500, "2026-06-20"), ("Brownie", "Dessert", 2, 1.750, "2026-06-21"),
    ("Iced Latte", "Coffee", 1, 2.750, "2026-06-21"), ("Matcha Latte", "Tea", 2, 2.900, "2026-06-21"),
    ("Americano", "Coffee", 4, 1.250, "2026-06-22"), ("Cold Brew", "Coffee", 2, 3.000, "2026-06-22"),
    ("Croissant", "Pastry", 1, 1.500, "2026-06-22"), ("Iced Latte", "Coffee", 3, 2.750, "2026-06-23"),
]
total_items = sum(row[2] for row in orders)
total_revenue = sum(row[2] * row[3] for row in orders)
coffee_revenue = sum(row[2] * row[3] for row in orders if row[1] == "Coffee")
if (total_items, round(total_revenue, 3), round(coffee_revenue, 3)) != (21, 45.800, 30.500):
    errors.append("teaching dataset KPI calculations are inconsistent")

product_revenue = defaultdict(float); category_revenue = defaultdict(float); daily_revenue = defaultdict(float)
product_items = defaultdict(int)
for product, category, quantity, unit_price, order_date in orders:
    revenue = quantity * unit_price
    product_revenue[product] += revenue; category_revenue[category] += revenue; daily_revenue[order_date] += revenue
    product_items[product] += quantity
expected_product_revenue = {"Iced Latte": 16.500, "Cold Brew": 9.000, "Croissant": 6.000, "Brownie": 3.500, "Matcha Latte": 5.800, "Americano": 5.000}
expected_category_revenue = {"Coffee": 30.500, "Pastry": 6.000, "Dessert": 3.500, "Tea": 5.800}
expected_daily_revenue = {"2026-06-20": 13.000, "2026-06-21": 12.050, "2026-06-22": 12.500, "2026-06-23": 8.250}
if any(round(product_revenue[key], 3) != value for key, value in expected_product_revenue.items()): errors.append("product revenue results are inconsistent")
if any(round(category_revenue[key], 3) != value for key, value in expected_category_revenue.items()): errors.append("category revenue results are inconsistent")
if any(round(daily_revenue[key], 3) != value for key, value in expected_daily_revenue.items()): errors.append("daily revenue results are inconsistent")
if dict(product_items) != {"Iced Latte": 6, "Cold Brew": 3, "Croissant": 4, "Brownie": 2, "Matcha Latte": 2, "Americano": 4}: errors.append("product item totals are inconsistent")
if (date(2026, 6, 23) - date(2026, 6, 20)).days != 3: errors.append("date-difference example is inconsistent")

all_html = unescape("\n".join(l["body"] for s in segments for l in s["lessons"]))
for required in ("45.800", "30.500", "22.250", "16.500", "13.000", "7.633", "8.867"):
    if required not in all_html: errors.append(f"expected verified result {required} is missing")

for forbidden in (
    "SUM(quantity) = 5",
    "These should usually match.",
    "average order value",
    "total_orders",
):
    if forbidden.lower() in all_html.lower(): errors.append(f"known incorrect or misleading phrase remains: {forbidden}")

# A zero-experience learner must be able to reproduce the teaching database.
setup_sql = ROOT / "setup" / "coffee_shop.sql"
setup_guide = ROOT / "setup" / "README.md"
if not setup_sql.is_file():
    errors.append("missing reproducible setup/coffee_shop.sql")
else:
    setup_text = setup_sql.read_text(encoding="utf-8")
    for required in ("DROP DATABASE IF EXISTS coffee_shop", "CREATE TABLE products", "CREATE TABLE orders", "INSERT INTO products", "INSERT INTO orders", "expected_45_800_revenue"):
        if required not in setup_text: errors.append(f"setup SQL is missing {required}")
if not setup_guide.is_file():
    errors.append("missing beginner setup guide and data dictionary")
else:
    guide_text = setup_guide.read_text(encoding="utf-8")
    for required in ("Test the connection", "Create the practice database", "Reset when needed", "How to run a lesson query", "Data dictionary"):
        if required not in guide_text: errors.append(f"setup guide is missing {required}")

# Job readiness must be a visible, assessed path—not an unlinked promise.
career_page = ROOT / "career-center.html"
capstone_setup = ROOT / "capstone" / "capstone_setup.sql"
capstone_solution = ROOT / "capstone" / "reference_solution.sql"
project_dataset = ROOT / "project_data" / "retail_project_setup.sql"
project_readme = ROOT / "project_data" / "README.md"
project_starters = ROOT / "project_data" / "starter_questions.sql"
project_walkthrough = ROOT / "project_data" / "analyst_walkthrough.md"
if not career_page.is_file():
    errors.append("missing learner-facing career center")
else:
    career_text = career_page.read_text(encoding="utf-8")
    for required in ("WORKPLACE SQL FIELD GUIDE", "least privilege", "Parameterize input", "UNION ALL", "DIALECTS", "CUMULATIVE ASSESSMENTS", "GATE 1", "GATE 2", "GATE 3", "PORTFOLIO CAPSTONE", "Required deliverables", "Quality assurance", "Scoring rubric", "TIMED INTERVIEW LAB", "PUBLISH THE EVIDENCE", "FINAL READINESS GATE"):
        if required not in career_text: errors.append(f"career center is missing {required}")
    if career_text.count("Expected:</strong>") < 5:
        errors.append("career center must contain five explained interview prompts")
index_text = (ROOT / "index.html").read_text(encoding="utf-8")
if index_text.count('href="career-center.html"') < 2:
    errors.append("career center is not linked from course header and learning path")
for required in ('href="academy.css"', 'id="curriculumToggle"', 'class="breadcrumbs"', 'id="lessonToc"', 'class="lesson-toc"'):
    if required not in index_text: errors.append(f"redesigned learning shell is missing {required}")
app_text = (ROOT / "app.js").read_text(encoding="utf-8")
for required in ("dataset.quizId", "Try again.", "Pass all ${required} questions first", "lesson.title==='Section knowledge check'"):
    if required not in app_text: errors.append(f"assessment gating is missing {required}")
for required in ("function renderToc", "function highlightSQL", "nav-group", "lesson-mode", "course-overview-link"):
    if required not in app_text: errors.append(f"redesigned course interaction is missing {required}")
for forbidden in ("total_orders", "avg_order_revenue"):
    if forbidden in app_text: errors.append(f"fallback lesson content still contains misleading label {forbidden}")
if not (ROOT / "academy.css").is_file():
    errors.append("missing redesigned academy stylesheet")
if not capstone_setup.is_file():
    errors.append("missing capstone setup dataset")
else:
    capstone_text = capstone_setup.read_text(encoding="utf-8")
    for required in ("CREATE TABLE stores", "CREATE TABLE customers", "CREATE TABLE products", "CREATE TABLE orders", "CREATE TABLE order_items", "'cancelled'", "'pending'", "NULL", "-1.500"):
        if required not in capstone_text: errors.append(f"capstone dataset is missing {required}")
if not capstone_solution.is_file():
    errors.append("missing capstone reference solution")
else:
    solution_text = capstone_solution.read_text(encoding="utf-8")
    for required in ("clean_order_items_v", "DENSE_RANK()", "AVG(sm.revenue) OVER", "NOT EXISTS", "LAG(revenue)", "completed_sales_v", "QA reconciliation", "EXPLAIN", "CREATE INDEX"):
        if required not in solution_text: errors.append(f"capstone solution is missing {required}")
if not project_dataset.is_file():
    errors.append("missing larger project dataset setup")
else:
    project_text = project_dataset.read_text(encoding="utf-8")
    for required in ("CREATE DATABASE metromart_project", "CREATE TABLE stores", "CREATE TABLE employees", "CREATE TABLE customers", "CREATE TABLE orders", "CREATE TABLE order_items", "CREATE TABLE returns", "CREATE TABLE inventory_snapshots", "CREATE TABLE customer_feedback", "raw_customer_import", "cte_max_recursion_depth", "WHERE n < 1800", "WHERE n < 5400"):
        if required not in project_text: errors.append(f"project dataset is missing {required}")
if not project_readme.is_file():
    errors.append("missing larger project dataset README")
else:
    readme_text = project_readme.read_text(encoding="utf-8")
    for required in ("MetroMart Project Dataset", "Practice Coverage", "Suggested Project Brief", "Important Business Rules"):
        if required not in readme_text: errors.append(f"project dataset README is missing {required}")
if not project_starters.is_file():
    errors.append("missing larger project starter questions")
else:
    starters_text = project_starters.read_text(encoding="utf-8")
    for required in ("GROUP BY", "HAVING", "LEFT JOIN", "WITH product_month", "DENSE_RANK()", "CREATE OR REPLACE VIEW completed_valid_sales_v", "EXPLAIN", "CREATE INDEX idx_orders_status_date_store"):
        if required not in starters_text: errors.append(f"project starter questions are missing {required}")
if not project_walkthrough.is_file():
    errors.append("missing analyst walkthrough for larger project dataset")
else:
    walkthrough_text = project_walkthrough.read_text(encoding="utf-8")
    for required in ("The Work Request", "Correct Customer Data in a Staging Layer", "customers_staging", "START TRANSACTION", "COMMIT", "Build the Trusted Reporting View", "Reconcile the View Against the Source", "Month-Over-Month Revenue Change", "Performance Check", "Analyst Summary Template"):
        if required not in walkthrough_text: errors.append(f"project analyst walkthrough is missing {required}")

for required in ("RIGHT JOIN", "A self join", "NOT EXISTS", "CROSS JOIN", "WITH product_sales", "ROW_NUMBER()", "DENSE_RANK()", "LAG(", "LEAD(", "AVG(revenue) OVER", "ROWS BETWEEN UNBOUNDED PRECEDING", "TIMESTAMPDIFF", "NULLIF", "Net revenue", "Writing findings and recommendations"):
    if required not in all_html: errors.append(f"required advanced concept {required} is missing")

walkthrough_coverage = {
    "SOURCE setup command": ("SOURCE ",),
    "boolean quality counts": ("SUM(quantity IS NULL)",),
    "DATE cast": ("DATE(",),
    "DATE_SUB interval": ("DATE_SUB",),
    "refund timing definition": ("refunds in the month", "return happened"),
}
for label, terms in walkthrough_coverage.items():
    if any(term in walkthrough_text for term in terms) and not any(term in all_html for term in terms):
        errors.append(f"walkthrough uses {label}, but the course does not teach it")

if errors:
    print("COURSE AUDIT FAILED")
    print("\n".join(f"- {error}" for error in errors))
    raise SystemExit(1)
print(f"COURSE AUDIT PASSED: {len(segments)} chapters, {sum(len(s['lessons']) for s in segments)} textbook sections")
