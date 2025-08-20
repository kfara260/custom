from odoo import models, fields

class AttendanceDraftLocation(models.Model):
    _inherit = 'hr.draft.attendance'
    _description = 'Attendance Draft Location'

    location_status = fields.Boolean('Location Status', required=True)
