"""Shared helpers for the Vercel Python functions in this directory.

Prefixed with an underscore so Vercel's zero-config Python routing does not
turn this file into an endpoint of its own.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler

# Make the existing macd-divergence-mcp/src package importable so the web
# API reuses the exact same strategy/indicator logic as the MCP server,
# instead of a second, drifting implementation.
_MCP_PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "macd-divergence-mcp")
if _MCP_PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _MCP_PROJECT_ROOT)


class JSONHandler(BaseHTTPRequestHandler):
    """Base handler with a helper for writing a JSON response with CORS
    headers, so each endpoint only needs to implement do_GET."""

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        # Silence BaseHTTPRequestHandler's default stderr access logging;
        # Vercel already captures function invocation logs.
        pass
