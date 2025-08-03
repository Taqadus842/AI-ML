# File: financial_parser_phase1.py

import pandas as pd
import openpyxl
from datetime import datetime
import os


class ExcelProcessor:
    """
    A class to process Excel files for financial data parsing.
    Phase 1: Read files, inspect sheets, display metadata.
    """
    
    def __init__(self):
        self.file_paths = {}
        self.workbooks = {}
        self.dataframes = {}

    def load_files(self, file_paths):
        """
        Load Excel files using pandas and openpyxl.
        
        Args:
            file_paths (dict): {'name': 'path/to/file.xlsx'}
        """
        self.file_paths = file_paths
        self.workbooks = {}
        self.dataframes = {}

        for name, path in file_paths.items():
            if not os.path.exists(path):
                raise FileNotFoundError(f"File not found: {path}")
            
            # Use openpyxl to load workbook (for sheet inspection)
            try:
                wb = openpyxl.load_workbook(path, read_only=True)
                self.workbooks[name] = wb
                print(f"[{datetime.now()}] Loaded workbook: {name} -> {path}")
            except Exception as e:
                raise Exception(f"Failed to load {path} with openpyxl: {e}")

            # Use pandas to read all sheets into DataFrames
            try:
                dfs = pd.read_excel(path, sheet_name=None, engine='openpyxl')
                self.dataframes[name] = dfs
                print(f"[{datetime.now()}] Loaded {len(dfs)} sheet(s) with pandas: {list(dfs.keys())}")
            except Exception as e:
                raise Exception(f"Failed to read {path} with pandas: {e}")

    def get_sheet_info(self):
        """
        Display basic information about each file and its sheets:
        - Sheet names
        - Dimensions (rows x cols)
        - Column names (first few)
        """
        info = {}

        for name in self.dataframes:
            print(f"\n=== File: {name} ===")
            file_info = []
            for sheet_name, df in self.dataframes[name].items():
                row_count, col_count = df.shape
                columns = list(df.columns)[:10]  # Show first 10 columns
                sheet_info = {
                    'sheet_name': sheet_name,
                    'rows': row_count,
                    'columns': col_count,
                    'column_names': columns
                }
                file_info.append(sheet_info)

                # Pretty print
                print(f"Sheet: '{sheet_name}'")
                print(f"  Dimensions: {row_count} rows × {col_count} columns")
                print(f"  Columns: {columns}")
                if len(df.columns) > 10:
                    print(f"  ... and {len(df.columns) - 10} more columns")

            info[name] = file_info
        return info

    def extract_data(self, sheet_name, file_key=None):
        """
        Extract data from a specific sheet.
        
        Args:
            sheet_name (str): Name of the sheet to extract
            file_key (str): Optional; specify which file (if multiple loaded)
        
        Returns:
            pd.DataFrame: The requested sheet's data, or None if not found
        """
        if file_key:
            if file_key in self.dataframes and sheet_name in self.dataframes[file_key]:
                return self.dataframes[file_key][sheet_name]
            else:
                print(f"Sheet '{sheet_name}' not found in file '{file_key}'")
                return None
        else:
            # Search across all files
            for name, dfs in self.dataframes.items():
                if sheet_name in dfs:
                    print(f"Found '{sheet_name}' in file: {name}")
                    return dfs[sheet_name]
            print(f"Sheet '{sheet_name}' not found in any loaded file.")
            return None

    def preview_data(self, file_key=None, sheet_name=None, rows=5):
        """
        Preview the first `rows` of data from specified or default sheet.
        
        Args:
            file_key (str): File name key
            sheet_name (str): Sheet to preview
            rows (int): Number of rows to show
        """
        if file_key is None:
            # Pick first file
            file_key = next(iter(self.dataframes))

        if sheet_name is None:
            # Pick first sheet
            sheet_name = next(iter(self.dataframes[file_key]))

        df = self.extract_data(sheet_name, file_key)
        if df is not None:
            print(f"\n--- Preview: {file_key} -> '{sheet_name}' (first {rows} rows) ---")
            print(df.head(rows))
        else:
            print("No data available to preview.")


# -----------------------------
#           Usage Example
# -----------------------------

if __name__ == "__main__":
    # Define file paths - UPDATE THESE PATHS TO POINT TO YOUR FILES
    FILE_PATHS = {
        "KH_Bank": "data/sample/KH_Bank.xlsx",
        "Customer_Ledger": "data/sample/Customer_Ledger_Entries_FULL.xlsx"
    }

    # Create processor instance
    processor = ExcelProcessor()

    try:
        # Load both files
        processor.load_files(FILE_PATHS)

        # Display sheet info
        info = processor.get_sheet_info()

        # Preview first few rows of first sheet in each file
        processor.preview_data(file_key="KH_Bank")
        processor.preview_data(file_key="Customer_Ledger")

    except Exception as e:
        print(f"Error during processing: {e}")