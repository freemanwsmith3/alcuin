"""Generate fake relational data via LLM and persist to SQLite."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from anthropic import Anthropic

_client = Anthropic()

_SYSTEM = """\
You are a data generator. Given a description, produce a JSON object with:

{
  "tables": [
    {
      "name": "TableName",
      "columns": ["col1", "col2", ...],
      "rows": [[val1, val2, ...], ...]
    }
  ],
  "relationships": [
    {
      "name": "REL_NAME",
      "from_table": "TableName",
      "from_col": "col",
      "to_table": "TableName",
      "to_col": "col",
      "pairs": [[from_val, to_val], ...]
    }
  ]
}

Rules:
- Generate realistic data (20-30 rows per table)
- Every table must have an "id" column as first column with unique integer values
- Relationships must reference valid id values from their tables
- Output ONLY valid JSON, no markdown, no explanation
"""


def generate(prompt: str, user_id: str) -> dict:
    """Ask the LLM to generate fake data, store in SQLite, return parsed schema."""
    response = _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0].strip()
    data = json.loads(raw)

    db_path = _db_path(user_id)
    _write_sqlite(data, db_path)

    return data


def load(user_id: str) -> dict | None:
    """Load previously generated data from SQLite."""
    db_path = _db_path(user_id)
    if not db_path.exists():
        return None

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    tables = []
    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '_%'"):
        table_name = row["name"]
        cursor = conn.execute(f"SELECT * FROM \"{table_name}\"")
        columns = [d[0] for d in cursor.description]
        rows = [list(r) for r in cursor.fetchall()]
        tables.append({"name": table_name, "columns": columns, "rows": rows})
    conn.close()
    return {"tables": tables}


def _db_path(user_id: str) -> Path:
    base = Path(os.environ.get("GRAPH_DATA_DIR", "/tmp/alcuin_graph"))
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{user_id}.db"


def _write_sqlite(data: dict, path: Path) -> None:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    for table in data["tables"]:
        cols = ", ".join(f'"{c}" TEXT' for c in table["columns"])
        conn.execute(f'CREATE TABLE "{table["name"]}" ({cols})')
        placeholders = ", ".join("?" * len(table["columns"]))
        conn.executemany(
            f'INSERT INTO "{table["name"]}" VALUES ({placeholders})',
            [list(map(str, row)) for row in table["rows"]],
        )
    conn.commit()
    conn.close()
