"""Build a KuzuDB graph from the generated SQLite data."""
from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path

import kuzu


def build(user_id: str, schema: dict) -> dict:
    """Build KuzuDB from schema dict returned by generator. Returns nodes+edges for viz."""
    kuzu_path = _kuzu_path(user_id)
    if kuzu_path.exists():
        shutil.rmtree(kuzu_path)

    db = kuzu.Database(str(kuzu_path))
    conn = kuzu.Connection(db)

    # Create node tables
    for table in schema["tables"]:
        cols = ", ".join(
            f"{c} INT64" if c == "id" else f"{c} STRING"
            for c in table["columns"]
        )
        conn.execute(f"CREATE NODE TABLE {table['name']}({cols}, PRIMARY KEY(id))")
        for row in table["rows"]:
            props = ", ".join(f"{c}: {_val(c, v)}" for c, v in zip(table["columns"], row))
            conn.execute(f"MERGE (:{table['name']} {{{props}}})")

    # Create relationship tables
    for rel in schema.get("relationships", []):
        conn.execute(
            f"CREATE REL TABLE {rel['name']}(FROM {rel['from_table']} TO {rel['to_table']})"
        )
        for from_val, to_val in rel["pairs"]:
            conn.execute(
                f"MATCH (a:{rel['from_table']} {{id: {from_val}}}), "
                f"(b:{rel['to_table']} {{id: {to_val}}}) "
                f"MERGE (a)-[:{rel['name']}]->(b)"
            )

    return _export_graph(conn, schema)


def load_graph(user_id: str, schema: dict) -> dict | None:
    """Load existing KuzuDB and export as nodes/edges."""
    kuzu_path = _kuzu_path(user_id)
    if not kuzu_path.exists():
        return None
    db = kuzu.Database(str(kuzu_path))
    conn = kuzu.Connection(db)
    return _export_graph(conn, schema)


def get_connection(user_id: str) -> tuple[kuzu.Connection, kuzu.Database] | None:
    kuzu_path = _kuzu_path(user_id)
    if not kuzu_path.exists():
        return None
    db = kuzu.Database(str(kuzu_path))
    return kuzu.Connection(db), db


def _export_graph(conn: kuzu.Connection, schema: dict) -> dict:
    nodes, edges = [], []
    for table in schema["tables"]:
        name = table["name"]
        result = conn.execute(f"MATCH (n:{name}) RETURN n")
        while result.has_next():
            row = result.get_next()
            node = row[0]
            props = {k: str(v) for k, v in node.items()}
            label = props.get("name") or props.get("title") or props.get("id", "?")
            nodes.append({"id": f"{name}_{props['id']}", "label": label, "group": name, "properties": props})

    for rel in schema.get("relationships", []):
        result = conn.execute(
            f"MATCH (a:{rel['from_table']})-[r:{rel['name']}]->(b:{rel['to_table']}) "
            f"RETURN a.id, b.id"
        )
        while result.has_next():
            row = result.get_next()
            edges.append({
                "source": f"{rel['from_table']}_{row[0]}",
                "target": f"{rel['to_table']}_{row[1]}",
                "label": rel["name"],
            })

    return {"nodes": nodes, "edges": edges}


def _val(col: str, v) -> str:
    return str(v) if col == "id" else f'"{str(v).replace(chr(34), chr(39))}"'


def _kuzu_path(user_id: str) -> Path:
    base = Path(os.environ.get("GRAPH_DATA_DIR", "/tmp/alcuin_graph"))
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{user_id}_kuzu"
