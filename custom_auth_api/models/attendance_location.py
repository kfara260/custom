from odoo import models, fields

class AttendanceLocation(models.Model):
    _name = 'attendance.location'
    _description = 'Attendance Location'

    name = fields.Char('Location Name', required=True)
    latitude = fields.Float('Latitude', required=True, digits=(16, 7))
    longitude = fields.Float('Longitude', required=True, digits=(16, 7))
    accepted_radius = fields.Float('Accepted Radius (m)', required=True)
