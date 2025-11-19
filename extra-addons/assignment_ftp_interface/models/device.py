from odoo import models, fields, api

class Device(models.Model):
    _name = 'assignment_ftp_interface.device'
    _description = 'Device'

    id = fields.Integer(string='ID', required=True)
    device_id = fields.Integer(string='Device ID', index=True, readonly=True)
    name = fields.Char(string='Name', required=True, size=32)
    description = fields.Char(string='Description', size=128)
    code = fields.Char(string='Code', required=True, size=30)
    expire_date = fields.Datetime(string='Expire Date')
    state = fields.Selection([
        ('enabled', 'Enabled'),
        ('disabled', 'Disabled'),
        ('deleted', 'Deleted'),
    ], string='State', default='enabled', required=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'The device code must be unique!')
    ]

    # Relationship to Content model
    content_ids = fields.One2many(
        'assignment_ftp_interface.content',
        'device',
        string='Contents'
    )