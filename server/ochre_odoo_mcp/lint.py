"""Static checks for Odoo v19 breaking changes in a custom module.

This is a blocklist. It catches patterns that are known to fail on v19.
It cannot prove a module is correct; a live install is the real test.
"""

import os
import re

CHECKS = [
    # (id, file types, regex, message)
    ("V19-GROUPS-CATEGORY", (".py", ".xml", ".csv"),
     r"res\.groups[^\n]*category_id|<record[^>]*model=\"res\.groups\"[\s\S]{0,400}?name=\"category_id\"",
     "res.groups.category_id was removed. Use privilege_id (res.groups.privilege) which carries category_id."),
    ("V19-USERS-GROUPS-ID", (".py", ".xml", ".csv"),
     r"\bgroups_id\b",
     "res.users.groups_id is now group_ids."),
    ("V19-GROUPS-USERS", (".xml", ".py"),
     r"name=\"users\"\s|\.users\b(?!_)",
     "res.groups.users is now user_ids. Check this reference."),
    ("V19-SQL-CONSTRAINTS", (".py",),
     r"_sql_constraints\s*=",
     "_sql_constraints is deprecated. Use models.Constraint(\"UNIQUE(col)\", \"message\") as a class attribute."),
    ("V19-PRODUCT-UOM", (".py", ".xml"),
     r"\bproduct_uom\b(?!_)",
     "product_uom is now product_uom_id on order lines."),
    ("V19-TAX-ID", (".py", ".xml"),
     r"\btax_id\b",
     "tax_id is now tax_ids."),
    ("V19-JSON-ROUTE", (".py",),
     r"type\s*=\s*['\"]json['\"]",
     "http.route type='json' is now type='jsonrpc'."),
    ("V19-KANBAN-BOX", (".xml",),
     r"kanban-box",
     "kanban-box template is replaced by <card>."),
    ("V19-PARTNER-TITLE", (".py", ".xml", ".csv"),
     r"res\.partner\.title|model_res_partner_title",
     "res.partner.title model was removed."),
    ("V19-REGISTRY-IMPORT", (".py",),
     r"from\s+odoo\s+import\s+[^\n]*\bregistry\b",
     "Use: from odoo.modules.registry import Registry"),
    ("V19-SEARCH-GROUP-ATTRS", (".xml",),
     r"<group\s+[^>]*(expand|string|name)\s*=",
     "Search view <group> no longer accepts expand/string/name. Use a bare <group> with group_by filters. (Ignore if this is a form view group.)"),
    ("V19-UOM-PO", (".py", ".xml", ".csv"),
     r"\buom_po_id\b",
     "uom_po_id was removed from product. Use uom_id, plus uom_ids for packagings."),
    ("V19-PRODUCT-TYPE", (".py", ".xml"),
     r"(detailed_)?type['\"]?\s*[:=]\s*['\"]product['\"]|name=\"(detailed_)?type\">product<",
     "product.type 'product' no longer exists. Use 'consu' with is_storable=True (requires the stock module)."),
    ("V19-WITHOUT-DEMO", (".py", ".conf", ".cfg"),
     r"without_demo\s*[=:]\s*['\"]?all",
     "without_demo is now boolean, not 'all'."),
]

SKIP_DIRS = {".git", "__pycache__", "node_modules", "static"}


LINT_EXTS = (".py", ".xml", ".csv", ".conf", ".cfg")


def _scan(items, max_findings):
    """items: iterable of (relative_path, text)."""
    compiled = [(cid, exts, re.compile(rx), msg) for cid, exts, rx, msg in CHECKS]
    findings, scanned, has_manifest = [], 0, False
    for rel, text in items:
        ext = os.path.splitext(rel)[1].lower()
        if ext not in LINT_EXTS:
            continue
        if os.path.basename(rel) == "__manifest__.py":
            has_manifest = True
        scanned += 1
        lines = text.splitlines()
        for cid, exts, rx, msg in compiled:
            if ext not in exts:
                continue
            for m in rx.finditer(text):
                if len(findings) >= max_findings:
                    break
                lineno = text.count("\n", 0, m.start()) + 1
                findings.append({
                    "check": cid,
                    "file": rel,
                    "line": lineno,
                    "code": lines[lineno - 1].strip()[:200] if lineno <= len(lines) else "",
                    "message": msg,
                })
    return {
        "has_manifest": has_manifest,
        "files_scanned": scanned,
        "finding_count": len(findings),
        "findings": findings,
        "note": "Static blocklist only. Confirm with a live install: odoo-bin -i <module> --stop-after-init.",
    }


def lint_module(path: str, max_findings: int = 300) -> dict:
    """Lint a module folder on the local disk."""
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isdir(path):
        return {"error": f"Not a directory: {path}"}

    def items():
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in files:
                if os.path.splitext(fname)[1].lower() not in LINT_EXTS:
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, encoding="utf-8", errors="replace") as fh:
                        yield os.path.relpath(fpath, path), fh.read()
                except OSError:
                    continue

    return {"module_path": path, **_scan(items(), max_findings)}


def lint_files(files: dict, max_findings: int = 300, max_bytes: int = 2_000_000) -> dict:
    """Lint file contents passed in directly: {"models/sale.py": "<source>", ...}."""
    if not isinstance(files, dict) or not files:
        return {"error": "Pass files as an object mapping relative path to file content."}
    total = sum(len(str(v)) for v in files.values())
    if total > max_bytes:
        return {"error": f"Too much content ({total} bytes). Limit is {max_bytes}. Lint fewer files per call."}
    return _scan(((str(k), str(v)) for k, v in files.items()), max_findings)
