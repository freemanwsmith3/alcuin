"""Anthropic tool definition and executor for camera operations."""
from __future__ import annotations

import logging

from app.camera import analyzer

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "name": "analyze_camera",
        "description": (
            "Capture a live snapshot from the camera and analyze it with computer vision. "
            "Use this to answer questions about what the camera currently sees, "
            "or to take measurements of things visible in the frame."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": (
                        "What to analyze or measure. For numeric measurements be explicit: "
                        "e.g. 'Estimate what percentage of the jar is filled with sourdough starter. "
                        "Return JSON: {\"value\": <0-100>, \"unit\": \"pct\", \"label\": \"jar fill\", \"notes\": \"<observations>\"}'. "
                        "For general queries: 'Describe what you see.'"
                    ),
                }
            },
            "required": ["question"],
        },
    }
]


def execute(tool_name: str, tool_input: dict, user_id: str) -> dict:
    if tool_name != "analyze_camera":
        return {"success": False, "error": f"Unknown camera tool: {tool_name}"}
    try:
        image = analyzer.fetch_snapshot()
        return analyzer.analyze(image, tool_input.get("question", "Describe what you see"))
    except Exception as e:
        logger.error("camera_tool_error", extra={"error": str(e)})
        return {"success": False, "error": str(e)}
