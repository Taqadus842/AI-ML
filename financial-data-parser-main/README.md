# THIS PROJECT IS STILL WORK IN PROGRESS

# Financial Data Parser

A simple system to read financial Excel files, detect data types, parse complex formats, and store data for fast analysis.

## Phases

### Phase 1: Read Excel Files
- Load `KH_Bank.xlsx` and `Customer_Ledger_Entries_FULL.xlsx`
- Use `pandas` and `openpyxl`
- Show sheet names, dimensions, and column lists

### Phase 2: Detect Data Types
Automatically classify each column as:
- **String**: Names, descriptions, categories
- **Number**: Amounts, balances, quantities
- **Date**: Transaction dates, periods
- Uses confidence scoring to decide the best type

### Phase 3: Parse Complex Formats
Convert messy values into clean data:
- **Amounts**: `$1,234.56`, `(500.00)`, `1.5M`, `€1.234,56`
- **Dates**: `12/31/2023`, `Q1-24`, `Dec-23`, Excel serials (`44927`)

### Phase 4: Store & Query Data
- Save cleaned data in efficient structures
- Support fast lookups and filters
- Enable grouping and aggregations (sum, average)
- Uses: Pandas DataFrames, dictionaries, and SQLite

## Getting Started

1. **Install libraries**:
   ```python
   pandas, openpyxl, numpy, sqlite3, re, datetime, decimal
   ```
2. **Run in Order**:
- Phase 1: Load and preview files
- Phase 2: Detect column types
- Phase 3: Parse values
- Phase 4: Store and query results

3. **Test with**:
    ```python
    # Amounts
    "$1,234.56", "(2,500.00)", "1.5M"
    # Dates
    "12/31/2023", "Q1-24", "44927"
    ```

# Tools Used:
- pandas: Data handling
- openpyxl: Read Excel files
- sqlite3: Fast in-memory queries
- re: Format detection