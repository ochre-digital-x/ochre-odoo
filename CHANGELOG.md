# Changelog

## 1.1.0 (2026-10-31)
- Hosted endpoint at https://mcp.ochre.digital/mcp, so users no longer need Python or uv.
- Per-request credentials in headers; the server stores nothing.
- Refuses private, loopback and cloud metadata addresses and plain http in hosted mode.
- Rate limit, Odoo call timeout and result size cap.
- odoo_v19_lint accepts file contents, so it works hosted.
- Clearer error messages for login, network and JSON problems.
- Docker image, Caddy config, GitHub Actions CI, privacy statement.

## 1.0.0 (2026-10-31)
- First release: MCP server, 3 skills, 2 rules, 1 agent, 2 commands.
