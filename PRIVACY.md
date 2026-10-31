# Privacy and security

By default the server runs on your own computer, started by the plugin. It connects only to the Odoo URL you configure. Your Odoo data and API key do not pass through Ochre or any other third party, apart from what your agent sends to its own model.

Stored: nothing. No database, no log of your data, no telemetry.

Safeguards
- Read only unless you set ODOO_ALLOW_WRITE to true. No delete and no arbitrary method calls exist in the server.
- 30 second timeout per Odoo call, 120 calls per minute per credential, result size capped.
- The API key carries the permissions of the Odoo user who created it. Create it on a user with only the access the agent needs. Revoke it in Odoo at any time.

Shared hosting (optional)
If a team runs the server as a shared service (deploy/DEPLOY.md), credentials travel in HTTPS request headers on each call, are used for that call only. The server keeps a hashed fingerprint in memory for up to 10 minutes to avoid logging in on every call, and writes nothing to disk. In that mode the server refuses plain http, private, loopback and cloud metadata addresses.

Contact: contact@ochre.digital
