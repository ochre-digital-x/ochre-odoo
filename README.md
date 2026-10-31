<img src="assets/ochre-wordmark.png" alt="Ochre" width="220">

# Connector for Odoo by Ochre Digital

[![CI](https://github.com/ochre-digital-x/ochre-odoo/actions/workflows/ci.yml/badge.svg)](https://github.com/ochre-digital-x/ochre-odoo/actions/workflows/ci.yml)

Lets your agent read your Odoo database and work on Odoo modules. Ask about sales, pipeline, receivables or stock in plain English, look up models and fields, and build or upgrade custom modules for Odoo 19.

Works in Grok Bot and Cursor. We are [Ochre Digital](https://ochre.digital), an Odoo implementation partner in Noida. The Odoo 19 checks are the ones that broke our own client modules during upgrades this year.

## Compared with other Odoo MCP servers

| | Most Odoo MCP servers | This one |
|---|---|---|
| Install | Clone, Python env, config file | Installs itself on first use; you fill in five settings |
| Default access | Full read and write | Read only. Writes need a setting and your yes |
| Delete and arbitrary methods | Often exposed | Not available |
| Odoo 19 module upgrades | Not covered | Linter, preflight skill, editor rules |
| Process guidance | None | Architect agent: standard Odoo first, custom last |
| Odoo on a private network | Not covered | Run it locally, same tools |

## What you get

| Component | Name | Purpose |
|---|---|---|
| MCP server | odoo | 10 tools: connection check, models, fields, search, count, read, modules, optional create and update, v19 lint |
| Skill | odoo-data-analyst | Answer sales, pipeline, receivables, purchase, stock and HR questions |
| Skill | odoo-v19-module-builder | Scaffold modules that install cleanly on Odoo 19 |
| Skill | odoo-v19-preflight | Review and upgrade a module for Odoo 19 |
| Rule | odoo-v19-standards | Odoo 19 breaking changes, applied while you edit module files |
| Rule | odoo-data-safety | Read first, confirm before write, protect personal data |
| Agent | odoo-architect | Fit gap and scoping, standard first |
| Command | /odoo-snapshot | One screen business summary |
| Command | /odoo-preflight | Lint the current module |

## Setup

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) on your computer (one command; many developers already have it). The plugin uses it to fetch and run the server the first time it starts.

1. In Odoo: your avatar, My Preferences (or Preferences), Account Security, New API Key. Copy the key.
2. Install the plugin from the marketplace.
3. Under Plugins, Configure, set:

| Variable | Example |
|---|---|
| ODOO_URL | https://yourcompany.odoo.com |
| ODOO_DB | yourcompany |
| ODOO_USERNAME | you@yourcompany.com |
| ODOO_API_KEY | the key from step 1 |
| ODOO_ALLOW_WRITE | false |

4. Ask: "Check my Odoo connection."

Works with Odoo 16 to 20 on Odoo Online (plans with external API access), Odoo.sh and self hosted servers, including ones on your own network. Create the key on a user with only the access the agent should have.

## Try these

- "What is our open pipeline by salesperson and stage?"
- "List customer invoices overdue more than 30 days, largest first."
- "Which storable products are below 10 units in the main warehouse?"
- "/odoo-snapshot"
- "Scaffold a module for a vehicle register with service due dates, a kanban by status and a manager group."
- "/odoo-preflight" with a v17 module open.

## Tools

| Tool | Writes |
|---|---|
| odoo_server_info | no |
| odoo_list_models | no |
| odoo_model_fields | no |
| odoo_search_read | no |
| odoo_count | no |
| odoo_read | no |
| odoo_module_status | no |
| odoo_create | only if ODOO_ALLOW_WRITE=true |
| odoo_update | only if ODOO_ALLOW_WRITE=true, max 100 records |
| odoo_v19_lint | no, needs no Odoo connection |

## Security

- The server runs on your computer and talks only to your Odoo. Ochre never sees your data or credentials. See [PRIVACY.md](PRIVACY.md).
- Refuses plain http, private, loopback and cloud metadata addresses.
- 30 second timeout per Odoo call, 120 calls per minute per user, result size capped.
- Credentials live in your plugin configuration, never in this repository.

## Run it as a shared service

Teams that prefer one shared endpoint can host the same server with Docker. See [deploy/DEPLOY.md](deploy/DEPLOY.md) and [examples/mcp.hosted.json](examples/mcp.hosted.json). In that mode it refuses private network addresses and plain http, rate limits each user and keeps no data.

## Development

```bash
pip install -e server
python3 tests/test_e2e.py
```

The suite starts the real server in both modes against a mock Odoo and runs 22 checks: every tool, the write switch, separation between users, and the network guards.

## Related

[Predict for Odoo](https://github.com/ochre-digital-x/odoo-predict) by the same team: revenue and demand forecasts, deal scoring, collection risk and duplicate bill checks.

## Support

contact@ochre.digital | +91 9266489230 | https://ochre.digital

## Licence

MIT
