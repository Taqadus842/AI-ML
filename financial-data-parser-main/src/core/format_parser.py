# File: financial_parser_phase3.py

import pandas as pd
import numpy as np
import re
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation


class FormatParser:
    """
    A class to parse and normalize financial data values based on detected formats.
    Supports amount and date normalization.
    """

    def __init__(self):
        # Precompile regex for performance
        self.amount_patterns = {
            'parentheses': re.compile(r'^\((.*)\)$'),
            'trailing_minus': re.compile(r'^(.*)-$'),
            'currency_prefix': re.compile(r'^[€$₹£¥](.+)$'),
            'currency_suffix': re.compile(r'^(.+)[€$₹£¥]$'),
            'abbreviated': re.compile(r'^([+-]?\d*\.?\d+)\s*([kmb])$', re.IGNORECASE),
            'comma_number': re.compile(r'^[\d,]+\.?\d*$'),
            'euro_number': re.compile(r'^[\d.]+,?\d*$'),
        }

        self.date_patterns = {
            'mm/dd/yyyy': re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{4})$'),
            'yyyy-mm-dd': re.compile(r'^(\d{4})-(\d{1,2})-(\d{1,2})$'),
            'dd-mon-yyyy': re.compile(r'^(\d{1,2})-([A-Za-z]{3})-(\d{4})$'),
            'mon-yyyy': re.compile(r'^([A-Za-z]+) (\d{4})$'),
            'quarter': re.compile(r'^(Q[1-4])\s*[-\s]?\s*(\d{2,4})$', re.IGNORECASE),
            'quarter_full': re.compile(r'^Quarter ([1-4]) (\d{4})$', re.IGNORECASE),
        }

        self.month_map = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
            'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }

    def parse_amount(self, value, detected_format=None) -> Decimal:
        """
        Parse a value into a normalized Decimal amount.

        Args:
            value: Raw value (str, int, float)
            detected_format: Optional hint from DataTypeDetector

        Returns:
            Decimal: Normalized amount, or None if invalid
        """
        if pd.isna(value):
            return None

        if isinstance(value, (int, float, np.integer, np.floating)):
            try:
                return Decimal(str(value))
            except InvalidOperation:
                return None

        original = str(value).strip()
        s = original.lower()

        # Handle parentheses for negative: (1,234.56) -> -1234.56
        m = self.amount_patterns['parentheses'].match(s)
        if m:
            inner = m.group(1)
            result = self._clean_and_parse_number(inner)
            return -result if result is not None else None

        # Handle trailing minus: 1234.56- -> -1234.56
        m = self.amount_patterns['trailing_minus'].match(s)
        if m:
            inner = m.group(1)
            result = self._clean_and_parse_number(inner)
            return -result if result is not None else None

        # Handle abbreviated: 1.5M -> 1500000
        m = self.amount_patterns['abbreviated'].match(s)
        if m:
            num = float(m.group(1))
            suffix = m.group(2).lower()
            multiplier = {'k': 1_000, 'm': 1_000_000, 'b': 1_000_000_000}.get(suffix, 1)
            try:
                return Decimal(str(num * multiplier))
            except InvalidOperation:
                return None

        # Handle currency prefix/suffix
        m = self.amount_patterns['currency_prefix'].match(original)
        if m:
            inner = m.group(1)
            return self._clean_and_parse_number(inner)

        m = self.amount_patterns['currency_suffix'].match(original)
        if m:
            inner = m.group(1)
            return self._clean_and_parse_number(inner)

        # Fallback: clean and parse
        return self._clean_and_parse_number(s)

    def _clean_and_parse_number(self, s: str) -> Decimal:
        """
        Remove commas, spaces, and other separators, then parse to Decimal.
        Handles both US (1,234.56) and European (1.234,56) formats.
        """
        s = s.strip()
        if not s:
            return None

        # Try standard format first (comma as thousand, dot as decimal)
        cleaned = re.sub(r'[^\d\.\-+]', '', s)
        if '.' in cleaned and ',' in s:
            # Likely European format: 1.234,56
            # Replace . with nothing, , with .
            cleaned = s.replace('.', '').replace(',', '.')
            cleaned = re.sub(r'[^\d\.\-+]', '', cleaned)
        elif ',' in s:
            # US format: 1,234.56
            cleaned = s.replace(',', '')

        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

    def parse_date(self, value, detected_format=None) -> date:
        """
        Parse a value into a normalized datetime.date object.

        Args:
            value: Raw value (str, int)
            detected_format: Optional hint from DataTypeDetector

        Returns:
            date: Normalized date, or None if invalid
        """
        if pd.isna(value):
            return None

        if isinstance(value, (int, np.integer)):
            # Excel serial date
            try:
                serial = int(value)
                if 1 <= serial <= 2958465:
                    base = datetime(1899, 12, 30)  # Excel epoch
                    dt = base + timedelta(days=serial)
                    return dt.date()
            except:
                return None

        s = str(value).strip()

        # MM/DD/YYYY or DD/MM/YYYY
        m = self.date_patterns['mm/dd/yyyy'].match(s)
        if m:
            try:
                month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
                # Heuristic: if day > 12, assume DD/MM/YYYY
                if day > 12:
                    return date(year, month, day)
                else:
                    # Default to MM/DD/YYYY unless clear DD/MM
                    return date(year, month, day)
            except ValueError:
                pass

        # YYYY-MM-DD
        m = self.date_patterns['yyyy-mm-dd'].match(s)
        if m:
            try:
                year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
                return date(year, month, day)
            except ValueError:
                pass

        # DD-MON-YYYY
        m = self.date_patterns['dd-mon-yyyy'].match(s)
        if m:
            try:
                day = int(m.group(1))
                mon = m.group(2).lower()
                year = int(m.group(3))
                month = self.month_map.get(mon)
                if month:
                    return date(year, month, day)
            except (ValueError, KeyError):
                pass

        # MON YYYY or MONTH YYYY
        m = self.date_patterns['mon-yyyy'].match(s)
        if m:
            try:
                mon = m.group(1)[:3].lower()
                year = int(m.group(2))
                month = self.month_map.get(mon)
                if month:
                    # Return first day of month
                    return date(year, month, 1)
            except (ValueError, KeyError):
                pass

        # Q1-24 or Quarter 1 2024
        m = self.date_patterns['quarter'].match(s)
        if m:
            try:
                q = int(m.group(1)[1])
                year = int(m.group(2))
                if len(str(year)) == 2:
                    year += 2000 if year < 50 else 1900
                month = (q - 1) * 3 + 1
                return date(year, month, 1)
            except (ValueError, IndexError):
                pass

        m = self.date_patterns['quarter_full'].match(s)
        if m:
            try:
                q = int(m.group(1))
                year = int(m.group(2))
                month = (q - 1) * 3 + 1
                return date(year, month, 1)
            except ValueError:
                pass

        return None


# -----------------------------
#        Usage Example
# -----------------------------

if __name__ == "__main__":
    parser = FormatParser()

    # Test amounts
    test_amounts = [
        "$1,234.56", "(2,500.00)", "€1.234,56", "1.5M", "₹1,23,456",
        "1234.56-", "£1,234.56", "¥1234.56"
    ]

    print("=== Amount Parsing ===")
    for val in test_amounts:
        parsed = parser.parse_amount(val)
        print(f"{val:>12} → {parsed}")

    # Test dates
    test_dates = [
        "12/31/2023", "2023-12-31", "Q4 2023", "Dec-23", "44927",
        "01-Jan-2024", "March 2024", "Q1-24"
    ]

    print("\n=== Date Parsing ===")
    for val in test_dates:
        parsed = parser.parse_date(val)
        print(f"{val:>12} → {parsed}")
    