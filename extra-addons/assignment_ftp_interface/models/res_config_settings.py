from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    """
    Inherits from the base settings model to add fields for this module.
    """

    _inherit = 'res.config.settings'
    csv_import_path = fields.Char(
        string='CSV Directory Path',
        config_parameter='assignment_ftp_interface.csv_import_path',
        help="The local path to the directory containing the .csv files."
    )

    csv_delimiter = fields.Char(
        string='CSV Delimiter',
        config_parameter='assignment_ftp_interface.csv_delimiter',
        default=',',
        help="The delimiter to be used in the .csv files."
    )