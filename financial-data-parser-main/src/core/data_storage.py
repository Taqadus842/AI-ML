# File: financial_parser_phase4.py

import pandas as pd
import numpy as np
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
import io


# -----------------------------
# Register Decimal adapter/converter for SQLite
# -----------------------------
def adapt_decimal(d):
    return str(d)

def convert_decimal(s):
    return Decimal(s)

sqlite3.register_adapter(Decimal, adapt_decimal)
sqlite3.register_converter("DECIMAL", convert_decimal)


class FinancialDataStore:
    """
    A class to store and manage parsed financial data with optimized structures
    for fast lookup, range queries, and aggregation.
    """

    def __init__(self):
        self.data = {}              # {dataset_name: DataFrame}
        self.metadata = {}          # {dataset_name: {col_name: type_info}}
        self.indexes = {}           # {dataset_name: {index_type: index_structure}}
        self.sqlite_conn = None     # In-memory SQLite connection
        self._init_sqlite()

    def _init_sqlite(self):
        """Initialize an in-memory SQLite database with Decimal support."""
        self.sqlite_conn = sqlite3.connect(
            ":memory:",
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.sqlite_conn.execute("PRAGMA temp_store = MEMORY;")
        self.sqlite_conn.execute("PRAGMA journal_mode = OFF;")

    def add_dataset(self, name: str, df: pd.DataFrame, column_types: Dict[str, Dict]):
        """
        Add a dataset to the store with metadata and indexes.

        Args:
            name (str): Dataset identifier
            df (pd.DataFrame): Parsed and cleaned DataFrame
            column_types (dict): {col_name: {'type': 'Date|Number|String', ...}}
        """
        print(f"[{datetime.now()}] Adding dataset: {name} ({len(df)} rows)")

        # Store data and metadata
        self.data[name] = df.copy()
        self.metadata[name] = column_types

        # Create indexes
        self._create_indexes(name, df, column_types)

        # Load into SQLite
        self._load_to_sqlite(name, df, column_types)

    def _create_indexes(self, name: str, df: pd.DataFrame, column_types: Dict[str, Dict]):
        """
        Create optimized lookup indexes for common query types.
        """
        index_store = {
            'date_columns': {},
            'numeric_columns': {},
            'category_columns': {},
            'multi_index': None
        }

        date_cols = []
        numeric_cols = []
        category_cols = []

        for col, info in column_types.items():
            if info['type'] == 'Date':
                date_cols.append(col)
            elif info['type'] == 'Number':
                numeric_cols.append(col)
            else:
                category_cols.append(col)

        # Date index: map date -> list of row indices
        for col in date_cols:
            date_index = {}
            for idx, val in enumerate(df[col]):
                if pd.notna(val) and isinstance(val, date):
                    if val not in date_index:
                        date_index[val] = []
                    date_index[val].append(idx)
            index_store['date_columns'][col] = date_index

        # Numeric index: store sorted values for range queries
        for col in numeric_cols:
            valid_vals = df[col].dropna()
            if not valid_vals.empty:
                sorted_vals = valid_vals.sort_values()
                index_store['numeric_columns'][col] = sorted_vals

        # Category index: map value -> list of row indices
        for col in category_cols:
            cat_index = {}
            for idx, val in enumerate(df[col]):
                if pd.notna(val):
                    key = str(val)
                    if key not in cat_index:
                        cat_index[key] = []
                    cat_index[key].append(idx)
            index_store['category_columns'][col] = cat_index

        # MultiIndex for fast groupby operations
        if len(df.columns) > 1:
            try:
                multi_idx = pd.MultiIndex.from_frame(df)
                index_store['multi_index'] = multi_idx
            except Exception:
                pass  # Skip if not possible

        self.indexes[name] = index_store

    def _load_to_sqlite(self, name: str, df: pd.DataFrame, column_types: Dict[str, Dict]):
        """
        Load dataset into SQLite for complex queries.
        Handles Decimal by converting to string.
        """
        # Normalize column names for SQLite
        df_copy = df.copy()
        df_copy.columns = [self._sanitize_column_name(col) for col in df.columns]

        # Convert date columns to string for SQLite storage
        for col, info in column_types.items():
            safe_col = self._sanitize_column_name(col)
            if info['type'] == 'Date' and safe_col in df_copy.columns:
                df_copy[safe_col] = df_copy[safe_col].apply(
                    lambda x: x.isoformat() if isinstance(x, date) else x
                )
            elif info['type'] == 'Number' and safe_col in df_copy.columns:
                # Convert Decimal to string for SQLite
                df_copy[safe_col] = df_copy[safe_col].apply(
                    lambda x: str(x) if isinstance(x, Decimal) else x
                )

        # Write to SQLite
        table_name = self._sanitize_table_name(name)
        df_copy.to_sql(table_name, self.sqlite_conn, if_exists='replace', index=False)
        print(f"[{datetime.now()}] Loaded {name} into SQLite table: {table_name}")

    def _sanitize_column_name(self, name: str) -> str:
        """Make column names SQLite-safe."""
        return "".join(ch for ch in name if ch.isalnum() or ch == '_').strip('_')

    def _sanitize_table_name(self, name: str) -> str:
        """Make table names SQLite-safe."""
        return "".join(ch for ch in name if ch.isalnum() or ch == '_').strip('_')

    def query_by_criteria(self, dataset_name: str, filters: Dict[str, Any]) -> pd.DataFrame:
        """
        Query dataset using key-value filters.
        Uses indexes where possible for performance.

        Args:
            dataset_name (str): Name of dataset
            filters (dict): {column: value} pairs

        Returns:
            pd.DataFrame: Filtered data
        """
        if dataset_name not in self.data:
            raise ValueError(f"Dataset '{dataset_name}' not found.")

        df = self.data[dataset_name]
        indexes = self.indexes.get(dataset_name, {})
        result_indices = set(range(len(df)))

        for col, value in filters.items():
            if col not in df.columns:
                continue

            # Use index if available
            col_type = self.metadata[dataset_name][col]['type']
            if col_type == 'Date' and col in indexes.get('date_columns', {}):
                date_idx = indexes['date_columns'][col]
                matching_indices = set(date_idx.get(value, []))
                result_indices &= matching_indices
            elif col_type == 'String' and col in indexes.get('category_columns', {}):
                cat_idx = indexes['category_columns'][col]
                matching_indices = set(cat_idx.get(str(value), []))
                result_indices &= matching_indices
            else:
                # Fallback to boolean indexing
                mask = df[col] == value
                matching_indices = set(df[mask].index)
                result_indices &= matching_indices

        # Return filtered DataFrame
        if result_indices:
            return df.iloc[sorted(result_indices)].copy()
        else:
            return pd.DataFrame(columns=df.columns)
    

    def query_sql(self, query: str) -> pd.DataFrame:
        """
        Execute raw SQL query on the SQLite database.

        Args:
            query (str): SQL query string

        Returns:
            pd.DataFrame: Query result
        """
        try:
            result_df = pd.read_sql_query(query, self.sqlite_conn)
            return result_df
        except Exception as e:
            print(f"SQLite query error: {e}")
            return pd.DataFrame()

    def get_dataset_info(self, dataset_name: str) -> Dict:
        """
        Get metadata and index info for a dataset.

        Args:
            dataset_name (str): Name of dataset

        Returns:
            dict: Info about the dataset
        """
        if dataset_name not in self.data:
            return {}

        df = self.data[dataset_name]
        meta = self.metadata.get(dataset_name, {})
        idxs = self.indexes.get(dataset_name, {})

        return {
            'rows': len(df),
            'columns': list(df.columns),
            'column_types': meta,
            'indexes': {
                'date_columns': list(idxs.get('date_columns', {}).keys()),
                'numeric_columns': list(idxs.get('numeric_columns', {}).keys()),
                'category_columns': list(idxs.get('category_columns', {}).keys())
            }
        }

    def close(self):
        """Close SQLite connection."""
        if self.sqlite_conn:
            self.sqlite_conn.close()
            
    def aggregate_data(self, dataset_name: str, group_by: List[str], measures: List[str]) -> pd.DataFrame:
        """
        Perform group-by aggregations on numeric columns.

        Args:
            dataset_name (str): Name of dataset
            group_by (list): Columns to group by
            measures (list): Numeric columns to aggregate

        Returns:
            pd.DataFrame: Aggregated data
        """
        if dataset_name not in self.data:
            raise ValueError(f"Dataset '{dataset_name}' not found.")

        df = self.data[dataset_name].copy() # Work on a copy

        # Validate columns
        missing_group = [col for col in group_by if col not in df.columns]
        missing_meas = [col for col in measures if col not in df.columns]
        if missing_group or missing_meas:
            raise ValueError(f"Missing columns: group_by={missing_group}, measures={missing_meas}")

        # Identify Decimal columns among measures
        decimal_cols = []
        for col in measures:
            # Check the first non-null value to infer type
            series = df[col].dropna()
            if not series.empty:
                first_val = series.iloc[0]
                if isinstance(first_val, Decimal):
                    decimal_cols.append(col)

        # For aggregation, convert Decimal columns to float to avoid pandas errors
        temp_cols = {} # To store original Decimal series for potential restoration
        for col in decimal_cols:
            temp_cols[col] = df[col] # Store original
            # Convert to float, handling None/NaN
            df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

        # Select only the columns needed for aggregation and ensure they are numeric
        agg_df = df[group_by + measures]
        # This step ensures that even if conversion above failed, non-numeric cols are excluded
        numeric_df = agg_df.select_dtypes(include=[np.number, np.floating, np.integer, 'float64', 'int64'])

        # If no numeric columns left after selection and conversion, return empty
        if numeric_df.empty or len(numeric_df.columns) == len(group_by):
            # No measure columns to aggregate
            return pd.DataFrame()

        # Determine which measure columns are actually numeric now
        measure_cols_for_agg = [col for col in measures if col in numeric_df.columns]

        if not measure_cols_for_agg:
            return pd.DataFrame()

        # Define aggregation functions
        agg_dict = {col: ['sum', 'mean', 'count'] for col in measure_cols_for_agg}

        try:
            # Perform groupby and aggregation
            grouped = agg_df.groupby(group_by).agg(agg_dict)
            # Flatten the MultiIndex columns created by agg
            grouped.columns = ['_'.join(col).strip() for col in grouped.columns]
            # Reset index to make group_by columns regular columns again
            result = grouped.reset_index()
            
            # Optional: Convert aggregated float results back to Decimal if desired
            # This is often not necessary for display/analysis, but can be done here if needed
            
            return result
        except Exception as e:
            print(f"Aggregation error: {e}")
            return pd.DataFrame()


# -----------------------------
#        Usage Example
# -----------------------------

if __name__ == "__main__":
    # This would normally come from earlier phases
    # For demo, we'll simulate parsed data

    # Sample parsed data
    sample_data = pd.DataFrame({
        'Date': [date(2023, 1, 15), date(2023, 2, 20), date(2023, 1, 15)],
        'Amount': [Decimal('1234.56'), Decimal('-2500.00'), Decimal('999.99')],
        'Category': ['Revenue', 'Expense', 'Revenue'],
        'Description': ['Sales', 'Office Supplies', 'Consulting']
    })

    column_types = {
        'Date': {'type': 'Date', 'confidence': 1.0},
        'Amount': {'type': 'Number', 'confidence': 1.0},
        'Category': {'type': 'String', 'confidence': 1.0},
        'Description': {'type': 'String', 'confidence': 1.0}
    }

    # Initialize store
    store = FinancialDataStore()

    try:
        # Add dataset
        store.add_dataset("sample_transactions", sample_data, column_types)

        # Query by criteria
        print("\n--- Query by Date ---")
        result = store.query_by_criteria("sample_transactions", {"Date": date(2023, 1, 15)})
        print(result)

        # Aggregate data
        print("\n--- Aggregate by Category ---")
        agg_result = store.aggregate_data(
            "sample_transactions",
            group_by=["Category"],
            measures=["Amount"]
        )
        print(agg_result)

        # Raw SQL query
        print("\n--- SQL Query ---")
        sql_result = store.query_sql("SELECT * FROM sample_transactions WHERE Amount > 0")
        print(sql_result)

        # Dataset info
        print("\n--- Dataset Info ---")
        info = store.get_dataset_info("sample_transactions")
        print(info)

    except Exception as e:
        print(f"Error in Phase 4: {e}")
    finally:
        store.close()