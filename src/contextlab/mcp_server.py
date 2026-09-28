"""Minimal MCP stdio transport for ContextBroker (no filesystem tool).

Launched with ``python -I .../mcp_server.py`` by the native CLI. Only this trusted
launcher loads the packet; model-supplied paths never reach the filesystem.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import TextIO

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contextlab.broker import ContextBroker, TOOL_DEFINITIONS, BudgetExceeded, ToolLimitExceeded


class StdioServer:
    def __init__(self, broker: ContextBroker, audit: Path):
        self.broker = broker
        self.audit = audit
        self.initialized = False
        self.terminal_limit: str | None = None
        self._save()

    def _save(self) -> None:
        state = {"initialized": self.initialized, "terminal_limit": self.terminal_limit,
                 "stats": self.broker.stats, "log": self.broker.log}
        pending = self.audit.with_suffix(".pending")
        pending.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        os.replace(pending, self.audit)

    def dispatch(self, message: dict) -> dict | None:
        request_id = message.get("id")
        method = message.get("method")
        if request_id is None:
            return None  # Notifications never receive JSON-RPC responses.
        response = {"jsonrpc": "2.0", "id": request_id}
        if message.get("jsonrpc") != "2.0" or not isinstance(method, str):
            return {**response, "error": {"code": -32600, "message": "Invalid request"}}
        params = message.get("params", {})
        if not isinstance(params, dict):
            return {**response, "error": {"code": -32602, "message": "Invalid params"}}
        if method == "initialize":
            requested = params.get("protocolVersion")
            supported = {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}
            self.initialized = True
            self._save()
            result = {"protocolVersion": requested if requested in supported else "2025-06-18",
                      "capabilities": {"tools": {}},
                      "serverInfo": {"name": "contextlab", "version": "0.1.0"}}
        elif method == "ping":
            result = {}
        elif not self.initialized:
            return {**response, "error": {"code": -32002, "message": "Not initialized"}}
        elif method == "tools/list":
            result = {"tools": [{"name": tool["name"], "description": tool["description"],
                                  "inputSchema": tool["input_schema"],
                                  "annotations": {"readOnlyHint": True, "destructiveHint": False,
                                                  "openWorldHint": False}}
                                 for tool in TOOL_DEFINITIONS]}
        elif method == "tools/call":
            try:
                text = self.broker.call(params.get("name", ""), params.get("arguments", {}))
            except (BudgetExceeded, ToolLimitExceeded) as exc:
                self.terminal_limit = type(exc).__name__
                self._save()
                # Do not substitute a free error response after budget exhaustion.
                # The orchestrator observes this state and terminates the CLI.
                raise
            self._save()
            result = {"content": [{"type": "text", "text": text}],
                      "isError": "error" in json.loads(text)}
        elif method in {"resources/list", "resources/templates/list", "prompts/list"}:
            result = {"resources/list": {"resources": []},
                      "resources/templates/list": {"resourceTemplates": []},
                      "prompts/list": {"prompts": []}}[method]
        else:
            return {**response, "error": {"code": -32601, "message": "Method not found"}}
        return {**response, "result": result}

    def serve(self, source: TextIO, destination: TextIO) -> None:
        for line in source:
            try:
                message = json.loads(line)
                if not isinstance(message, dict):
                    raise ValueError("Object expected")
                result = self.dispatch(message)
            except (ValueError, json.JSONDecodeError):
                result = {"jsonrpc": "2.0", "id": None,
                          "error": {"code": -32700, "message": "Parse error"}}
            except (BudgetExceeded, ToolLimitExceeded):
                break
            if result is not None:
                destination.write(json.dumps(result, ensure_ascii=False) + "\n")
                destination.flush()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    # The trusted server has no provider calls and never needs inherited auth.
    for name in list(os.environ):
        if any(part in name for part in ("TOKEN", "API_KEY", "SECRET", "PASSWORD")):
            os.environ.pop(name, None)
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    broker = ContextBroker(packet["files"], packet["context_chars"],
                           initial_text=packet.get("initial_text", ""),
                           max_calls=packet["tool_calls"])
    StdioServer(broker, args.audit).serve(sys.stdin, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
