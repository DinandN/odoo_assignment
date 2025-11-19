from odoo import models, api
from datetime import datetime, timedelta
import logging
import re
from typing import Optional, List, Dict, Any, Tuple, Set

_logger = logging.getLogger(__name__)

class CsvCleaner(models.TransientModel):
    _name = 'assignment_ftp_interface.csv_cleaner'
    _description = 'CSV Cleaner Transient Model'

    _device_columns = ['id', 'name', 'description', 'code', 'expire_date', 'state']
    _content_columns = ['id', 'name', 'description', 'device_code', 'expire_date', 'state']

    # --- DATETIME HELPER METHODS ---

    @staticmethod
    def _fix_malformed_timestamp(timestamp_str: str) -> Optional[datetime]:
        """
        Corrects a malformed timestamp string by parsing its components and using timedelta
        to handle rollovers (e.g., 66 seconds becomes 1 minute, 6 seconds).

        Args:
            timestamp_str: The raw timestamp string to fix.

        Returns:
            A corrected datetime object, or None if the format is unrecognizable.
        """
        pattern = re.compile(
            r'(\d{4})-(\d{2})-(\d{2})\s+'  # Date: YYYY-MM-DD
            r'(\d{2}):(\d{2}):(\d{2})'  # Time: HH:MM:SS
            r'(?:\.(\d+))?'  # Optional Milliseconds
            r'([+-]\d{2}:\d{2})?'  # Optional Timezone
        )
        match = pattern.match(timestamp_str)

        if not match:
            _logger.warning(f"Timestamp format not recognized: {timestamp_str}")
            return None

        parts = match.groups()
        year, month, day, hour, minute, second = [int(p) for p in parts[:6]]
        microsecond = int(parts[6].ljust(6, '0')[:6]) if parts[6] else 0

        try:
            base_date = datetime(year, month, day)
            corrected_dt = base_date + timedelta(
                hours=hour,
                minutes=minute,
                seconds=second,
                microseconds=microsecond
            )
            return corrected_dt

        except (ValueError, OverflowError) as e:
            _logger.warning(f"Could not construct a valid date from '{timestamp_str}': {e}")
            return None

    @staticmethod
    def _extract_latest_datetime_str(text: str) -> Optional[str]:
        """
        Finds all datetime-like strings in a line of text and returns the most recent one.

        Args:
            text: A string which may contain multiple datetimes.

        Returns:
            The string of the latest datetime found, or None.
        """
        pattern = r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2})?'
        matches = re.findall(pattern, text)

        if not matches:
            _logger.info(f"No datetime patterns found in text: {text}")
            return None

        if len(matches) > 1:
            _logger.info(f"Multiple datetimes found: {matches}. Selecting the latest.")
            return max(matches)

        return matches[0]

    def _parse_and_clean_datetime(self, text: str, line_num: int) -> Optional[datetime]:
        """
        Orchestrates the process of finding, cleaning, and parsing a datetime from a raw string.

        Args:
            text: The raw string from the CSV line.
            line_num: The current line number for logging.

        Returns:
            A valid datetime object or None if the process fails.
        """
        latest_datetime_str = self._extract_latest_datetime_str(text)

        if not latest_datetime_str:
            _logger.warning(f"Line {line_num}: No valid datetime pattern found.")
            return None

        cleaned_datetime = self._fix_malformed_timestamp(latest_datetime_str)

        if not cleaned_datetime:
            _logger.warning(
                f"Line {line_num}: Could not fix or parse the datetime string '{latest_datetime_str}'.")
            return None

        return cleaned_datetime

    # --- HELPER METHODS ---

    @staticmethod
    def _preprocess_and_split_line(line: str) -> List[str]:
        """
        Pre-processes a raw CSV line to handle specific malformations like
        missing commas between an ID and a quoted field, then splits it into a list of fields.
        """
        # Add a comma between a number and a quote if it's missing
        corrected_line = re.sub(r'(\d)(")', r'\1,\2', line.strip())

        # This regex finds a closing quote, optional whitespace, and an opening quote,
        # and replaces it with a '","' sequence to ensure separation.
        corrected_line = re.sub(r'"\s*"', '","', corrected_line)

        # Standardize commas by removing whitespace around them and remove any trailing comma.
        standardized_line = re.sub(r'\s*,\s*', ',', corrected_line).rstrip(',')

        # Split into a list of fields.
        return standardized_line.split(',')

    @staticmethod
    def _process_id(id_field: str, seen_ids: Set[int], line_num: int, original_line: str) -> Optional[int]:
        """Validates and processes the ID field, checking for duplicates."""
        id_str = re.sub(r'\D', '', id_field)
        if not id_str:
            _logger.warning(f"Line {line_num}: DISCARDED - No numeric ID found. Original line: '{original_line}'")
            return None

        device_id = int(id_str)
        if device_id in seen_ids:
            _logger.warning(
                f"Line {line_num}: DISCARDED - Duplicate ID '{device_id}' found. Original line: '{original_line}'")
            return None

        return device_id

    @staticmethod
    def _extract_status(fields: List[str]) -> str:
        """Extracts the status ('enabled' or 'deleted') from a list of fields."""
        for field in fields:
            if field.lower().strip() in ['enabled', 'deleted']:
                return field.lower().strip()
        return 'enabled'

    @staticmethod
    def _find_device_code(fields: List[str], seen_codes: Set[str], line_num: int, original_line: str) -> Optional[Tuple[str, int]]:
        """Finds the device code and its index, checking for duplicates."""
        for idx, field in enumerate(fields):
            cleaned_field = field.strip()
            if re.match(r'^[A-Z0-9]{4,30}$', cleaned_field):
                if cleaned_field in seen_codes:
                    _logger.warning(
                        f"Line {line_num}: DISCARDED - Duplicate code '{cleaned_field}' found. Original line: '{original_line}'")
                    return None
                return cleaned_field, idx

        _logger.warning(
            f"Line {line_num}: DISCARDED - No potential serial number/code found. Original line: '{original_line}'")
        return None

    @staticmethod
    def _extract_name_and_description(fields: List[str], code_index: int, device_id: int) -> Tuple[str, str]:
        """Extracts the device name and description based on the code's position."""
        if len(fields) > 1:
            device_name = fields[1].strip().strip('"')
        else:
            device_name = f"Machine {device_id}"

        description_parts = []
        if code_index > 2:
            description_parts = fields[2:code_index]
        device_description = " ".join(part.strip().strip('"') for part in description_parts)

        return device_name, device_description

    @staticmethod
    def _truncate_field(value: str, max_len: int, field_name: str, line_num: int) -> str:
        """Truncates a field to a maximum length and logs a warning if it was too long."""
        if len(value) > max_len:
            _logger.warning(f"Line {line_num}: {field_name} too long, truncating. Original: '{value}'")
            return value[:max_len]
        return value

    # --- MAIN CLEANING METHOD ---

    @api.model
    def clean_device_data(self, raw_data: str) -> List[Dict[str, Any]]:
        """
        Cleans and validates raw CSV data for device import with detailed logging.
        """
        cleaned_rows = []
        seen_ids = set()
        seen_codes = set()
        discarded_rows = 0

        lines = raw_data.strip().split('\n')
        total_rows = len(lines)
        _logger.info(f"Starting cleaning process for {total_rows} raw lines.")

        for i, line in enumerate(lines, 1):
            if not line.strip():
                _logger.warning(f"Line {i}: Skipping empty line.")
                discarded_rows += 1
                continue

            original_line = line
            fields = self._preprocess_and_split_line(original_line)
            if not fields or not fields[0]:
                _logger.warning(
                    f"Line {i}: DISCARDED - Line appears to be empty after processing. Original line: '{original_line}'")
                discarded_rows += 1
                continue

            # 1. Process ID
            device_id = self._process_id(fields[0], seen_ids, i, original_line)
            if device_id is None:
                discarded_rows += 1
                continue

            # 2. Process Datetime
            latest_dt_obj = self._parse_and_clean_datetime(original_line, i)
            if not latest_dt_obj:
                _logger.warning(
                    f"Line {i}: DISCARDED - No valid datetime could be processed. Original line: '{original_line}'")
                discarded_rows += 1
                continue
            latest_datetime_str = latest_dt_obj.strftime('%Y-%m-%d %H:%M:%S')

            # 3. Extract Status
            status = self._extract_status(fields)

            # 4. Find Device Code
            code_info = self._find_device_code(fields, seen_codes, i, original_line)
            if not code_info:
                discarded_rows += 1
                continue
            device_code, code_index = code_info

            # 5. Extract Name and Description
            device_name, device_description = self._extract_name_and_description(fields, code_index, device_id)

            # 6. Validate Field Lengths
            device_name = self._truncate_field(device_name, 32, "Name", i)
            device_description = self._truncate_field(device_description, 128, "Description", i)

            # 7. Final Assembly
            final_row = {
                'id': device_id,
                'name': device_name,
                'description': device_description,
                'code': device_code,
                'expire_date': latest_datetime_str,
                'state': status
            }

            cleaned_rows.append(final_row)
            seen_ids.add(device_id)
            seen_codes.add(device_code)
            _logger.info(f"Line {i}: Successfully cleaned row. Result: {final_row}")

        success_rows = len(cleaned_rows)
        _logger.info(
            f"Cleaning process finished. Total rows: {total_rows}, "
            f"Successfully cleaned: {success_rows}, Discarded: {discarded_rows}."
        )
        return cleaned_rows