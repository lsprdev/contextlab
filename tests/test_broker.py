import json

import pytest

from contextlab.broker import BudgetExceeded, ContextBroker, ToolLimitExceeded


def test_initial_context_and_every_repeated_response_are_charged():
    broker = ContextBroker({"module.py": "α = 1\n"}, 2000, initial_text="abc")
    first = broker.call("read_file", {"path": "module.py"})
    second = broker.call("read_file", {"path": "module.py"})
    assert first == second
    assert broker.stats["chars_used"] == 3 + len(first) + len(second)
    assert broker.stats["tool_calls"] == 2
    assert sum(item["delivered_chars"] for item in broker.log) == len(first) * 2


def test_denied_reads_are_charged_and_cannot_escape_snapshot():
    broker = ContextBroker({"allowed.py": "okay"}, 3000)
    for path in ["../secret", "/etc/passwd", "allowed.py/../../secret", "outside.py"]:
        response = broker.call("read_file", {"path": path})
        assert "error" in json.loads(response)
        assert broker.log[-1]["status"] == "denied"
    assert broker.stats["chars_used"] == sum(item["delivered_chars"] for item in broker.log)


def test_budget_never_partially_delivers_or_refills():
    broker = ContextBroker({"file.py": "hello"}, 20, initial_text="a" * 19)
    with pytest.raises(BudgetExceeded):
        broker.call("read_file", {"path": "file.py"})
    assert broker.stats["chars_used"] == 19
    assert broker.log[-1]["delivered_chars"] == 0
    assert broker.log[-1]["status"] == "budget_exceeded"
    with pytest.raises(BudgetExceeded):
        broker.call("list_files", {})
    assert broker.log[-1]["status"] == "budget_exhausted"
    with pytest.raises(BudgetExceeded):
        ContextBroker({}, 2, initial_text="abc")


def test_limit_stops_further_calls():
    broker = ContextBroker({}, 1000, max_calls=1)
    broker.call("list_files", {})
    with pytest.raises(ToolLimitExceeded):
        broker.call("list_files", {})
    assert broker.stats["tool_calls"] == 1


def test_literal_search_lines_and_scoped_listing_are_deterministic():
    broker = ContextBroker({"z.py": "x\n", "p/b.py": "alpha.*\nbeta\n", "p/a.py": "alpha\n"}, 3000)
    assert json.loads(broker.call("list_files", {"path": "p"}))["files"] == ["p/a.py", "p/b.py"]
    result = json.loads(broker.call("search", {"query": ".*"}))
    assert result["matches"] == [{"path": "p/b.py", "line": 1, "text": "alpha.*"}]
    read = json.loads(broker.call("read_file", {"path": "p/b.py", "start_line": 2, "end_line": 2}))
    assert read["content"] == "beta\n"


def test_unknown_tools_and_malformed_arguments_are_denied():
    broker = ContextBroker({"m.py": "data"}, 3000)
    for name, args in [("exec", {"cmd": "pwd"}), ("read_file", {"path": "m.py", "start_line": True}), ("search", {"query": ""}), ("list_files", {"cmd": "ls"}), ("search", [])]:
        assert "error" in json.loads(broker.call(name, args))


def test_local_virtual_snippets_do_not_unlock_original_file():
    broker = ContextBroker({"deps.py::L4-L6": "def visible():\n    return 1\n"}, 3000)
    assert "error" in json.loads(broker.call("read_file", {"path": "deps.py"}))
    assert "visible" in broker.call("read_file", {"path": "deps.py::L4-L6"})


def test_snapshot_is_copied_and_search_truncation_is_explicit():
    files = {"many.py": "match\n" * 202}
    broker = ContextBroker(files, 40000)
    files["secret.py"] = "secret"
    assert "secret.py" not in broker.files
    result = json.loads(broker.call("search", {"query": "match"}))
    assert len(result["matches"]) == 200 and result["truncated"]
