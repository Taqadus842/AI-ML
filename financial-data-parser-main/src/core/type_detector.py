# File: financial_parser_phase2.py

import pandas as pd
import numpy as np
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, Tuple, Optional


class DataTypeDetector:
    """
    A class to detect and classify column data types in financial datasets.
    Supports String, Number, and Date types with confidence scoring.
    """

    def __init__(self):
        # Pre-compiled regex patterns for performance
        self.date_patterns = [
            re.compile(r'^\d{1,2}/\d{1,2}/\d{4}$', re.IGNORECASE),           # MM/DD/YYYY or DD/MM/YYYY
            re.compile(r'^\d{4}-\d{2}-\d{2}$', re.IGNORECASE),               # YYYY-MM-DD
            re.compile(r'^\d{1,2}-[A-Z]{3}-\d{4}$', re.IGNORECASE),          # DD-MON-YYYY
            re.compile(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[ -]\d{4}$', re.IGNORECASE),  # Mar 2024
            re.compile(r'^(January|February|March|April|May|June|July|August|September|October|November|December) \d{4}$', re.IGNORECASE),
            re.compile(r'^Q[1-4] ?[-\s]?[0-9]{2,4}$', re.IGNORECASE),       # Q1-24, Q4 2023
            re.compile(r'^Quarter [1-4] \d{4}$', re.IGNORECASE)
        ]

    def detect_column_type(self, column: pd.Series) -> Dict[str, float]:
        """
        Detect the most likely type of a column with confidence scores.

        Args:
            column (pd.Series): A column of data

        Returns:
            dict: {'type': 'Date|Number|String', 'confidence': 0.0-1.0, 'format_hint': str}
        """
        # Remove nulls
        non_null = column.dropna()
        if len(non_null) == 0:
            return {'type': 'String', 'confidence': 1.0, 'format_hint': 'empty_or_null'}

        total = len(non_null)
        if total == 0:
            return {'type': 'String', 'confidence': 1.0, 'format_hint': 'no_data'}

        # Use first 1000 values for performance
        sample = non_null.head(1000)

        date_matches = 0
        number_matches = 0
        format_hint = None

        for val in sample:
            val_type = type(val)

            # Skip complex types
            if val_type not in (str, int, float, np.integer, np.floating):
                continue

            # Convert everything to string for parsing (except numbers)
            if val_type in (int, float, np.integer, np.floating):
                str_val = str(val)
            else:
                str_val = val.strip() if isinstance(val, str) else str(val)

            # Try date first (highest priority)
            date_result = self.detect_date_format(str_val)
            if date_result['is_match']:
                date_matches += 1
                if not format_hint and date_result['format']:
                    format_hint = date_result['format']
                continue  # Dates take precedence

            # Then try number
            num_result = self.detect_number_format(str_val)
            if num_result['is_match']:
                number_matches += 1
                if not format_hint and num_result['format']:
                    format_hint = num_result['format']

        # Compute confidence scores
        date_score = date_matches / len(sample)
        number_score = number_matches / len(sample)

        # Final decision
        if date_score > 0.7:
            return {'type': 'Date', 'confidence': round(date_score, 3), 'format_hint': format_hint}
        elif number_score > 0.7:
            return {'type': 'Number', 'confidence': round(number_score, 3), 'format_hint': format_hint}
        else:
            return {'type': 'String', 'confidence': round(1.0 - max(date_score, number_score), 3), 'format_hint': None}

    def detect_date_format(self, value: str) -> Dict[str, object]:
        """
        Check if value matches any known date format.
        Returns match status and format hint.
        """
        value = value.strip()

        # Handle Excel serial dates (e.g., 44927 = Jan 1, 2023)
        if value.isdigit():
            serial = int(value)
            if 1 <= serial <= 2958465:  # Excel date range: 1900-01-01 to 9999-12-31
                try:
                    # Excel serial 1 = Dec 31 1899 (Windows epoch)
                    base = datetime(1899, 12, 30)  # Adjust for Excel leap year bug
                    dt = base + pd.Timedelta(days=serial)
                    if 1900 <= dt.year <= 9999:
                        return {'is_match': True, 'format': 'ExcelSerial', 'value': dt}
                except:
                    pass

        # Regular string patterns (regex pre-compiled)
        for pattern in self.date_patterns:
            if pattern.match(value):
                return {'is_match': True, 'format': 'PatternMatch'}

        # Try parsing common formats
        date_formats = [
            ('%m/%d/%Y', 'MM/DD/YYYY'),
            ('%d/%m/%Y', 'DD/MM/YYYY'),
            ('%Y-%m-%d', 'YYYY-MM-DD'),
            ('%d-%b-%Y', 'DD-MON-YYYY'),
            ('%b %Y', 'MON YYYY'),
            ('%B %Y', 'MONTH YYYY'),
        ]

        for fmt, hint in date_formats:
            try:
                datetime.strptime(value, fmt)
                return {'is_match': True, 'format': hint}
            except ValueError:
                continue

        return {'is_match': False, 'format': None}

    def detect_number_format(self, value: str) -> Dict[str, object]:
        """
        Detect if value is a number, including currency, negatives, and abbreviations.
        Returns match status, format, and normalized Decimal if possible.
        """
        value = value.strip().lower()

        if not value:
            return {'is_match': False, 'format': None}

        # Remove leading/trailing non-numeric chars (but keep -+. and digits)
        cleaned = re.sub(r'^[^\d\-\+\.]+', '', value)
        cleaned = re.sub(r'[^\d\-\+\.]+$', '', cleaned)
        if not cleaned:
            return {'is_match': False, 'format': None}

        # Handle parentheses for negatives: (1,234.56) → -1234.56
        if value.startswith('(') and value.endswith(')'):
            cleaned = '-' + re.sub(r'[^\d\-\+\.]', '', cleaned.replace('(', '').replace(')', ''))
        elif value.endswith('-'):
            cleaned = '-' + re.sub(r'[^\d\-\+\.]', '', value[:-1])

        # Remove commas and other thousand separators
        num_str = re.sub(r'[,\s]', '', cleaned)

        # Handle abbreviated numbers: 1.5K, 2.5M, 1.2B
        abbrev_match = re.match(r'^([+-]?\d*\.?\d+)\s*([kmb])$', num_str)
        if abbrev_match:
            num = float(abbrev_match.group(1))
            suffix = abbrev_match.group(2)
            multiplier = {'k': 1_000, 'm': 1_000_000, 'b': 1_000_000_000}[suffix]
            try:
                result = Decimal(str(num * multiplier))
                return {'is_match': True, 'format': f'Abbreviated-{suffix.upper()}', 'value': result}
            except InvalidOperation:
                pass

        # Try to parse as regular number
        try:
            result = Decimal(num_str)
            return {'is_match': True, 'format': 'Decimal', 'value': result}
        except InvalidOperation:
            pass

        # Currency symbols at start/end
        currency_pattern = r'^[€$₹£¥]([ \d,]+\.?\d*)$|([ \d,]+\.?\d*)[€$₹£¥]$'
        currency_match = re.match(currency_pattern, value)
        if currency_match:
            num_part = currency_match.group(1) or currency_match.group(2)
            num_part = re.sub(r'[,\s]', '', num_part)
            try:
                result = Decimal(num_part)
                symbol = 'Euro' if '€' in value else 'USD' if '$' in value else 'INR' if '₹' in value else 'GBP' if '£' in value else 'JPY' if '¥' in value else 'Other'
                return {'is_match': True, 'format': f'Currency-{symbol}', 'value': result}
            except InvalidOperation:
                pass

        return {'is_match': False, 'format': None}
    
# Try it out! Uncomment the following code:
    
# if __name__ == "__main__":
#     FILE_PATHS = {
#         "KH_Bank": "data/sample/KH_Bank.xlsx",
#         "Customer_Ledger": "data/sample/Customer_Ledger_Entries_FULL.xlsx"
#     }

#     try:
#         df = pd.read_excel(FILE_PATHS["KH_Bank"], sheet_name=0, engine='openpyxl')
#         print(f"Loaded '{FILE_PATHS['KH_Bank']}' with {df.shape[1]} columns.\n")

#         detector = DataTypeDetector()

#         for col in df.columns:
#             series = df[col]
#             result = detector.detect_column_type(series)
#             print(f"Column: '{col}' → Type: {result['type']} "
#                   f"(Confidence: {result['confidence']:.2f}) "
#                   f"[Format: {result['format_hint']}]")

#     except Exception as e:
#         print(f"Error in Phase 2: {e}")