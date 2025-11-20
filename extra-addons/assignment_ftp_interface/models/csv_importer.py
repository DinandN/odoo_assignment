from odoo import models, api
import os
from datetime import datetime
from ..utils import csv_cleaner
import logging

_logger = logging.getLogger(__name__)

class CsvImporter(models.Model):
    _name = 'assignment_ftp_interface.csv_importer'
    _description = 'CSV Import Transient Model'

    @api.model
    def get_csv_settings(self):
        """
        Retrieves the CSV import path and delimiter from the Odoo system parameters.
        """
        get_param = self.env['ir.config_parameter'].sudo().get_param
        # Retrieve the CSV path from settings
        path = get_param('assignment_ftp_interface.csv_import_path')
        # Retrieve the CSV delimiter from settings, with a fallback default of ','
        delimiter = get_param('assignment_ftp_interface.csv_delimiter', default=',')
        return path, delimiter

    @api.model
    def import_csv_data(self):
        _logger.info("Starting CSV import cron job.")

        csv_path, delimiter = self.get_csv_settings()

        if not csv_path:
            _logger.error("The CSV import path is not configured. Please set it in the settings.")
            return False

        self._import_devices(csv_path, delimiter)
        self._import_content(csv_path, delimiter)

        _logger.info("Finished CSV import cron job.")
        return True

    @api.model
    def _import_devices(self, path, delimiter):
        device_file_path = os.path.join(path, 'devices.csv')
        _logger.info(f"Starting import of devices from: {device_file_path}")
        try:
            with open(device_file_path, 'r', encoding='utf-8') as file:
                raw_content = file.read()
                cleaned_data = csv_cleaner.clean_device_data(raw_content, delimiter)

                data_by_code = {row['code']: row for row in cleaned_data}
                csv_codes = list(data_by_code.keys())

                existing_devices = self.env['assignment_ftp_interface.device'].search([('code', 'in', csv_codes)])

                odoo_devices_by_code = {dev.code: dev for dev in existing_devices}

                devices_to_create_vals = []

                for code, row in data_by_code.items():
                    expire_date_obj = datetime.strptime(row['expire_date'], '%Y-%m-%d %H:%M:%S')
                    state = 'disabled' if expire_date_obj < datetime.now() else row.get('state', 'enabled')

                    vals = {
                        'device_id': row['id'],
                        'name': row['name'],
                        'description': row['description'],
                        'code': row['code'],
                        'expire_date': expire_date_obj.strftime('%Y-%m-%d %H:%M:%S'),
                        'state': state,
                    }

                    if code in odoo_devices_by_code:
                        device_to_update = odoo_devices_by_code[code]
                        device_to_update.write(vals)
                        _logger.info(f"Updating device with code: {code}")
                    else:
                        devices_to_create_vals.append(vals)

                if devices_to_create_vals:
                    self.env['assignment_ftp_interface.device'].create(devices_to_create_vals)
                    _logger.info(f"Created {len(devices_to_create_vals)} new devices in bulk.")


        except FileNotFoundError:
            _logger.error(f"Device CSV file not found at: {device_file_path}")
        except Exception as e:
            _logger.error(f"An unexpected error occurred during device import: {e}", exc_info=True)

    @api.model
    def _import_content(self, path, delimiter):
        content_file_path = os.path.join(path, 'content.csv')
        _logger.info(f"Starting BULK import of content from: {content_file_path}")
        try:
            with open(content_file_path, 'r', encoding='utf-8') as file:
                raw_content = file.read()
                cleaned_data = csv_cleaner.clean_content_data(raw_content, delimiter)

                all_devices = self.env['assignment_ftp_interface.device'].search([])
                devices_by_ext_id = {dev.device_id: dev.id for dev in all_devices if dev.device_id}

                data_by_id = {row['id']: row for row in cleaned_data}
                csv_ids = list(data_by_id.keys())

                existing_content = self.env['assignment_ftp_interface.content'].search(
                    [('content_id', 'in', csv_ids)])
                odoo_content_by_ext_id = {c.content_id: c for c in existing_content}

                content_to_create_vals = []

                for ext_id, row in data_by_id.items():
                    device_id = devices_by_ext_id.get(row['device_external_id'])
                    if not device_id:
                        _logger.error(f"Device link not found for content with content ID {ext_id}. Skipping.")
                        continue

                    expire_date_obj = datetime.strptime(row['expire_date'], '%Y-%m-%d %H:%M:%S')
                    state = 'disabled' if expire_date_obj < datetime.now() else row.get('state', 'enabled')

                    vals = {
                        'content_id': ext_id,
                        'name': row['name'],
                        'description': row['description'],
                        'device': device_id,
                        'expire_date': expire_date_obj.strftime('%Y-%m-%d %H:%M:%S'),
                        'state': state,
                    }

                    if ext_id in odoo_content_by_ext_id:
                        content_to_update = odoo_content_by_ext_id[ext_id]
                        content_to_update.write(vals)
                        _logger.info(f"Updating content with content ID: {ext_id}")
                    else:
                        content_to_create_vals.append(vals)

                if content_to_create_vals:
                    self.env['assignment_ftp_interface.content'].create(content_to_create_vals)
                    _logger.info(f"Created {len(content_to_create_vals)} new content records in bulk.")

        except FileNotFoundError:
            _logger.error(f"Content CSV file not found at: {content_file_path}")
        except Exception as e:
            _logger.error(f"An unexpected error occurred during content import: {e}", exc_info=True)