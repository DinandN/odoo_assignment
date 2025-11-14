# -*- coding: utf-8 -*-
# from odoo import http


# class AssignmentFtpInterface(http.Controller):
#     @http.route('/assignment_ftp_interface/assignment_ftp_interface', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/assignment_ftp_interface/assignment_ftp_interface/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('assignment_ftp_interface.listing', {
#             'root': '/assignment_ftp_interface/assignment_ftp_interface',
#             'objects': http.request.env['assignment_ftp_interface.assignment_ftp_interface'].search([]),
#         })

#     @http.route('/assignment_ftp_interface/assignment_ftp_interface/objects/<model("assignment_ftp_interface.assignment_ftp_interface"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('assignment_ftp_interface.object', {
#             'object': obj
#         })

