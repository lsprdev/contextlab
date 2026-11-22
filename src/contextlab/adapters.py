"""Native CLI adapters. Tool mediation is separate from the evaluation process.

Compatibility checks are necessary, not a proof of isolation: the frozen study
must also record an adversarial pilot for the exact CLI/model configuration.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any

TOOLS = ("list_files", "read_file", "search")
OUTPUT_SCHEMA = {"type": "object", "properties": {"test_code": {"type": "string"}},
                 "required": ["test_code"], "additionalProperties": False}
CODEX_DISABLED = ("shell_tool", "unified_exec", "apps", "multi_agent", "memories",
                  "hooks", "goals", "shell_snapshot", "remote_plugin",
                  "skill_mcp_dependency_install", "view_image", "browser_use",
                  "browser_use_external", "computer_use", "image_generation",
                  "plugins", "skill_search", "sleep_tool")
CLAUDE_FLAGS = ("--bare", "--restricted", "--tools", "--strict-mcp-config",
                "--no-session-persistence", "--json-schema", "--setting-sources",
                "--permission-mode", "--mcp-config", "--output-format")
CODEX_FLAGS = ("--json", "--ephemeral", "--ignore-user-config", "--output-schema",
               "--sandbox", "--skip-git-repo-check", "--output-last-message")


def _redact(value: str, secrets: list[str]) -> str:
    for secret in sorted(set(secrets), key=len, reverse=True):
        if len(secret) >= 8:
            value = value.replace(secret, "[REDACTED]")
    value = re.sub(r"\bsk-[A-Za-z0-9_-]{12,}", "[REDACTED]", value)
    return re.sub(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[REDACTED]", value)


def _credential_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [s for v in value.values() for s in _credential_strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _credential_strings(v)]
    return [value] if isinstance(value, str) and len(value) >= 12 else []


def _environment(private: Path, kind: str) -> dict[str, str]:
    # Child-only environment: do not inherit application keys, Python startup
    # hooks, plugins, NODE_OPTIONS, provider overrides or the user's configs.
    env = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT",
                                    "SSL_CERT_FILE", "SSL_CERT_DIR") if k in os.environ}
    env.update(HOME=str(private), USERPROFILE=str(private),
               XDG_CONFIG_HOME=str(private / "config"),
               XDG_CACHE_HOME=str(private / "cache"),
               CODEX_HOME=str(private / "codex"),
               CLAUDE_CONFIG_DIR=str(private / "claude"),
               NO_COLOR="1")
    credential = "CODEX_API_KEY" if kind == "codex" else "ANTHROPIC_API_KEY"
    if os.environ.get(credential):
        env[credential] = os.environ[credential]
    return env


def _probe(command: list[str], env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True,
                          timeout=15, check=False)


def doctor_agent(agent: dict) -> dict:
    """Read local CLI capabilities without calling a model or logging in."""
    kind = agent.get("kind")
    if kind not in {"codex", "claude"}:
        return {"ready": False, "version": None, "details": "Unsupported native agent kind."}
    binary = shutil.which(str(agent.get("binary", kind)))
    credential = "CODEX_API_KEY" if kind == "codex" else "ANTHROPIC_API_KEY"
    auth_file = agent.get("auth_file") if kind == "codex" else None
    auth_ready = bool(Path(auth_file).expanduser().is_file()) if auth_file else bool(os.environ.get(credential))
    result = {"ready": False, "binary": binary, "version": None,
              "auth_ready": auth_ready, "missing_flags": [], "details": []}
    if not binary:
        result["details"].append(f"Install {kind} CLI; executable was not found.")
        return result
    try:
        with tempfile.TemporaryDirectory(prefix="contextlab-doctor-") as temp:
            private = Path(temp)
            env = _environment(private, kind)
            Path(env["CODEX_HOME" if kind == "codex" else "CLAUDE_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)
            # Doctor does not need credentials even if a CLI changes behavior.
            env.pop(credential, None)
            version = _probe([binary, "--version"], env, private)
            if version.returncode:
                raise ValueError("CLI --version failed")
            result["version"] = version.stdout.strip()[:200]
            help_command = [binary, "exec", "--help"] if kind == "codex" else [binary, "--help"]
            help_result = _probe(help_command, env, private)
            if help_result.returncode:
                raise ValueError("CLI help failed")
            required = CODEX_FLAGS if kind == "codex" else CLAUDE_FLAGS
            result["missing_flags"] = [flag for flag in required if flag not in help_result.stdout]
            if kind == "codex":
                command = [binary]
                for feature in CODEX_DISABLED:
                    command += ["--disable", feature]
                feature_result = _probe(command + ["features", "list"], env, private)
                states = {}
                for line in feature_result.stdout.splitlines():
                    fields = line.split()
                    if len(fields) >= 2:
                        states[fields[0]] = fields[-1].lower()
                # Some catalogs force the unified-exec *implementation* on even
                # when shell_tool is off. Verify the actual tool registry below.
                missing = [name for name in CODEX_DISABLED
                           if name != "unified_exec" and states.get(name) != "false"]
                if feature_result.returncode or missing:
                    result["details"].append("Cannot verify disabled Codex features: " + ", ".join(missing))
                if not result["missing_flags"] and not result["details"] and agent.get("model") and not str(agent["model"]).startswith("SUBSTITUA_"):
                    from .codex_policy import probe_tools
                    result["capabilities"] = probe_tools(binary, agent["model"], private, env)
            if not auth_ready:
                result["details"].append(f"Configure {credential}" +
                    (" or an explicit protected auth_file." if kind == "codex" else "; --bare does not use subscription OAuth."))
            if not agent.get("model") or str(agent.get("model", "")).startswith("SUBSTITUA_"):
                result["details"].append("Set an explicit model identifier.")
            result["ready"] = not result["missing_flags"] and not result["details"]
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        result["details"].append(type(exc).__name__ + ": " + str(exc))
    result["isolation_verified"] = False
    return result


def _mcp_config(packet: Path, audit: Path) -> dict:
    # Launch this package with the same interpreter; no repository-controlled
    # Python imports or arbitrary shell launcher are accepted.
    launcher = Path(__file__).with_name("mcp_server.py")
    return {"command": sys.executable,
            "args": ["-I", str(launcher), "--packet", str(packet), "--audit", str(audit)]}


def _codex_command(binary: str, model: str, workspace: Path, schema: Path,
                   final: Path, mcp: dict, catalog: Path, reasoning_effort: str | None = None) -> list[str]:
    command = [binary, "exec", "--json", "--ephemeral", "--ignore-user-config",
               "--skip-git-repo-check", "--sandbox", "read-only", "--model", model,
               "--output-schema", str(schema), "--output-last-message", str(final),
               "--cd", str(workspace)]
    settings: dict[str, Any] = {
        "approval_policy": "never", "web_search": "disabled", "project_doc_max_bytes": 0,
        "cli_auth_credentials_store": "file",
        "project_doc_fallback_filenames": [], "model_catalog_json": str(catalog),
        "agents.enabled": False, "features.multi_agent_v2.enabled": False,
        "skills.bundled.enabled": False, "skills.include_instructions": False,
        "tools.experimental_request_user_input.enabled": False,
        "features.tool_registry.turn_metadata_includes_tool_info": True,
        "features.code_mode.enabled": False, "features.context_management.experimental_mode": False,
        "browser_use.allow_history_access": False,
        "browser_use.default_origin_policy.access": "deny", "computer_use.default_app_access": "deny",
        "mcp_servers.contextlab.command": mcp["command"],
        "mcp_servers.contextlab.args": mcp["args"],
        "mcp_servers.contextlab.required": True,
        "mcp_servers.contextlab.enabled_tools": list(TOOLS),
        "mcp_servers.contextlab.default_tools_approval_mode": "approve",
    }
    if reasoning_effort:
        # A configuração do usuário é ignorada (--ignore-user-config): o esforço vem só do manifesto.
        settings["model_reasoning_effort"] = reasoning_effort
    settings.update({"features." + name: False for name in CODEX_DISABLED})
    for key, value in settings.items():
        command += ["-c", key + "=" + json.dumps(value, ensure_ascii=False)]
    return command + ["-"]


def _claude_command(binary: str, model: str, mcp_file: Path) -> list[str]:
    return [binary, "--print", "--bare", "--restricted", "--tools", "",
            "--strict-mcp-config", "--mcp-config", str(mcp_file), "--setting-sources", "",
            "--no-session-persistence", "--permission-mode", "dontAsk",
            "--allowedTools", ",".join("mcp__contextlab__" + t for t in TOOLS),
            "--model", model, "--output-format", "stream-json", "--verbose",
            "--json-schema", json.dumps(OUTPUT_SCHEMA)]


def parse_native(kind: str, raw: str, final_text: str | None = None) -> dict:
    """Fail closed on malformed output, unknown tool events or forbidden calls."""
    events = []
    for line in raw.splitlines():
        if line.strip():
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("Native output is not valid JSONL") from exc
            if not isinstance(event, dict):
                raise ValueError("Native event is not an object")
            events.append(event)
    usage: dict = {}
    violations: list[str] = []
    response = None
    completed = False
    failed = False
    session_id = None
    for event in events:
        if kind == "codex":
            event_type = event.get("type")
            if event_type not in {"thread.started", "turn.started", "turn.completed",
                                  "turn.failed", "error", "item.started", "item.updated", "item.completed"}:
                violations.append("Unexpected Codex event: " + str(event_type))
            if event_type == "thread.started":
                session_id = event.get("thread_id")
            elif event_type == "turn.completed":
                completed = True
                usage = event.get("usage", {})
            elif event_type in {"turn.failed", "error"}:
                failed = True
            if str(event_type).startswith("item."):
                item = event.get("item", {})
                item_type = item.get("type")
                if item_type == "mcp_tool_call":
                    if item.get("server") != "contextlab" or item.get("tool") not in TOOLS:
                        violations.append("MCP outside ContextLab allowlist")
                elif item_type not in {"agent_message", "reasoning", "todo_list"}:
                    violations.append("Unexpected Codex item: " + str(item_type))
                elif item_type == "agent_message" and event_type == "item.completed":
                    response = item.get("text")
        else:
            if event.get("type") not in {"system", "assistant", "user", "result", "rate_limit_event"}:
                violations.append("Unexpected Claude event: " + str(event.get("type")))
            if event.get("type") == "system" and event.get("subtype") not in {"init", "status", "compact_boundary"}:
                violations.append("Unexpected Claude system event: " + str(event.get("subtype")))
            if event.get("type") == "system" and event.get("subtype") == "init":
                session_id = event.get("session_id")
                listed = event.get("tools", [])
                allowed = {"mcp__contextlab__" + t for t in TOOLS} | {"StructuredOutput", "EndConversation"}
                if any(t not in allowed for t in listed):
                    violations.append("Claude advertised tools outside ContextLab allowlist")
                if any(p for p in event.get("plugins", [])):
                    violations.append("Claude loaded plugins")
            if event.get("type") == "assistant":
                for content in event.get("message", {}).get("content", []):
                    if content.get("type") == "tool_use":
                        name = content.get("name")
                        allowed = {"mcp__contextlab__" + t for t in TOOLS} | {"StructuredOutput", "EndConversation"}
                        if name not in allowed:
                            violations.append("Unexpected Claude tool: " + str(name))
            if event.get("type") == "result":
                completed = event.get("subtype") == "success" and not event.get("is_error", False)
                failed = not completed
                usage = event.get("usage", {})
                if "total_cost_usd" in event:
                    usage["total_cost_usd"] = event["total_cost_usd"]
                response = event.get("structured_output", event.get("result"))
    if kind == "codex" and final_text is not None:
        response = final_text
    if violations:
        return {"status": "protocol_violation", "response": None, "usage": usage,
                "details": violations, "session_id": session_id}
    if failed or not completed:
        return {"status": "infrastructure_error", "response": None, "usage": usage,
                "details": ["Native session did not complete successfully."], "session_id": session_id}
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            response = None
    if not isinstance(response, dict) or set(response) != {"test_code"} or not isinstance(response["test_code"], str):
        return {"status": "protocol_violation", "response": None, "usage": usage,
                "details": ["Final response must be exactly {test_code: string}."], "session_id": session_id}
    return {"status": "completed", "response": response["test_code"], "usage": usage,
            "details": [], "session_id": session_id}


def _stop(proc: subprocess.Popen) -> None:
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        proc.kill()


def run_agent(agent: dict, prompt: str, context: dict, output_dir: Path, limits: dict) -> dict:
    """Run one fresh CLI trajectory; never execute or repair its returned test."""
    started = time.monotonic()
    result = {"status": "infrastructure_error", "response": None,
              "input_tokens": None, "output_tokens": None, "seconds": 0.0,
              "version": None, "tool_log": [], "usage": {}, "details": []}
    readiness = doctor_agent(agent)
    result["version"] = readiness.get("version")
    if not readiness.get("ready"):
        result["details"] = ["CLI compatibility/authentication preflight failed", readiness]
        result["seconds"] = time.monotonic() - started
        return result
    kind = agent["kind"]
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    secrets = [os.environ[k] for k in ("CODEX_API_KEY", "ANTHROPIC_API_KEY") if os.environ.get(k)]
    try:
        with tempfile.TemporaryDirectory(prefix="contextlab-agent-") as temp:
            private = Path(temp)
            workspace = private / "workspace"
            workspace.mkdir()
            env = _environment(private / "home", kind)
            Path(env["HOME"]).mkdir()
            auth_source = Path(agent["auth_file"]).expanduser().resolve() if kind == "codex" and agent.get("auth_file") else None
            auth_copy = Path(env["CODEX_HOME"]) / "auth.json"
            original_auth_hash = None
            if auth_source:
                env.pop("CODEX_API_KEY", None)  # Explicit auth_file wins over an ambient API key.
                original = auth_source.read_bytes()
                original_auth_hash = hashlib.sha256(original).hexdigest()
                secrets.extend(_credential_strings(json.loads(original)))
                auth_copy.parent.mkdir(parents=True)
                auth_copy.write_bytes(original)
                auth_copy.chmod(0o600)
            packet = private / "context.json"
            packet.write_text(json.dumps({"files": context["files"], "initial_text": context.get("text", ""),
                "context_chars": limits["context_chars"], "tool_calls": limits["tool_calls"]}, ensure_ascii=False), encoding="utf-8")
            audit = private / "tool_audit.json"
            schema = private / "schema.json"
            schema.write_text(json.dumps(OUTPUT_SCHEMA), encoding="utf-8")
            final = private / "final.json"
            mcp = _mcp_config(packet, audit)
            if kind == "codex":
                from .codex_policy import prepare_catalog
                catalog, catalog_hash = prepare_catalog(readiness["binary"], agent["model"], private, env)
                if catalog_hash != readiness["capabilities"]["catalog_sha256"]:
                    raise ValueError("Codex model catalog changed after capability verification")
                result["capabilities"] = readiness["capabilities"]
                command = _codex_command(readiness["binary"], agent["model"], workspace, schema, final, mcp, catalog,
                                         agent.get("reasoning_effort"))
            else:
                mcp_file = private / "mcp.json"
                mcp_file.write_text(json.dumps({"mcpServers": {"contextlab": mcp}}), encoding="utf-8")
                command = _claude_command(readiness["binary"], agent["model"], mcp_file)
            proc = subprocess.Popen(command, cwd=workspace, env=env, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                start_new_session=(os.name == "posix"))
            timeout = False
            terminal_limit = None
            deadline = time.monotonic() + limits["generation_seconds"]
            stdin_text = prompt
            try:
                while True:
                    try:
                        raw, stderr = proc.communicate(stdin_text, timeout=min(0.1, max(0.001, deadline - time.monotonic())))
                        break
                    except subprocess.TimeoutExpired:
                        stdin_text = None  # communicate continues buffering on retry.
                        if audit.is_file():
                            terminal_limit = json.loads(audit.read_text(encoding="utf-8")).get("terminal_limit")
                        timeout = time.monotonic() >= deadline
                        if terminal_limit or timeout:
                            _stop(proc)
                            raw, stderr = proc.communicate()
                            break
            except KeyboardInterrupt:
                _stop(proc)
                proc.communicate()
                raise
            finally:
                # Stop the CLI and its MCP child before removing their temporary
                # files, including on unexpected parser/I/O errors in the loop.
                if proc.poll() is None:
                    _stop(proc)
                    proc.communicate()
            # Only auth.json is reused, never history, instructions, MCP config
            # or cached context. Avoid overwriting a concurrently refreshed file.
            if auth_source and auth_copy.is_file() and original_auth_hash:
                refreshed = auth_copy.read_bytes()
                secrets.extend(_credential_strings(json.loads(refreshed)))
                if hashlib.sha256(auth_source.read_bytes()).hexdigest() == original_auth_hash:
                    fd, pending = tempfile.mkstemp(prefix=".contextlab-auth-", dir=auth_source.parent)
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(refreshed)
                    os.replace(pending, auth_source)
            (output_dir / "native.jsonl").write_text(_redact(raw, secrets), encoding="utf-8")
            (output_dir / "stderr.txt").write_text(_redact(stderr, secrets), encoding="utf-8")
            result["returncode"] = proc.returncode
            if audit.is_file():
                state = json.loads(audit.read_text(encoding="utf-8"))
                result["tool_log"] = state.get("log", [])
                result["context_stats"] = state.get("stats", {})
                (output_dir / "tool_audit.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                state = {}
            terminal_limit = terminal_limit or state.get("terminal_limit")
            if terminal_limit:
                result.update(status="limit", response=None, details=[terminal_limit])
            elif timeout:
                result.update(status="timeout", details=["Generation wall-clock limit exceeded."])
            elif proc.returncode:
                result["details"] = ["Native CLI failed; inspect redacted stderr.txt."]
            else:
                final_text = final.read_text(encoding="utf-8") if final.is_file() else None
                result.update(parse_native(kind, raw, final_text))
                if result["status"] == "completed" and not state.get("initialized"):
                    result.update(status="infrastructure_error", response=None,
                                  details=["Required context MCP server did not initialize."])
            usage = result.get("usage", {})
            # Cache counters remain separate: providers use different accounting.
            result["input_tokens"] = usage.get("input_tokens")
            result["output_tokens"] = usage.get("output_tokens")
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        result.update(status="infrastructure_error", response=None,
                      details=[_redact(type(exc).__name__ + ": " + str(exc), secrets)])
    result["seconds"] = time.monotonic() - started
    return result
