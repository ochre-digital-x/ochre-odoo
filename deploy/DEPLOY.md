# Deploying the hosted endpoint

Target: https://mcp.ochre.digital/mcp on a Hostinger VPS (any Ubuntu VPS with Docker works).

1. DNS: add an A record `mcp` on ochre.digital pointing to the VPS IP. Wait until `dig mcp.ochre.digital` shows it.
2. On the VPS:
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin git
   git clone https://github.com/ochre-digital-x/ochre-odoo.git && cd ochre-odoo/deploy
   sudo docker compose up -d --build
   ```
   Caddy obtains the TLS certificate automatically.
3. Check: `curl https://mcp.ochre.digital/health` returns `{"status":"ok",...}`.
4. Monitoring: add https://mcp.ochre.digital/health to UptimeRobot (free) with an email alert.
5. Updates: `git pull && sudo docker compose up -d --build`.

Sizing: 1 vCPU and 1 GB RAM handles hundreds of concurrent users. The server is stateless and stores nothing; it only forwards each request to that user's Odoo.

Do not enable header logging anywhere in front of this service. The Authorization header is the customer's Odoo API key.
