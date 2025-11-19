from odoo import models, api
from odoo.modules.module import get_module_path
import os
import csv
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class CsvImporter(models.TransientModel):
    _name = 'assignment_ftp_interface.csv_importer'
    _description = 'CSV Import Transient Model'

    @api.model
    def import_csv_data(self):
        _logger.info("Starting CSV import cron job.")

        #Get the module path`
        module_path = get_module_path('assignment_ftp_interface')
        csv_path = os.path.join(module_path, 'data', 'csv')
        _logger.info(f"Attempting to read CSV files from resolved path: {csv_path}")

        # Define the delimiter used in the CSV files
        delimiter = ','

        self._import_devices(csv_path, delimiter)
        # self._import_content(csv_path, delimiter)

        _logger.info("Finished CSV import cron job.")
        return True

    @api.model
    def _import_devices(self, path, delimiter):
        device_file_path = os.path.join(path, 'devices.csv')
        _logger.info(f"Starting import of devices from: {device_file_path}")
        try:
            with open(device_file_path, 'r', encoding='utf-8') as file:
                raw_content = file.read()

                # Use the cleaning function to preprocess the data
                cleaner_model = self.env['assignment_ftp_interface.csv_cleaner']
                cleaned_data = cleaner_model.clean_device_data(raw_content)

                for row in cleaned_data:
                    try:
                        # Data is now clean and validated, proceed with import
                        expire_date_obj = datetime.strptime(row['expire_date'], '%Y-%m-%d %H:%M:%S')

                        # The state is already cleaned, but you can add extra logic if needed
                        state = 'disabled' if expire_date_obj < datetime.now() else row.get('state', 'enabled')

                        device_vals = {
                            # The 'id' field from the CSV is not used to create the Odoo record ID
                            'name': row['name'],
                            'description': row['description'],
                            'code': row['code'],
                            'expire_date': expire_date_obj.strftime('%Y-%m-%d %H:%M:%S'),
                            'state': state,
                        }

                        # Search for existing device by the unique code
                        existing_device = self.env['assignment_ftp_interface.device'].search(
                            [('code', '=', row['code'])], limit=1)

                        if existing_device:
                            existing_device.write(device_vals)
                            _logger.info(f"Updated device with code: {row['code']}")
                        else:
                            self.env['assignment_ftp_interface.device'].create(device_vals)
                            _logger.info(f"Created new device with code: {row['code']}")

                    except Exception as e:
                        _logger.error(f"Error processing cleaned device row: {row}. Error: {e}")
        except FileNotFoundError:
            _logger.error(f"Device CSV file not found at: {device_file_path}")

    @api.model
    def _import_content(self, path, delimiter):
        content_file_path = os.path.join(path, 'content.csv')
        try:
            with open(content_file_path, 'r') as file:
                reader = csv.DictReader(file, delimiter=delimiter)
                for row in reader:
                    try:
                        device = self.env['device'].search([('code', '=', row['device_code'])], limit=1)
                        if not device:
                            _logger.warning(
                                f"Device with code {row['device_code']} not found for content {row['name']}. Skipping.")
                            continue

                        expire_date = datetime.strptime(row['expire_date'], '%Y-%m-%d %H:%M:%S')
                        state = 'disabled' if expire_date < datetime.now() else row.get('state', 'enabled')

                        content_vals = {
                            'name': row['name'],
                            'description': row['description'],
                            'device': device.id,
                            'expire_date': expire_date,
                            'state': state,
                        }

                        # Assuming content is uniquely identified by name and device for simplicity
                        existing_content = self.env['content'].search(
                            [('name', '=', row['name']), ('device', '=', device.id)], limit=1)
                        if existing_content:
                            existing_content.write(content_vals)
                            _logger.info(f"Updated content: {row['name']} for device: {device.code}")
                        else:
                            self.env['content'].create(content_vals)
                            _logger.info(f"Created new content: {row['name']} for device: {device.code}")

                    except Exception as e:
                        _logger.error(f"Error processing content row: {row}. Error: {e}")
        except FileNotFoundError:
            _logger.error(f"Content CSV file not found at: {content_file_path}")
