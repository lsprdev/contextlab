import copy
import json

import pytest

from contextlab.codex_policy import MCP_TOOLS, RESOURCE_TOOLS, verify_registry


def registry_body():
    namespaces = {}
    for namespace, names in (("functions", RESOURCE_TOOLS), ("mcp__contextlab", MCP_TOOLS)):
        source = {"kind": "harness"} if namespace == "functions" else {"kind": "mcp", "server_name": "contextlab"}
        namespaces[namespace] = {"functions": {name: {"direct": True, "deferred": False,
            "code_mode_name": None, "source": source} for name in names}}
    return namespaces


def body(namespaces):
    return {"client_metadata": {"x-codex-turn-metadata": json.dumps({"tool_namespaces_info": namespaces})}}


def test_exact_registry_and_missing_metadata():
    assert len(verify_registry(body(registry_body()))) == 6
    with pytest.raises(ValueError):
        verify_registry({})


@pytest.mark.parametrize("extra", ["exec_command", "apply_patch", "view_image", "exec"])
def test_forbidden_builtins_are_rejected(extra):
    registry = registry_body()
    registry["functions"]["functions"][extra] = copy.deepcopy(registry["functions"]["functions"]["list_mcp_resources"])
    with pytest.raises(ValueError):
        verify_registry(body(registry))


@pytest.mark.parametrize("change", ["other_server", "missing_tool", "code_mode", "deferred", "namespace"])
def test_registry_cannot_hide_or_redirect_tools(change):
    registry = registry_body()
    tools = registry["mcp__contextlab"]["functions"]
    if change == "other_server":
        tools["read_file"]["source"] = {"kind": "mcp", "server_name": "outside"}
    elif change == "missing_tool":
        del tools["read_file"]
    elif change == "code_mode":
        tools["read_file"]["code_mode_name"] = "mcp__contextlab__read_file"
    elif change == "deferred":
        tools["read_file"]["deferred"] = True
    else:
        registry["collaboration"] = {"functions": {}}
    with pytest.raises(ValueError):
        verify_registry(body(registry))
