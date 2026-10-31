from odoo import models, fields, registry
class X(models.Model):
    _name = "x.x"
    _sql_constraints = [("u", "unique(name)", "dup")]
    def f(self):
        return self.env.user.groups_id, self.order_line.product_uom, self.tax_id
