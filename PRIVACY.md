# Privacy and security

Hosted endpoint: https://mcp.ochre.digital/mcp, operated by Ochre Tech and Marketing Pvt Ltd.

What passes through
- Your Odoo URL, database, username and API key arrive in request headers on each call, over HTTPS.
- The server uses them to call your Odoo and returns the result to your agent.

What is stored
- Nothing persistent. No database, no request bodies, no credentials on disk.
- In memory only: a hashed fingerprint of your credentials mapped to your Odoo user id for up to 10 minutes (avoids logging in on every call), and call timestamps for rate limiting.
- Access logs exclude headers.

Safeguards
- Read only unless you set ODOO_ALLOW_WRITE to true. No delete and no arbitrary method calls exist in the server.
- Only https Odoo URLs on public addresses are accepted. Private, loopback and cloud metadata addresses are refused.
- 30 second timeout per Odoo call, 120 calls per minute per credential, result size capped.
- The API key carries the permissions of the Odoo user who created it. Create it on a user with only the access the agent needs. Revoke it in Odoo at any time.

Prefer nothing leaves your network? Run the same server locally; see examples/mcp.local.json.

Contact: contact@ochre.digital
