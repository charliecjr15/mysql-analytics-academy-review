"""Build browser lesson data from the canonical course transcripts."""
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile
from hashlib import sha256
import html, json, re
from course_enrichment import ENRICHMENTS

ROOT = Path(__file__).resolve().parent
EXPECTED_RESULTS_PATH = ROOT / "expected-results.json"
EXPECTED_RESULTS = json.loads(EXPECTED_RESULTS_PATH.read_text(encoding="utf-8")) if EXPECTED_RESULTS_PATH.exists() else {}
SOURCES = []
for n in range(1, 4):
    docx_source = Path.home() / f"Desktop/MySQL Analytics Lessons/MySQL for Data Analytics Segment {n}.docx"
    txt_source = Path.home() / f"Documents/MySQL for Data Analytics Segment {n}.txt"
    SOURCES.append(docx_source if docx_source.exists() else txt_source)
SOURCES.extend(Path.home() / f"Documents/MySQL for Data Analytics Segment {n}.txt" for n in range(4, 8))
TRANSCRIPTS = [Path.home() / f"Documents/MySQL for Data Analytics Segment {n}.txt" for n in range(1, 8)]
SOURCES.extend(ROOT / f"lessons/segment_{n}.txt" for n in range(8, 14))
TRANSCRIPTS.extend(ROOT / f"lessons/segment_{n}.txt" for n in range(8, 14))
META = [
    ("MySQL Basics", "Understand databases, tables, SELECT, filters, sorting, and limits."),
    ("Build the Database", "Create coffee_shop, design products, load data, reset safely, and debug errors."),
    ("Orders & KPIs", "Create orders and calculate revenue, aggregates, KPIs, and filtered metrics."),
    ("GROUP BY", "Build product, category, and daily performance reports from grouped data."),
    ("HAVING", "Filter grouped summaries and combine row-level and group-level conditions."),
    ("JOINS", "Connect products and orders with INNER JOIN and LEFT JOIN reports."),
    ("Keys & Database Design", "Replace repeated product data with primary and foreign keys."),
    ("Subqueries & CTEs", "Build readable multi-step analyses with nested queries and named intermediate results."),
    ("Window Functions", "Create rankings, running totals, period comparisons, and analytical windows."),
    ("CASE, Dates & Text", "Create business labels, calendar dimensions, and clean reporting text."),
    ("Data Cleaning", "Profile, standardize, validate, and safely correct unreliable source data."),
    ("Views & Reporting", "Package trusted SQL logic into reusable reporting views."),
    ("Query Performance", "Read execution plans, design indexes, and reduce unnecessary query work."),
]
ORIGINAL_TITLES = [title for title, _ in META]
WORKFLOW_ORDER = [
    "MySQL Basics",
    "Build the Database",
    "Keys & Database Design",
    "Data Cleaning",
    "CASE, Dates & Text",
    "Orders & KPIs",
    "JOINS",
    "GROUP BY",
    "HAVING",
    "Views & Reporting",
    "Subqueries & CTEs",
    "Window Functions",
    "Query Performance",
]
SECTION = re.compile(r"^(\d+)\.\s+(.+)$", re.M)
PRACTICE = re.compile(r"^(?:Practice|Question)\s+(\d+)(?::\s*([^\n]+))?$", re.M | re.I)
SQL_START = re.compile(r"^(WITH\s+[a-z_][\w]*\s+AS\s*\(|EXPLAIN\b|SHOW\s+INDEX\b|SELECT\b|FROM\s+[a-z_]|WHERE\s+[a-z_]|GROUP BY\s+[a-z_]+(?:,\s*[a-z_]+)*(?:;|$)|ORDER BY\s+[a-z_]|LIMIT\s+\d|CREATE\b|ALTER\b|UPDATE\s+[a-z_]|DELETE\s+FROM\b|START\s+TRANSACTION\b|COMMIT\b|ROLLBACK\b|SOURCE\s+|USE\s+[a-z_]|DROP\b|INSERT\s+INTO\b|VALUES\s*\(|DESCRIBE\s+[a-z_]|ROUND\(|SUM\(|AVG\(|COUNT\()", re.I)
WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def normalize_transcript(raw):
    """Convert lightweight Markdown transcripts to the course's plain-text format."""
    lines = raw.replace("\r\n", "\n").replace("\\t", "\t").splitlines()
    normalized = []
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if stripped == "---":
            continue
        if re.match(r"^Absolutely, Charlie\b", stripped, re.I):
            continue
        if re.match(r"^Say [“\"]?next segment", stripped, re.I):
            continue
        heading = re.match(r"^#\s+(\d+\.\s+.+)$", stripped)
        if heading:
            line = heading.group(1)
        elif stripped.startswith("# "):
            line = stripped[2:]
        elif stripped.startswith("## "):
            line = stripped[3:]
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-+:?", cell.replace(" ", "")) for cell in cells):
                continue
            line = "\t".join(cells)
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = re.sub(r"`([^`]+)`", r"\1", line)
        line = re.sub(r"^>\s+", "", line)
        normalized.append(line)
    return "\n".join(normalized)

def node_text(node):
    """Read Word text while preserving tabs and explicit line breaks."""
    parts = []
    for item in node.iter():
        if item.tag == f"{WORD_NS}t": parts.append(item.text or "")
        elif item.tag == f"{WORD_NS}tab": parts.append("\t")
        elif item.tag in (f"{WORD_NS}br", f"{WORD_NS}cr"): parts.append("\n")
    return "".join(parts)

def read_docx(path):
    """Extract paragraphs and tables directly from the Word lesson source."""
    with ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    blocks = []
    body = root.find(f"{WORD_NS}body")
    for node in body:
        if node.tag == f"{WORD_NS}p":
            blocks.append(node_text(node))
        elif node.tag == f"{WORD_NS}tbl":
            rows = []
            for row in node.findall(f"{WORD_NS}tr"):
                cells = []
                for cell in row.findall(f"{WORD_NS}tc"):
                    cells.append(node_text(cell))
                rows.append("\t".join(cells))
            blocks.append("\n".join(rows))
    return "\n\n".join(blocks)

def render_table(block):
    rows = [line.split("\t") for line in block.splitlines()]
    width = max(map(len, rows))
    if width < 2: return None
    rows = [row + [""] * (width - len(row)) for row in rows]
    caption = ""
    if len(rows) > 1 and sum(bool(cell.strip()) for cell in rows[0]) == 1 and all(cell.strip() for cell in rows[1]):
        caption = next(cell.strip() for cell in rows[0] if cell.strip())
        rows = rows[1:]
    head = "".join(f"<th>{html.escape(x)}</th>" for x in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{html.escape(x)}</td>" for x in row) + "</tr>" for row in rows[1:])
    if not body:
        body = f'<tr class="empty-result"><td colspan="{width}">No data rows</td></tr>'
    caption_html = f'<caption>{html.escape(caption)}</caption>' if caption else ""
    return f'<div class="table-scroll"><table class="data-table">{caption_html}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'

def render_block(block):
    block = block.strip()
    if not block: return ""
    if "\t" in block:
        lines = block.splitlines()
        split_at = next((i for i, line in enumerate(lines[1:], 1) if "\t" not in line), len(lines))
        result = render_table("\n".join(lines[:split_at]))
        if result:
            remainder = "\n".join(lines[split_at:]).strip()
            return result + (render_block(remainder) if remainder else "")
    if any(x in block for x in ("│", "┌", "├", "└", "↓", "→", "✅", "❌")):
        return f'<pre class="diagram">{html.escape(block.expandtabs(4))}</pre>'
    lines = block.splitlines()
    if lines[0].strip().lower() in ("sql:", "sql says:") and len(lines) > 1:
        label = html.escape(lines[0].strip())
        return f"<p>{label}</p>" + render_block("\n".join(lines[1:]))
    first_is_sql = bool(SQL_START.match(lines[0].strip()))
    if re.match(r"^From (?:the|our)\b", lines[0].strip(), re.I):
        first_is_sql = False
    if re.match(r"^(Where|From|Select|Order By|Group By|Limit)\b", lines[0].strip()) and not re.match(r"^(WHERE|FROM|SELECT|ORDER BY|GROUP BY|LIMIT)\b", lines[0].strip()):
        first_is_sql = False
    clause_start = re.match(r"^(WHERE|GROUP BY|ORDER BY|LIMIT)\b", lines[0].strip())
    if clause_start:
        valid_clause = re.match(
            r"^(?:WHERE\s+[a-z_][\w.]*\s*(?:=|<>|>=|<=|>|<|IN\b|IS\b|BETWEEN\b)|GROUP BY\s+[a-z_][\w.]*(?:\s*,\s*[a-z_][\w.]*)*|ORDER BY\s+[a-z_][\w.]*(?:\s+(?:ASC|DESC))?|LIMIT\s+\d+)",
            lines[0].strip(), re.I
        )
        first_is_sql = bool(valid_clause)
    sql_tokens = ("WITH", "EXPLAIN", "SHOW INDEX", "SELECT", "FROM", "CREATE", "ALTER", "UPDATE", "START TRANSACTION", "COMMIT", "ROLLBACK", "SOURCE", "INSERT", "WHERE", "GROUP BY", "ORDER BY", "LIMIT", "VALUES", "DROP", "USE COFFEE_SHOP", "DESCRIBE")
    aggregate_list = len(lines) > 1 and not any(line.rstrip().endswith(";") for line in lines) and lines[0].strip().upper() in ("COUNT", "SUM", "AVG", "MIN", "MAX")
    if first_is_sql and not aggregate_list and not block.lower().endswith("means:") and any(x in block.upper() for x in sql_tokens):
        statement_end = next((i for i, line in enumerate(lines) if line.rstrip().endswith(";")), None)
        if statement_end is not None and statement_end < len(lines) - 1:
            return render_block("\n".join(lines[:statement_end + 1])) + render_block("\n".join(lines[statement_end + 1:]))
        return f'<div class="code-block"><div class="code-label"><span>SQL</span><button data-copy>Copy query</button></div><pre><code>{html.escape(block)}</code></pre></div>'
    if len(block.splitlines()) > 1 and all(x.startswith("- ") for x in block.splitlines()):
        return "<ul>" + "".join(f"<li>{html.escape(x[2:])}</li>" for x in block.splitlines()) + "</ul>"
    return f'<p>{html.escape(block.expandtabs(4)).replace(chr(10), "<br>")}</p>'

def make_body(number, title, text):
    blocks = [x.strip() for x in re.split(r"\n\s*\n", text.strip()) if x.strip()]
    grouped = []; index = 0
    statement_start = re.compile(r"^(WITH\s+\w+\s+AS\s*\(|EXPLAIN\b|SHOW\s+INDEX\b|SELECT\s+\S|CREATE\s+(?:DATABASE|TABLE|VIEW|INDEX)\b|ALTER\s+TABLE\b|UPDATE\s+\w|DELETE\s+FROM\b|START\s+TRANSACTION\b|COMMIT\b|ROLLBACK\b|SOURCE\s+|USE\s+\w|DROP\s+(?:DATABASE|TABLE|VIEW|INDEX)\b|INSERT\s+INTO\s+\w|DESCRIBE\s+\w)", re.I)
    while index < len(blocks):
        current = blocks[index]
        next_block = blocks[index + 1] if index + 1 < len(blocks) else ""
        exact_select = current.upper() == "SELECT" and not next_block.lower().startswith("select means")
        statement_window = []
        for candidate_block in blocks[index:index + 16]:
            if statement_window and re.match(r"^(?:Better|Wrong|Correct|Incorrect|Answer|Expected result|Why)(?::|$)", candidate_block.strip(), re.I):
                break
            statement_window.append(candidate_block)
        has_terminator = any(x.rstrip().endswith(";") for x in statement_window)
        starts_statement = bool(statement_start.match(current)) and not current.lower().startswith("select means")
        if (starts_statement or exact_select) and not current.rstrip().endswith(";") and has_terminator:
            statement = [current]
            index += 1
            while index < len(blocks):
                statement.append(blocks[index])
                ended = blocks[index].rstrip().endswith(";")
                index += 1
                if ended: break
            grouped.append("\n".join(statement))
        else:
            grouped.append(current); index += 1
    visual_grouped = []; index = 0
    diagram_tokens = ("│", "┌", "├", "└", "↓", "→", "✅", "❌")
    while index < len(grouped):
        if any(token in grouped[index] for token in diagram_tokens):
            visual = [grouped[index]]; index += 1
            while index < len(grouped) and any(token in grouped[index] for token in diagram_tokens):
                visual.append(grouped[index]); index += 1
            visual_grouped.append("\n".join(visual))
        else:
            visual_grouped.append(grouped[index]); index += 1
    content = "".join(render_block(x) for x in visual_grouped)
    return f'<p class="eyebrow">SOURCE LESSON {number}</p><h2>{html.escape(title)}</h2>{content}'

def parse_source(path, transcript, title, desc):
    # DOCX files are canonical where present. Their matching transcripts
    # preserve tabs and row breaks that Word stores as positioned text.
    if not path.exists(): raise FileNotFoundError(path)
    raw = normalize_transcript(transcript.read_text(encoding="utf-8"))
    segment_starts = list(re.finditer(r"(?m)^Segment\s+\d+\s*[—-]", raw))
    if len(segment_starts) > 1:
        raw = raw[:segment_starts[1].start()].rstrip()
    raw = re.sub(r"average order value", "average order-row revenue", raw, flags=re.I)
    if title == "MySQL Basics":
        raw = raw.replace(
            "Expected result:\n\nproduct_name\tprice\nCold Brew\t3.000\nIced Latte",
            "Expected result:\n\nproduct_name\tprice\nCold Brew\t3.000\nIced Latte\t2.750",
        )
    if title == "Orders & KPIs":
        raw = raw.replace("total_orders", "total_order_rows")
        raw = raw.replace("Total orders", "Total order rows")
    if title == "JOINS":
        raw = raw.replace("These should usually match.", "In this fixed teaching dataset, these should match. In real sales data they may differ because of discounts or price changes.")
    pipeline_step = re.compile(r"^(FROM|WHERE|GROUP BY|HAVING|SELECT|ORDER BY|LIMIT)\s{2,}", re.I)
    candidates = [match for match in SECTION.finditer(raw) if not pipeline_step.match(match.group(2))]
    matches = []; expected = 1
    for candidate in candidates:
        if int(candidate.group(1)) == expected:
            matches.append(candidate); expected += 1
    lessons = []
    preamble = raw[raw.find("\n") + 1:matches[0].start()].strip()
    lessons.append({"title":"Segment overview","time":max(3,len(preamble.split())//130),"body":make_body("00","What you will learn",preamble)})
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        number, heading = match.group(1), match.group(2).strip()
        text = raw[match.end():end].strip()
        if "practice questions" in heading.lower() or "practice queries" in heading.lower():
            practice_matches = list(PRACTICE.finditer(text))
            if practice_matches:
                intro = text[:practice_matches[0].start()].strip()
                for practice_index, practice_match in enumerate(practice_matches):
                    practice_end = practice_matches[practice_index + 1].start() if practice_index + 1 < len(practice_matches) else len(text)
                    practice_number = practice_match.group(1)
                    practice_text = text[practice_match.end():practice_end].strip()
                    practice_title = (practice_match.group(2) or "").strip()
                    if not practice_title:
                        for line in practice_text.splitlines():
                            candidate = line.strip()
                            if not candidate or candidate.lower() in ("question:", "answer:", "sql:", "hint:", "expected result:"):
                                continue
                            if SQL_START.match(candidate):
                                continue
                            practice_title = candidate
                            break
                    practice_title = practice_title or f"Question {practice_number}"
                    lesson_text = ((intro + "\n\n") if practice_index == 0 and intro else "") + practice_text
                    lessons.append({
                        "title":f"Practice {practice_number}: {practice_title}",
                        "time":max(3, min(18, len(lesson_text.split()) // 110 + 2)),
                        "body":make_body(f"{number}.{practice_number}", f"Practice {practice_number}: {practice_title}", lesson_text),
                    })
                continue
        lessons.append({"title":heading,"time":max(3,min(18,len(text.split())//110+2)),"body":make_body(number,heading,text)})
    return {"title":title,"desc":desc,"lessons":lessons}

VISUALS = [
    ("segment-01-sql-basics.webp", "SQL basics illustrated as selecting columns, filtering rows, and sorting a database result.", "A database holds related tables. SELECT chooses columns, WHERE filters rows, and ORDER BY sorts the result."),
    ("segment-02-build-database.webp", "Database construction illustrated in four stages: create database, create table, define columns, and insert rows.", "Build the container first, define its table structure, then load rows that follow that structure."),
    ("segment-03-kpis.webp", "Order rows passing through a revenue calculation and producing business KPI cards.", "Row-level revenue is quantity multiplied by unit price. Aggregates combine those rows into useful KPIs."),
    ("segment-04-group-by.webp", "Mixed order cards separated into product buckets and summarized into one row per group.", "GROUP BY creates a bucket for each distinct value, and aggregate functions calculate within each bucket."),
    ("segment-05-having.webp", "Two-stage SQL filtering with WHERE before grouping and HAVING after grouping.", "WHERE removes raw rows before groups are formed. HAVING removes completed summary groups afterward."),
    ("segment-06-joins.webp", "Products and orders connected by matching product identifiers to create combined result rows.", "A JOIN matches related rows. The result can contain selected columns from both connected tables."),
    ("segment-07-keys.webp", "Primary keys in a parent products table connected to foreign keys in child order rows.", "Primary keys identify parent rows. Foreign keys create protected one-to-many relationships."),
    ("segment-08-ctes.webp", "Orders flowing through product sales and average sales CTE stages into an above-average result.", "CTEs give names to intermediate query results, making multi-step analysis easier to read and verify."),
    ("segment-09-windows.webp", "A window moving across dated rows while calculating running totals, ranks, and previous values.", "Window functions calculate across related rows while keeping the individual result rows visible."),
    ("segment-10-functions.webp", "Order receipts moving through CASE labeling, date extraction, and text-cleaning stations.", "CASE, date functions, and text functions turn stored facts into useful reporting dimensions."),
    ("segment-11-cleaning.webp", "Messy product records being profiled, cleaned, validated, and converted into trusted data.", "Cleaning starts by finding issues, applies written business rules, and validates results before committing changes."),
    ("segment-12-views.webp", "Products and orders flowing through a saved SQL view into several reusable reports.", "A view saves a query definition so multiple reports can reuse the same trusted logic."),
    ("segment-13-performance.webp", "A slow query scan being explained and redirected through an organized index toward a fast result.", "EXPLAIN reveals the query plan, while appropriate indexes can reduce the rows MySQL must inspect."),
]

def add_segment_visuals(segments):
    """Add one accessible, responsive visual explainer to each segment overview."""
    for segment, (filename, alt, caption) in zip(segments, VISUALS):
        figure = (
            f'<figure class="lesson-visual">'
            f'<img src="assets/lesson-visuals/{filename}" alt="{html.escape(alt)}" loading="lazy" decoding="async">'
            f'<figcaption><strong>Visual model</strong>{html.escape(caption)} <em>Concept illustration; use the lesson tables for exact course values.</em></figcaption>'
            f'</figure>'
        )
        segment["lessons"][0]["body"] += figure

def reorder_for_workflow(segments):
    """Present the same source lessons in the order an analyst uses them at work."""
    global ENRICHMENTS, VISUALS, SEGMENT_RELEVANCE, SEGMENT_CONCEPTS
    by_title = {segment["title"]: segment for segment in segments}
    missing = [title for title in WORKFLOW_ORDER if title not in by_title]
    if missing:
        raise ValueError(f"Workflow order references unknown segments: {missing}")
    original_index = {title: index for index, title in enumerate(ORIGINAL_TITLES)}
    for source_number, segment in enumerate(segments, 1):
        segment["source_number"] = source_number
    ENRICHMENTS = [ENRICHMENTS[original_index[title]] for title in WORKFLOW_ORDER]
    VISUALS = [VISUALS[original_index[title]] for title in WORKFLOW_ORDER]
    SEGMENT_RELEVANCE = [SEGMENT_RELEVANCE[original_index[title]] for title in WORKFLOW_ORDER]
    SEGMENT_CONCEPTS = [SEGMENT_CONCEPTS[original_index[title]] for title in WORKFLOW_ORDER]
    reordered = [by_title[title] for title in WORKFLOW_ORDER]
    for workflow_number, segment in enumerate(reordered, 1):
        segment["workflow_number"] = workflow_number
    return reordered

def relabel_workflow_chapters(segments):
    """Keep visible chapter labels aligned with the workflow order."""
    for chapter_number, segment in enumerate(segments, 1):
        section_number = 0
        for lesson in segment["lessons"]:
            if lesson["title"] == "Section knowledge check" or lesson["title"].startswith("Mini-project:"):
                continue
            section_number += 1
            lesson["body"] = re.sub(
                r'<p class="chapter-label">CHAPTER \d+ · SECTION \d+</p>',
                f'<p class="chapter-label">CHAPTER {chapter_number} · SECTION {section_number}</p>',
                lesson["body"],
                count=1,
            )

def visual_flow(stages, caption):
    cards = "".join(
        f'<div class="flow-step"><span>{index}</span><strong>{html.escape(title)}</strong><small>{html.escape(detail)}</small></div>'
        for index, (title, detail) in enumerate(stages, 1)
    )
    return (
        f'<figure class="query-visual" role="img" aria-label="{html.escape(caption)}">'
        f'<div class="query-visual-title"><span>VISUAL WALKTHROUGH</span><strong>{html.escape(caption)}</strong></div>'
        f'<div class="query-flow">{cards}</div>'
        f'</figure>'
    )

def scene_item(icon, title, detail="", state=""):
    return (
        f'<div class="scene-item {state}"><span class="scene-icon">{icon}</span>'
        f'<div><strong>{html.escape(title)}</strong>'
        f'{f"<small>{html.escape(detail)}</small>" if detail else ""}</div></div>'
    )

def transformation_scene(title, operation, inputs, outputs, note):
    return (
        f'<figure class="statement-scene" role="img" aria-label="{html.escape(title)}">'
        f'<div class="scene-heading"><span>STATEMENT IN ACTION</span><strong>{html.escape(title)}</strong></div>'
        f'<div class="scene-stage">'
        f'<section><b>BEFORE</b><div class="scene-items">{"".join(inputs)}</div></section>'
        f'<div class="scene-operation"><i>→</i><div><span>{operation[0]}</span><strong>{html.escape(operation[1])}</strong><small>{html.escape(operation[2])}</small></div><i>→</i></div>'
        f'<section><b>AFTER</b><div class="scene-items">{"".join(outputs)}</div></section>'
        f'</div><figcaption>{html.escape(note)}</figcaption></figure>'
    )

def compact_sql(text, limit=82):
    """Collapse SQL whitespace for a truthful, compact visual label."""
    value = " ".join(html.unescape(text).split())
    return value if len(value) <= limit else value[:limit - 1].rstrip() + "…"

def accurate_statement_scene(sql):
    """Build a visual only from identifiers and clauses present in this SQL."""
    raw = html.unescape(sql).strip()
    starter = re.search(
        r"(?is)(?<![A-Z0-9_])(?:WITH\s+[A-Z_][A-Z0-9_]*\s+AS\s*\(|EXPLAIN\b|SHOW\s+INDEX\b|SELECT\b|CREATE\s+(?:DATABASE|TABLE|VIEW|INDEX)\b|ALTER\s+TABLE\b|INSERT\s+INTO\b|UPDATE\s+[A-Z_]|DELETE\s+FROM\b|START\s+TRANSACTION\b|COMMIT\b|ROLLBACK\b|SOURCE\s+|USE\s+[A-Z_]|DROP\s+(?:DATABASE|TABLE|VIEW|INDEX)\b|DESCRIBE\s+[A-Z_]|WHERE\s+[A-Z_]|GROUP\s+BY\s+[A-Z_]|ORDER\s+BY\s+[A-Z_]|LIMIT\s+\d)",
        raw,
    )
    if not starter:
        return ""
    raw = raw[starter.start():].strip()
    upper = raw.upper()
    stages = []
    caption = "How this statement is processed"

    # Multi-statement setup scripts are shown as their real ordered operations.
    statements = [compact_sql(part, 58) for part in raw.split(";") if part.strip()]
    if len(statements) > 1 and not upper.startswith(("WITH ", "SELECT ", "EXPLAIN ")):
        stages = [(f"Statement {index}", statement) for index, statement in enumerate(statements[:6], 1)]
        caption = "Run this SQL script in statement order"
        return visual_flow(stages, caption).replace("VISUAL WALKTHROUGH", "STATEMENT IN ACTION")

    if upper.startswith("EXPLAIN"):
        inner = re.sub(r"(?is)^EXPLAIN\s+", "", raw, count=1)
        tables = re.findall(r"(?i)\b(?:FROM|JOIN)\s+([a-z_][\w]*)", inner)
        stages = [("Read the query", compact_sql(inner)), ("Plan table access", ", ".join(dict.fromkeys(tables)) or "No table source")]
        stages += [("Return plan columns", "Inspect type, possible_keys, key, rows, filtered, and Extra")]
        caption = "EXPLAIN plans this exact query without returning its normal rows"
    elif upper.startswith("SHOW INDEX"):
        table = re.search(r"(?i)SHOW\s+INDEX\s+FROM\s+([a-z_][\w]*)", raw)
        stages = [("Inspect table", table.group(1) if table else compact_sql(raw)), ("List indexes", "Return index names, columns, sequence, uniqueness, and visibility")]
        caption = "SHOW INDEX reports the table's current index definitions"
    elif re.match(r"(?is)^(WITH\b|SELECT\b)", raw):
        ctes = re.findall(r"(?i)(?:\bWITH|,)\s*([a-z_][\w]*)\s+AS\s*\(", raw)
        if ctes:
            stages.append(("Build CTEs", ", ".join(ctes)))
        tables = re.findall(r"(?i)\b(?:FROM|JOIN)\s+([a-z_][\w]*)", raw)
        stages.append(("Read sources", ", ".join(dict.fromkeys(tables)) or "Expression-only SELECT"))
        select_starts = list(re.finditer(r"(?i)\bSELECT\b", raw))
        final_sql = raw[select_starts[-1].start():] if ctes and select_starts else raw
        joins = re.findall(r"(?i)\b(?:(LEFT|RIGHT|INNER|CROSS)\s+)?JOIN\s+([a-z_][\w]*)", final_sql)
        on_rules = re.findall(r"(?is)\bON\s+(.+?)(?=\b(?:LEFT|RIGHT|INNER|CROSS)?\s*JOIN\b|\bWHERE\b|\bGROUP\s+BY\b|\bHAVING\b|\bORDER\s+BY\b|\bLIMIT\b|;|$)", final_sql)
        for join_index, (join_type, joined_table) in enumerate(joins):
            rule = compact_sql(on_rules[join_index]) if join_index < len(on_rules) else "Combine every row pair (no ON condition)"
            stages.append((f"{(join_type or 'INNER').upper()} JOIN {joined_table}", rule))
        where = re.search(r"(?is)\bWHERE\s+(.+?)(?=\bGROUP\s+BY\b|\bHAVING\b|\bORDER\s+BY\b|\bLIMIT\b|;|$)", final_sql)
        group = re.search(r"(?is)\bGROUP\s+BY\s+(.+?)(?=\bHAVING\b|\bORDER\s+BY\b|\bLIMIT\b|;|$)", final_sql)
        having = re.search(r"(?is)\bHAVING\s+(.+?)(?=\bORDER\s+BY\b|\bLIMIT\b|;|$)", final_sql)
        if where: stages.append(("Filter source rows", compact_sql(where.group(1))))
        if group: stages.append(("Create groups", compact_sql(group.group(1))))
        if having: stages.append(("Filter groups", compact_sql(having.group(1))))
        window_functions = list(dict.fromkeys(re.findall(r"(?i)\b(ROW_NUMBER|RANK|DENSE_RANK|LAG|LEAD|SUM|AVG|COUNT)\s*\([^)]*\)\s+OVER", final_sql)))
        if window_functions: stages.append(("Calculate windows", ", ".join(name.upper() for name in window_functions)))
        window_specs = list(dict.fromkeys(compact_sql(spec) for spec in re.findall(r"(?is)\bOVER\s*\(([^)]*)\)", final_sql)))
        if window_specs: stages.append(("Window definition", " · ".join(window_specs)))
        selected = re.search(r"(?is)\bSELECT\s+(.+?)(?=\bFROM\b|$)", final_sql)
        stages.append(("Return columns", compact_sql(selected.group(1)) if selected else "Columns named by the final SELECT"))
        order_starts = list(re.finditer(r"(?i)\bORDER\s+BY\b", final_sql))
        order_text = ""
        if order_starts:
            order_text = re.split(r"(?is)\bLIMIT\b|;", final_sql[order_starts[-1].end():], maxsplit=1)[0].strip()
        limit = re.search(r"(?i)\bLIMIT\s+(\d+)", final_sql)
        if order_text: stages.append(("Sort result", compact_sql(order_text)))
        if limit: stages.append(("Keep rows", f"First {limit.group(1)} rows after sorting"))
        caption = "Execution map derived from this query's actual clauses"
    elif upper.startswith("INSERT"):
        table = re.search(r"(?i)INSERT\s+INTO\s+([a-z_][\w]*)", raw)
        groups = len(re.findall(r"\([^()]*(?:'[^']*'[^()]*)*\)\s*(?:,|;|$)", raw[raw.upper().find("VALUES") + 6:])) if "VALUES" in upper else 0
        stages = [("Target table", table.group(1) if table else "Named INSERT table"), ("Map columns", compact_sql(re.search(r"(?is)INSERT\s+INTO\s+[\w]+\s*(\([^)]*\))", raw).group(1)) if re.search(r"(?is)INSERT\s+INTO\s+[\w]+\s*(\([^)]*\))", raw) else "Use table column order"), ("Validate and store", f"{groups or 'Each'} VALUES row group")]
        caption = "INSERT maps these values into the named destination columns"
    elif upper.startswith("UPDATE"):
        table = re.search(r"(?i)UPDATE\s+([a-z_][\w]*)", raw)
        assignment = re.search(r"(?is)\bSET\s+(.+?)(?=\bWHERE\b|;|$)", raw)
        condition = re.search(r"(?is)\bWHERE\s+(.+?)(?=;|$)", raw)
        stages = [("Target table", table.group(1) if table else "Named table"), ("Choose rows", compact_sql(condition.group(1)) if condition else "Every row—verify this is intentional"), ("Assign values", compact_sql(assignment.group(1)) if assignment else "SET clause")]
        caption = "UPDATE applies this exact SET expression to matching rows"
    elif upper.startswith("DELETE"):
        table = re.search(r"(?i)DELETE\s+FROM\s+([a-z_][\w]*)", raw)
        condition = re.search(r"(?is)\bWHERE\s+(.+?)(?=;|$)", raw)
        stages = [("Target table", table.group(1) if table else "Named table"), ("Choose rows", compact_sql(condition.group(1)) if condition else "Every row—verify this is intentional"), ("Remove matches", "Return an affected-row count")]
        caption = "DELETE removes only rows selected by this condition"
    elif re.match(r"(?is)^CREATE(?:\s+OR\s+REPLACE)?\s+VIEW\b", raw):
        view = re.search(r"(?i)CREATE(?:\s+OR\s+REPLACE)?\s+VIEW\s+([a-z_]\w*)", raw)
        tables = re.findall(r"(?i)\b(?:FROM|JOIN)\s+([a-z_]\w*)", raw)
        stages = [
            ("Name the view", view.group(1) if view else "Named view"),
            ("Read source tables", ", ".join(dict.fromkeys(tables)) or "Sources named by the SELECT"),
            ("Save SELECT definition", "Future queries run this definition against current source rows"),
        ]
        caption = "CREATE VIEW saves this query and its actual table dependencies"
    elif upper.startswith(("CREATE ", "ALTER ", "DROP ", "USE ", "DESCRIBE ", "START TRANSACTION", "COMMIT", "ROLLBACK")):
        keyword = " ".join(upper.split()[:2]) if upper.startswith(("CREATE ", "ALTER ", "DROP ", "START ")) else upper.split()[0]
        stages = [("Send statement", compact_sql(raw)), ("MySQL action", {"USE":"Select the active database", "DESCRIBE":"Return the table definition", "COMMIT":"Make the transaction's changes permanent", "ROLLBACK":"Undo uncommitted transaction changes", "START TRANSACTION":"Begin a transaction boundary"}.get(keyword, "Change or inspect the named database object"))]
        caption = f"{keyword.title()} acts on the object named in this statement"
    elif upper.startswith("SOURCE "):
        stages = [("Locate script", compact_sql(raw)), ("Run statements", "Execute the SQL file from top to bottom"), ("Select project database", "Use metromart_project for the build-along queries")]
        caption = "SOURCE runs the MetroMart setup script"
    else:
        stages = [("Apply clause", compact_sql(raw)), ("Affect the query", "This fragment belongs inside a complete SQL statement")]
        caption = "This clause changes the surrounding query"
    return visual_flow(stages, caption).replace("VISUAL WALKTHROUGH", "STATEMENT IN ACTION")

def statement_scene(sql):
    """Render the course dataset changing as a SQL statement acts on it."""
    return accurate_statement_scene(sql)
    # Legacy scene templates remain below only as historical source context;
    # the return above prevents hard-coded examples from being attached to
    # unrelated statements.
    normalized = html.unescape(sql).upper()
    statement = re.search(r"\b(WITH|EXPLAIN|SHOW\s+INDEX|SELECT|INSERT\s+INTO|UPDATE|ALTER\s+TABLE|CREATE\s+(?:TABLE|DATABASE|VIEW|INDEX)|DROP|START\s+TRANSACTION|VALUES\s*\()", normalized)
    if statement:
        normalized = normalized[statement.start():]
    exists_subquery = re.search(r"\b(NOT\s+)?EXISTS\s*\(\s*SELECT\b", normalized)
    if exists_subquery:
        negated = bool(exists_subquery.group(1))
        return transformation_scene(
            f"{'NOT EXISTS' if negated else 'EXISTS'} checks each product for matching orders", ("🔍", "NOT EXISTS?" if negated else "EXISTS?", "Compare o.product_id with the current p.product_id"),
            [scene_item("☕", "Iced Latte", "product_id 1"), scene_item("🥤", "Cold Brew", "product_id 2"), scene_item("🍵", "Chai", "product_id 7")],
            ([scene_item("✕", "Iced Latte removed", "a matching order exists", "removed"), scene_item("✕", "Cold Brew removed", "a matching order exists", "removed"), scene_item("✅", "Chai kept", "no matching order exists", "kept")] if negated else [scene_item("✅", "Iced Latte kept", "orders contain product_id 1", "kept"), scene_item("✅", "Cold Brew kept", "orders contain product_id 2", "kept"), scene_item("✕", "Chai removed", "no order has product_id 7", "removed")]),
            ("NOT EXISTS keeps outer rows for which the correlated search finds nothing." if negated else "EXISTS returns only true or false. Multiple matching orders still keep the product once.")
        )
    if normalized.lstrip().startswith("EXPLAIN"):
        return transformation_scene(
            "EXPLAIN reveals how MySQL plans to execute a query", ("🗺", "EXPLAIN", "Inspect access type, chosen key, and estimated rows"),
            [scene_item("SQL", "Query statement", "the result you want")],
            [scene_item("📋", "Execution plan", "table · type · key · rows"), scene_item("🔎", "Optimization clue", "where MySQL expects work")],
            "EXPLAIN provides a plan to investigate; measure the real workload before and after changing it."
        )
    if normalized.lstrip().startswith("SHOW INDEX"):
        return transformation_scene(
            "SHOW INDEX lists the lookup structures already defined on a table", ("🔎", "SHOW INDEX", "Inspect names, columns, order, and uniqueness"),
            [scene_item("▦", "orders table", "primary key and foreign-key relationship")],
            [scene_item("🗂", "Index inventory", "key names and indexed columns", "kept")],
            "Inspect existing indexes before creating another one that duplicates the same leading columns."
        )
    if normalized.lstrip().startswith("CREATE VIEW"):
        return transformation_scene(
            "CREATE VIEW saves a SELECT definition under a reusable name", ("🔭", "CREATE VIEW", "Store the query definition, not copied result rows"),
            [scene_item("▦", "products", "current table rows"), scene_item("🧾", "orders", "current table rows"), scene_item("SQL", "Saved SELECT", "join and calculations")],
            [scene_item("👁", "Reusable view", "reports query one trusted interface", "kept")],
            "When underlying tables change, later view queries read the current data through the saved definition."
        )
    if normalized.lstrip().startswith("CREATE INDEX"):
        return transformation_scene(
            "CREATE INDEX builds an organized lookup path", ("🗂", "CREATE INDEX", "Arrange key values with row locations"),
            [scene_item("📦", "Unordered rows", "many values to scan")],
            [scene_item("A→Z", "Index entries", "ordered search values"), scene_item("⚡", "Narrow lookup", "fewer candidate rows")],
            "An index can reduce read work for suitable filters, but it consumes space and adds write maintenance."
        )
    if normalized.lstrip().startswith("UPDATE"):
        return transformation_scene(
            "UPDATE changes only rows whose WHERE condition is true", ("✏", "UPDATE", "SET assigns new values after filtering target rows"),
            [scene_item("🪪", "Coffee", "target row", "kept"), scene_item("🪪", "Coffees", "inconsistent target", "kept"), scene_item("🪪", "Tea", "not targeted")],
            [scene_item("✅", "Coffee", "standardized"), scene_item("✅", "Coffee", "standardized"), scene_item("🪪", "Tea", "unchanged")],
            "Preview the same WHERE condition with SELECT and validate affected rows before COMMIT."
        )
    if normalized.lstrip().startswith("ALTER TABLE"):
        return transformation_scene(
            "ALTER TABLE adds a rule to existing structure", ("🛡", "ADD CONSTRAINT", "Validate future values against the rule"),
            [scene_item("▦", "Existing table", "columns and current rows")],
            [scene_item("✅", "Protected table", "invalid values are rejected", "kept")],
            "Existing data must satisfy the constraint before MySQL can add it successfully."
        )
    if normalized.lstrip().startswith("DROP"):
        object_type = "VIEW" if "DROP VIEW" in normalized else "INDEX" if "DROP INDEX" in normalized else "TABLE"
        detail = "saved query definition" if object_type == "VIEW" else "lookup structure" if object_type == "INDEX" else "table structure and rows"
        note = "Dropping a view leaves its underlying tables intact." if object_type == "VIEW" else "Dropping an index leaves table rows intact but removes that lookup path." if object_type == "INDEX" else "Dropping a table removes its definition and stored rows."
        return transformation_scene(
            f"DROP {object_type} removes the named database object", ("🗑", f"DROP {object_type}", f"Remove the {detail}"),
            [scene_item("▦", f"Existing {object_type.lower()}", detail)],
            [scene_item("∅", f"{object_type.title()} removed", "no longer available")], note
        )
    if " OVER " in f" {normalized} " or "OVER(" in normalized:
        return transformation_scene(
            "The window calculation looks across rows without removing them", ("🪟", "OVER", "Read neighboring or partitioned rows"),
            [scene_item("📅", "June 20", "revenue 13.000"), scene_item("📅", "June 21", "revenue 12.050"), scene_item("📅", "June 22", "revenue 12.500")],
            [scene_item("1", "June 20 stays visible", "running total 13.000"), scene_item("2", "June 21 stays visible", "previous value 13.000"), scene_item("3", "June 22 stays visible", "running total 37.550")],
            "Unlike GROUP BY, a window function attaches an analytical value while preserving each result row."
        )
    if normalized.lstrip().startswith("WITH"):
        cte_names = re.findall(r"(?:WITH|,)\s*([A-Z_][A-Z0-9_]*)\s+AS\s*\(", normalized)
        named_outputs = [scene_item("📦", name.lower(), "named intermediate rows", "kept") for name in cte_names[:3]]
        return transformation_scene(
            "CTEs turn a complex query into named intermediate results", ("⚙", "WITH", "Build each named query result in sequence"),
            [scene_item("▦", "Source rows", "tables or earlier CTE results"), scene_item("SQL", "CTE query", "select, join, group, or filter")],
            (named_outputs or [scene_item("📦", "Named CTE", "intermediate rows", "kept")]) + [scene_item("📋", "Final query", "reads the named results", "kept")],
            "Each CTE produces rows that the next part of the same statement can read by name."
        )
    if normalized.lstrip().startswith("CREATE TABLE") and re.search(r"\bAS\s+SELECT\b", normalized):
        return transformation_scene(
            "CREATE TABLE ... AS SELECT copies query results into a new table", ("📋", "AS SELECT", "Run the query and store its result rows"),
            [scene_item("▦", "Source table", "existing rows and columns"), scene_item("SQL", "SELECT result", "rows chosen for the copy")],
            [scene_item("▦", "New staging table", "copied rows", "kept")],
            "The copied table does not automatically inherit every index, key, or constraint from the source."
        )
    if normalized.lstrip().startswith("CREATE TABLE"):
        table_match = re.search(r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+([A-Z_][A-Z0-9_]*)", normalized)
        table_name = table_match.group(1).lower() if table_match else "new_table"
        return transformation_scene(
            "CREATE TABLE turns a schema blueprint into an empty table", ("🛠", "CREATE TABLE", "Apply names, data types, and constraints"),
            [scene_item("📐", "Column blueprint", "names and data types"), scene_item("🛡", "Constraints", "keys and validation rules")],
            [scene_item("▦", f"{table_name} table", "defined columns created"), scene_item("∅", "No rows yet", "ready for INSERT")],
            "The statement creates structure only; rows are loaded later."
        )
    if normalized.lstrip().startswith("CREATE DATABASE"):
        return transformation_scene(
            "CREATE DATABASE adds a container to the MySQL server", ("🏗", "CREATE DATABASE", "Create coffee_shop if it is absent"),
            [scene_item("🖥", "MySQL server", "coffee_shop not present")],
            [scene_item("🗄", "coffee_shop", "new database container", "kept")],
            "USE coffee_shop selects this container for later table statements."
        )
    if normalized.lstrip().startswith("INSERT") or normalized.lstrip().startswith("VALUES"):
        inserting_orders = bool(re.search(r"INSERT\s+INTO\s+ORDERS\b", normalized))
        inputs = ([scene_item("#", "product_id", "1"), scene_item("×", "quantity", "2"), scene_item("$", "unit_price", "2.750"), scene_item("📅", "order_date", "2026-06-20")] if inserting_orders else [scene_item("1", "product_id", "1"), scene_item("Aa", "product_name", "'Iced Latte'"), scene_item("$", "price", "2.750")])
        result = "1 | 2 | 2.750 | 2026-06-20" if inserting_orders else "1 | Iced Latte | 2.750"
        return transformation_scene(
            "INSERT maps each value to its named destination column", ("➕", "INSERT", "Match values by position, then validate types"),
            inputs, [scene_item("🪪", "New stored row", result, "kept")],
            "Text is quoted, numbers remain numeric, and one parenthesized value group becomes one row."
        )
    if "CASE" in normalized:
        return transformation_scene(
            "CASE evaluates conditions in order and assigns the first matching label", ("🏷", "CASE", "Test WHEN conditions from top to bottom"),
            [scene_item("A", "Candidate value A", "test from first WHEN"), scene_item("B", "Candidate value B", "continue if earlier test is false"), scene_item("C", "Candidate value C", "use fallback if no WHEN matches")],
            [scene_item("1", "First label", "first WHEN is true", "kept"), scene_item("2", "Later label", "later WHEN is true", "kept"), scene_item("E", "ELSE label", "no WHEN is true", "kept")],
            "CASE stops at the first true WHEN condition, so condition order changes the result."
        )
    if any(function in normalized for function in ("DATE_FORMAT(", "YEAR(", "MONTH(", "DAY(", "DATEDIFF(")):
        return transformation_scene(
            "Date functions derive reporting values without changing the stored date", ("📅", "DATE FUNCTION", "Extract, format, or compare calendar values"),
            [scene_item("📆", "2026-06-22", "stored DATE value")],
            [scene_item("Y", "Year", "2026"), scene_item("M", "Month", "06"), scene_item("W", "Weekday", "Monday")],
            "The expression creates result columns; the underlying order_date remains a DATE."
        )
    if any(function in normalized for function in ("TRIM(", "LOWER(", "UPPER(", "CONCAT(")):
        return transformation_scene(
            "Text functions standardize or combine display values", ("Aa", "TEXT FUNCTION", "Transform the value in the query result"),
            [scene_item("Aa", "  Iced Latte  ", "outside spaces"), scene_item("Aa", "coffee", "inconsistent case")],
            [scene_item("✓", "Iced Latte", "TRIM applied", "kept"), scene_item("✓", "COFFEE", "UPPER applied", "kept")],
            "The query result changes; stored text changes only when an UPDATE is executed."
        )
    if " JOIN " in f" {normalized} ":
        left_join = "LEFT JOIN" in normalized
        on_match = re.search(r"\bON\s+(.+?)(?:\bWHERE\b|\bGROUP BY\b|\bORDER BY\b|;|$)", normalized, re.S)
        on_rule = " ".join(on_match.group(1).split())[:60] if on_match else "matching columns are equal"
        matching_by_name = "PRODUCT_NAME" in on_rule
        left_detail = "product_name = Iced Latte" if matching_by_name else "product_id = 1"
        right_detail = "product_name = Iced Latte" if matching_by_name else "product_id = 1"
        return transformation_scene(
            f"{'LEFT JOIN' if left_join else 'INNER JOIN'} connects rows using the ON condition", ("🔗", "ON", on_rule),
            [scene_item("☕", "products row", left_detail), scene_item("🧾", "orders row", right_detail), scene_item("🧾", "unmatched row", "no equal ON value", "removed")],
            ([scene_item("✅", "Combined result row", "Iced Latte · quantity 2", "kept"), scene_item("∅", "Unmatched left row", "right-side columns become NULL", "kept")] if left_join else [scene_item("✅", "Combined result row", "Iced Latte · quantity 2", "kept"), scene_item("✕", "Unmatched row", "not returned", "removed")]),
            ("LEFT JOIN preserves every row from the left table and fills unmatched right-side columns with NULL." if left_join else "INNER JOIN returns only row pairs that satisfy the ON condition.")
        )
    if "GROUP BY" in normalized:
        having = "HAVING" in normalized
        group_match = re.search(r"GROUP BY\s+(.+?)(?:\bHAVING\b|\bORDER BY\b|\bLIMIT\b|;|$)", normalized, re.S)
        group_key = " ".join(group_match.group(1).split())[:55] if group_match else "grouping value"
        return transformation_scene(
            "GROUP BY collects detail rows into one summary row per distinct value", ("🪣", "GROUP BY", group_key),
            [scene_item("🧾", "Group value A", "detail row 1"), scene_item("🧾", "Group value A", "detail row 2"), scene_item("🧾", "Group value B", "detail row 3")],
            ([scene_item("✅", "Group A summary", "HAVING condition is true", "kept"), scene_item("✕", "Group B summary", "HAVING condition is false", "removed")] if having else [scene_item("A", "Group A summary", "one calculated row", "kept"), scene_item("B", "Group B summary", "one calculated row", "kept")]),
            ("GROUP BY calculates each bucket first; HAVING then keeps only summary groups whose condition is true." if having else "Rows with equal grouping values become one bucket and produce one summary row.")
        )
    where_match = re.search(r"WHERE\s+(.+?)(?:GROUP BY|HAVING|ORDER BY|LIMIT|;|$)", normalized, re.S)
    if where_match:
        condition = " ".join(where_match.group(1).split())[:64]
        category_match = re.search(r"CATEGORY\s*(=|<>)\s*'COFFEE'", condition)
        quantity_match = re.search(r"QUANTITY\s*(>=|<=|<>|=|>|<)\s*(\d+)", condition)
        if category_match:
            keep_coffee = category_match.group(1) == "="
            before = [scene_item("☕", "Iced Latte", "Coffee"), scene_item("🥐", "Croissant", "Pastry"), scene_item("🍵", "Matcha Latte", "Tea")]
            after = [scene_item("✅" if keep_coffee else "✕", "Iced Latte", "Coffee " + ("matches" if keep_coffee else "excluded"), "kept" if keep_coffee else "removed"), scene_item("✕" if keep_coffee else "✅", "Croissant", "Pastry " + ("removed" if keep_coffee else "kept"), "removed" if keep_coffee else "kept"), scene_item("✕" if keep_coffee else "✅", "Matcha Latte", "Tea " + ("removed" if keep_coffee else "kept"), "removed" if keep_coffee else "kept")]
        elif quantity_match:
            operator, threshold = quantity_match.group(1), int(quantity_match.group(2))
            tests = {">": lambda v: v > threshold, "<": lambda v: v < threshold, ">=": lambda v: v >= threshold, "<=": lambda v: v <= threshold, "=": lambda v: v == threshold, "<>": lambda v: v != threshold}
            values = (1, 2, 4)
            before = [scene_item("🧾", f"Quantity {value}", "test the WHERE condition") for value in values]
            after = [scene_item("✅" if tests[operator](value) else "✕", f"Quantity {value}", "passes" if tests[operator](value) else "fails", "kept" if tests[operator](value) else "removed") for value in values]
        else:
            before = [scene_item("🧾", "Candidate row A", "test the condition"), scene_item("🧾", "Candidate row B", "test the condition"), scene_item("🧾", "Candidate row C", "test the condition")]
            after = [scene_item("✅", "True row", "kept", "kept"), scene_item("✕", "False row", "removed", "removed")]
        return transformation_scene(
            "WHERE tests the condition against each source row", ("⏬", "WHERE", condition), before, after,
            "Only rows for which the condition evaluates to true continue to SELECT."
        )
    if any(function in normalized for function in ("SUM(", "AVG(", "COUNT(", "MIN(", "MAX(")):
        function = next((name for name in ("SUM", "AVG", "COUNT", "MIN", "MAX") if f"{name}(" in normalized), "AGGREGATE")
        return transformation_scene(
            f"{function} combines several input rows into a summary metric", ("🧮", function, "Calculate across the qualifying rows"),
            [scene_item("🧾", "Order row", "quantity 2"), scene_item("🧾", "Order row", "quantity 1"), scene_item("🧾", "Order row", "quantity 3")],
            [scene_item("Σ", f"{function} result", "one calculated metric", "kept")],
            "The aggregate reads many row values and returns a summarized answer."
        )
    if normalized.lstrip().startswith("SELECT"):
        selected = re.search(r"SELECT\s+(.+?)\s+FROM", normalized, re.S)
        columns = " ".join(selected.group(1).split())[:54] if selected else "requested expression"
        return transformation_scene(
            "SELECT controls which information appears in the result", ("🔦", "SELECT", columns),
            [scene_item("🪪", "Product row", "id 1 · Iced Latte · Coffee · 2.750"), scene_item("🪪", "Product row", "id 2 · Cold Brew · Coffee · 3.000")],
            [scene_item("📋", "Result row", "only selected fields"), scene_item("📋", "Result row", "only selected fields")],
            "The source table is unchanged; SELECT creates a temporary result containing the requested fields."
        )
    return ""

def query_visual(sql):
    """Create an accurate high-level execution picture from a lesson's first SQL example."""
    scene = statement_scene(sql)
    if scene:
        return scene
    normalized = html.unescape(sql).upper()
    statement = re.search(r"\b(WITH|EXPLAIN|SHOW\s+INDEX|SELECT|INSERT\s+INTO|UPDATE|ALTER\s+TABLE|CREATE\s+(?:TABLE|DATABASE|VIEW|INDEX)|DROP|START\s+TRANSACTION|VALUES\s*\()", normalized)
    if statement:
        normalized = normalized[statement.start():]
    if " EXISTS " in f" {normalized} ":
        return visual_flow([
            ("Take an outer row", "Start with one row from the outer table."),
            ("Search the inner table", "Look for a correlated matching row."),
            ("Return yes or no", "EXISTS only tests whether a match was found."),
            ("Keep matching rows", "True survives the outer WHERE filter."),
        ], "How EXISTS filters the outer rows")
    if normalized.lstrip().startswith("WITH"):
        return visual_flow([
            ("Build named result", "Run each CTE inside the WITH clause."),
            ("Use the CTE", "Treat its rows like a temporary named table."),
            ("Combine or filter", "Apply joins, comparisons, or calculations."),
            ("Return final rows", "The CTE disappears after this statement."),
        ], "How the CTE query moves through intermediate results")
    if " OVER " in f" {normalized} " or "OVER(" in normalized:
        return visual_flow([
            ("Keep the rows", "Window functions do not collapse row detail."),
            ("Define the window", "PARTITION BY and ORDER BY choose related rows."),
            ("Calculate across rows", "Compute rank, running total, lag, or another metric."),
            ("Display each row", "Attach the window value to the existing result."),
        ], "How a window function calculates without hiding rows")
    if normalized.lstrip().startswith("INSERT"):
        return visual_flow([
            ("Choose the table", "INSERT INTO identifies the destination."),
            ("Map the columns", "The column list defines value positions."),
            ("Validate values", "Types and constraints are checked."),
            ("Store new rows", "Valid value groups become table rows."),
        ], "How INSERT turns values into stored rows")
    if normalized.lstrip().startswith("VALUES"):
        return visual_flow([
            ("Follow column order", "Each value maps to the column in the same position."),
            ("Quote text and dates", "String values need quotation marks."),
            ("Leave numbers numeric", "Numeric values do not need text quotes."),
            ("Create the row", "A valid value group becomes one stored record."),
        ], "How a VALUES list maps into a table row")
    if "CREATE TABLE" in normalized:
        return visual_flow([
            ("Name the table", "CREATE TABLE defines the new object."),
            ("Define columns", "Each column receives a name and data type."),
            ("Apply constraints", "Keys and required-value rules protect data."),
            ("Create structure", "MySQL builds an empty table ready for rows."),
        ], "How a table definition becomes database structure")
    if "CREATE DATABASE" in normalized:
        return visual_flow([
            ("Send CREATE", "Ask MySQL for a new database container."),
            ("Check existence", "IF NOT EXISTS prevents a duplicate error."),
            ("Create container", "The database becomes available on the server."),
        ], "How CREATE DATABASE builds the course workspace")
    if normalized.lstrip().startswith("DROP"):
        return visual_flow([
            ("Find the object", "Locate the named table or database."),
            ("Check existence", "IF EXISTS avoids an error when it is absent."),
            ("Remove it", "The object and its stored data are deleted."),
        ], "How DROP removes a database object")
    if " JOIN " in f" {normalized} ":
        return visual_flow([
            ("Read the left table", "FROM supplies the starting rows."),
            ("Read the joined table", "JOIN supplies related candidate rows."),
            ("Test the ON rule", "Matching key values connect the rows."),
            ("Build result rows", "SELECT returns fields from the matched data."),
        ], "How JOIN connects related table rows")
    if "GROUP BY" in normalized:
        stages = [("Read source rows", "FROM chooses the input table.")]
        if "WHERE" in normalized: stages.append(("Filter rows", "WHERE removes detail rows before grouping."))
        stages.extend([("Create groups", "GROUP BY makes one bucket per distinct value."), ("Calculate summaries", "Aggregate functions calculate inside each bucket.")])
        if "HAVING" in normalized: stages.append(("Filter groups", "HAVING removes summary groups that fail the condition."))
        if "ORDER BY" in normalized: stages.append(("Sort results", "ORDER BY arranges the summary rows."))
        return visual_flow(stages, "How grouped SQL turns detail rows into summaries")
    if any(function in normalized for function in ("SUM(", "AVG(", "COUNT(", "MIN(", "MAX(")):
        return visual_flow([
            ("Read rows", "FROM chooses the rows to analyze."),
            ("Filter if needed", "WHERE controls which rows participate."),
            ("Calculate aggregate", "The function combines many values."),
            ("Return the metric", "The result is a summary value."),
        ], "How an aggregate query produces a metric")
    if normalized.lstrip().startswith("SELECT"):
        stages = [("Read the table", "FROM identifies the source rows.")] if "FROM" in normalized else [("Evaluate expression", "SELECT calculates or returns the requested value.")]
        if "WHERE" in normalized: stages.append(("Filter rows", "WHERE keeps rows whose condition is true."))
        stages.append(("Choose output", "SELECT returns the requested columns or calculations."))
        if "ORDER BY" in normalized: stages.append(("Sort output", "ORDER BY arranges the surviving rows."))
        if "LIMIT" in normalized: stages.append(("Keep a subset", "LIMIT returns only the requested number of rows."))
        return visual_flow(stages, "How this SELECT query produces its result")
    return ""

CONCEPT_VISUALS = {
    "Why Are We Repeating Product Name and Price?": ([('Beginner order rows', 'Product name, category, and sale price are repeated so early aggregate lessons use one table.'), ('Learn summary queries', 'Practice COUNT, SUM, AVG, GROUP BY, and ORDER BY before adding relationships.'), ('Normalize in Segment 7', 'Replace repeated product attributes with product_id and reconnect tables using JOIN.')], "Why the early teaching schema is intentionally denormalized"),
    "Common mistakes": ([('State the grain', 'Write what one result row should represent.'), ('Test one layer', 'Run the inner query or CTE independently.'), ('Validate the output', 'Check row count, keys, NULLs, and totals before continuing.')], "A reliable way to debug analytical SQL"),
    "What Is a KPI?": ([('Business activity', 'Orders and sales create measurable facts.'), ('Calculate a metric', 'SQL summarizes the relevant facts.'), ('Track performance', 'The KPI supports a business decision.')], "How raw activity becomes a KPI"),
    "The main idea": ([('Start with two tables', 'Each table contains a different part of the story.'), ('Choose a matching rule', 'Related values identify which rows belong together.'), ('Combine matched facts', 'The result can use columns from both tables.')], "The central idea behind a JOIN"),
    "What is COALESCE()?": ([('Read a value', 'A missing aggregate may produce NULL.'), ('Test alternatives', 'COALESCE checks arguments from left to right.'), ('Return the first value', 'Use 0 when the earlier value is NULL.')], "How COALESCE replaces a missing value"),
    "Important real-world note: joining by name is not ideal": ([('Names can change', 'Spelling and formatting create fragile matches.'), ('IDs stay stable', 'A key identifies the same entity reliably.'), ('Join on the key', 'Stable relationships produce trustworthy results.')], "Why database joins should use IDs"),
    "Important Database Design Rule": ([('Store one fact once', 'Keep product details in the products table.'), ('Reference its ID', 'Orders store product_id instead of repeated text.'), ('Join when needed', 'Queries reconnect the facts safely.')], "How normalized design reduces duplicated data"),
    "Segment 7 Final Mental Model": ([('Product table', 'Stores what each product is.'), ('Order table', 'Stores what happened in each sale line.'), ('product_id link', 'The key connects the event to its product.')], "The final key-based database model"),
    "Why intermediate results matter": ([('Calculate product totals', 'Complete the first analytical step.'), ('Calculate the benchmark', 'Use those totals to find the average.'), ('Compare results', 'Return only products above the benchmark.')], "Why complex analysis needs intermediate results"),
    "Why CROSS JOIN works here": ([('One benchmark row', 'The average CTE must return exactly one row.'), ('Attach it to each product', 'CROSS JOIN repeats that benchmark for comparison.'), ('Filter comparisons', 'Each product can now be tested against the average.')], "How a one-row CROSS JOIN supplies a benchmark"),
    "Subquery or CTE?": ([('Short single value', 'Use a scalar subquery for a compact benchmark.'), ('Existence check', 'Use EXISTS when only matching presence matters.'), ('Named multi-step logic', 'Use a CTE for readable intermediate results.')], "Choosing between a subquery, EXISTS, and a CTE"),
    "Why window functions matter": ([('Start with detail rows', 'Keep the original result grain.'), ('Look across related rows', 'Define a partition, order, or frame.'), ('Attach analytical values', 'Add rankings or comparisons without collapsing rows.')], "Why window functions preserve useful detail"),
    "Why Data Analysts Love Tables": ([('Organized rows', 'Each row represents one consistent type of observation.'), ('Ask a question', 'SQL filters, groups, or calculates from those rows.'), ('Produce evidence', 'The result supports a business decision.')], "How structured tables become analytical answers"),
    "Mini Practice Dataset": ([('Inspect the columns', 'Identify IDs, categories, and measurable values.'), ('Choose the needed rows', 'Filter the dataset for the business question.'), ('Calculate the answer', 'Select, sort, or aggregate the surviving data.')], "How to approach a new practice dataset"),
    "Creating Your First Table": ([('Decide the grain', 'State what one table row represents.'), ('Choose columns', 'List the facts each row must store.'), ('Assign data types', 'Protect numbers, text, and dates appropriately.')], "How analysts design a table before creating it"),
    "Data Types": ([('Understand the value', 'Decide whether the fact is text, whole-number, decimal, or date.'), ('Choose the type', 'Select VARCHAR, INT, DECIMAL, or DATE.'), ('Protect data quality', 'MySQL validates values against that type.')], "How a value becomes a database data type"),
    "Seeing Your Table": ([('Run DESCRIBE', 'Ask MySQL for the table definition.'), ('Inspect fields and types', 'Confirm each column matches the design.'), ('Correct problems early', 'Fix structure before loading analytical data.')], "How to verify a table structure"),
    "Data Analyst Thinking: Why This Matters": ([('Reliable structure', 'Consistent columns and types reduce ambiguity.'), ('Reliable queries', 'Clean structure makes calculations predictable.'), ('Reliable decisions', 'Trustworthy results support better business choices.')], "Why database structure affects analytical trust"),
    "Why We Need an orders Table": ([('Products describe the menu', 'They show what could be sold.'), ('Orders record events', 'They show what customers actually bought.'), ('Analyze behavior', 'Order rows support revenue, volume, and time metrics.')], "Why transaction data unlocks business analysis"),
    "COUNT(*) vs SUM(quantity)": ([('Count rows', 'COUNT(*) measures how many order lines exist.'), ('Add quantities', 'SUM(quantity) measures how many units were sold.'), ('Name the metric clearly', 'Rows and units answer different questions.')], "Why order rows and items sold are different metrics"),
    "Visual: what the join is doing": ([('Take one order row', 'Read its product matching value.'), ('Find the product row', 'Apply the ON equality condition.'), ('Combine the fields', 'Build one matched result row.')], "What happens to a row during an INNER JOIN"),
    "The Problem With Our Current Design": ([('Repeat product text', 'Names, categories, and prices appear in many order rows.'), ('Create inconsistency risk', 'Typos and updates can make copies disagree.'), ('Replace copies with a key', 'Store product_id as the stable relationship.')], "How repeated data creates database risk"),
    "Important Question: Why Keep unit_price in Orders?": ([('Menu price can change', 'The current product price describes today.'), ('Sale price is historical', 'unit_price records what was charged then.'), ('Preserve accurate revenue', 'Historical calculations use the sold price.')], "Why an order keeps its historical unit price"),
    "What Happens If We Delete a Product?": ([('Product is referenced', 'Order rows still point to its product_id.'), ('Foreign key checks safety', 'Deleting it would create broken references.'), ('MySQL blocks the delete', 'The parent remains unless a deliberate rule says otherwise.')], "How referential integrity protects historical orders"),
    "Professional Analytics Mindset": ([('Define the business entity', 'Know what each table and row represents.'), ('Protect relationships', 'Use stable keys and constraints.'), ('Validate every result', 'Check grain, row counts, NULLs, and totals.')], "A professional workflow for trustworthy analytics"),
    "View limitations": ([('Expand the saved definition', 'A view can hide joins and calculations behind its name.'), ('Inspect the real plan', 'Use EXPLAIN on the query that reads the view.'), ('Protect the interface', 'Changing view columns can break dependent reports.')], "Why a convenient view still requires performance and dependency checks"),
}

def add_lesson_visual_aids(segments):
    """Audit every lesson and add a visual model when it clarifies the material."""
    for segment in segments:
        for lesson_index, lesson in enumerate(segment["lessons"]):
            if lesson_index == 0:
                continue
            visual = ""
            for code in re.findall(r'<pre><code>(.*?)</code></pre>', lesson["body"], re.S):
                visual = query_visual(code)
                if visual:
                    break
            if not visual and lesson["title"] in CONCEPT_VISUALS:
                stages, caption = CONCEPT_VISUALS[lesson["title"]]
                visual = visual_flow(stages, caption)
            if visual:
                lesson["body"] += visual

def add_assessments_and_projects(segments):
    """Append assessed knowledge checks and a project to every segment."""
    if len(segments) != len(ENRICHMENTS):
        raise ValueError("Every segment must have one enrichment definition")
    for segment_number, (segment, enrichment) in enumerate(zip(segments, ENRICHMENTS), 1):
        if segment["title"] == "JOINS":
            segment["lessons"].extend([
                {
                    "title": "RIGHT JOIN and readable join direction",
                    "time": 7,
                    "body": (
                        '<p class="eyebrow">JOIN PATTERNS</p><h2>RIGHT JOIN preserves the table written on the right.</h2>'
                        '<p>A RIGHT JOIN returns every row from its right table and matching rows from its left table. Unmatched left-side columns become NULL. It is valid MySQL, but teams often rewrite it as a LEFT JOIN so the preserved table appears first.</p>'
                        '<div class="code-block"><div class="code-label"><span>MYSQL</span><button data-copy>Copy query</button></div><pre><code>'
                        'SELECT p.product_name, o.order_id\nFROM orders o\nRIGHT JOIN products p\n  ON p.product_name = o.product_name\nORDER BY p.product_id, o.order_id;'
                        '</code></pre></div>'
                        '<div class="diagram">orders (left)  → matching names ←  products (right, all preserved)\nNo matching order means order_id is NULL.</div>'
                        '<p>The equivalent, usually clearer form is <code>FROM products p LEFT JOIN orders o</code> with the same ON condition. Choose direction for readability, not because one keyword is more advanced.</p>'
                        '<section class="quiz" data-correct="1" data-why="RIGHT JOIN preserves every row from the table written to its right."><span class="quiz-tag">KNOWLEDGE CHECK</span><h3>Which table is preserved in this query?</h3><div class="answers"><button class="answer" data-answer="0">orders</button><button class="answer" data-answer="1">products</button><button class="answer" data-answer="2">Neither table</button></div><div class="feedback" role="status" aria-live="polite"></div></section>'
                    ),
                },
                {
                    "title": "Self joins for relationships inside one table",
                    "time": 9,
                    "body": (
                        '<p class="eyebrow">JOIN PATTERNS</p><h2>A self join gives one table two roles.</h2>'
                        '<p>A self join is not a separate JOIN keyword. Reference the same table twice with different aliases. A common use is an employee hierarchy where each employee row may point to another employee row as manager.</p>'
                        '<div class="code-block"><div class="code-label"><span>MYSQL</span><button data-copy>Copy query</button></div><pre><code>'
                        'WITH employees AS (\n  SELECT 1 AS employee_id, \'Maya\' AS employee_name, NULL AS manager_id\n  UNION ALL SELECT 2, \'Omar\', 1\n  UNION ALL SELECT 3, \'Layla\', 1\n)\nSELECT e.employee_name AS employee,\n       m.employee_name AS manager\nFROM employees e\nLEFT JOIN employees m\n  ON m.employee_id = e.manager_id\nORDER BY e.employee_id;'
                        '</code></pre></div>'
                        '<div class="query-visual" role="img" aria-label="One employee table used in employee and manager roles"><div class="query-visual-title"><span>VISUAL WALKTHROUGH</span><strong>One table, two aliases</strong></div><div class="query-flow"><div class="flow-step"><span>1</span><strong>employees e</strong><small>The row being reported</small></div><div class="flow-step"><span>2</span><strong>Match manager_id</strong><small>Connect it to an employee_id</small></div><div class="flow-step"><span>3</span><strong>employees m</strong><small>The matching row in manager role</small></div></div></div>'
                        '<p>Use LEFT JOIN when top-level employees with no manager must remain. Always qualify shared column names with aliases.</p>'
                        '<section class="quiz" data-correct="0" data-why="LEFT JOIN preserves Maya even though her manager_id is NULL."><span class="quiz-tag">KNOWLEDGE CHECK</span><h3>Why use LEFT JOIN in this hierarchy?</h3><div class="answers"><button class="answer" data-answer="0">Keep employees without managers</button><button class="answer" data-answer="1">Remove every NULL</button><button class="answer" data-answer="2">Create duplicate employees</button></div><div class="feedback" role="status" aria-live="polite"></div></section>'
                    ),
                },
            ])
            for section_number, lesson in enumerate(segment["lessons"][-2:], len(segment["lessons"])-1):
                original_body = strip_micro_heading(lesson["body"])
                lesson["body"] = (
                    f'<p class="chapter-label">CHAPTER {segment_number} · SECTION {section_number}</p>'
                    f'<h2>{html.escape(lesson["title"])}</h2>'
                    '<p class="chapter-lead">This join pattern extends the chapter model. Read the relationship in words, identify which rows must survive, and then verify the output grain.</p>'
                    f'<div class="chapter-reading"><section class="textbook-subsection" data-source-title="{html.escape(lesson["title"], quote=True)}">'
                    f'<h3>Pattern, example, and interpretation</h3>{original_body}</section></div>'
                )
                lesson["source_titles"] = [lesson["title"]]
        checks = []
        for question_number, (question, options, correct, explanation) in enumerate(enrichment["checks"], 1):
            answers = "".join(
                f'<button class="answer" data-answer="{index}">{html.escape(option)}</button>'
                for index, option in enumerate(options)
            )
            checks.append(
                f'<section class="quiz" data-correct="{correct}" data-why="{html.escape(explanation, quote=True)}">'
                f'<span class="quiz-tag">KNOWLEDGE CHECK {question_number} OF {len(enrichment["checks"])}</span>'
                f'<h3>{html.escape(question)}</h3><div class="answers">{answers}</div>'
                f'<div class="feedback" role="status" aria-live="polite"></div></section>'
            )
        segment["lessons"].append({
            "title": "Section knowledge check",
            "time": 8,
            "body": (
                f'<p class="eyebrow">ASSESS · SECTION {segment_number}</p>'
                f'<h2>Check your understanding</h2>'
                f'<p>Answer each question before moving to the project. Feedback explains the rule, not just the letter.</p>'
                + "".join(checks)
            ),
        })
        title, brief, deliverables, criteria, solution = enrichment["project"]
        deliverable_html = "".join(f"<li>{html.escape(item)}</li>" for item in deliverables)
        criteria_html = "".join(f"<li>{html.escape(item)}</li>" for item in criteria)
        segment["lessons"].append({
            "title": f"Mini-project: {title}",
            "time": 35,
            "body": (
                f'<p class="eyebrow">APPLY · SECTION {segment_number}</p><h2>{html.escape(title)}</h2>'
                f'<div class="project-brief"><strong>Business brief</strong><p>{html.escape(brief)}</p></div>'
                f'<h3>Deliverables</h3><ol>{deliverable_html}</ol>'
                f'<h3>Acceptance criteria</h3><ul class="project-checklist">{criteria_html}</ul>'
                f'<details class="project-hint"><summary>Need a starting hint?</summary><p>Write the required result grain in one sentence, identify the source rows, then build and test one clause at a time.</p></details>'
                f'<details class="project-solution"><summary>Reveal reference solution after attempting</summary>'
                f'<p>This is one valid solution. Compare the result grain, logic, and output—not only formatting.</p>'
                f'<div class="code-block"><div class="code-label"><span>REFERENCE SQL</span><button data-copy>Copy query</button></div>'
                f'<pre><code>{html.escape(solution)}</code></pre></div></details>'
                f'<h3>Self-assessment rubric</h3>'
                f'<table class="data-table"><thead><tr><th>Level</th><th>Evidence</th></tr></thead><tbody>'
                f'<tr><td>Ready</td><td>All criteria pass; result is verified and explained in business language.</td></tr>'
                f'<tr><td>Revise</td><td>Query partly works, but one criterion, validation step, or explanation is missing.</td></tr>'
                f'<tr><td>Relearn</td><td>Result grain or core section concept is incorrect; revisit the linked lessons before retrying.</td></tr>'
                f'</tbody></table>'
            ),
        })

def expected_result_key(segment_number, sql):
    normalized = "\n".join(line.rstrip() for line in html.unescape(sql).strip().splitlines())
    return f"{segment_number}:{sha256(normalized.encode()).hexdigest()}"

def expected_card(title, body, tone="result"):
    return (
        f'<aside class="expected-result {tone}">'
        f'<div class="expected-result-title"><span>EXPECTED {"ERROR" if tone == "error" else "RESULT"}</span><strong>{html.escape(title)}</strong></div>'
        f'{body}</aside>'
    )

def render_captured_result(result):
    if result["kind"] == "error":
        return expected_card("MySQL rejects this example", f'<p><code>{html.escape(result["message"])}</code></p>', "error")
    columns, rows, count = result["columns"], result["rows"], result["row_count"]
    if not columns:
        return expected_card("Statement completes without a result grid", "<p>MySQL returns no columns or data rows.</p>")
    head = "".join(f"<th>{html.escape(str(column))}</th>" for column in columns)
    if rows:
        body = "".join(
            "<tr>" + "".join(f'<td class="{("null-value" if str(value) == "NULL" else "")}">{html.escape(str(value))}</td>' for value in row) + "</tr>"
            for row in rows
        )
    else:
        body = f'<tr class="empty-result"><td colspan="{len(columns)}">No data rows</td></tr>'
    note = f"{count} row{'s' if count != 1 else ''} returned."
    if result.get("truncated"): note += f" The first {len(rows)} rows are shown."
    table = f'<div class="table-scroll"><table class="data-table expected-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    return expected_card("Output from the course dataset", table + f"<p>{note}</p>")

def statement_outcome(sql, segment_number):
    """Return an explicit outcome for every displayed SQL block."""
    raw = html.unescape(sql).strip()
    upper = raw.upper()
    placeholders = ("FROM TABLE;", "LEFT_TABLE", "RIGHT_TABLE", "TABLE_NAME", "COLUMN_1", "COLUMN_2", "GROUP_COLUMN", "AGGREGATE_FUNCTION", "RESULT_NAME", "CONDITION_ON_")
    if any(token in upper for token in placeholders):
        return expected_card("Syntax template—not runnable yet", "<p>Replace the placeholder table, column, expression, and condition names. The completed query then returns the columns and rows requested by those replacements.</p>")
    statements = [part.strip() for part in raw.split(";") if part.strip()]
    if len(statements) > 1:
        insert_rows = 0
        if "VALUES" in upper:
            values_part = raw[upper.find("VALUES") + 6:]
            insert_rows = len(re.findall(r"(?m)^\s*\(", values_part)) or 1
        outcomes = []
        for index, statement in enumerate(statements, 1):
            statement_upper = statement.upper()
            label = compact_sql(statement, 70)
            if statement_upper.startswith("CREATE DATABASE"):
                result = "Creates the database; no result grid."
            elif statement_upper.startswith("USE "):
                result = "Selects the active database; no result grid."
            elif statement_upper.startswith("DROP "):
                result = "Removes the named object if present; no result grid."
            elif statement_upper.startswith("CREATE TABLE"):
                result = "Creates the table definition; the new table initially has zero rows."
            elif statement_upper.startswith("CREATE INDEX"):
                result = "Creates the index; verify its columns with SHOW INDEX."
            elif statement_upper.startswith("SOURCE "):
                result = "Runs the setup file from top to bottom. If your editor does not support SOURCE, open the SQL file and execute the full script manually."
            elif statement_upper.startswith("INSERT INTO"):
                result = f"Inserts the VALUES rows; this script contains {insert_rows} row group{'s' if insert_rows != 1 else ''}."
            elif statement_upper.startswith("DESCRIBE"):
                result = "Returns one definition row per table column (Field, Type, Null, Key, Default, Extra)."
            elif statement_upper.startswith("EXPLAIN"):
                result = "Returns the execution-plan columns for the following query; it does not return normal query rows."
            elif statement_upper.startswith("SELECT") or statement_upper.startswith("WITH"):
                result = "Returns the verification or analysis rows requested by this SELECT. Compare its row count and values with the stated project criteria."
            elif statement_upper.startswith("START TRANSACTION"):
                result = "Starts a transaction; no result grid."
            elif statement_upper.startswith("ROLLBACK"):
                result = "Undoes the uncommitted changes; no result grid."
            elif statement_upper.startswith("COMMIT"):
                result = "Makes the pending changes permanent; no result grid."
            else:
                result = "MySQL reports success or an affected-row count; the statement itself returns no analysis grid."
            outcomes.append(f'<li><strong>{index}. <code>{html.escape(label)}</code></strong><span>{html.escape(result)}</span></li>')
        return expected_card("Ordered outcomes for this script", f'<ol class="script-outcomes">{"".join(outcomes)}</ol>')
    captured = EXPECTED_RESULTS.get(expected_result_key(segment_number, raw))
    if captured:
        return render_captured_result(captured)
    if re.match(r"(?is)^DELETE\s+FROM\s+products\b", raw) and "PRODUCT_ID = 1" in upper:
        return expected_card("Foreign-key protection blocks the deletion", "<p>MySQL returns a foreign-key constraint error because order rows still reference <code>product_id = 1</code>. The product and its orders remain unchanged.</p>", "error")
    if re.match(r"(?is)^CREATE\s+DATABASE\b", raw):
        return expected_card("Database container created", "<p>No data rows are returned. MySQL reports success; <code>SHOW DATABASES LIKE 'coffee_shop';</code> returns one row afterward.</p>")
    if re.match(r"(?is)^USE\s+", raw):
        database = re.search(r"(?i)^USE\s+([a-z_]\w*)", raw)
        return expected_card("Active database selected", f'<p>No result grid is returned. Later unqualified table names resolve inside <code>{html.escape(database.group(1) if database else "the named database")}</code>.</p>')
    if re.match(r"(?is)^CREATE\s+TABLE\b", raw):
        table = re.search(r"(?i)CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+([a-z_]\w*)", raw)
        return expected_card("Table structure created", f'<p>No data rows are returned. MySQL creates <code>{html.escape(table.group(1) if table else "the named table")}</code>; run <code>DESCRIBE {html.escape(table.group(1) if table else "table_name")};</code> to verify its columns and constraints.</p>')
    if re.match(r"(?is)^CREATE(?:\s+OR\s+REPLACE)?\s+VIEW\b", raw):
        view = re.search(r"(?i)CREATE(?:\s+OR\s+REPLACE)?\s+VIEW\s+([a-z_]\w*)", raw)
        name = view.group(1) if view else "the named view"
        return expected_card("View definition saved", f'<p>No rows are displayed by CREATE VIEW. MySQL saves <code>{html.escape(name)}</code>; querying that view returns the rows produced by its SELECT definition.</p>')
    if re.match(r"(?is)^CREATE\s+INDEX\b", raw):
        index = re.search(r"(?i)CREATE\s+INDEX\s+([a-z_]\w*)", raw)
        return expected_card("Index created", f'<p>No data rows are returned. MySQL creates <code>{html.escape(index.group(1) if index else "the named index")}</code>; confirm its column order with <code>SHOW INDEX</code>.</p>')
    if re.match(r"(?is)^INSERT\s+INTO\b", raw):
        table = re.search(r"(?i)INSERT\s+INTO\s+([a-z_]\w*)", raw)
        values_part = raw[upper.find("VALUES") + 6:] if "VALUES" in upper else ""
        rows = len(re.findall(r"(?m)^\s*\(", values_part)) or (1 if values_part.strip() else 0)
        return expected_card("Rows inserted", f'<p>No result grid is returned. MySQL reports {rows or "the"} affected row{"s" if rows != 1 else ""} in <code>{html.escape(table.group(1) if table else "the target table")}</code>. Run the following lesson SELECT to verify stored values.</p>')
    if re.match(r"(?is)^UPDATE\s+", raw):
        return expected_card("Matching rows evaluated and updated", "<p>UPDATE returns an affected-row message, not a result grid. Preview the same WHERE condition, then use the following SELECT to verify exact values before COMMIT.</p>")
    if re.match(r"(?is)^ALTER\s+TABLE\b", raw):
        return expected_card("Constraint or structure change applied", "<p>No result grid is returned. MySQL reports success only if existing rows satisfy the new rule; <code>SHOW CREATE TABLE</code> verifies the resulting definition.</p>")
    if re.match(r"(?is)^DROP\s+", raw):
        return expected_card("Named object removed if present", "<p>No data rows are returned. With <code>IF EXISTS</code>, an absent object produces a note instead of stopping the reset script.</p>")
    if re.match(r"(?is)^START\s+TRANSACTION", raw):
        return expected_card("Transaction started", "<p>No result grid is returned. Later supported data changes remain pending until COMMIT and can be undone with ROLLBACK.</p>")
    if re.match(r"(?is)^ROLLBACK", raw):
        return expected_card("Uncommitted changes undone", "<p>No result grid is returned. The product rows return to their values from before START TRANSACTION.</p>")
    if re.match(r"(?is)^COMMIT", raw):
        return expected_card("Transaction changes made permanent", "<p>No result grid is returned. A later ROLLBACK cannot undo the committed changes.</p>")
    if re.match(r"(?is)^SOURCE\s+", raw):
        return expected_card("Project setup script executed", "<p>MySQL runs the statements inside <code>project_data/retail_project_setup.sql</code>. The script creates and loads <code>metromart_project</code>; run row-count checks afterward to confirm the load.</p>")
    if re.match(r"(?is)^EXPLAIN\b", raw):
        return expected_card("Execution plan to inspect", "<p>MySQL returns plan columns such as table, access type, possible keys, chosen key, estimated rows, and Extra. Use this plan as performance evidence, then run the SELECT itself to verify the business result.</p>")
    if re.match(r"(?is)^SHOW\s+INDEX\b", raw):
        return expected_card("Index metadata to inspect", "<p>MySQL returns one metadata row per indexed column. Use Key_name and Seq_in_index to verify index names and column order.</p>")
    if re.match(r"(?is)^DESCRIBE\b", raw):
        return expected_card("Table definition to inspect", "<p>MySQL returns one metadata row per column. Use Field, Type, Null, Key, Default, and Extra to verify the table structure.</p>")
    if re.match(r"(?is)^(SELECT|WITH)\b", raw):
        return expected_card("Analysis result to verify", "<p>Run the query against the MetroMart project database. Verify the result grain, row count, key columns, NULL behavior, and at least one hand-checked metric before using the answer in the final walkthrough.</p>")
    if re.match(r"(?is)^(WHERE|GROUP\s+BY|ORDER\s+BY|LIMIT|VALUES|SELECT\s*$)", raw):
        return expected_card("Clause fragment", "<p>This is not a complete standalone statement. Its expected effect is demonstrated in the nearest complete query in this lesson.</p>")
    if ";" in raw:
        return expected_card("Script outcome", "<p>Run the statements in order. Structure-changing statements report success without rows; the final verification SELECT displays the resulting records.</p>")
    return expected_card("Teaching fragment", "<p>This block illustrates SQL syntax but is not complete enough to execute by itself.</p>")

def add_expected_results(segments):
    """Place an expected result or explicit outcome after every SQL block."""
    pattern = re.compile(r"(<div class=\"code-block\">.*?<pre><code>(.*?)</code></pre></div>)", re.S)
    for segment_number, segment in enumerate(segments, 1):
        result_segment_number = segment.get("source_number", segment_number)
        for lesson in segment["lessons"]:
            lesson["body"] = pattern.sub(lambda match: match.group(1) + statement_outcome(match.group(2), result_segment_number), lesson["body"])

SEGMENT_RELEVANCE = [
    "Analysts turn business questions into columns, rows, filters, and sorted results every day.",
    "Reliable analysis starts with tables whose names, types, and stored values match the intended design.",
    "Employers expect analysts to distinguish transaction rows, units, revenue, and averages before reporting KPIs.",
    "GROUP BY controls report grain: it decides what one summary row represents.",
    "HAVING lets analysts keep only meaningful summary groups without filtering away source rows too early.",
    "Business facts usually live in multiple tables, so accurate joins and cardinality checks are essential.",
    "Stable keys and constraints keep relationships trustworthy as datasets grow and change.",
    "Subqueries and CTEs make multi-step business logic testable, readable, and easier for teammates to review.",
    "Window functions power rankings, running totals, and comparisons without discarding useful row detail.",
    "CASE, date, and text expressions convert stored values into dimensions people can use in reports.",
    "A correct query on unreliable data still produces an unreliable answer; profiling and safe cleaning protect decisions.",
    "Views package reviewed definitions into stable reporting interfaces that other analysts and dashboards can reuse.",
    "Production SQL must return the right result with evidence about how much work the database performs.",
]

def lesson_goal(title):
    cleaned = re.sub(r"^[^:]+:\s*", "", title).rstrip(" ✅")
    if title.startswith("Practice "):
        return f"Solve the {cleaned.lower()} task independently, then explain why the result is correct."
    if title.startswith("Mini-project:"):
        return "Combine this section's skills into a reproducible business deliverable."
    if title == "Section knowledge check":
        return "Retrieve the section's key ideas from memory before beginning the project."
    if title == "Segment overview":
        return "Understand the section's destination, vocabulary, and connection to the complete analyst workflow."
    if "mistake" in title.lower() or "debug" in title.lower():
        return f"Recognize, explain, and correct {cleaned.lower()} instead of guessing at a fix."
    if re.match(r"^(What|Why|How|When|Can|Which)\b", cleaned, re.I):
        return f"Answer “{cleaned.rstrip('?')}” in your own words and demonstrate the idea with SQL."
    return f"Explain {cleaned.lower()}, identify when it is useful, and apply it to the course database."

def learning_brief(segment_number, lesson_index, lesson, previous_title):
    builds_on = "No prior SQL knowledge required." if segment_number == 1 and lesson_index == 0 else f"Builds on: {previous_title or 'the section overview'}."
    return (
        '<section class="learning-brief" aria-label="Lesson purpose">'
        f'<div><span>LEARNING GOAL</span><p>{html.escape(lesson_goal(lesson["title"]))}</p></div>'
        f'<div><span>WHY IT MATTERS</span><p>{html.escape(SEGMENT_RELEVANCE[segment_number - 1])}</p></div>'
        f'<div><span>CONNECTION</span><p>{html.escape(builds_on)}</p></div>'
        '</section>'
    )

def query_parts(raw):
    """Extract the outer query clauses used for a learner-facing walkthrough."""
    upper = raw.upper()
    ctes = re.findall(r"(?i)(?:\bWITH|,)\s*([a-z_]\w*)\s+AS\s*\(", raw)
    if ctes:
        starts = list(re.finditer(r"(?i)\bSELECT\b", raw))
        final_sql = raw[starts[-1].start():] if starts else raw
    else:
        final_sql = raw
    selected = re.search(r"(?is)\bSELECT\s+(.+?)(?=\bFROM\b|$)", final_sql)
    source = re.search(r"(?i)\bFROM\s+([a-z_]\w*)(?:\s+(?:AS\s+)?([a-z_]\w*))?", final_sql)
    joins = re.findall(r"(?i)\b(?:(LEFT|RIGHT|INNER|CROSS)\s+)?JOIN\s+([a-z_]\w*)", final_sql)
    on_rules = re.findall(r"(?is)\bON\s+(.+?)(?=\b(?:LEFT|RIGHT|INNER|CROSS)?\s*JOIN\b|\bWHERE\b|\bGROUP\s+BY\b|\bHAVING\b|\bORDER\s+BY\b|\bLIMIT\b|;|$)", final_sql)
    where = re.search(r"(?is)\bWHERE\s+(.+?)(?=\bGROUP\s+BY\b|\bHAVING\b|\bORDER\s+BY\b|\bLIMIT\b|;|$)", final_sql)
    group = re.search(r"(?is)\bGROUP\s+BY\s+(.+?)(?=\bHAVING\b|\bORDER\s+BY\b|\bLIMIT\b|;|$)", final_sql)
    having = re.search(r"(?is)\bHAVING\s+(.+?)(?=\bORDER\s+BY\b|\bLIMIT\b|;|$)", final_sql)
    order_starts = list(re.finditer(r"(?i)\bORDER\s+BY\b", final_sql))
    order = re.split(r"(?is)\bLIMIT\b|;", final_sql[order_starts[-1].end():], maxsplit=1)[0].strip() if order_starts else ""
    limit = re.search(r"(?i)\bLIMIT\s+(\d+)", final_sql)
    windows = list(dict.fromkeys(compact_sql(spec) for spec in re.findall(r"(?is)\bOVER\s*\(([^)]*)\)", final_sql)))
    cte_details=[]
    if ctes:
        for cte_name in ctes:
            start_match=re.search(rf"(?i)\b{re.escape(cte_name)}\s+AS\s*\(",raw)
            if not start_match: continue
            depth=1; position=start_match.end()
            while position<len(raw) and depth:
                if raw[position]=='(': depth+=1
                elif raw[position]==')': depth-=1
                position+=1
            body=raw[start_match.end():position-1]
            cte_source=re.search(r"(?i)\bFROM\s+([a-z_]\w*)",body)
            cte_group=re.search(r"(?is)\bGROUP\s+BY\s+(.+?)(?=\bHAVING\b|\bORDER\s+BY\b|;|$)",body)
            aggregates=list(dict.fromkeys(re.findall(r"(?i)\b(COUNT|SUM|AVG|MIN|MAX)\s*\(",body)))
            cte_details.append({"name":cte_name,"source":cte_source.group(1) if cte_source else "an earlier result","group":compact_sql(cte_group.group(1)) if cte_group else "","aggregates":aggregates})
    return {"ctes":ctes,"cte_details":cte_details,"final":final_sql,"selected":compact_sql(selected.group(1)) if selected else "","source":source.group(1) if source else "","joins":joins,"on":on_rules,"where":compact_sql(where.group(1)) if where else "","group":compact_sql(group.group(1)) if group else "","having":compact_sql(having.group(1)) if having else "","order":compact_sql(order),"limit":limit.group(1) if limit else "","windows":windows,"subquery":len(re.findall(r"(?i)\bSELECT\b",raw))>1 and not ctes}

def error_teaching(message):
    lower = message.lower()
    if "unknown column 'coffee'" in lower: return "Coffee is text, so it must be quoted as <code>'Coffee'</code>. Without quotes, MySQL searches for a column named Coffee."
    if "unknown column 'productname'" in lower or "unknown column 'product'" in lower: return "MySQL matches identifiers exactly. Compare the requested column with the table definition and correct the spelling."
    if "doesn't exist" in lower: return "The named table is a placeholder or misspelling. Replace it with a table that exists in the active database."
    if "not in group by" in lower: return "Every selected field must either define the group or be calculated from the group. Add the field to GROUP BY or remove it from SELECT."
    if "invalid use of group function" in lower: return "WHERE runs before groups and aggregates exist. Move the aggregate condition to HAVING."
    if "ambiguous" in lower: return "Both joined tables contain that column name. Prefix it with the intended table or alias so MySQL knows which value to return."
    return "Read the first MySQL error, locate the referenced clause or identifier, and compare it with the valid pattern shown in the lesson."

def query_teaching_block(sql, segment_number, lesson_title):
    raw = html.unescape(sql).strip(); upper = raw.upper()
    captured = EXPECTED_RESULTS.get(expected_result_key(segment_number, raw))
    if captured and captured.get("kind") == "error":
        explanation = error_teaching(captured["message"])
        return (
            '<section class="query-teaching error-teaching"><p class="teaching-kicker">UNDERSTAND THE ERROR</p>'
            f'<h3>Why this query does not run</h3><p>{explanation}</p>'
            '<div class="teaching-check"><strong>Debugging habit</strong><span>Change one thing, rerun the smallest statement, and verify the result before making another change.</span></div></section>'
        )
    if not re.match(r"(?is)^(SELECT\b|WITH\s+[a-z_]\w*\s+AS\s*\(|EXPLAIN\b|SHOW\s+INDEX\b|CREATE\b|ALTER\b|INSERT\b|UPDATE\b|DELETE\b|DROP\b|USE\b|DESCRIBE\b|START\s+TRANSACTION\b|COMMIT\b|ROLLBACK\b)", raw):
        return ""
    if not raw.rstrip().endswith(";") and re.match(r"(?is)^(SELECT|WITH|EXPLAIN|SHOW|DESCRIBE)\b",raw):
        return ""
    if any(token in upper for token in ("TABLE_NAME", "LEFT_TABLE", "RIGHT_TABLE", "COLUMN_1", "GROUP_COLUMN", "AGGREGATE_FUNCTION", "...")):
        return ""
    steps=[]; plain=""; grain=""; verify=""; practice=""; notice=""
    if re.match(r"(?is)^EXPLAIN\b",raw):
        planned=re.sub(r"(?is)^EXPLAIN\s+","",raw,count=1)
        plan_row=(captured.get("rows") or [[]])[0] if captured and captured.get("kind")=="rows" else []
        plan=dict(zip(captured.get("columns",[]),plan_row)) if captured and captured.get("kind")=="rows" else {}
        plain="MySQL does not return the SELECT's normal business rows. It asks the optimizer to describe how it intends to access the tables and perform the work."
        grain="One plan row per table access in this query; this example accesses the orders table once."
        steps=[("EXPLAIN","Request a plan","Ask for optimizer estimates instead of normal query output."),("PLANNED QUERY",compact_sql(planned,100),"This is the query whose work MySQL is estimating."),("READ THE PLAN","type · possible_keys · key · rows · Extra","Start with access method, available index, chosen index, estimated rows, and extra operations.")]
        if plan:
            notice=f"Here, type is {plan.get('type','—')}, key is {plan.get('key','—')}, estimated rows is {plan.get('rows','—')}, and Extra says {plan.get('Extra','—')}. These are estimates, not the query's business result."
        verify="Run the SELECT without EXPLAIN to verify its answer separately. After a tuning change, compare both the plan and the unchanged result."
        practice="Predict whether MySQL will scan or use an index, then compare your prediction with type and key."
    elif re.match(r"(?is)^SHOW\s+INDEX\b",raw):
        plain="MySQL reads its metadata and lists every index defined on the named table, one row per indexed column."
        grain="One metadata row per column within each index; composite indexes therefore occupy multiple rows."
        steps=[("SHOW INDEX",compact_sql(raw),"Inspect index name, uniqueness, column order, cardinality estimate, and visibility.")]
        notice="Seq_in_index tells you the left-to-right column order. Non_unique = 0 means the index enforces uniqueness."
        verify="Match each returned index and column sequence with SHOW CREATE TABLE before adding another index."
        practice="Find the primary key and explain how its uniqueness differs from a normal secondary index."
    elif re.match(r"(?is)^DESCRIBE\b",raw):
        plain="MySQL returns the stored definition of the table rather than its data rows."
        grain="One metadata row per table column."
        steps=[("DESCRIBE",compact_sql(raw),"Read each field's type, NULL rule, key role, default, and automatic behavior.")]
        notice="The Key and Extra columns reveal primary keys, indexed fields, and AUTO_INCREMENT behavior."
        verify="Compare the returned fields and types with the CREATE TABLE statement used in the lesson."
        practice="Choose one field and explain what invalid value its type or NULL rule would reject."
    elif re.match(r"(?is)^(SELECT|WITH)\b", raw):
        parts=query_parts(raw)
        if parts["ctes"]:
            for detail in parts["cte_details"]:
                description=f"Read {detail['source']}"
                if detail["group"]: description+=f", create one row per {detail['group']}"
                if detail["aggregates"]: description+=f", and calculate {', '.join(detail['aggregates'])}"
                steps.append((f"CTE {detail['name']}",detail["name"],description+". This intermediate result exists only for this statement."))
        if parts["source"]: steps.append(("FROM", parts["source"], "Choose the rows the outer query starts from."))
        for index,(join_type,table) in enumerate(parts["joins"]):
            rule=compact_sql(parts["on"][index]) if index<len(parts["on"]) else "Every row pair"
            steps.append((f"{(join_type or 'INNER').upper()} JOIN", table, f"Connect rows using {rule}."))
        if parts["where"]: steps.append(("WHERE", parts["where"], "Remove source rows that do not satisfy this condition before grouping."))
        if parts["group"]: steps.append(("GROUP BY", parts["group"], "Create one bucket for each distinct grouping value."))
        if parts["having"]: steps.append(("HAVING", parts["having"], "Remove completed groups whose aggregate result fails this condition."))
        if parts["windows"]: steps.append(("OVER", " · ".join(parts["windows"]), "Define which related rows the window function may inspect and in what order."))
        if parts["selected"]: steps.append(("SELECT", parts["selected"], "Calculate and name the columns displayed in the final result."))
        if parts["order"]: steps.append(("ORDER BY", parts["order"], "Sort the completed result; sorting does not change the stored table."))
        if parts["limit"]: steps.append(("LIMIT", parts["limit"], "Keep only this many rows after sorting."))
        clauses=[]
        for detail in parts["cte_details"]:
            cte_sentence=f"first build <code>{html.escape(detail['name'])}</code> from <code>{html.escape(detail['source'])}</code>"
            if detail["group"]: cte_sentence+=f" at one row per <code>{html.escape(detail['group'])}</code>"
            clauses.append(cte_sentence)
        if parts["source"]: clauses.append(f"read rows from <code>{html.escape(parts['source'])}</code>")
        if parts["subquery"]: clauses.append("calculate the nested query first and use its answer in the outer query")
        if parts["where"]: clauses.append(f"keep rows where <code>{html.escape(parts['where'])}</code>")
        if parts["group"]: clauses.append(f"form one group per <code>{html.escape(parts['group'])}</code>")
        if parts["windows"]: clauses.append("attach a window calculation without collapsing the result rows")
        if parts["selected"]: clauses.append(f"return <code>{html.escape(parts['selected'])}</code>")
        plain=("MySQL will "+", then ".join(clauses)+".") if clauses else "MySQL evaluates the SELECT expressions and returns a temporary result."
        if parts["group"]: grain=f"One output row per distinct {parts['group']} value."
        elif re.search(r"(?i)\b(COUNT|SUM|AVG|MIN|MAX)\s*\(",parts["selected"]) and not parts["windows"]: grain="One summary row because the query aggregates without GROUP BY."
        elif parts["windows"]: grain="The final source-row grain is preserved; the window value is attached as another column."
        elif parts["joins"]: grain="One row per matching row combination. Confirm the join does not multiply facts unexpectedly."
        else: grain="One output row per source row that survives WHERE, unless LIMIT keeps fewer."
        result=captured if captured and captured.get("kind")=="rows" else None
        if result: verify=f"Expect {result['row_count']} row{'s' if result['row_count']!=1 else ''} with columns {', '.join(result['columns']) or 'shown by the statement'}. Check the row count before interpreting values."
        else: verify="Check column names, result grain, row count, NULLs, and one value calculated by hand."
        if parts["windows"] and "LAG(" in upper: notice="Each previous-value column comes from the row immediately before it in the window order. The first row is NULL because no earlier row exists."
        elif parts["windows"] and "LEAD(" in upper: notice="Each next-value column comes from the following row in the window order. The last row is NULL because no later row exists."
        elif parts["windows"]: notice="The window calculation adds analytical context while leaving the underlying result rows visible."
        elif parts["group"]: notice=f"Rows sharing the same {parts['group']} value contribute to the same output row. Changing GROUP BY changes the report grain."
        elif parts["joins"]: notice="Columns from both tables appear on one result row only when the ON relationship produces that row. Repeated matches can increase row count."
        elif parts["where"]: notice="Every returned row passed the WHERE condition; rows that evaluate false or unknown are absent."
        else: notice="SELECT creates a temporary result for analysis. It does not change the source table."
        if parts["group"]: practice=f"Choose one {parts['group']} value and reproduce its aggregate manually from the detail rows."
        elif parts["where"]: practice="Change one filter value, predict which rows will enter or leave, then run the modified query."
        elif parts["windows"]: practice="Reverse or change the window order and predict which comparison or running value changes first."
        elif parts["order"]: practice="Switch ASC and DESC, then predict the first row before running the query."
        else: practice="Remove one selected column, predict the new result shape, then run the modified query."
    else:
        normalized_upper=compact_sql(raw,10000).upper()
        command=re.match(r"(?i)^([A-Z]+(?:\s+[A-Z]+)?)",raw).group(1).upper()
        object_match=re.search(r"(?i)\b(?:DATABASE|TABLE|VIEW|INDEX|INTO|UPDATE|FROM|USE|DESCRIBE)\s+([a-z_]\w*)",raw)
        object_name=object_match.group(1) if object_match else "the named database object"
        actions={"CREATE DATABASE":"create a database container","CREATE TABLE":"define an empty table and its rules","CREATE VIEW":"save a SELECT definition","CREATE INDEX":"build a lookup structure","INSERT INTO":"validate and store new rows","UPDATE":"change values in rows selected by WHERE","DELETE FROM":"remove rows selected by WHERE","ALTER TABLE":"change an existing table definition","DROP TABLE":"remove the named table","DROP VIEW":"remove the saved view definition","USE":"select the active database","DESCRIBE":"inspect a table definition","EXPLAIN SELECT":"return a query plan rather than normal result rows","SHOW INDEX":"inspect existing indexes","START TRANSACTION":"begin a reversible unit of work","ROLLBACK":"undo uncommitted changes","COMMIT":"make pending changes permanent"}
        action=next((value for key,value in actions.items() if normalized_upper.startswith(key)),"perform the displayed database operation")
        plain=f"This statement tells MySQL to {action} for <code>{html.escape(object_name)}</code>."
        grain="This operation changes or inspects database state; it does not produce an analytical row grain."
        steps=[(command,compact_sql(raw,100),action.capitalize()+".")]
        verify="Read MySQL's success or affected-row message, then use DESCRIBE, SHOW CREATE TABLE, SHOW INDEX, or a narrow SELECT to confirm the outcome."
        practice="State what should exist or change before running the statement, then verify that exact condition afterward."
        notice="The statement's success message proves only that MySQL accepted it. A separate verification statement proves the intended state."
    step_html="".join(f'<li><span>{index}</span><div><code>{html.escape(keyword)}</code><strong>{html.escape(fragment)}</strong><p>{html.escape(explanation)}</p></div></li>' for index,(keyword,fragment,explanation) in enumerate(steps,1))
    return (
        '<section class="query-teaching"><p class="teaching-kicker">UNDERSTAND THE QUERY</p><h3>Read it as a sequence of decisions</h3>'
        f'<div class="teaching-summary"><div><span>PLAIN ENGLISH</span><p>{plain}</p></div><div><span>RESULT GRAIN</span><p>{html.escape(grain)}</p></div><div><span>WHAT TO NOTICE</span><p>{html.escape(notice)}</p></div></div>'
        f'<ol class="clause-walkthrough">{step_html}</ol>'
        f'<div class="teaching-check"><strong>How to verify it</strong><span>{html.escape(verify)}</span></div>'
        f'<div class="teaching-check practice-prompt"><strong>Predict, then try</strong><span>{html.escape(practice)}</span></div></section>'
    )

SEGMENT_CONCEPTS = [
    ("SQL does not search a spreadsheet visually. It reads a table with a known row meaning, chooses columns, filters rows, and returns a new result.", "In products, one row is one menu product. Asking for product_name does not alter the other stored columns; it only changes the result shape.", "What does one row represent, and which columns would answer the business question?"),
    ("A table definition is a contract: column names describe facts, data types restrict their form, and constraints reject values that violate the rules.", "A DECIMAL price behaves numerically, while a VARCHAR product name remains text. Swapping those types would make analysis unreliable.", "What invalid value should each column type prevent?"),
    ("Transactional rows record events. Metrics are deliberate calculations over those rows, and different calculations answer different questions.", "Ten order lines contain 21 units and 45.800 revenue. Row count, unit count, and money are three different KPIs.", "Is the requested metric counting rows, adding units, or calculating money?"),
    ("GROUP BY establishes result grain before aggregates are interpreted. Equal grouping values enter the same bucket.", "GROUP BY product_name produces one row per product; SUM then calculates inside each product bucket.", "Complete this sentence: one output row represents one _____."),
    ("WHERE decides which detail rows enter groups; HAVING decides which completed groups remain in the report.", "A June date filter belongs in WHERE. A minimum category revenue threshold belongs in HAVING because revenue exists only after grouping.", "Does the condition refer to a stored row value or a calculated group value?"),
    ("A join compares candidate row pairs using ON. Join type decides whether unmatched rows disappear or remain with NULLs.", "An order's product value finds the corresponding product row, allowing one result row to contain sale facts and product attributes.", "What is each table's grain, and can the ON rule create more than one match?"),
    ("Keys express identity and relationships. Normalization stores a fact once and references it with a stable identifier.", "products stores one product row; orders stores product_id plus historical sale facts. A foreign key prevents an order from referencing a nonexistent product.", "Which table owns the descriptive fact, and which table should store only its key?"),
    ("Complex analysis becomes reliable when it is separated into named, testable intermediate results.", "A product_sales CTE can calculate one row per product; a later step can compare those rows with their average.", "Can you run and validate each intermediate step before combining them?"),
    ("A window function looks across related result rows without collapsing them. PARTITION BY defines groups and ORDER BY defines sequence.", "LAG compares a day with the prior day while both daily rows remain visible.", "Which rows belong in the window, and what ordering makes previous or running meaningful?"),
    ("Reporting expressions translate stored facts into useful labels, calendar periods, and presentation-ready text without changing source data.", "CASE can label revenue bands; DATE_FORMAT can create a month label; TRIM can remove outside spaces in the result.", "Is this expression changing storage or deriving a reporting value?"),
    ("Cleaning is a controlled process: profile, define a rule, preview, change safely, and validate. Never start by overwriting raw evidence.", "Before standardizing Coffee and coffees, count each value, preview targeted rows, update inside a transaction, and confirm the result.", "What evidence proves both that the intended rows changed and unintended rows did not?"),
    ("A view is a saved query interface. It centralizes reviewed logic but normally stores no separate copy of the rows.", "order_details can expose a trusted join and revenue definition that multiple reports query consistently.", "What is the view's row grain, and which reports depend on its columns?"),
    ("Performance work begins after correctness. EXPLAIN supplies a plan, indexes supply lookup paths, and measurement determines whether a change helped.", "A date-range query may use an order_date index instead of examining every row, but the result must remain identical.", "What evidence shows less work without changing the answer?"),
]

CONCEPT_DETAILS = {
    "Database vs Table vs Row vs Column": ("A database contains related tables. A table contains rows and columns. A row is one record; a column is one consistently defined fact about every record.", "In products, the row for Cold Brew is one product record; price is a column shared by all product rows.", "Point to one database, one table, one row, and one column in the course dataset."),
    "Why Data Analysts Love Tables": ("Consistent row grain and column definitions let the same operation be applied safely across thousands or millions of records.", "If every orders row means one sale line, SUM(quantity) has a consistent meaning across the entire table.", "What would break if different rows represented different kinds of events?"),
    "Creating Your First Table": ("CREATE TABLE converts a written data model into an empty structure. It defines what facts may be stored before any rows exist.", "Define product_id as a whole number, product_name as text, and price as an exact decimal before loading menu rows.", "Why should types and constraints be chosen before INSERT?"),
    "Table Blueprint": ("A blueprint states table grain first, then lists the columns required to describe one row at that grain.", "For products, one row per product requires an ID, name, category, and current price—not an order date.", "Write one sentence defining the table grain before naming columns."),
    "Data Types": ("A data type controls storage, valid operations, and error detection. Choose it from the meaning of the fact, not from how a sample happens to look.", "Quantity uses INT because units are whole numbers; price uses DECIMAL because exact arithmetic matters.", "Which operations must this value support: arithmetic, date comparison, or text matching?"),
    "Understanding VARCHAR": ("VARCHAR stores variable-length text up to a declared maximum. Numbers stored as VARCHAR sort and calculate like text, not numbers.", "product_name fits VARCHAR because names vary in length and are compared as text.", "Why should quantity not be VARCHAR even if the source file contains digit characters?"),
    "Understanding DECIMAL(6,3)": ("DECIMAL(6,3) allows six total digits, three after the decimal. It stores fixed-point values exactly.", "2.750 is stored exactly; the largest positive value fitting this definition is 999.999.", "What do the 6 and 3 control independently?"),
    "Text Values Need Quotes": ("Quotes mark a value as text. Without quotes, MySQL interprets a word as an identifier such as a column name.", "'Coffee' is a text value; Coffee without quotes asks MySQL for a column named Coffee.", "Which items need quotes: a product name, quantity, price, and date literal?"),
    "Why We Need an orders Table": ("A catalog describes what can be sold; an orders table records what actually happened. Analysis requires event data.", "products may contain Iced Latte once, while orders contains each sale line that references or repeats that product.", "Which business questions can orders answer that products alone cannot?"),
    "Products Table vs Orders Table": ("Entity tables describe things; transaction tables describe events involving those things.", "products has one row per menu item. orders has one row per sale line, so the same product can appear repeatedly.", "Which table should change when a new sale happens?"),
    "What Columns Should orders Have?": ("Columns must describe one order-line event: identity, product, quantity, sale price, and date.", "unit_price belongs on the order because it preserves what was charged even if the menu price later changes.", "Does each proposed column describe the event at the table's grain?"),
    "Understanding the New Data Type: DATE": ("DATE stores a calendar date as YYYY-MM-DD and supports chronological comparison and date functions.", "'2026-06-20' sorts before '2026-06-21' because both are real DATE values, not inconsistent display text.", "Why is a typed date safer than several text formats?"),
    "What Is an Aggregate Function?": ("An aggregate combines values from several rows into a summary such as a count, total, average, minimum, or maximum.", "SUM(quantity) turns ten order-line quantities into the total 21 units.", "Which rows are entering the aggregate, and what single metric comes out?"),
    "COUNT(*) vs SUM(quantity)": ("COUNT(*) counts rows. SUM(quantity) adds the units stored inside those rows. They match only when every quantity is one.", "The course has 10 order rows but 21 units because several rows contain multiple items.", "If one row has quantity 4, how much does it add to each metric?"),
    "What Is a KPI?": ("A KPI is a precisely defined metric used to monitor performance against a goal. The definition must specify population, time, grain, and calculation.", "Completed revenue for June is more precise than sales because it defines status, period, and formula.", "Could another analyst reproduce the same number from your written definition?"),
    "Visual idea of GROUP BY": ("Imagine sorting detail rows into labeled baskets. The grouping value labels each basket; aggregates calculate inside it.", "All Iced Latte rows enter one basket, then their row revenues add to 16.500.", "What changes if category replaces product_name as the basket label?"),
    "Simple definition": ("HAVING is a condition on groups after aggregate values have been calculated.", "HAVING SUM(quantity) > 3 keeps products whose completed bucket contains more than three units.", "Why can the same aggregate condition not normally be placed in WHERE?"),
    "Why do we need JOINS?": ("Normalized databases separate facts by entity. JOIN reconstructs the business story when a question needs attributes from more than one table.", "orders supplies quantity and sale price; products supplies product name and category.", "Which requested output columns come from each table?"),
    "The main idea": ("For each row from the starting table, MySQL searches candidate rows in the joined table and keeps combinations that satisfy ON.", "An order with product_id 2 matches the products row whose product_id is also 2.", "Is the matching field unique on either side, and what does that imply for row count?"),
    "What is COALESCE()?": ("COALESCE returns the first non-NULL value in its argument list. It changes display or calculation behavior, not the stored NULL.", "A product with no orders has SUM(quantity) = NULL after a LEFT JOIN; COALESCE(..., 0) displays zero.", "When does zero accurately mean no activity rather than missing information?"),
    "PRIMARY KEY vs FOREIGN KEY": ("A primary key identifies a row in its own table. A foreign key stores a permitted primary-key value from another table.", "products.product_id identifies a product; orders.product_id points each sale line to one valid product.", "Which side is the parent, and can a child reference a value that does not exist?"),
    "Why intermediate results matter": ("One large query is difficult to reason about when several transformations happen at once. Intermediate results let each grain and calculation be checked independently.", "First calculate product totals, then calculate their average, then compare each product with that benchmark.", "What should one row represent after each step?"),
    "Subquery or CTE?": ("Use a scalar subquery for one compact value, EXISTS for a yes/no match, and a CTE when naming a multi-step result improves clarity or reuse within the statement.", "An average price can be a scalar subquery; product_sales is clearer as a CTE when later steps reuse its columns.", "Does the next step need a value, an existence test, or a named set of rows?"),
    "Why window functions matter": ("GROUP BY summarizes and hides detail rows. Window functions calculate across related rows while keeping each row visible.", "Daily rows remain visible while SUM(...) OVER adds a running total beside each date.", "Do you need one row per group, or a group calculation attached to each row?"),
    "View limitations": ("A view improves reuse, not automatically performance. Its underlying query still runs, dependencies can break, and some views cannot be updated safely.", "A convenient reporting view can still hide a costly join; EXPLAIN the query that reads it.", "What complexity or dependency does the view hide from its consumers?"),
}

def concept_teaching_block(segment_number,title):
    if title in CONCEPT_DETAILS: core,example,check=CONCEPT_DETAILS[title]
    elif "Common mistake" in title or "Debug" in title: core,example,check=("A query can run successfully and still answer the wrong question. Debug syntax, grain, row count, NULL behavior, and totals separately.",SEGMENT_CONCEPTS[segment_number-1][1],"What evidence would distinguish a syntax problem from a logic problem?")
    elif "cheat sheet" in title.lower() or "checklist" in title.lower() or title in ("What You Learned","Your First MySQL Vocabulary"):
        core,example,check=("Use this summary for retrieval practice after attempting the idea from memory. Recognition is not the same as being able to write or explain it.","Cover the pattern, write it from memory, then compare clause order and meaning with the reference.","Can you explain when to use each pattern without reading its label?")
    else: core,example,check=SEGMENT_CONCEPTS[segment_number-1]
    return ('<section class="concept-teaching"><p class="teaching-kicker">BUILD THE MENTAL MODEL</p>'
            f'<div><span>CORE IDEA</span><p>{html.escape(core)}</p></div>'
            f'<div><span>CONCRETE EXAMPLE</span><p>{html.escape(example)}</p></div>'
            f'<div><span>EXPLAIN IT BACK</span><p>{html.escape(check)}</p></div></section>')

def add_instructional_context(segments):
    """Add purpose and an actual explanation—not merely syntax—to every lesson."""
    code_pattern=re.compile(r'(<div class="code-block">.*?<pre><code>(.*?)</code></pre></div>)',re.S)
    for segment_number,segment in enumerate(segments,1):
        previous_title=""
        for lesson_index,lesson in enumerate(segment["lessons"]):
            brief=learning_brief(segment_number,lesson_index,lesson,previous_title)
            lesson["body"]=re.sub(r"(</h2>)",r"\1"+brief,lesson["body"],count=1)
            teaching_added=False
            if not lesson["title"].startswith("Mini-project:"):
                matches=list(code_pattern.finditer(lesson["body"]))
                for match in matches:
                    teaching=query_teaching_block(match.group(2),segment_number,lesson["title"])
                    if teaching:
                        lesson["body"]=lesson["body"][:match.start()]+teaching+lesson["body"][match.start():]
                        teaching_added=True
                        break
            if not teaching_added and lesson["title"]!="Section knowledge check" and not lesson["title"].startswith("Mini-project:"):
                lesson["body"]=lesson["body"].replace(brief,brief+concept_teaching_block(segment_number,lesson["title"]),1)
            visible_text=html.unescape(re.sub(r"<[^>]+>"," ",lesson["body"]))
            word_count=len(re.findall(r"\b[\w'-]+\b",visible_text))
            lesson["time"]=max(lesson["time"],min(35,max(3,(word_count+179)//180)))
            previous_title=lesson["title"]

TEXTBOOK_UNITS = [
    [
        ("Databases, Tables, and the Analyst's Mental Model",1,4,"Before writing syntax, you need a precise picture of what SQL acts on. This section introduces relational tables, row grain, and the difference between stored data and a query result."),
        ("Constructing a SELECT Statement",5,8,"A SELECT statement is a request for a result, not a command to change the table. We build the request from its two essential decisions: which columns to display and which table supplies the rows."),
        ("Filtering and Shaping a Result",9,13,"Most business questions need only some rows in a useful order. Here we develop WHERE, comparison operators, ORDER BY, and LIMIT as connected parts of one query."),
        ("Guided Lab: Reading the Product Catalog",14,20,"The best way to learn retrieval is to predict a result and then run the query. Work through these tasks in order; each adds one decision to the same product dataset."),
        ("Analyst Reasoning and Chapter Review",21,23,"Syntax matters, but the professional habit is translating a vague question into a specific result grain, columns, filters, and sort order. This review connects the vocabulary to that workflow."),
    ],
    [
        ("From Server to Table",1,4,"A MySQL server can hold many databases, and each database can hold many related tables. This section follows the path from creating the container to selecting it as the active workspace."),
        ("Designing the Products Table",5,12,"Table design begins with what one row represents. From that decision, we choose columns, data types, punctuation, and a verification query that make the structure unambiguous."),
        ("Loading and Inspecting Rows",13,17,"INSERT maps values to columns by position. We begin with one row, extend the pattern to several rows, and verify that text, numbers, and decimals arrived in the intended columns."),
        ("Reproducible Setup and Safe Resets",18,24,"A useful learning database must be reproducible. We assemble the complete script, examine duplicate-object and duplicate-data failures, then develop a reset pattern that returns the schema to a known state."),
        ("Retrieval Lab",25,31,"Use the table you built to practice column selection, filters, sorting, and top-N questions. Write each query before revealing or comparing the supplied answer."),
        ("Debugging and Chapter Review",32,34,"Errors are information about the statement MySQL could not interpret or execute. This section separates punctuation, quoting, identifier, and object-existence problems so you can debug deliberately."),
    ],
    [
        ("Modeling Sales Events",1,5,"A products table describes the menu; it cannot tell us what sold. We define the grain of an order row and decide which event facts must be recorded before calculating any metric."),
        ("Building and Loading the Orders Table",6,10,"The order schema introduces dates and repeated sale-line facts. We create it, load a fixed dataset, inspect the rows, and preserve a reset script for repeatable analysis."),
        ("Calculated Columns and Aliases",11,13,"Row-level arithmetic creates a value for each source row. We calculate revenue, name it with an alias, and distinguish a temporary result expression from a permanent table change."),
        ("Aggregate Functions and KPI Foundations",14,22,"Aggregate functions reduce many rows to summary evidence. COUNT, SUM, AVG, MIN, and MAX answer different questions, so we connect each calculation to its exact business meaning."),
        ("Filtering the Input to a Metric",23,30,"WHERE controls which detail rows enter a calculation. We combine category, quantity, and date conditions while keeping filter logic separate from the aggregate itself."),
        ("Designing a Small KPI Report",31,33,"A dashboard is a set of consistently defined metrics, not merely several numbers. We combine the recurring query pattern and document what each KPI counts or calculates."),
        ("Sales Analysis Lab and Review",34,46,"These exercises move from row inspection to filtered revenue metrics. Treat the challenge and debugging sections as a closed-book check of both syntax and metric meaning."),
    ],
    [
        ("Why Grouping Changes the Question",1,4,"An aggregate without GROUP BY answers one question about the entire input. GROUP BY divides that input into meaningful buckets so the same calculation can answer one question per product, category, or date."),
        ("Product and Category Summaries",5,10,"We build grouped reports in small steps: calculate revenue, sort it, keep a leader, and compare monetary performance with unit volume at two business grains."),
        ("Daily Reports and Multiple Metrics",11,15,"Time-based grouping turns transactions into a daily series. Several aggregates can be calculated from the same daily bucket when their names and meanings remain distinct."),
        ("Controlling Grouped Result Grain",16,19,"Every nonaggregated selected column must be compatible with the grouping grain. We use multiple grouping columns and pre-group filters to construct a reliable analyst report."),
        ("Grouping Lab and Chapter Summary",20,24,"The exercises ask you to define the output grain before writing the aggregate. Use the chapter summary only after attempting each report from memory."),
    ],
    [
        ("Filtering Rows Versus Filtering Groups",1,4,"WHERE and HAVING both remove data from a result, but they act at different stages. This section establishes the logical boundary between source-row conditions and aggregate conditions."),
        ("Building Aggregate Thresholds",5,11,"Starting with units and revenue, we develop HAVING conditions carefully and examine how boundary choices such as greater-than versus at-least change the answer."),
        ("Combining WHERE and HAVING",12,16,"Many reports need both a population rule and a performance threshold. We filter the source first, form groups second, and then apply one or more conditions to the calculated summaries."),
        ("Writing and Reviewing HAVING Reports",17,19,"Aliases, clause order, and aggregate placement are common sources of confusion. We correct the failure patterns and assemble a complete grouped report."),
        ("HAVING Lab and Chapter Summary",20,24,"These exercises require you to identify whether each condition belongs before or after grouping. State that reasoning before writing the SQL."),
    ],
    [
        ("Why Relational Questions Need Joins",1,4,"Separate tables reduce repetition but no longer contain the complete answer by themselves. A join reconnects related facts through an explicit matching rule."),
        ("Inner Joins, Qualification, and Aliases",5,9,"We begin with a clean INNER JOIN, then make every shared column unambiguous using table names and aliases. The ON condition determines which row pairs can appear."),
        ("Analyzing Matched Rows",10,17,"Once the relationship is correct, joined rows can support product, category, date, and price-comparison reports. We validate the join before trusting its aggregates."),
        ("Outer Joins and Missing Relationships",18,24,"LEFT JOIN preserves a chosen population even when no match exists. NULL tests and COALESCE then help us distinguish missing relationships from zero activity."),
        ("Combining Joins with Grouped Analysis",25,28,"Real reports combine relationships, grouping, thresholds, and validation. This section develops that pipeline and identifies fragile name-based joins."),
        ("Join Lab and Chapter Summary",29,34,"The exercises cover matched rows, unmatched rows, aggregate reports, and price-quality checks. Always write the expected join cardinality before running the query."),
    ],
    [
        ("From Repeated Text to Relational Design",1,6,"The early schema was convenient for learning but repeats product facts in every order. We diagnose the update risk and replace repeated attributes with a stable relationship."),
        ("Rebuilding with Keys and Constraints",7,12,"A professional rebuild defines primary keys, foreign keys, required values, and historical sale price deliberately. We load valid rows and test that an invalid relationship is rejected."),
        ("Querying the Normalized Schema",13,17,"Normalization changes where facts live, not the business questions. Joins restore product labels and categories while order rows retain quantity, date, and charged price."),
        ("Integrity and Professional Database Behavior",18,21,"Keys protect identity and history. We examine deletion behavior, parent-child responsibility, and the validation habits expected when schemas support real reporting."),
        ("Completeness Reports and Design Rules",22,27,"A normalized design must also represent absence correctly. Outer joins reveal products with no sales, and table-grain rules guide future schema decisions."),
        ("Normalization Lab",28,33,"These exercises revisit the full reporting workflow on the key-based schema. Confirm relationship cardinality and revenue reconciliation in every solution."),
        ("Chapter Synthesis and Rebuild Script",34,36,"The final model, chapter review, and clean script bring design and analysis together. You should be able to recreate the schema and explain why each fact belongs where it does."),
    ],
    [
        ("Thinking in Intermediate Results",1,4,"Complex SQL becomes understandable when each step has a clear grain and purpose. We begin with nested queries that produce one value for an outer comparison."),
        ("Membership, Existence, and Correlation",5,9,"IN, EXISTS, NOT EXISTS, correlated subqueries, and derived tables solve different relationship problems. We compare what each inner query returns and how the outer query consumes it."),
        ("Common Table Expressions",10,14,"A CTE names an intermediate result for the duration of one statement. We build single and multiple CTE pipelines, then use a one-row CROSS JOIN to supply a benchmark."),
        ("Choosing and Validating a Multi-Step Pattern",15,19,"Readable syntax is not enough: NULL behavior, repeated evaluation, untested grain, and unsupported findings can still produce incorrect results. We establish criteria for choosing, debugging, and communicating each pattern."),
        ("Subquery and CTE Lab",20,23,"The exercises progress from scalar benchmarks to absence tests and share-of-total calculations. Run each intermediate result independently before composing the final statement."),
        ("Chapter Summary",24,24,"Use this summary to compare the shape produced by scalar subqueries, IN, EXISTS, derived tables, and CTEs before moving to window functions."),
    ],
    [
        ("Analytical Windows and Preserved Detail",1,5,"Window functions calculate across related rows without replacing them with one grouped row. OVER and PARTITION BY establish the set of rows available to each calculation."),
        ("Running Totals and Rankings",6,10,"Ordering inside a window gives rows analytical position. We develop running totals and three ranking functions, then use a CTE to filter a top-N-per-group result."),
        ("Comparing Rows Across Time and Peers",11,15,"LAG, LEAD, moving frames, and aggregate peer windows turn a daily series or peer group into comparisons. The partition, order, and frame determine which values participate."),
        ("Shares, Ordering, and Layered Analysis",16,20,"Percentage-of-total and combined grouped/window reports show how analytical stages can be layered. We separate window order from final display order and review failure patterns."),
        ("Window Function Lab",21,25,"These exercises cover ranking, partitioning, top-N logic, revenue share, running totals, and change. State the partition and order in words before writing OVER."),
        ("Chapter Summary",26,26,"Use the summary to choose among grouping, ranking, navigation, and aggregate window functions based on the required output grain."),
    ],
    [
        ("Turning Facts into Business Categories",1,3,"CASE applies ordered business rules inside a query. We use it both to label individual rows and to count conditional populations within an aggregate."),
        ("Working with Dates, Text, and Safe Ratios",4,13,"Dates, text, and NULL-aware expressions often require transformation before reporting. We extract calendar parts, format labels, measure intervals, build rolling windows, standardize text, combine fields, handle missing display values, and protect ratio calculations."),
        ("Project Metric Definitions",14,16,"A useful report combines transformations without obscuring their meaning. We connect gross revenue, net revenue, refunds, inventory rules, monthly reporting, and common mistakes to explicit business definitions."),
        ("Functions Lab and Chapter Summary",17,22,"The exercises combine CASE, weekday reporting, cleaned labels, and grouped revenue bands. Use the summary to distinguish formatting from permanent data cleaning."),
    ],
    [
        ("Profiling Data Before Changing It",1,8,"Cleaning begins with evidence. We measure completeness, boolean quality failures, blanks, inconsistent categories, duplicates, and invalid numeric ranges before defining any correction."),
        ("Safe Corrections and Preventive Rules",9,12,"A correction should be previewed, reversible, and validated. Transactions, staging tables, constraints, and quality reports turn one-time cleanup into a controlled process."),
        ("Quality Rules, Tests, and Relationships",13,16,"Professional data cleaning converts business rules into repeatable tests: completeness, uniqueness, accepted values, relationship integrity, freshness, and distribution."),
        ("Deduplication, Audit Logs, and Reconciliation",17,21,"Cleaning decisions must be explainable. We mark duplicate candidates with survivor rules, log changes, reconcile totals, and avoid destructive shortcuts."),
        ("Data Quality Lab and Chapter Summary",22,29,"These exercises ask you to detect issues and preview transformations without destroying source evidence. Use the checklist as an ordered cleaning workflow."),
    ],
    [
        ("Views as Saved Query Interfaces",1,5,"A standard view stores a SELECT definition, not a copy of its result. We create, query, filter, group, and safely replace a reusable reporting interface."),
        ("Designing Reporting Views",6,12,"Good views have documented grain, stable names, deliberate security exposure, and understood limitations. We build KPI views, layer reports above them, and compare them with CTEs."),
        ("Views Lab",13,16,"The exercises create product and category reporting views, then use them for filters and percentage comparisons. Treat each view definition as a contract for downstream users."),
        ("Chapter Summary",17,17,"Use the summary to decide when logic belongs in a one-query CTE, a reusable view, or the consuming report itself."),
    ],
    [
        ("Measure Before Optimizing",1,4,"Performance tuning begins with a correct query and a baseline. EXPLAIN exposes access strategy, estimated rows, candidate indexes, and extra work such as temporary results."),
        ("Index Design and Searchable Predicates",5,9,"Indexes are ordered lookup structures with costs. We compare single and composite indexes, leftmost prefixes, and date predicates that preserve index searchability."),
        ("Reducing Work Without Changing Results",10,14,"Selecting fewer columns, indexing relationships, controlling join cardinality, and removing unused indexes can reduce work. Every change must preserve the verified answer."),
        ("Performance Lab and Chapter Summary",15,20,"The exercises require before-and-after plan evidence, result reconciliation, and explicit tradeoffs. Avoid claiming improvement from an index name alone."),
    ],
]

def strip_micro_heading(body):
    """Remove a generated micro-lesson title before nesting it in a textbook section."""
    return re.sub(r'^<p class="eyebrow">.*?</p><h2>.*?</h2>', '', body, count=1, flags=re.S)

def consolidate_textbook_units(segments):
    """Combine fragmented source screens into coherent, chapter-style sections."""
    if len(segments) != len(TEXTBOOK_UNITS):
        raise ValueError("Every chapter needs a textbook unit map")
    consolidated=[]
    for chapter_number,(segment,unit_defs) in enumerate(zip(segments,TEXTBOOK_UNITS),1):
        source_lessons=segment["lessons"]
        units=[]; covered=[]
        for section_number,(title,start,end,lead) in enumerate(unit_defs,1):
            selected=source_lessons[start-1:end]; covered.extend(range(start,end+1))
            sections=[]
            for source in selected:
                subsection_title="Chapter Roadmap" if source["title"]=="Segment overview" else source["title"]
                sections.append(f'<section class="textbook-subsection" data-source-title="{html.escape(source["title"],quote=True)}"><h3>{html.escape(subsection_title)}</h3>{strip_micro_heading(source["body"])}</section>')
            body=(f'<p class="chapter-label">CHAPTER {chapter_number} · SECTION {section_number}</p>'
                  f'<h2>{html.escape(title)}</h2><p class="chapter-lead">{html.escape(lead)}</p>'
                  f'<div class="chapter-reading">{"".join(sections)}</div>')
            units.append({"title":title,"time":max(8,min(45,sum(item["time"] for item in selected))),"body":body,"source_titles":[item["title"] for item in selected]})
        expected=list(range(1,len(source_lessons)+1))
        if covered!=expected:
            raise ValueError(f"Chapter {chapter_number} textbook map covers {covered}, expected {expected}")
        consolidated.append({"title":segment["title"],"desc":segment["desc"],"lessons":units})
    return consolidated

def add_walkthrough_bridge_notes(segments):
    """Cover practical commands used by the larger project walkthrough."""
    setup_note = (
        '<section class="textbook-subsection" data-source-title="Running a complete setup script">'
        '<h3>Running a complete setup script</h3>'
        '<p>Some MySQL tools let you execute a saved SQL file from the prompt with '
        '<code>SOURCE path/to/file.sql;</code>. The command runs the statements in the file in order.</p>'
        '<p>Use <code>SOURCE</code> for reproducible setup scripts, then run <code>USE database_name;</code> '
        'so later queries point at the intended database. If your editor does not support <code>SOURCE</code>, '
        'open the script, select all of it, and execute it manually.</p>'
        '</section>'
    )
    target = segments[1]["lessons"][3]
    target["body"] = target["body"].replace("</div>", setup_note + "</div>", 1)
    target.setdefault("source_titles", []).append("Running a complete setup script")

PROJECT_BUILD_ALONG = [
    {
        "title": "Project build-along: Start the MetroMart assignment",
        "brief": "Open the final project dataset early and use basic SELECT skills to orient yourself like an analyst receiving a new data extract.",
        "setup": """SOURCE project_data/retail_project_setup.sql;
USE metromart_project;""",
        "grain": "One output row per order returned by the filter.",
        "sql": """SELECT
    order_id,
    order_date,
    channel,
    status,
    payment_method
FROM orders
WHERE status = 'completed'
ORDER BY order_date
LIMIT 20;""",
        "validation": "Confirm the result shows only completed orders and that the earliest returned rows match the January-June 2026 assignment window.",
    },
    {
        "title": "Project build-along: Load and inspect MetroMart",
        "brief": "After running project_data/retail_project_setup.sql, verify that the project database exists and that the core tables loaded before analyzing anything.",
        "grain": "One output row per table being counted.",
        "sql": """USE metromart_project;

SELECT 'orders' AS table_name, COUNT(*) AS row_count FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'stores', COUNT(*) FROM stores;""",
        "validation": "Treat unexpected row counts as a setup problem, not an analysis problem. Fix the load before writing KPI queries.",
    },
    {
        "title": "Project build-along: Map keys and table grain",
        "brief": "Use the MetroMart schema to identify parent tables, transaction tables, and the key relationships that later joins must respect.",
        "grain": "One output row per order item with its parent order and product keys visible.",
        "sql": """SELECT
    oi.order_item_id,
    oi.order_id,
    o.customer_id,
    o.store_id,
    oi.product_id,
    oi.quantity,
    oi.unit_price
FROM order_items AS oi
JOIN orders AS o ON o.order_id = oi.order_id
ORDER BY oi.order_item_id
LIMIT 20;""",
        "validation": "State the grain out loud: order_items is one row per product line inside an order, so revenue belongs at this level.",
    },
    {
        "title": "Project build-along: Profile messy source data",
        "brief": "Before trusting revenue or customer analysis, measure invalid metrics, blanks, suspicious emails, and inconsistent values.",
        "grain": "One summary row containing data-quality failure counts.",
        "sql": """SELECT
    COUNT(*) AS item_rows,
    SUM(quantity IS NULL) AS null_quantity_rows,
    SUM(quantity <= 0) AS non_positive_quantity_rows,
    SUM(unit_price IS NULL) AS null_price_rows,
    SUM(unit_price < 0) AS negative_price_rows,
    SUM(discount_amount < 0) AS negative_discount_rows
FROM order_items;""",
        "validation": "Do not delete bad rows. Write the business rule that decides whether each row should be excluded, corrected, or escalated.",
    },
    {
        "title": "Project build-along: Define reusable business fields",
        "brief": "Create reporting-friendly fields for dates, customer quality, loyalty tiers, and metric labels without changing the raw tables.",
        "grain": "One output row per customer returned by the query.",
        "sql": """SELECT
    customer_id,
    TRIM(customer_name) AS clean_name,
    LOWER(TRIM(email)) AS clean_email,
    CASE
        WHEN email IS NULL OR TRIM(email) = '' THEN 'missing email'
        WHEN email NOT LIKE '%@%.%' THEN 'invalid email'
        ELSE 'usable email'
    END AS email_quality,
    CASE
        WHEN loyalty_tier IS NULL THEN 'Unknown'
        ELSE CONCAT(UPPER(LEFT(TRIM(loyalty_tier), 1)), LOWER(SUBSTRING(TRIM(loyalty_tier), 2)))
    END AS normalized_tier
FROM customers
ORDER BY customer_id
LIMIT 50;""",
        "validation": "Check that blank strings become visible as quality issues and that tier labels use one consistent spelling.",
    },
    {
        "title": "Project build-along: Calculate the first sales KPIs",
        "brief": "Use the valid completed sales population to calculate order count, units, revenue, and revenue per order.",
        "grain": "One summary row for the completed valid order-item population.",
        "sql": """SELECT
    COUNT(DISTINCT o.order_id) AS completed_orders,
    SUM(oi.quantity) AS units_sold,
    ROUND(SUM(oi.quantity * oi.unit_price - oi.discount_amount), 2) AS gross_revenue,
    ROUND(SUM(oi.quantity * oi.unit_price - oi.discount_amount) / COUNT(DISTINCT o.order_id), 2) AS revenue_per_order
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.order_id
WHERE o.status = 'completed'
  AND oi.quantity > 0
  AND oi.unit_price >= 0;""",
        "validation": "Verify that completed_orders counts distinct orders while units_sold sums product quantities. These are different metrics.",
    },
    {
        "title": "Project build-along: Join the business dimensions",
        "brief": "Connect order facts to stores, regions, products, and categories so the project can answer where and what performance questions.",
        "grain": "One output row per valid completed order item with business labels attached.",
        "sql": """SELECT
    o.order_id,
    DATE(o.order_date) AS order_date,
    r.region_name,
    s.store_name,
    p.product_name,
    pc.category_name,
    pc.department,
    oi.quantity,
    oi.quantity * oi.unit_price - oi.discount_amount AS gross_revenue
FROM orders AS o
JOIN stores AS s ON s.store_id = o.store_id
JOIN regions AS r ON r.region_id = s.region_id
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
JOIN product_categories AS pc ON pc.category_id = p.category_id
WHERE o.status = 'completed'
  AND oi.quantity > 0
  AND oi.unit_price >= 0
ORDER BY o.order_date, o.order_id
LIMIT 30;""",
        "validation": "Check that joining dimensions adds labels but does not change the intended item-line grain.",
    },
    {
        "title": "Project build-along: Summarize monthly store performance",
        "brief": "Turn item-level facts into a monthly store report that operations leaders can scan.",
        "grain": "One output row per store per sales month.",
        "sql": """SELECT
    s.store_name,
    DATE_FORMAT(o.order_date, '%Y-%m') AS sales_month,
    COUNT(DISTINCT o.order_id) AS completed_orders,
    SUM(oi.quantity) AS units_sold,
    ROUND(SUM(oi.quantity * oi.unit_price - oi.discount_amount), 2) AS gross_revenue
FROM orders AS o
JOIN stores AS s ON s.store_id = o.store_id
JOIN order_items AS oi ON oi.order_id = o.order_id
WHERE o.status = 'completed'
  AND oi.quantity > 0
  AND oi.unit_price >= 0
GROUP BY s.store_id, s.store_name, DATE_FORMAT(o.order_date, '%Y-%m')
ORDER BY sales_month, gross_revenue DESC;""",
        "validation": "Before interpreting revenue, confirm the GROUP BY columns describe exactly one store-month.",
    },
    {
        "title": "Project build-along: Apply business thresholds",
        "brief": "Use HAVING to keep only product groups with enough sales volume to matter for operational decisions.",
        "grain": "One output row per product that meets the unit threshold.",
        "sql": """SELECT
    p.product_name,
    SUM(oi.quantity) AS units_sold,
    ROUND(SUM(oi.quantity * oi.unit_price - oi.discount_amount), 2) AS gross_revenue
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
WHERE o.status = 'completed'
  AND oi.quantity > 0
  AND oi.unit_price >= 0
GROUP BY p.product_id, p.product_name
HAVING SUM(oi.quantity) >= 300
ORDER BY units_sold DESC;""",
        "validation": "Explain why the status and metric-quality rules belong in WHERE, while the unit threshold belongs in HAVING.",
    },
    {
        "title": "Project build-along: Package the trusted sales view",
        "brief": "Save the completed-sales business rules as a reusable reporting layer so later analysis reads from one reviewed source.",
        "grain": "The view returns one row per valid item line from a completed order.",
        "sql": """CREATE OR REPLACE VIEW completed_valid_sales_v AS
SELECT
    o.order_id,
    DATE(o.order_date) AS order_date,
    DATE_FORMAT(o.order_date, '%Y-%m') AS sales_month,
    r.region_name,
    s.store_name,
    o.channel,
    p.product_id,
    p.product_name,
    pc.category_name,
    pc.department,
    oi.order_item_id,
    oi.quantity,
    oi.unit_price,
    oi.discount_amount,
    oi.quantity * oi.unit_price - oi.discount_amount AS gross_revenue
FROM orders AS o
JOIN stores AS s ON s.store_id = o.store_id
JOIN regions AS r ON r.region_id = s.region_id
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
JOIN product_categories AS pc ON pc.category_id = p.category_id
WHERE o.status = 'completed'
  AND oi.quantity > 0
  AND oi.unit_price >= 0;""",
        "validation": "Immediately reconcile view row count and revenue against the source tables before using it in reports.",
    },
    {
        "title": "Project build-along: Build a CTE movement report",
        "brief": "Break monthly product movement into named steps so the benchmark and comparison are reviewable.",
        "grain": "One output row per product per month.",
        "sql": """WITH product_month AS (
    SELECT
        product_id,
        product_name,
        sales_month,
        ROUND(SUM(gross_revenue), 2) AS revenue
    FROM completed_valid_sales_v
    GROUP BY product_id, product_name, sales_month
), product_average AS (
    SELECT
        product_id,
        ROUND(AVG(revenue), 2) AS avg_monthly_revenue
    FROM product_month
    GROUP BY product_id
)
SELECT
    pm.product_name,
    pm.sales_month,
    pm.revenue,
    pa.avg_monthly_revenue,
    ROUND(pm.revenue - pa.avg_monthly_revenue, 2) AS difference_from_average
FROM product_month AS pm
JOIN product_average AS pa ON pa.product_id = pm.product_id
ORDER BY pm.product_name, pm.sales_month;""",
        "validation": "Run each CTE by itself while developing. The first CTE should be product-month grain; the second should be product grain.",
    },
    {
        "title": "Project build-along: Rank and compare performance",
        "brief": "Use window functions to answer top-products and peer-comparison questions without losing the rows being reported.",
        "grain": "One output row per ranked product within a department.",
        "sql": """WITH product_sales AS (
    SELECT
        department,
        category_name,
        product_name,
        ROUND(SUM(gross_revenue), 2) AS revenue
    FROM completed_valid_sales_v
    GROUP BY department, category_name, product_id, product_name
), ranked AS (
    SELECT
        product_sales.*,
        DENSE_RANK() OVER (
            PARTITION BY department
            ORDER BY revenue DESC
        ) AS department_revenue_rank
    FROM product_sales
)
SELECT *
FROM ranked
WHERE department_revenue_rank <= 3
ORDER BY department, department_revenue_rank, product_name;""",
        "validation": "Confirm the rank restarts for each department and that ties keep the same dense rank.",
    },
    {
        "title": "Project build-along: Collect performance evidence",
        "brief": "Before presenting the project, show that an important filter has a measured plan and an intentional index candidate.",
        "grain": "One execution-plan row per table access in the explained query.",
        "sql": """EXPLAIN
SELECT store_id, order_date, status
FROM orders
WHERE status = 'completed'
  AND order_date >= '2026-03-01'
  AND order_date < '2026-04-01';""",
        "validation": "After adding an index, rerun EXPLAIN and confirm the business result still matches. Performance work cannot change the answer.",
    },
]

def add_project_build_along(segments):
    """Make the final MetroMart project a chapter-by-chapter build-along."""
    if len(segments) != len(PROJECT_BUILD_ALONG):
        raise ValueError("Every chapter needs one MetroMart build-along task")
    for chapter_number, (segment, task) in enumerate(zip(segments, PROJECT_BUILD_ALONG), 1):
        setup_html = ""
        if task.get("setup"):
            setup_html = (
                '<div class="project-brief setup-brief"><strong>Do this before the first project query</strong>'
                '<p>The MetroMart build-along uses a separate project database. Run the setup script once before continuing.</p>'
                '<ol>'
                '<li>Open MySQL from the folder that contains this course repository, or open the file manually in MySQL Workbench.</li>'
                '<li>Run the setup command below. If your tool does not support <code>SOURCE</code>, open <code>project_data/retail_project_setup.sql</code>, select the whole file, and execute it.</li>'
                '<li>After the script finishes, keep using <code>metromart_project</code> for every project build-along query.</li>'
                '</ol></div>'
                '<div class="code-block"><div class="code-label"><span>PROJECT SETUP</span><button data-copy>Copy setup</button></div>'
                f'<pre><code>{html.escape(task["setup"])}</code></pre></div>'
            )
        lesson = {
            "title": task["title"],
            "time": 18,
            "source_titles": [task["title"]],
            "body": (
                f'<p class="chapter-label">CHAPTER {chapter_number} · SECTION 999</p>'
                f'<h2>{html.escape(task["title"])}</h2>'
                f'<p class="chapter-lead">{html.escape(task["brief"])}</p>'
                '<div class="chapter-reading">'
                f'<section class="textbook-subsection" data-source-title="{html.escape(task["title"], quote=True)}">'
                '<h3>Build the project while you learn</h3>'
                '<p>Run this against the MetroMart project database. This is one piece of the final analyst walkthrough, introduced now so the capstone grows with the course.</p>'
                f'{setup_html}'
                f'<div class="project-brief"><strong>Analyst task</strong><p>{html.escape(task["brief"])}</p></div>'
                f'<p><strong>Result grain:</strong> {html.escape(task["grain"])}</p>'
                '<div class="code-block"><div class="code-label"><span>PROJECT SQL</span><button data-copy>Copy query</button></div>'
                f'<pre><code>{html.escape(task["sql"])}</code></pre></div>'
                f'<p><strong>Validation habit:</strong> {html.escape(task["validation"])}</p>'
                '</section></div>'
            ),
        }
        insert_at = next((index for index, item in enumerate(segment["lessons"]) if item["title"] == "Section knowledge check"), len(segment["lessons"]))
        segment["lessons"].insert(insert_at, lesson)

segments = [parse_source(path, transcript, *meta) for path, transcript, meta in zip(SOURCES, TRANSCRIPTS,META)]
segments = consolidate_textbook_units(segments)
add_walkthrough_bridge_notes(segments)
segments = reorder_for_workflow(segments)
add_segment_visuals(segments)
add_assessments_and_projects(segments)
add_project_build_along(segments)
relabel_workflow_chapters(segments)
add_expected_results(segments)
add_instructional_context(segments)
(ROOT / "source-lessons.js").write_text("window.SOURCE_SEGMENTS = " + json.dumps(segments, ensure_ascii=False) + ";\n", encoding="utf-8")
print(f"Built {sum(len(x['lessons']) for x in segments)} lessons from {len(segments)} complete source documents.")
