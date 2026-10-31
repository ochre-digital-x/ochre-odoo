---
name: odoo-v19-preflight
description: Check a custom Odoo module before an upgrade to v19 or before shipping it. Use when the user asks to review, upgrade, port, migrate or preflight an Odoo module, or when an install fails with a field, view validation or access error.
---

# Odoo v19 preflight

## Step 1: Static scan
Read every .py, .xml and .csv file in the module (skip static/). Call odoo_v19_lint with `files` set to a JSON object of relative path to content. For modules over about 1.5 MB, send in batches by folder. Group findings by check id. Some findings are false positives (for example a form view <group string="..."> is fine; only search views are restricted). Read each line before changing it.

## Step 2: Fix in this order
1. Security: privilege_id, group_ids, user_ids
2. Models: models.Constraint, Registry import, removed models
3. Fields: product_uom_id, tax_ids, product type values, uom_po_id, is_storable dependency
4. Views: <card>, search view groups
5. Controllers: type='jsonrpc'
6. Version string in the manifest: 19.0.x.y.z

## Step 3: Live install (the real test)
Static checks cannot see whether a field exists. Give the user these commands, or run them if a shell is available:
```bash
git clone --depth 1 -b 19.0 https://github.com/odoo/odoo.git
pip install -r odoo/requirements.txt   # swap psycopg2 for psycopg2-binary if build fails
createdb preflight
python3 odoo/odoo-bin -d preflight --addons-path=odoo/addons,./custom_addons \
  -i <module> --stop-after-init --test-enable 2>&1 | tee install.log
grep -E "ERROR|CRITICAL|WARNING" install.log
```
On a fresh database always use -i, not -u.

## Step 4: Report
Give the user: findings fixed, findings dismissed with reason, install result, and anything left to verify by hand (reports, portal pages, scheduled actions).
