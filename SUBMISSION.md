# Grok Bot marketplace submission

Form: https://x.ai/bot/marketplace/submit-a-plugin

## Form fields

| Field | Value |
|---|---|
| First Name | Prasant |
| Last Name | Agarwal |
| Work Email | an address on the ochre.digital domain that you monitor |
| Organization Name | Ochre Digital |
| Organization Handle | ochre-digital |
| Website URL | https://ochre.digital |
| Logotype URL | https://raw.githubusercontent.com/ochre-digital-x/ochre-odoo/main/assets/logo.png |
| Where to list | Grok Bot, Cursor, Grok (coming soon) |
| MCP Server URL or Public GitHub Repository | https://github.com/ochre-digital-x/ochre-odoo |

Use the GitHub repo, not the bare MCP URL. The repo carries the skills, rules, agent and commands as well as the server.

## Brief Description

Connect Grok Bot or Cursor to any Odoo 16 to 20 database to ask about sales, pipeline, receivables and stock in plain language, inspect models and fields, and build or upgrade custom modules for Odoo 19 using a breaking-change linter drawn from real client upgrades. Read only by default. There is no delete, and writes need both a setting and the user's confirmation. The server runs on the user's machine, so no data passes through Ochre. Built by Ochre Digital, an Odoo implementation partner.

## Testing Instructions

No Odoo account needed (2 minutes):
1. Make sure uv is installed (https://docs.astral.sh/uv). Install the plugin. Put any placeholder in the five settings.
2. Clone the repo, open tests/fixtures/legacy_module and run /odoo-preflight. Expect six findings: _sql_constraints, groups_id, product_uom, tax_id, kanban-box and the registry import, each with its Odoo 19 fix.

With a free Odoo trial (5 minutes):
1. Start a trial at odoo.com with CRM, Sales and Invoicing. Preferences, Account Security, New API Key.
2. Set ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_API_KEY under Plugins, Configure. Leave ODOO_ALLOW_WRITE=false.
3. Ask "Check my Odoo connection", then "How many customers do I have?", then run /odoo-snapshot.
4. Ask the agent to create a contact. It reports that writes are disabled.

Automated: `pip install -e server && python3 tests/test_e2e.py` runs 22 checks against the real server over stdio and HTTP. CI runs the same on every push.

Requires uv on the reviewer's machine (https://docs.astral.sh/uv). The plugin starts the server itself.

## Checklist before you press submit

1. GitHub: create the public repo ochre-odoo in the ochre-digital-x organisation. Push this folder to main. Confirm the CI badge goes green.
2. Hosting is optional and can come later. The plugin runs on the user's machine.
3. Logo: replace assets/logo.svg and assets/logo.png with the real Ochre mark, square, on a white plate.
4. Test in Grok Bot and in Cursor against a real Odoo trial. The form asks you to confirm this. Run every prompt in the Testing Instructions.
5. Record a 60 to 90 second screen capture: install, connection check, /odoo-snapshot, /odoo-preflight. Put it at the top of the README. Reviewers decide fast.
6. Add repo topics on GitHub: odoo, mcp, mcp-server, erp, cursor-plugin, grok.
7. Read the Publisher Terms: https://cursor.com/marketplace-publisher-terms
