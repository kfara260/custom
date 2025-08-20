import random
import string
from odoo import models, fields, api
from odoo.osv import expression

from datetime import datetime, timedelta
import hashlib
import logging
_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    code_name_search = fields.Char(compute="compute_code_name_search",store=True)

    @api.depends('name','code_num')
    def compute_code_name_search(self):
        for rec in self:
            rec.code_name_search = str(rec.name)+"-"+str(rec.code_num)

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = ['|', ('name', operator, name), ('code_num', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    password = fields.Char(string="Set Password", )

    otp_number = fields.Char(string="OTP Number", readonly=True)
    generated_at = fields.Datetime(string="Generated At", readonly=True)

    location_ids = fields.Many2many('attendance.location', string='Check-In Location')

    is_admin = fields.Boolean(string="Is Admin?",  readonly=True) 

    mac_address = fields.Char(string="Mac Address", readonly=True)
    
    _sql_constraints = [
        ('unique_work_email', 'unique(work_email)', 'The Email must be unique!')
    ]

    # @api.onchange('password')
    # def _onchange_password(self):
    #     for rec in self:
    #         if rec.password:
    #             rec.password = hashlib.sha256(rec.password.encode()).hexdigest()


    def generate_otp_number(self):
        """Generate a random number only if expired."""
        for rec in self:
            expiration_hours = self.env['ir.config_parameter'].sudo().get_param('custom_auth_api.expiration_hours', default=1)
            expiration_hours = int(expiration_hours) if expiration_hours else 1

            rec.otp_number = ''.join(random.choices(string.digits, k=6)) 
            rec.generated_at = fields.Datetime.now()

            return rec.otp_number
