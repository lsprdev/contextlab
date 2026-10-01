import io
import json
import os
from pathlib import Path
import sys

import pytest

from contextlab.adapters import (CODEX_FLAGS, CODEX_DISABLED, doctor_agent,
                                parse_native, run_agent, _claude_command, _redact)
from contextlab.broker import ContextBroker
from contextlab.mcp_server import StdioServer


def lines(*events):
    return "\n".join(json.dumps(e) for e in events)


def test_codex_does_not_accept_unknown_tools_or_partial_success():
    completed = {"type": "turn.completed", "usage": {"input_tokens": 4, "output_tokens": 3}}
    answer = json.dumps({"test_code": "def test_a(): assert 1"})
    assert parse_native("codex", lines(completed), answer)["status"] == "completed"
    for item in ({"type": "command_execution"}, {"type": "file_change"},
                 {"type": "mcp_tool_call", "server": "other", "tool": "read_file"},
                 {"type": "new_unknown_tool"}):
        parsed = parse_native("codex", lines({"type": "item.started", "item": item}, completed), answer)
        assert parsed["status"] == "protocol_violation"
        assert parsed["response"] is None
    assert parse_native("codex", "", answer)["status"] == "infrastructure_error"
    with pytest.raises(ValueError, match="JSONL"):
        parse_native("codex", "CLI banner", answer)


def test_claude_audits_advertised_and_called_tools():
    result = {"type": "result", "subtype": "success", "is_error": False,
              "structured_output": {"test_code": "def test_a(): assert 1"},
              "usage": {"input_tokens": 1, "output_tokens": 2}, "total_cost_usd": 0.01}
    init = {"type": "system", "subtype": "init", "tools": ["mcp__contextlab__read_file", "StructuredOutput"]}
    assert parse_native("claude", lines(init, result))["status"] == "completed"
    init["tools"].append("Bash")
    assert parse_native("claude", lines(init, result))["status"] == "protocol_violation"
    tool = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "WebFetch"}]}}
    assert parse_native("claude", lines(tool, result))["status"] == "protocol_violation"
    result["structured_output"]["extra"] = 1
    assert parse_native("claude", lines(result))["status"] == "protocol_violation"


def test_claude_has_no_builtins_and_exact_server_configuration():
    command = _claude_command("claude", "pinned-model", Path("/tmp/contextlab-mcp.json"))
    assert command[command.index("--tools") + 1] == ""
    assert "--bare" in command and "--restricted" in command
    assert "--strict-mcp-config" in command and "--no-session-persistence" in command
    assert not any("skip-permissions" in option for option in command)


def test_mcp_only_returns_snapshot_content_and_stops_at_budget(tmp_path):
    audit = tmp_path / "audit.json"
    server = StdioServer(ContextBroker({"safe.py": "x = 1\n"}, 1000, max_calls=2), audit)
    source = io.StringIO(lines(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "../../secret"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "safe.py"}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "safe.py"}}},
    ))
    output = io.StringIO()
    server.serve(source, output)
    responses = [json.loads(line) for line in output.getvalue().splitlines()]
    assert [r["id"] for r in responses] == [1, 2, 3, 4]
    assert [t["name"] for t in responses[1]["result"]["tools"]] == ["list_files", "read_file", "search"]
    assert responses[2]["result"]["isError"]
    assert "x = 1" in responses[3]["result"]["content"][0]["text"]
    state = json.loads(audit.read_text())
    assert state["terminal_limit"] == "ToolLimitExceeded"
    assert state["stats"]["tool_calls"] == 2


@pytest.fixture
def fake_codex(tmp_path):
    """Executable transport fixture; deliberately never calls a model."""
    path = tmp_path / "fake-codex"
    script = f"""#!{sys.executable}
import json, os, subprocess, sys, time
from pathlib import Path
args = sys.argv[1:]
if '--version' in args:
    print('codex-cli test-fixture')
elif '--help' in args:
    print({repr(' '.join(CODEX_FLAGS))})
elif 'features' in args:
    for name in {repr(CODEX_DISABLED)}: print(name, 'stable false')
else:
    model = args[args.index('--model') + 1]
    if model == 'fixture-timeout': time.sleep(5)
    if model == 'fixture-auth':
        assert 'CODEX_API_KEY' not in os.environ
        auth_root = Path(os.environ['CODEX_HOME'])
        assert set(p.name for p in auth_root.iterdir()) == {{'auth.json'}}
        (auth_root / 'auth.json').write_text(json.dumps({{'access_token': 'fixture-refreshed-token'}}))
    settings = dict(args[i+1].split('=', 1) for i, val in enumerate(args[:-1]) if val == '-c')
    cmd = [json.loads(settings['mcp_servers.contextlab.command'])] + json.loads(settings['mcp_servers.contextlab.args'])
    events = [{{'jsonrpc':'2.0','id':1,'method':'initialize','params':{{'protocolVersion':'2025-06-18'}}}},
              {{'jsonrpc':'2.0','id':2,'method':'tools/call','params':{{'name':'read_file','arguments':{{'path':'safe.py'}}}}}}]
    subprocess.run(cmd, input='\\n'.join(json.dumps(e) for e in events)+'\\n', text=True, capture_output=True, check=True)
    if model == 'fixture-limit': time.sleep(5)
    answer = {{'test_code': 'def test_x(): assert True\\n'}}
    Path(args[args.index('--output-last-message')+1]).write_text(json.dumps(answer))
    print(json.dumps({{'type':'thread.started','thread_id':'fixture-session'}}))
    if model == 'fixture-forbidden':
        print(json.dumps({{'type':'item.started','item':{{'type':'command_execution'}}}}))
    print(json.dumps({{'type':'turn.completed','usage':{{'input_tokens':11,'output_tokens':8}}}}))
    print('diagnostic ' + os.environ.get('CODEX_API_KEY',''), file=sys.stderr)
"""
    path.write_text(script)
    path.chmod(0o755)
    return path


@pytest.mark.parametrize("enabled_feature", [None, "unified_exec"])
def test_doctor_creates_private_home_and_keeps_feature_rejection(fake_codex, monkeypatch, enabled_feature):
    monkeypatch.setenv("CODEX_API_KEY", "fixture-not-a-real-credential")
    script = fake_codex.read_text()
    script = script.replace("elif 'features' in args:\n", "elif 'features' in args:\n    assert Path(os.environ['CODEX_HOME']).is_dir()\n")
    if enabled_feature:
        script = script.replace("print(name, 'stable false')", "print(name, 'stable', 'true' if name == 'unified_exec' else 'false')")
    fake_codex.write_text(script)
    result = doctor_agent({"kind": "codex", "model": "fixture-ok", "binary": str(fake_codex)})
    assert result["ready"] is (enabled_feature is None)
    assert result["isolation_verified"] is False
    if enabled_feature:
        assert "Cannot verify disabled Codex features: unified_exec" in result["details"]


def test_native_lifecycle_and_redaction(fake_codex, tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_API_KEY", "sk-dummy-secret-not-a-real-key")
    agent = {"kind": "codex", "model": "fixture-ok", "binary": str(fake_codex)}
    assert doctor_agent(agent)["ready"]
    context = {"files": {"safe.py": "x = 1\n"}, "text": ""}
    limits = {"context_chars": 1000, "tool_calls": 5, "generation_seconds": 5}
    result = run_agent(agent, "Generate a test", context, tmp_path / "run", limits)
    assert result["status"] == "completed"
    assert result["response"].startswith("def test_x")
    assert result["input_tokens"] == 11
    assert result["tool_log"][0]["tool"] == "read_file"
    stderr = (tmp_path / "run" / "stderr.txt").read_text()
    assert "sk-dummy" not in stderr and "[REDACTED]" in stderr
    agent["model"] = "fixture-forbidden"
    assert run_agent(agent, "Generate", context, tmp_path / "forbidden", limits)["status"] == "protocol_violation"


def test_native_limits_stop_process(fake_codex, tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_API_KEY", "sk-dummy-secret-not-a-real-key")
    agent = {"kind": "codex", "model": "fixture-limit", "binary": str(fake_codex)}
    context = {"files": {"safe.py": "x = 1\n"}, "text": ""}
    limits = {"context_chars": 1, "tool_calls": 5, "generation_seconds": 3}
    result = run_agent(agent, "Generate", context, tmp_path / "limited", limits)
    assert result["status"] == "limit" and result["response"] is None
    assert result["seconds"] < 3
    agent["model"] = "fixture-timeout"
    limits["generation_seconds"] = 0.1
    result = run_agent(agent, "Generate", context, tmp_path / "timeout", limits)
    assert result["status"] == "timeout" and result["response"] is None


def test_doctor_missing_binary_is_not_ready(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert not doctor_agent({"kind": "claude", "model": "x", "binary": "/does/not/exist"})["ready"]
    assert _redact("secret abcdefghijkl", ["abcdefghijkl"]) == "secret [REDACTED]"


def test_oauth_reuses_only_auth_file_and_preserves_refresh(fake_codex, tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_API_KEY", "sk-other-auth-must-not-be-selected")
    credentials = tmp_path / "private" / "auth.json"
    credentials.parent.mkdir()
    credentials.write_text(json.dumps({"access_token": "fixture-original-token"}))
    (credentials.parent / "config.toml").write_text("private instructions")
    agent = {"kind": "codex", "model": "fixture-auth", "binary": str(fake_codex),
             "auth_file": str(credentials)}
    result = run_agent(agent, "Generate", {"files": {"safe.py": "x=1"}, "text": ""},
                       tmp_path / "oauth-run", {"context_chars": 1000, "tool_calls": 5, "generation_seconds": 5})
    assert result["status"] == "completed"
    assert json.loads(credentials.read_text())["access_token"] == "fixture-refreshed-token"
    assert credentials.stat().st_mode & 0o777 == 0o600
    assert (credentials.parent / "config.toml").read_text() == "private instructions"
    agent["auth_file"] = str(tmp_path / "absent.json")
    assert not doctor_agent(agent)["ready"]


@pytest.mark.parametrize("failure", [KeyboardInterrupt, ValueError])
def test_interruption_or_unexpected_error_stops_native_process_before_cleanup(tmp_path, monkeypatch, failure):
    from contextlab import adapters

    class InterruptedProcess:
        returncode = None
        calls = 0

        def communicate(self, *_args, **_kwargs):
            assert self.cwd.exists()
            self.calls += 1
            if self.calls == 1:
                raise failure()
            return "", ""

        def poll(self):
            return self.returncode

    proc = InterruptedProcess()
    stopped = []

    def start(*_args, **kwargs):
        proc.cwd = kwargs["cwd"]
        return proc

    def stop(process):
        stopped.append(process)
        process.returncode = -9

    monkeypatch.setattr(adapters, "doctor_agent", lambda _agent: {
        "ready": True, "version": "test-fixture", "binary": "/fake/never-executed"})
    monkeypatch.setattr(adapters.subprocess, "Popen", start)
    monkeypatch.setattr(adapters, "_stop", stop)
    args = ({"kind": "codex", "model": "fixture"}, "Generate",
            {"files": {"safe.py": "x=1"}, "text": ""}, tmp_path / "run",
            {"context_chars": 1000, "tool_calls": 5, "generation_seconds": 5})
    if failure is KeyboardInterrupt:
        with pytest.raises(KeyboardInterrupt):
            run_agent(*args)
    else:
        assert run_agent(*args)["status"] == "infrastructure_error"
    assert stopped == [proc]
    assert proc.calls == 2
    assert not proc.cwd.exists()
