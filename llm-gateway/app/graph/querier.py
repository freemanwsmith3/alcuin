"""Translate natural language questions to Cypher and query KuzuDB."""
from __future__ import annotations

import logging

from anthropic import Anthropic

from app.graph.builder import get_connection

_client = Anthropic()
logger = logging.getLogger(__name__)


def query(question: str, user_id: str, schema: dict) -> str | None:
    """Return a text answer by translating question → Cypher → KuzuDB result."""
    result = get_connection(user_id)
    if result is None:
        return None
    conn, _db = result  # keep _db alive so conn stays valid

    schema_desc = _describe_schema(schema)

    cypher = _to_cypher(question, schema_desc)
    if not cypher:
        logger.warning("graph_query_no_cypher", extra={"question": question[:100]})
        return None

    try:
        result = conn.execute(cypher)
        rows = []
        while result.has_next():
            rows.append(result.get_next())
        if not rows:
            return "No results found in the graph for that question."
        return _rows_to_answer(question, rows)
    except Exception as e:
        logger.warning("graph_query_execute_failed", extra={"cypher": cypher, "error": str(e)})
        return None


def _to_cypher(question: str, schema_desc: str) -> str | None:
    response = _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=512,
        system=f"""\
You are a Cypher query generator for KuzuDB. Given a schema and a question,
output ONLY a valid Cypher query with no explanation or markdown.

Schema:
{schema_desc}

STRICT rules:
- ALWAYS include a node label in every MATCH clause: MATCH (n:NodeLabel) not MATCH (n)
- Use only node/relationship names exactly as listed in the schema above
- Property access: n.property_name
- No APOC, no Neo4j-specific functions
- For general questions like "show me everything", pick the most relevant node table and return all rows
- LIMIT results to 20 rows maximum
""",
        messages=[{"role": "user", "content": question}],
    )
    cypher = response.content[0].text.strip()
    if cypher.startswith("```"):
        cypher = cypher.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return cypher if cypher.upper().startswith("MATCH") else None


def _rows_to_answer(question: str, rows: list) -> str:
    rows_text = "\n".join(str(r) for r in rows[:20])
    response = _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=512,
        system="Convert these query results into a clear, concise natural language answer.",
        messages=[{"role": "user", "content": f"Question: {question}\n\nResults:\n{rows_text}"}],
    )
    return response.content[0].text.strip()


def _describe_schema(schema: dict) -> str:
    lines = []
    for table in schema.get("tables", []):
        lines.append(f"Node: {table['name']} — properties: {', '.join(table['columns'])}")
    for rel in schema.get("relationships", []):
        lines.append(f"Relationship: (:{rel['from_table']})-[:{rel['name']}]->(:{rel['to_table']})")
    return "\n".join(lines)
