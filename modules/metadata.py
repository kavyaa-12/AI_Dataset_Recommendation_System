import os
import pandas as pd
import numpy as np

def get_file_size(filepath):
    """
    Returns file size in bytes and a human-readable formatted string.
    """
    try:
        size_bytes = os.path.getsize(filepath)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return size_bytes, f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return size_bytes * 1024.0, f"{size_bytes * 1024.0:.2f} GB"
    except Exception:
        return 0, "0 B"

def extract_metadata(filepath):
    """
    Reads the CSV and extracts structural metadata:
    - Number of rows
    - Number of columns
    - Column names
    - Column data types (mapped to clean strings)
    - Duplicate rows count
    - File size
    - Estimated memory usage
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # Read CSV (limit reading rows initially if huge, but let's read full for profiling)
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise ValueError(f"Could not read CSV file. Error: {str(e)}")
    
    num_rows = len(df)
    num_cols = len(df.columns)
    column_names = list(df.columns)
    
    # Map pandas data types to clean, user-friendly labels
    dtypes_map = {}
    for col in df.columns:
        col_type = df[col].dtype
        if np.issubdtype(col_type, np.integer):
            dtypes_map[col] = "Integer"
        elif np.issubdtype(col_type, np.floating):
            dtypes_map[col] = "Float"
        elif np.issubdtype(col_type, np.datetime64) or df[col].astype(str).str.match(r'^\d{4}-\d{2}-\d{2}').all(): # Simple datetime heuristic
            dtypes_map[col] = "Datetime"
        elif col_type == object or isinstance(col_type, pd.CategoricalDtype):
            # Check if it could be a boolean
            unique_vals = df[col].dropna().unique()
            if len(unique_vals) <= 2 and all(str(v).lower() in ['true', 'false', 'yes', 'no', '1', '0', 't', 'f', 'y', 'n'] for v in unique_vals):
                dtypes_map[col] = "Boolean"
            else:
                dtypes_map[col] = "Categorical/String"
        else:
            dtypes_map[col] = str(col_type)

    # Estimate duplicates
    duplicate_count = int(df.duplicated().sum())
    
    # File size and memory usage
    size_bytes, size_str = get_file_size(filepath)
    memory_usage_bytes = df.memory_usage(deep=True).sum()
    memory_usage_str = f"{memory_usage_bytes / 1024:.2f} KB" if memory_usage_bytes < 1024*1024 else f"{memory_usage_bytes / (1024*1024):.2f} MB"
    
    # Separate numeric and categorical lists
    numeric_cols = [col for col, dtype in dtypes_map.items() if dtype in ["Integer", "Float"]]
    categorical_cols = [col for col, dtype in dtypes_map.items() if dtype in ["Categorical/String", "Boolean"]]
    
    return {
        "filename": os.path.basename(filepath),
        "num_rows": num_rows,
        "num_cols": num_cols,
        "column_names": column_names,
        "column_dtypes": dtypes_map,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
        "duplicate_rows": duplicate_count,
        "file_size_bytes": size_bytes,
        "file_size_str": size_str,
        "memory_usage_bytes": int(memory_usage_bytes),
        "memory_usage_str": memory_usage_str
    }
