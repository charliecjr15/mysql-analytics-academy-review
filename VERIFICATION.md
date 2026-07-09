# Verification record

Verified on 2026-07-05 with Python 3, Node.js, Chromium, and an isolated MySQL
8.4.10 instance. The instance used a temporary data directory, local Unix socket,
no network listener, and no personal server credentials.

## Course build and structural audit

```text
python3 build_lessons.py
Built 98 textbook sections from 13 complete source documents.

python3 audit_course.py
COURSE AUDIT PASSED: 13 chapters, 98 textbook sections
```

The audit proves:

- exact workflow-based chapter ordering and expected lesson counts;
- one accessible overview visual and visual learning material per lesson;
- 68 source practice exercises;
- three interactive questions and one rubric-based mini-project per section;
- hidden project reference solutions;
- required advanced concepts and verified teaching-dataset values;
- baseline setup/reset guide and data dictionary;
- cumulative assessments, capstone, interview lab, portfolio, and application
  readiness artifacts;
- capstone schema, imperfect data cases, and reference-solution techniques.

`python3 -m py_compile build_lessons.py audit_course.py course_enrichment.py`,
`node --check app.js`, and `node --check source-lessons.js` passed.

## MySQL execution

`setup/coffee_shop.sql` executed from an empty server and returned:

```text
products: 6
order rows: 10
units: 21
revenue: 45.800
```

`audit_queries.sql` then executed successfully, including schema migration,
CTEs, windows, CASE/date/text functions, a reporting view, transaction rollback,
EXPLAIN, and index creation. Headline results included Iced Latte revenue
`16.500` and final running revenue `45.800`.

`capstone/capstone_setup.sql` and `capstone/reference_solution.sql` executed from
an empty server. Both independent revenue paths reconciled exactly:

```text
valid completed item rows: 21
reporting-view revenue:    121.050
source-query revenue:      121.050
```

The clean-item and completed-sales views were queryable. The composite
`idx_orders_status_date_store` index existed with `status`, `order_date`, and
`store_id` in the documented order. Both EXPLAIN statements executed.

The supplemental RIGHT JOIN and CTE-backed self join also executed. The self
join returned Maya with no manager and Omar/Layla with Maya as manager.

## Browser verification

Chromium loaded the main course and career center through a local HTTP server.
Desktop (1440 px) and mobile (390 px) render checks showed readable responsive
layouts. Course scripts and lesson visual assets returned HTTP 200. A deep link
to section 1's knowledge check rendered all three questions with distinct IDs.

The application tracks each answer separately, restores passed answers, allows
wrong answers to be retried, and refuses to complete a section knowledge-check
lesson until every question is correct.

## Query visuals and expected results

The lesson generator was re-audited after replacing the legacy hard-coded
“Statement in action” scenes. Current execution maps are derived from each
statement's actual CTE names, source tables, JOIN types and ON rules, filters,
grouping keys, window definitions, selected expressions, and final sorting.
Automated identifier comparison checked 250 statement visuals with zero table
or object mismatches.

All 397 displayed SQL blocks across all 13 segments have one adjacent expected
result or expected-outcome card. MySQL 8.4 execution captured 239 unique complete
read-only examples: 230 successful result definitions and nine deliberately
incorrect teaching examples. Result cards show up to 12 rows and state the full
row count; zero-row results and NULL values are explicit. DDL, DML, transaction,
template, and multi-statement examples explain their expected structural,
affected-row, error, or verification outcome.

Live execution also found and corrected three content defects: the reserved
`YEAR_MONTH`-style alias was renamed to `sales_month`, and the Segment 8 and 10
mini-project solutions were updated to join normalized orders to products.

## Known environment note

The user's normal MySQL server rejected passwordless access as expected. No
password was requested, read, stored, or printed. Verification used the isolated
disposable server instead.

## Course-reader redesign

The public DataReady site was used as interaction and information-architecture
inspiration without copying its text, branding, or implementation. Query Grounds
now has separate overview and lesson modes, a persistent 13-section curriculum,
one expanded active section, lesson breadcrumbs, a focused reading column,
right-side “On this lesson” navigation, SQL syntax highlighting, compact progress,
and responsive mobile curriculum navigation.

Chromium checks at 1440×1000 and 390×844 verified the overview and real lesson
layouts. A hydrated DOM test confirmed 13 curriculum groups, exactly one expanded
section, lesson-outline links, syntax highlighting, expected results, and retained
lesson SQL. All 359 original/enriched teaching topics plus the three course supplements are preserved inside 98 connected
textbook sections. The 397 SQL/result pairs, quizzes, projects, progress, career
center, and assessment gates remain intact.

## Textbook restructuring

The former 369-screen micro-lesson structure and repeated generated teaching
panels were removed. Each chapter is now divided into connected reading sections
with an authored introduction, logically ordered subsections, worked SQL examples,
adjacent expected results, practice sets, a chapter knowledge check, and a project.
Automated checks enforce the 98-section map, preserve 359 original/enriched topics
plus two join supplements and one setup supplement, and reject the retired
template panels if they reappear.

The visible chapter order is now workflow-first: foundations and setup, schema
design, data cleaning, transformations and metric definitions, KPI queries,
joins, grouped reporting, HAVING thresholds, trusted views, CTEs, windows, and
performance tuning. The builder preserves original source numbers internally so
captured MySQL expected results still attach to the correct SQL examples after
the visible reorder.
