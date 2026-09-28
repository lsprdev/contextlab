"""Read-only tools over an in-memory snapshot, with one delivery budget.

No filesystem path is opened here. All JSON response characters, including
errors and repeated reads, count; an oversized response is never partly sent.
"""
from __future__ import annotations

import json
from typing import Any

from .context import ContextError, _clean_path


class BudgetExceeded(RuntimeError):
    """No response can be delivered within the frozen character budget."""


class ToolLimitExceeded(RuntimeError):
    """The frozen maximum number of tool calls has been exhausted."""


TOOL_DEFINITIONS = [
    {"name": "list_files", "description": "List permitted virtual files under an optional directory prefix.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "additionalProperties": False}},
    {"name": "read_file", "description": "Read permitted virtual file lines. Line numbers start at 1 in the virtual file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "start_line": {"type": "integer", "minimum": 1}, "end_line": {"type": "integer", "minimum": 1}}, "required": ["path"], "additionalProperties": False}},
    {"name": "search", "description": "Case-sensitive literal search in permitted files. No regex or shell syntax is executed.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string", "minLength": 1}, "path": {"type": "string"}}, "required": ["query"], "additionalProperties": False}},
]


class ContextBroker:
    def __init__(self, files: dict[str, str], budget: int, initial_text: str = "", max_calls: int = 100):
        if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
            raise ValueError("budget must be a positive integer")
        if isinstance(max_calls, bool) or not isinstance(max_calls, int) or max_calls < 1:
            raise ValueError("max_calls must be a positive integer")
        if len(initial_text) > budget:
            raise BudgetExceeded("Initial context exceeds the character budget")
        self.files = dict(sorted(files.items()))
        for path, content in self.files.items():
            _clean_path(path)
            if not isinstance(content, str):
                raise ValueError("Virtual file contents must be strings")
        self.budget = budget
        self.max_calls = max_calls
        self.chars_used = len(initial_text)
        self.initial_chars = len(initial_text)
        self.tool_calls = 0
        self._exhausted = False
        self.log: list[dict[str, Any]] = []

    @property
    def stats(self) -> dict[str, int]:
        return {"chars_used": self.chars_used, "initial_chars": self.initial_chars,
                "response_chars": self.chars_used - self.initial_chars,
                "remaining_chars": self.budget - self.chars_used, "tool_calls": self.tool_calls,
                "max_calls": self.max_calls, "budget": self.budget}

    @staticmethod
    def _prefix(arguments: dict[str, Any]) -> str:
        prefix = arguments.get("path", "")
        if prefix in {"", "."}:
            return ""
        return _clean_path(prefix)

    def _paths(self, prefix: str) -> list[str]:
        return [path for path in self.files if not prefix or path == prefix or path.startswith(prefix.rstrip("/") + "/")]

    def _result(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        accepted = {"list_files": {"path"}, "read_file": {"path", "start_line", "end_line"}, "search": {"query", "path"}}
        if name not in accepted:
            raise ValueError("Unknown tool; only list_files, read_file and search are permitted")
        if set(arguments) - accepted[name]:
            raise ValueError("Unsupported tool arguments")
        if name == "list_files":
            return {"files": self._paths(self._prefix(arguments))}
        if name == "read_file":
            path = _clean_path(arguments.get("path", ""))
            if path not in self.files:
                raise ValueError("File is not in the permitted snapshot")
            lines = self.files[path].splitlines(keepends=True)
            start = arguments.get("start_line", 1)
            end = arguments.get("end_line", max(1, len(lines)))
            if any(isinstance(value, bool) or not isinstance(value, int) for value in [start, end]) or start < 1 or end < start:
                raise ValueError("Line bounds must be positive integers with end_line >= start_line")
            return {"path": path, "start_line": start, "end_line": min(end, len(lines)), "content": "".join(lines[start - 1:end])}
        query = arguments.get("query")
        if not isinstance(query, str) or not query or len(query) > 512:
            raise ValueError("query must be a literal string containing 1 to 512 characters")
        matches = []
        # A bounded response protects memory; the delivered JSON still consumes
        # the same budget. Truncation is explicit and whole lines are preserved.
        for path in self._paths(self._prefix(arguments)):
            for number, line in enumerate(self.files[path].splitlines(), 1):
                if query in line:
                    if len(matches) == 200:
                        return {"matches": matches, "truncated": True, "limit": 200}
                    matches.append({"path": path, "line": number, "text": line})
        return {"matches": matches, "truncated": False, "limit": 200}

    def call(self, name: str, arguments: dict[str, Any]) -> str:
        """Return the exact text charged to the delivery budget.

        Budget/tool exhaustion raises a terminal exception; adapters must stop
        without sending an uncharged substitute response to the model.
        """
        entry: dict[str, Any] = {"index": self.tool_calls + 1, "tool": name, "arguments": arguments,
                                 "delivered_chars": 0, "chars_before": self.chars_used}
        if self._exhausted:
            entry.update(status="budget_exhausted", chars_after=self.chars_used)
            self.log.append(entry)
            raise BudgetExceeded("A prior response exhausted this generation's budget")
        if self.tool_calls >= self.max_calls:
            entry.update(status="tool_limit", chars_after=self.chars_used)
            self.log.append(entry)
            raise ToolLimitExceeded("Tool call limit reached")
        self.tool_calls += 1
        try:
            if not isinstance(arguments, dict):
                raise ValueError("Tool arguments must be an object")
            result = self._result(name, arguments)
            entry["status"] = "ok"
        except (ContextError, ValueError, TypeError) as exc:
            result = {"error": str(exc)}
            entry["status"] = "denied"
        text = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if self.chars_used + len(text) > self.budget:
            self._exhausted = True
            entry.update(status="budget_exceeded", requested_chars=len(text), chars_after=self.chars_used)
            self.log.append(entry)
            raise BudgetExceeded("Tool response would exceed the remaining character budget")
        self.chars_used += len(text)
        entry.update(delivered_chars=len(text), chars_after=self.chars_used)
        self.log.append(entry)
        return text
