from odoo import models, fields, api

class HrLeaveTypeInherit(models.Model):
    _inherit = 'hr.leave.type'

    is_description = fields.Boolean(string="Description required", )

