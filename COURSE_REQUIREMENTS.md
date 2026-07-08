# Query Grounds — Course Completion Requirements

This document defines completion for the beginner-to-job-ready SQL course. A
green structural audit alone is not sufficient.

## Learner outcome

A learner starting with no SQL experience can install the required tools,
understand relational data, write and debug MySQL queries, analyze realistic
business data, design trustworthy reports, improve query performance, and
present portfolio work during an entry-level analyst interview.

## Required curriculum

1. SQL and relational database foundations
2. MySQL setup, database creation, tables, data types, and data loading
3. SELECT, aliases, expressions, NULL, DISTINCT, filtering, sorting, and limits
4. Aggregate functions, KPIs, GROUP BY, and HAVING
5. INNER, LEFT, RIGHT, CROSS, self joins, unions, and join validation
6. Primary keys, foreign keys, constraints, normalization, and schema design
7. Subqueries, correlated subqueries, EXISTS, and CTEs
8. Window functions, partitions, frames, ranking, and period comparisons
9. CASE, date functions, text functions, and NULL handling
10. Data profiling, cleaning, deduplication, validation, and safe updates
11. Views, reusable reporting layers, and report quality checks
12. Transactions, permissions, security basics, and responsible data handling
13. EXPLAIN, indexes, sargability, query rewrites, and performance tradeoffs
14. Workplace workflow: requirements, metric definitions, QA, documentation,
    version control, communicating findings, interviews, and portfolio delivery

MySQL is the teaching dialect. Lessons must identify important portability
differences where common PostgreSQL, SQL Server, or SQLite syntax differs.

## Required structure for every section

Each section must include:

- measurable prerequisites and learning objectives;
- concise concept lessons with plain-language explanations;
- a visual or tabular model where it materially improves understanding;
- executable SQL examples and the expected result or verification method;
- guided practice followed by independent practice;
- knowledge checks with explanations for correct and incorrect answers;
- a mini-project with a business brief, deliverables, acceptance criteria,
  hints, a solution, and a self-assessment rubric;
- a section summary and a readiness checkpoint.

Answers must not be visible before the learner attempts a question unless the
learner deliberately reveals them.

## Learning-method coverage

The same important concept must be available through multiple modes:

- **Read:** concise explanation and vocabulary.
- **See:** diagram, annotated query, table, or before/after result.
- **Do:** runnable query and graduated practice.
- **Explain:** prediction, debugging, or teach-back prompt.
- **Apply:** realistic business question and project deliverable.

Accessibility requirements include keyboard navigation, semantic headings,
visible focus, sufficient contrast, useful alternative text, responsive layout,
and no learning interaction that depends only on color.

## Practice database requirements

The repository must contain reproducible setup and reset scripts, realistic
seed data, a data dictionary, and verified reference queries. A learner must be
able to start from an empty local MySQL installation and reproduce every lesson
result. Destructive statements must be clearly marked and use a safe practice
schema.

## Assessment and job-readiness gates

Completion requires all of the following:

- diagnostic starting assessment;
- section knowledge checks and 13 section mini-projects;
- cumulative assessments at beginner, intermediate, and advanced milestones;
- a final capstone using a larger, imperfect dataset;
- capstone brief, stakeholder questions, SQL deliverables, QA checklist,
  README/report template, solution, and scoring rubric;
- timed SQL interview practice and explained solutions;
- portfolio publishing guidance and a job-application readiness checklist;
- a final assessment threshold based on demonstrated skills, not lesson clicks.

## Accuracy and verification gates

- All setup and solution SQL executes successfully on the documented MySQL
  version from a clean database.
- Displayed expected results match the seeded data.
- Every assessment answer and explanation is reviewed for correctness.
- Every explicit topic above is mapped to at least one lesson and one assessed
  task.
- Automated checks verify required section components, internal links, source
  assets, and curriculum coverage.
- A manual usability pass verifies desktop, mobile, keyboard, answer reveal,
  progress persistence, and reset behavior.

## Current-state audit — 2026-07-05

The browser build now contains 13 segments and 98 generated textbook sections.
Each section ends with three interactive knowledge checks and one rubric-based
mini-project with a deliberately hidden reference solution. The repository also
contains reproducible baseline setup/reset SQL, a learner data dictionary, three
cumulative assessments, a larger imperfect capstone dataset and reference
solution, five timed interview prompts, portfolio guidance, an application
readiness gate, and a workplace guide covering requirements, permissions,
parameterization, transactions, set operations, and dialect differences.

The course shell also links a learner-facing `sql-mastery-guide.html` page,
created from the themes in the saved long-form SQL/data analyst videos. It
maps the course to a zero-to-job-ready path, distinguishes analyst-critical SQL
from optional advanced database objects, and gives learners a repeatable
practice loop for projects, validation, and portfolio evidence.

Segment 11 now goes deeper on data cleaning, based on current data-quality
practice: data-quality dimensions, raw/staging/clean layers, SQL equivalents
of generic tests (`not_null`, `unique`, `accepted_values`, `relationships`),
relationship failure checks, safe deduplication with `ROW_NUMBER`, cleaning
logs, reconciliation, freshness, and distribution checks.

The lesson builder now adds an explanation layer to every lesson: learning
goal, why the topic matters, prior-knowledge connection, query plain-English
translation, result grain, clause walkthrough, verification method, and a
predict-then-try prompt. Non-query topics receive a mental-model panel with a
core idea, concrete example, and explain-it-back question.

`audit_course.py` enforces these artifacts and currently passes. Python and
JavaScript syntax checks also pass. The baseline, advanced audit queries,
capstone setup, capstone reference solution, views, reconciliation, and indexes
were executed successfully against a clean disposable MySQL 8.4.10 instance;
the durable evidence is recorded in `VERIFICATION.md`.
