from odoo import models, fields

class Content(models.Model):
    _name = 'assignment_ftp_interface.content'
    _description = 'Content'

    id = fields.Integer(string='ID', required=True)
    content_id = fields.Integer(string='Content ID', index=True, readonly=True)
    name = fields.Char(string='Name', required=True, size=100)
    description = fields.Char(string='Description', size=128)
    expire_date = fields.Datetime(string='Expire Date')
    state = fields.Selection([
        ('enabled', 'Enabled'),
        ('disabled', 'Disabled'),
        ('deleted', 'Deleted'),
    ], string='State', default='enabled', required=True)

    device = fields.Many2one('assignment_ftp_interface.device', string='Device', required=True)