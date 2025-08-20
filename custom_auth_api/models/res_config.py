from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expiration_hours = fields.Integer(
        string="Expiration Time (Hours)", 
        default=1, 
        config_parameter='custom_auth_api.expiration_hours'
    )
