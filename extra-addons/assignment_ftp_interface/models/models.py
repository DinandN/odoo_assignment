# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class assignment_ftp_interface(models.Model):
#     _name = 'assignment_ftp_interface.assignment_ftp_interface'
#     _description = 'assignment_ftp_interface.assignment_ftp_interface'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

