"""Constrain native Codex capabilities and probe the real registry offline.

The localhost provider is a diagnostic fixture, never an experimental agent.
It receives no credentials, project sources, or user prompts.
"""
from __future__ import annotations

import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import subprocess
import threading

MCP_TOOLS = {"list_files", "read_file", "search"}
# Codex always adds these helpers. Our sole MCP server lists no resources or
# templates and refuses resources/read; none provides another content channel.
RESOURCE_TOOLS = {"list_mcp_resources", "list_mcp_resource_templates", "read_mcp_resource"}


def prepare_catalog(binary: str, model: str, private: Path, env: dict) -> tuple[Path, str]:
    result = subprocess.run([binary, "debug", "models", "--bundled"], cwd=private, env=env,
                            capture_output=True, text=True, timeout=15, check=True)
    catalog = json.loads(result.stdout)
    selected = next((m for m in catalog["models"] if m["slug"] == model), None)
    if selected is None:
        raise ValueError(f"Model {model} is absent from the bundled Codex catalog")
    # Retain model identity, instructions and inference defaults. Only the
    # native tool surface changes, uniformly across the experimental arms.
    selected.update(tool_mode="standard", multi_agent_version="v1",
                    apply_patch_tool_type=None, experimental_supported_tools=[],
                    supports_search_tool=False)
    data = json.dumps({"models": [selected]}, sort_keys=True, ensure_ascii=False).encode()
    path = private / "restricted-models.json"
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


def verify_registry(body: dict) -> list[str]:
    metadata = json.loads(body.get("client_metadata", {}).get("x-codex-turn-metadata", "{}"))
    registry = metadata.get("tool_namespaces_info")
    if not isinstance(registry, dict) or set(registry) != {"functions", "mcp__contextlab"}:
        raise ValueError("Unexpected or missing Codex tool namespaces")
    names = []
    for namespace, expected in (("functions", RESOURCE_TOOLS), ("mcp__contextlab", MCP_TOOLS)):
        functions = registry[namespace]["functions"]
        if set(functions) != expected:
            raise ValueError(f"Unexpected or missing Codex tools in {namespace}")
        for name, tool in functions.items():
            source = tool.get("source", {})
            valid_source = (source == {"kind": "harness"} if namespace == "functions"
                            else source == {"kind": "mcp", "server_name": "contextlab"})
            if not valid_source or tool.get("direct") is not True or tool.get("deferred") is not False or tool.get("code_mode_name") is not None:
                raise ValueError("Unexpected Codex tool routing")
            names.append(namespace + "." + name)
    return sorted(names)


def probe_tools(binary: str, model: str, private: Path, env: dict) -> dict:
    from .adapters import OUTPUT_SCHEMA, _codex_command, _mcp_config

    catalog, catalog_hash = prepare_catalog(binary, model, private, env)
    workspace = private / "probe-workspace"
    workspace.mkdir()
    packet = private / "probe-packet.json"
    packet.write_text(json.dumps({"files": {"allowed.py": "VALUE = 7\n"}, "initial_text": "",
                                  "context_chars": 2000, "tool_calls": 5}))
    audit = private / "probe-audit.json"
    schema = private / "probe-schema.json"
    schema.write_text(json.dumps(OUTPUT_SCHEMA))
    requests = []
    sentinel = private / "forbidden-write"
    outside = private / "outside-packet.txt"
    outside.write_text("CONTEXTLAB_PRIVATE_CANARY")
    calls = [
        ("functions", "exec_command", {"cmd": "touch " + str(sentinel)}),
        ("mcp__contextlab", "read_file", {"path": str(outside)}),
        ("mcp__contextlab", "read_file", {"path": "allowed.py"}),
    ]

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(body)
            answer = json.dumps({"test_code": "# offline capability probe"})
            item = {"id": "msg_probe", "type": "message", "role": "assistant", "status": "completed",
                    "content": [{"type": "output_text", "text": answer, "annotations": []}]}
            index = len(requests) - 1
            if index < len(calls):
                namespace, name, arguments = calls[index]
                item = {"type": "function_call", "id": f"fc_{index}", "call_id": f"call_{index}",
                        "namespace": namespace, "name": name, "arguments": json.dumps(arguments), "status": "completed"}
            events = [
                {"type": "response.created", "response": {"id": "resp_probe", "status": "in_progress", "output": []}},
                {"type": "response.output_item.added", "output_index": 0, "item": item},
                {"type": "response.output_item.done", "output_index": 0, "item": item},
                {"type": "response.completed", "response": {"id": "resp_probe", "status": "completed", "output": [item],
                     "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}}},
            ]
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for event in events:
                self.wfile.write(("event: " + event["type"] + "\ndata: " + json.dumps(event) + "\n\n").encode())

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        command = _codex_command(binary, model, workspace, schema, private / "probe-final.json",
                                 _mcp_config(packet, audit), catalog)
        settings = {
            "model_provider": "contextlab_probe",
            "model_providers.contextlab_probe.name": "Offline ContextLab capability probe",
            "model_providers.contextlab_probe.base_url": f"http://127.0.0.1:{server.server_port}/v1",
            "model_providers.contextlab_probe.wire_api": "responses",
            "model_providers.contextlab_probe.requires_openai_auth": False,
            "model_providers.contextlab_probe.request_max_retries": 0,
            "model_providers.contextlab_probe.stream_max_retries": 0,
            "features.enable_request_compression": False,
        }
        for key, value in settings.items():
            command[-1:-1] = ["-c", key + "=" + json.dumps(value)]
        result = subprocess.run(command, cwd=workspace, env=env, input="Return the requested JSON object.",
                                text=True, capture_output=True, timeout=20, check=True)
        if len(requests) != len(calls) + 1:
            raise ValueError("Codex capability probe did not complete the adversarial calls")
        for body in requests:
            names = verify_registry(body)
        events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        if any(e.get("type") in {"error", "turn.failed"} or e.get("item", {}).get("type") == "error" for e in events):
            raise ValueError("Codex reported a configuration error during capability probe")
        state = json.loads(audit.read_text())
        if not state.get("initialized"):
            raise ValueError("ContextLab MCP did not initialize during capability probe")
        outputs = {item.get("call_id"): item.get("output") for body in requests
                   for item in body.get("input", []) if item.get("type") == "function_call_output"}
        if sentinel.exists() or outputs.get("call_0") != "unsupported call: exec_command":
            raise ValueError("Codex did not reject the forbidden command tool")
        if (len(state["log"]) != 2 or "Path escapes the project" not in str(outputs.get("call_1", ""))
                or "CONTEXTLAB_PRIVATE_CANARY" in json.dumps(outputs) or "VALUE = 7" not in str(outputs.get("call_2", ""))):
            raise ValueError("Codex MCP boundary probe failed")
        return {"tool_surface_verified": True, "tools": names, "catalog_sha256": catalog_hash,
                "probe": "offline-localhost", "model": model,
                "command_rejected": True, "outside_packet_rejected": True, "allowed_read_verified": True}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
