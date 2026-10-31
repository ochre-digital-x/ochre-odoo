# Changelog

## 1.2.0 (2026-10-31)
- The plugin now starts the server on the user's machine through uv. No Ochre hosting involved; data goes only between the user's computer and their Odoo.
- Shared hosting stays available for teams that want it (deploy/, examples/mcp.hosted.json).

## 1.1.0 (2026-10-31)
- Shared HTTP mode for running one endpoint for many users.
- Per-request credentials in headers; the server stores nothing.
- Refuses private, loopback and cloud metadata addresses and plain http in hosted mode.
- Rate limit, Odoo call timeout and result size cap.
- odoo_v19_lint accepts file contents, so it works hosted.
- Clearer error messages for login, network and JSON problems.
- Docker image, Caddy config, GitHub Actions CI, privacy statement.

## 1.0.0 (2026-10-31)
- First release: MCP server, 3 skills, 2 rules, 1 agent, 2 commands.
