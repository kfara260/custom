from odoo import models, fields, api

class resUser(models.Model):
    _inherit = 'res.users'

    is_admin = fields.Boolean(string="Is Admin?", compute='_compute_is_admin', store=True)

    @api.depends('leave_manager_id')
    def _compute_is_admin(self):
        for rec in self:
            # Check if any employee has this employee as their leave manager
            is_admin = self.env['hr.employee'].sudo().search_count([
                ('leave_manager_id', '=', rec.id)
            ]) > 0
            
            rec.is_admin = is_admin
            rec.employee_id.is_admin = is_admin


