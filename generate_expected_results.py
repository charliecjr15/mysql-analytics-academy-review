"""Capture exact result sets for complete read-only course queries on MySQL 8."""
from __future__ import annotations

from hashlib import sha256
from html import unescape
from pathlib import Path
import argparse
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parent

def result_key(segment_number: int, sql: str) -> str:
    normalized = "\n".join(line.rstrip() for line in unescape(sql).strip().splitlines())
    return f"{segment_number}:{sha256(normalized.encode()).hexdigest()}"

def complete_read_query(sql: str) -> bool:
    text = unescape(sql).strip()
    if not re.match(r"(?is)^(SELECT\b|WITH\s+[a-z_]\w*\s+AS\s*\(|EXPLAIN\b|SHOW\s+INDEX\b|DESCRIBE\b)", text):
        return False
    if text.count(";") > 1 or not text.rstrip().endswith(";"):
        return False
    forbidden = ("...", "TABLE_NAME", "TABLE_1", "TABLE_2", "COLUMN_", "GROUP_COLUMN", "AGGREGATE_FUNCTION", "RESULT_NAME", "CONDITION_ON_")
    return not any(token in text.upper() for token in forbidden)

def run(mysql: list[str], database: str, sql: str) -> dict:
    proc = subprocess.run(mysql + [database, "-e", sql], text=True, capture_output=True)
    if proc.returncode:
        message = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "MySQL rejected the statement."
        return {"kind": "error", "message": message}
    lines = proc.stdout.splitlines()
    if not lines:
        return {"kind": "rows", "columns": [], "rows": [], "row_count": 0}
    columns = lines[0].split("\t")
    rows = [line.split("\t") for line in lines[1:]]
    return {"kind": "rows", "columns": columns, "rows": rows[:12], "row_count": len(rows), "truncated": len(rows) > 12}

def apply_course_state(mysql: list[str], segment_number: int, sql: str) -> None:
    """Replay persistent view/index statements that affect later lesson output."""
    text = unescape(sql).strip()
    if segment_number == 12 and re.match(r"(?is)^(CREATE(?:\s+OR\s+REPLACE)?\s+VIEW|DROP\s+VIEW)\b", text):
        subprocess.run(mysql + ["course_audit", "-e", text], text=True, capture_output=True)
    if segment_number == 13 and re.match(r"(?is)^(CREATE\s+INDEX|DROP\s+INDEX)\b", text):
        subprocess.run(mysql + ["course_audit", "-e", text], text=True, capture_output=True)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    parser.add_argument("--user", default="root")
    args = parser.parse_args()
    mysql = ["mysql", "--no-defaults", "--batch", "--raw", f"--socket={args.socket}", f"-u{args.user}"]
    payload = (ROOT / "source-lessons.js").read_text(encoding="utf-8")
    segments = json.loads(payload.removeprefix("window.SOURCE_SEGMENTS = ").removesuffix(";\n"))
    results = {}
    attempted = 0
    for segment_number, segment in enumerate(segments, 1):
        database = "coffee_shop" if segment_number <= 6 else "course_audit"
        for lesson in segment["lessons"]:
            for encoded in re.findall(r"<pre><code>(.*?)</code></pre>", lesson["body"], re.S):
                sql = unescape(encoded).strip()
                if not complete_read_query(sql):
                    apply_course_state(mysql, segment_number, sql)
                    continue
                attempted += 1
                results[result_key(segment_number, sql)] = run(mysql, database, sql)
    (ROOT / "expected-results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Captured {len(results)} unique expected results from {attempted} complete read-only examples.")

if __name__ == "__main__":
    main()
