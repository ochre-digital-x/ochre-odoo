---
name: odoo-data-analyst
description: Answer business questions from a live Odoo database using the odoo MCP tools. Use when the user asks about sales, pipeline, invoices, receivables, purchases, stock, manufacturing or HR figures held in Odoo.
---

# Odoo data analyst

## Approach
1. Map the question to models. Common ones:
   - Pipeline: crm.lead (type = opportunity), stage_id, expected_revenue, probability, user_id
   - Sales: sale.order (state = sale), sale.order.line
   - Invoices and bills: account.move (move_type out_invoice / in_invoice, state = posted, payment_state)
   - Receivables ageing: account.move.line with account_type = asset_receivable, reconciled = false
   - Purchase: purchase.order, purchase.order.line
   - Stock: stock.quant (quantity, location_id.usage = internal), stock.move, stock.picking
   - Manufacturing: mrp.production, mrp.bom
   - People: hr.employee, hr.leave, hr.attendance
2. If unsure, call odoo_list_models with a keyword, then odoo_model_fields with a search term.
3. Call odoo_count first when the result size is unknown.
4. Pull only needed fields with odoo_search_read and aggregate yourself. Many2one values come back as [id, name].
5. State the period, filters and currency you used. Odoo stores dates in UTC.

## Answer format
Lead with the number or the finding. Then the two or three drivers behind it. Then the exact filters used so the user can reproduce it in Odoo.

## Limits
Read only by default. If the user asks to change data, follow the data safety rule: show the change, get a yes, then call odoo_update or odoo_create (only available when ODOO_ALLOW_WRITE is true).
