from odoo import models, fields

class Content(models.Model):
    _name = 'assignment.content'
    _description = 'Content'

    name =          fields.Char(string='Name', required=True, size=100)
    description =   fields.Char(string='Description', size=128)

    device = fields.Many2one('assignment.device', string='Device', required=True)
    expire_date = fields.Datetime(string='Expire Date')
    state = fields.Selection([
        ('enabled', 'Enabled'),
        ('disabled', 'Disabled'),
        ('deleted', 'Deleted'),
    ], string='State', default='enabled', required=True)