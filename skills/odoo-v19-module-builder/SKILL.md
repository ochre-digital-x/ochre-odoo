---
name: odoo-v19-module-builder
description: Scaffold or extend a custom Odoo 19 module that installs cleanly the first time. Use when the user asks to create a new Odoo module, add a model, view, menu, security group, wizard, report or controller, or port an older module to v19.
---

# Odoo v19 module builder

## Before writing code
1. Confirm the target: Odoo version (19 by default), Community or Enterprise, and where it deploys (Odoo.sh, self hosted, odoo.com SaaS cannot take custom Python).
2. Confirm dependencies. Depend on the smallest set that provides every field you touch. If you need is_storable, depend on stock.
3. If the odoo MCP server is connected, call odoo_module_status and odoo_model_fields on the models you extend so field names come from the live system, not memory.

## Layout
```
my_module/
  __init__.py
  __manifest__.py
  models/__init__.py
  models/<model>.py
  views/<model>_views.xml
  views/menus.xml
  security/security.xml        # groups, only if needed
  security/ir.model.access.csv
  data/                        # sequences, cron, mail templates
  static/description/icon.png
  tests/__init__.py
  tests/test_<feature>.py
```

## Manifest
- version: "19.0.1.0.0"
- license: "LGPL-3" for open modules, "OPL-1" for paid App Store modules
- data order: security first, then data, then views, then menus last
- Leave external_dependencies empty if third party libraries are imported lazily inside methods

## Models
- One model per file. _name, _description, _order. Add _inherit = ["mail.thread", "mail.activity.mixin"] only when chatter is wanted.
- Constraints as `models.Constraint(...)` class attributes, never _sql_constraints.
- Monetary fields need a currency_id field.
- Every new model needs an access line in ir.model.access.csv or it is invisible to non admin users.

## Views
- Kanban uses <card>.
- Search views: bare <group> wrapping group_by filters.
- Use groups= on fields, buttons and menus for role control.

## Security groups in v19
Groups attach to a privilege, not directly to a category:
```xml
<record id="privilege_my_app" model="res.groups.privilege">
    <field name="name">My App</field>
    <field name="category_id" ref="base.module_category_services"/>
</record>
<record id="group_my_app_user" model="res.groups">
    <field name="name">User</field>
    <field name="privilege_id" ref="privilege_my_app"/>
</record>
```

## Finish
1. Call odoo_v19_lint with `files` (relative path to content for each .py, .xml and .csv file) and fix every finding that applies.
2. Tell the user how to install and test: `odoo-bin -c odoo.conf -d test -i my_module --stop-after-init --test-enable`.
3. List what you did not verify.
