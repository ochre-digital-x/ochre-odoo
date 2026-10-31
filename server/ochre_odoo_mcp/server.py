"""Ochre Odoo MCP server.

Two ways to run:

1. Hosted (streamable HTTP). One public endpoint serves many users. Each
   request carries that user's own Odoo credentials in headers. The server
   stores nothing and never uses its own environment for Odoo credentials.

       X-Odoo-Url:          https://yourcompany.odoo.com
       X-Odoo-Db:           yourcompany
       X-Odoo-Username:     you@yourcompany.com
       Authorization:       Bearer <odoo api key>
       X-Odoo-Allow-Write:  false

2. Local (stdio). Credentials come from environment variables:
   ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_API_KEY, ODOO_ALLOW_WRITE.

Run:  ochre-odoo-mcp                      (stdio)
      ochre-odoo-mcp --transport http     (hosted, listens on $PORT or 8000)
"""

import argparse
import hashlib
import ipaddress
import json
import logging
import os
import socket
import threading
import time
import xmlrpc.client
from dataclasses import dataclass
from urllib.parse import urlparse

from mcp.server.fastmcp import Context, FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import __version__
from .lint import lint_files, lint_module

log = logging.getLogger("ochre-odoo")

mcp = FastMCP("ochre-odoo", stateless_http=True, json_response=True)

MAX_LIMIT = 500
MAX_RESPONSE_BYTES = 400_000
RPC_TIMEOUT = float(os.environ.get("OCHRE_RPC_TIMEOUT", "30"))
RATE_PER_MIN = int(os.environ.get("OCHRE_RATE_PER_MIN", "120"))
SESSION_TTL = 600
ALLOW_PRIVATE = os.environ.get("OCHRE_ALLOW_PRIVATE_TARGETS", "").lower() in ("1", "true", "yes")


# Credentials

@dataclass(frozen=True)
class Creds:
    url: str
    db: str
    user: str
    key: str
    allow_write: bool
    hosted: bool

    @property
    def fingerprint(self) -> str:
        raw = "\x00".join((self.url, self.db, self.user, self.key))
        return hashlib.sha256(raw.encode()).hexdigest()


def _truthy(v) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes")


def _request(ctx: Context | None):
    try:
        return ctx.request_context.request if ctx else None
    except (AttributeError, ValueError, LookupError):
        return None


def get_creds(ctx: Context | None) -> Creds:
    req = _request(ctx)
    if req is not None:
        h = req.headers
        auth = h.get("authorization", "")
        key = auth[7:].strip() if auth.lower().startswith("bearer ") else (h.get("x-odoo-api-key") or "")
        return Creds(
            url=(h.get("x-odoo-url") or "").strip().rstrip("/"),
            db=(h.get("x-odoo-db") or "").strip(),
            user=(h.get("x-odoo-username") or "").strip(),
            key=key,
            allow_write=_truthy(h.get("x-odoo-allow-write")),
            hosted=True,
        )
    return Creds(
        url=(os.environ.get("ODOO_URL") or "").strip().rstrip("/"),
        db=(os.environ.get("ODOO_DB") or "").strip(),
        user=(os.environ.get("ODOO_USERNAME") or "").strip(),
        key=os.environ.get("ODOO_API_KEY") or "",
        allow_write=_truthy(os.environ.get("ODOO_ALLOW_WRITE")),
        hosted=False,
    )


def _validate(c: Creds):
    missing = [n for n, v in (("Odoo URL", c.url), ("database", c.db),
                              ("username", c.user), ("API key", c.key)) if not v]
    if missing:
        where = "request headers" if c.hosted else "environment variables"
        raise UserError(f"Missing {', '.join(missing)} in {where}. See the plugin README for setup.")
    p = urlparse(c.url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise UserError("Odoo URL must look like https://yourcompany.odoo.com")
    if c.hosted:
        if p.scheme != "https" and not ALLOW_PRIVATE:
            raise UserError("The hosted service only connects to https Odoo URLs.")
        _guard_target(p.hostname, p.port or (443 if p.scheme == "https" else 80))


def _guard_target(host: str, port: int):
    """Stop the hosted service being used to reach private networks."""
    if ALLOW_PRIVATE:
        return
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise UserError(f"Cannot resolve {host}.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise UserError("That Odoo URL points to a private or reserved address. "
                            "Run the plugin locally (stdio mode) for servers on a private network.")


class UserError(Exception):
    pass


# Rate limit

_rate_lock = threading.Lock()
_rate: dict[str, list[float]] = {}


def _rate_check(fp: str):
    now = time.monotonic()
    with _rate_lock:
        window = [t for t in _rate.get(fp, []) if now - t < 60]
        if len(window) >= RATE_PER_MIN:
            raise UserError(f"Rate limit reached ({RATE_PER_MIN} calls per minute). Wait a moment and retry.")
        window.append(now)
        _rate[fp] = window
        if len(_rate) > 10_000:
            for k in [k for k, v in _rate.items() if not v or now - v[-1] > 60]:
                _rate.pop(k, None)


# Odoo client

class _TimeoutTransport(xmlrpc.client.Transport):
    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = RPC_TIMEOUT
        return conn


class _TimeoutSafeTransport(xmlrpc.client.SafeTransport):
    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = RPC_TIMEOUT
        return conn


def _proxy(url: str, path: str):
    transport = _TimeoutSafeTransport() if url.startswith("https") else _TimeoutTransport()
    return xmlrpc.client.ServerProxy(f"{url}{path}", allow_none=True, transport=transport)


_uid_lock = threading.Lock()
_uid_cache: dict[str, tuple[int, float]] = {}


def _uid(c: Creds) -> int:
    fp = c.fingerprint
    now = time.monotonic()
    with _uid_lock:
        hit = _uid_cache.get(fp)
        if hit and now - hit[1] < SESSION_TTL:
            return hit[0]
    uid = _proxy(c.url, "/xmlrpc/2/common").authenticate(c.db, c.user, c.key, {})
    if not uid:
        raise UserError("Odoo rejected the login. Check database name, username and API key.")
    with _uid_lock:
        if len(_uid_cache) > 5_000:
            _uid_cache.clear()
        _uid_cache[fp] = (uid, now)
    return uid


def odoo_call(ctx, model, method, args=None, kwargs=None):
    c = get_creds(ctx)
    _validate(c)
    _rate_check(c.fingerprint)
    uid = _uid(c)
    return _proxy(c.url, "/xmlrpc/2/object").execute_kw(c.db, uid, c.key, model, method, args or [], kwargs or {})


# Helpers

def _parse(value, default):
    if value is None or value == "":
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise UserError(f"Invalid JSON: {e.msg}")
    return value


def _err(e: Exception) -> dict:
    if isinstance(e, UserError):
        return {"error": str(e)}
    if isinstance(e, xmlrpc.client.Fault):
        lines = [ln for ln in e.faultString.strip().splitlines() if ln.strip()]
        return {"error": lines[-1] if lines else "Odoo returned an error."}
    if isinstance(e, xmlrpc.client.ProtocolError):
        return {"error": f"Odoo endpoint returned HTTP {e.errcode}. Check the Odoo URL."}
    if isinstance(e, (socket.timeout, TimeoutError)):
        return {"error": f"Odoo did not respond within {RPC_TIMEOUT:.0f} seconds."}
    if isinstance(e, OSError):
        return {"error": "Could not reach the Odoo server. Check the URL and that it is online."}
    log.exception("unexpected error")
    return {"error": "Unexpected error. Please retry; if it persists contact contact@ochre.digital."}


def _cap(payload: dict, list_key: str) -> dict:
    """Trim large result sets so they fit comfortably in the agent's context."""
    rows = payload.get(list_key) or []
    size = len(json.dumps(payload, default=str))
    if size <= MAX_RESPONSE_BYTES or not rows:
        return payload
    keep = max(1, int(len(rows) * MAX_RESPONSE_BYTES / size * 0.9))
    payload[list_key] = rows[:keep]
    payload["truncated"] = True
    payload["note"] = f"Showing {keep} of {len(rows)} rows to stay within size limits. Request fewer fields or use offset."
    return payload


# Tools

@mcp.tool()
def odoo_server_info(ctx: Context) -> dict:
    """Confirm the Odoo connection works and return the server version and user id."""
    try:
        c = get_creds(ctx)
        _validate(c)
        _rate_check(c.fingerprint)
        info = _proxy(c.url, "/xmlrpc/2/common").version()
        return {"server_version": info.get("server_version"), "uid": _uid(c),
                "database": c.db, "writes_enabled": c.allow_write,
                "mode": "hosted" if c.hosted else "local", "plugin_version": __version__}
    except Exception as e:
        return _err(e)


@mcp.tool()
def odoo_list_models(ctx: Context, search: str = "", limit: int = 50) -> dict:
    """List installed models. `search` filters on technical name or label, e.g. 'sale' or 'invoice'."""
    try:
        domain = ["|", ["model", "ilike", search], ["name", "ilike", search]] if search else []
        rows = odoo_call(ctx, "ir.model", "search_read", [domain],
                         {"fields": ["model", "name"], "limit": max(1, min(limit, MAX_LIMIT)), "order": "model"})
        return {"count": len(rows), "models": [{"model": r["model"], "label": r["name"]} for r in rows]}
    except Exception as e:
        return _err(e)


@mcp.tool()
def odoo_model_fields(ctx: Context, model: str, search: str = "") -> dict:
    """Describe fields of a model (type, label, relation, required). Call before building a domain."""
    try:
        attrs = ["string", "type", "relation", "required", "readonly", "store", "selection"]
        fields = odoo_call(ctx, model, "fields_get", [], {"attributes": attrs})
        s = search.lower()
        out = [{"name": n, **{k: v for k, v in m.items() if v not in (None, False, [])}}
               for n, m in sorted(fields.items())
               if not s or s in n.lower() or s in str(m.get("string", "")).lower()]
        return _cap({"model": model, "count": len(out), "fields": out}, "fields")
    except Exception as e:
        return _err(e)


@mcp.tool()
def odoo_search_read(ctx: Context, model: str, domain: str = "[]", fields: str = "[]",
                     limit: int = 50, offset: int = 0, order: str = "") -> dict:
    """Search records and return field values.

    domain: Odoo domain as JSON, e.g. [["state","=","sale"],["amount_total",">",100000]]
    fields: JSON list of field names. Always pass a short list on large models.
    """
    try:
        kw = {"fields": _parse(fields, []), "limit": max(1, min(limit, MAX_LIMIT)), "offset": max(0, offset)}
        if order:
            kw["order"] = order
        rows = odoo_call(ctx, model, "search_read", [_parse(domain, [])], kw)
        return _cap({"model": model, "count": len(rows), "records": rows}, "records")
    except Exception as e:
        return _err(e)


@mcp.tool()
def odoo_count(ctx: Context, model: str, domain: str = "[]") -> dict:
    """Count records matching a domain (JSON). Use before large searches."""
    try:
        return {"model": model, "count": odoo_call(ctx, model, "search_count", [_parse(domain, [])])}
    except Exception as e:
        return _err(e)


@mcp.tool()
def odoo_read(ctx: Context, model: str, ids: str, fields: str = "[]") -> dict:
    """Read specific records by id. ids: JSON list, e.g. [12, 15]."""
    try:
        id_list = _parse(ids, [])
        if len(id_list) > MAX_LIMIT:
            raise UserError(f"Read at most {MAX_LIMIT} ids per call.")
        rows = odoo_call(ctx, model, "read", [id_list], {"fields": _parse(fields, [])})
        return _cap({"model": model, "records": rows}, "records")
    except Exception as e:
        return _err(e)


@mcp.tool()
def odoo_module_status(ctx: Context, name: str = "", state: str = "installed", limit: int = 100) -> dict:
    """List modules and their state. Filter by name fragment and state
    (installed, uninstalled, to upgrade, to install). Pass state='' for all."""
    try:
        domain = []
        if name:
            domain.append(["name", "ilike", name])
        if state:
            domain.append(["state", "=", state])
        rows = odoo_call(ctx, "ir.module.module", "search_read", [domain],
                         {"fields": ["name", "shortdesc", "state", "installed_version", "author"],
                          "limit": max(1, min(limit, MAX_LIMIT)), "order": "name"})
        return {"count": len(rows), "modules": rows}
    except Exception as e:
        return _err(e)


@mcp.tool()
def odoo_create(ctx: Context, model: str, values: str) -> dict:
    """Create one record. values: JSON object. Only works when writes are enabled.
    Show the user the exact model and values and get an explicit yes before calling."""
    try:
        if not get_creds(ctx).allow_write:
            raise UserError("Write tools are disabled. Set ODOO_ALLOW_WRITE to true in the plugin configuration.")
        vals = _parse(values, {})
        if not isinstance(vals, dict) or not vals:
            raise UserError("values must be a non-empty JSON object.")
        return {"model": model, "id": odoo_call(ctx, model, "create", [vals])}
    except Exception as e:
        return _err(e)


@mcp.tool()
def odoo_update(ctx: Context, model: str, ids: str, values: str) -> dict:
    """Update records. ids: JSON list (max 100); values: JSON object. Only works when writes are enabled.
    Show the user the records and the change and get an explicit yes before calling."""
    try:
        if not get_creds(ctx).allow_write:
            raise UserError("Write tools are disabled. Set ODOO_ALLOW_WRITE to true in the plugin configuration.")
        id_list, vals = _parse(ids, []), _parse(values, {})
        if not id_list or len(id_list) > 100:
            raise UserError("Update between 1 and 100 records per call.")
        if not isinstance(vals, dict) or not vals:
            raise UserError("values must be a non-empty JSON object.")
        return {"model": model, "updated": odoo_call(ctx, model, "write", [id_list, vals]), "ids": id_list}
    except Exception as e:
        return _err(e)


@mcp.tool()
def odoo_v19_lint(ctx: Context, module_path: str = "", files: str = "") -> dict:
    """Check a custom Odoo module for known Odoo 19 breaking changes
    (groups_id, _sql_constraints, type='json', kanban-box, product_uom, tax_id and more).
    No Odoo connection needed.

    Pass `files` as a JSON object of relative path to file content, e.g.
    {"models/sale.py": "...", "views/sale_views.xml": "..."}. Read the module's
    .py, .xml and .csv files from the workspace and send them. `module_path`
    (a local folder) only works when the server runs locally.
    """
    try:
        if files:
            return lint_files(_parse(files, {}))
        if module_path:
            if _request(ctx) is not None:
                raise UserError("The hosted service cannot read your disk. Send the module files in `files` instead.")
            return lint_module(module_path)
        raise UserError("Pass `files` (path to content) or, in local mode, `module_path`.")
    except Exception as e:
        return _err(e)


# Http extras

@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "ochre-odoo-mcp", "version": __version__})


@mcp.custom_route("/", methods=["GET"])
async def root(_: Request) -> JSONResponse:
    return JSONResponse({
        "service": "Odoo MCP by Ochre Digital",
        "mcp_endpoint": "/mcp",
        "docs": "https://github.com/ochre-digital-x/ochre-odoo",
        "contact": "contact@ochre.digital",
    })


def main():
    ap = argparse.ArgumentParser(prog="ochre-odoo-mcp")
    ap.add_argument("--transport", choices=["stdio", "http"], default=os.environ.get("MCP_TRANSPORT", "stdio"))
    ap.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    a = ap.parse_args()
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "WARNING"))
    if a.transport == "http":
        mcp.settings.host = a.host
        mcp.settings.port = a.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
