"""Anthropic tool definitions and executor for graph operations."""
from __future__ import annotations

import logging

from app.graph import builder, generator

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "name": "generate_graph_data",
        "description": (
            "Generate fake relational data based on a natural language description. "
            "Creates realistic tables with rows and relationships between them. "
            "Use this when the user wants to create, explore, or demo a knowledge graph."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Description of the dataset to generate, e.g. 'A tech company with employees, departments, and projects'",
                }
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "build_knowledge_graph",
        "description": (
            "Build a queryable knowledge graph from the previously generated data. "
            "Must be called after generate_graph_data. "
            "Returns node and edge counts once the graph is ready."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def execute(tool_name: str, tool_input: dict, user_id: str) -> dict:
    """Execute a graph tool and return a serialisable result dict."""
    try:
        if tool_name == "generate_graph_data":
            schema = generator.generate(tool_input["prompt"], user_id)
            return {
                "success": True,
                "tables": len(schema["tables"]),
                "rows": sum(len(t["rows"]) for t in schema["tables"]),
                "table_names": [t["name"] for t in schema["tables"]],
                "schema": schema,
            }

        if tool_name == "build_knowledge_graph":
            schema = generator.load(user_id)
            if schema is None:
                return {"success": False, "error": "No data found. Generate data first."}
            graph = builder.build(user_id, schema)
            return {
                "success": True,
                "nodes": len(graph["nodes"]),
                "edges": len(graph["edges"]),
                "graph": graph,
                "schema": schema,
            }

        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.error("tool_execute_error", extra={"tool": tool_name, "error": str(e)})
        return {"success": False, "error": str(e)}
