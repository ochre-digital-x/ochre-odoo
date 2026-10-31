"""End to end tests: real MCP server (stdio and hosted HTTP) against a mock Odoo.

Run:  pip install -e server && python3 tests/test_e2e.py
"""
import asyncio
import json
import os
import socket
import subprocess
import sys
import threading
import time
from xmlrpc.server import SimpleXMLRPCServer

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "legacy_module")
DATA = {"res.partner": [{"id": 1, "name": "Acme", "email": "a@acme.in"},
                        {"id": 2, "name": "Beta", "email": "b@beta.in"}],
        "ir.model": [{"id": 1, "model": "res.partner", "name": "Contact"}]}
GOOD = ("demo", "admin@x.in", "KEY")


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def start_mock_odoo():
    port = free_port()
    srv = SimpleXMLRPCServer(("127.0.0.1", port), allow_none=True, logRequests=False)
    srv.RequestHandlerClass.rpc_paths = ("/xmlrpc/2/common", "/xmlrpc/2/object")

    def authenticate(db, u, k, ctx): return 7 if (db, u, k) == GOOD else False
    def version(): return {"server_version": "19.0"}

    def execute_kw(db, uid, key, model, method, args, kw):
        if (db, key) != (GOOD[0], GOOD[2]):
            raise Exception("AccessDenied")
        if method == "search_read":
            rows = DATA.get(model, [])
            return [{k: r[k] for k in (kw.get("fields") or r)} for r in rows][: kw.get("limit", 80)]
        if method == "search_count": return len(DATA.get(model, []))
        if method == "fields_get": return {"name": {"string": "Name", "type": "char"},
                                           "email": {"string": "Email", "type": "char"}}
        if method == "create": return 99
        if method == "write": return True
        raise Exception("unsupported " + method)

    for f in (authenticate, version, execute_kw):
        srv.register_function(f)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}"


def module_files():
    out = {}
    for root, _, files in os.walk(FIXTURE):
        for f in files:
            p = os.path.join(root, f)
            out[os.path.relpath(p, FIXTURE)] = open(p).read()
    return json.dumps(out)


async def exercise(session):
    await session.initialize()
    tools = sorted(t.name for t in (await session.list_tools()).tools)

    async def call(name, **a):
        res = await session.call_tool(name, a)
        return json.loads(res.content[0].text)

    return tools, {
        "info": await call("odoo_server_info"),
        "models": await call("odoo_list_models", search="partner"),
        "fields": await call("odoo_model_fields", model="res.partner"),
        "search": await call("odoo_search_read", model="res.partner", fields='["name"]'),
        "count": await call("odoo_count", model="res.partner"),
        "create": await call("odoo_create", model="res.partner", values='{"name":"New"}'),
        "bad_json": await call("odoo_count", model="res.partner", domain="[oops"),
        "lint_files": await call("odoo_v19_lint", files=module_files()),
        "lint_path": await call("odoo_v19_lint", module_path=FIXTURE),
    }


async def run_stdio(odoo_url, allow_write):
    env = dict(os.environ, ODOO_URL=odoo_url, ODOO_DB=GOOD[0], ODOO_USERNAME=GOOD[1],
               ODOO_API_KEY=GOOD[2], ODOO_ALLOW_WRITE=allow_write)
    params = StdioServerParameters(command="ochre-odoo-mcp", args=[], env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            return await exercise(s)


async def run_http(endpoint, headers):
    async with streamablehttp_client(endpoint, headers=headers) as (r, w, _):
        async with ClientSession(r, w) as s:
            return await exercise(s)


def start_http_server(allow_private, extra_env=None):
    port = free_port()
    env = dict(os.environ, PORT=str(port), HOST="127.0.0.1",
               OCHRE_ALLOW_PRIVATE_TARGETS="true" if allow_private else "false", **(extra_env or {}))
    proc = subprocess.Popen(["ochre-odoo-mcp", "--transport", "http"], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    return proc, f"http://127.0.0.1:{port}/mcp"


def headers(url, write="false", key=GOOD[2]):
    return {"X-Odoo-Url": url, "X-Odoo-Db": GOOD[0], "X-Odoo-Username": GOOD[1],
            "Authorization": f"Bearer {key}", "X-Odoo-Allow-Write": write}


def main():
    odoo = start_mock_odoo()
    checks = {}

    # Local stdio mode
    tools, ro = asyncio.run(run_stdio(odoo, "false"))
    _, rw = asyncio.run(run_stdio(odoo, "true"))
    lint_ids = {f["check"] for f in ro["lint_path"]["findings"]}
    expected = {"V19-SQL-CONSTRAINTS", "V19-USERS-GROUPS-ID", "V19-PRODUCT-UOM",
                "V19-TAX-ID", "V19-KANBAN-BOX", "V19-REGISTRY-IMPORT"}
    checks.update({
        "stdio: 10 tools": len(tools) == 10,
        "stdio: auth + version": ro["info"].get("uid") == 7 and ro["info"]["mode"] == "local",
        "stdio: search honours fields": ro["search"]["records"] == [{"name": "Acme"}, {"name": "Beta"}],
        "stdio: count": ro["count"]["count"] == 2,
        "stdio: write blocked by default": "disabled" in ro["create"].get("error", ""),
        "stdio: write allowed when enabled": rw["create"].get("id") == 99,
        "stdio: bad JSON gives clear error": "Invalid JSON" in ro["bad_json"].get("error", ""),
        "stdio: lint by path": lint_ids >= expected,
        "stdio: lint by files": {f["check"] for f in ro["lint_files"]["findings"]} >= expected,
    })

    # Hosted HTTP mode, server env holds DIFFERENT credentials that must never be used
    proc, ep = start_http_server(True, {"ODOO_URL": odoo, "ODOO_DB": "demo",
                                        "ODOO_USERNAME": "admin@x.in", "ODOO_API_KEY": "KEY"})
    try:
        tools_h, h = asyncio.run(run_http(ep, headers(odoo)))
        _, hw = asyncio.run(run_http(ep, headers(odoo, write="true")))
        _, wrong = asyncio.run(run_http(ep, headers(odoo, key="WRONG")))
        _, none = asyncio.run(run_http(ep, {}))
        import urllib.request
        health = json.load(urllib.request.urlopen(ep.replace("/mcp", "/health")))
    finally:
        proc.terminate()
    checks.update({
        "http: 10 tools": len(tools_h) == 10,
        "http: auth from headers": h["info"].get("uid") == 7 and h["info"]["mode"] == "hosted",
        "http: search": h["search"]["count"] == 2,
        "http: write blocked by default": "disabled" in h["create"].get("error", ""),
        "http: write allowed by header": hw["create"].get("id") == 99,
        "http: wrong key rejected": "rejected" in wrong["info"].get("error", ""),
        "http: never falls back to server env creds": "Missing" in none["info"].get("error", ""),
        "http: lint by files": {f["check"] for f in h["lint_files"]["findings"]} >= expected,
        "http: lint by path refused": "cannot read your disk" in h["lint_path"].get("error", ""),
        "http: health endpoint": health.get("status") == "ok",
    })

    # Hosted HTTP mode with production guards: private targets and plain http blocked
    proc, ep = start_http_server(False)
    try:
        _, g1 = asyncio.run(run_http(ep, headers(odoo)))
        _, g2 = asyncio.run(run_http(ep, headers("https://127.0.0.1:8069")))
        _, g3 = asyncio.run(run_http(ep, headers("https://169.254.169.254")))
    finally:
        proc.terminate()
    checks.update({
        "guard: plain http refused": "https" in g1["info"].get("error", ""),
        "guard: loopback refused": "private" in g2["info"].get("error", ""),
        "guard: cloud metadata address refused": "private" in g3["info"].get("error", ""),
    })

    for k, v in checks.items():
        print(("PASS  " if v else "FAIL  ") + k)
    print(f"\n{sum(checks.values())}/{len(checks)} passed")
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
