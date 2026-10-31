---
name: odoo-snapshot
description: One screen business snapshot from the connected Odoo database
---

# Odoo snapshot

Using the odoo MCP tools, read only:
1. odoo_server_info to confirm connection and version.
2. Open pipeline: count and sum of expected_revenue on crm.lead where type = opportunity and active.
3. Sales this month: count and sum of amount_untaxed on sale.order with state = sale and date_order in the current month.
4. Receivables: sum of amount_residual on account.move with move_type = out_invoice, state = posted, payment_state in (not_paid, partial). Split into current and overdue by invoice_date_due.
5. Payables due in the next 14 days from account.move with move_type = in_invoice.
Skip any section whose app is not installed (check odoo_module_status for crm, sale, account).
Present as a short table with one line of commentary per row. State the currency and date.
