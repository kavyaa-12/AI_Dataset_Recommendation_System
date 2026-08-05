import pandas as pd
import numpy as np

def clean_column_names(df):
    """
    Cleans column names of a DataFrame:
    - Strips whitespace.
    - Replaces spaces and special characters with underscores.
    - Lowers casing.
    """
    df_cleaned = df.copy()
    new_cols = {}
    for col in df_cleaned.columns:
        clean_name = str(col).strip().lower().replace(" ", "_")
        # remove non-alphanumeric chars except underscores
        clean_name = "".join(c for c in clean_name if c.isalnum() or c == "_")
        new_cols[col] = clean_name
    df_cleaned.rename(columns=new_cols, inplace=True)
    return df_cleaned

def auto_impute(df, numeric_strategy='mean', categorical_strategy='mode'):
    """
    Imputes missing values in the DataFrame:
    - Numeric: 'mean', 'median', or 'zero'
    - Categorical: 'mode' or 'unknown'
    """
    df_imputed = df.copy()
    
    for col in df_imputed.columns:
        if df_imputed[col].isnull().sum() == 0:
            continue
            
        col_type = df_imputed[col].dtype
        if np.issubdtype(col_type, np.number):
            if numeric_strategy == 'mean':
                val = df_imputed[col].mean()
            elif numeric_strategy == 'median':
                val = df_imputed[col].median()
            else:
                val = 0.0
            df_imputed[col].fillna(val, inplace=True)
        else:
            if categorical_strategy == 'mode':
                modes = df_imputed[col].mode()
                val = str(modes.iloc[0]) if not modes.empty else "Unknown"
            else:
                val = "Unknown"
            df_imputed[col].fillna(val, inplace=True)
            
    return df_imputed

def standardize_types(df):
    """
    Attempts to cast columns to the most appropriate types:
    - Object/String columns that are purely numeric -> numeric.
    - Object/String columns that are valid dates -> datetime formatted as strings.
    """
    df_std = df.copy()
    
    for col in df_std.columns:
        # Check if object column is actually numeric
        if df_std[col].dtype == object:
            # Try to convert to numeric, ignoring errors
            converted = pd.to_numeric(df_std[col], errors='coerce')
            # If the proportion of successfully converted non-null values is high (> 90%), keep it
            nulls_before = df_std[col].isnull().sum()
            nulls_after = converted.isnull().sum()
            
            # If we didn't introduce a lot of new nulls, cast it
            if len(df_std) - nulls_after > 0 and (nulls_after - nulls_before) / len(df_std) < 0.10:
                df_std[col] = converted
                continue
                
            # Try datetime parsing
            try:
                # Only try if string contains date separators
                sample_non_null = df_std[col].dropna().head(10)
                if any(isinstance(x, str) and any(sep in x for sep in ['-', '/', '.']) for x in sample_non_null):
                    converted_dt = pd.to_datetime(df_std[col], errors='coerce')
                    if converted_dt.notnull().sum() / len(df_std) > 0.80:
                        df_std[col] = converted_dt
            except Exception:
                pass
                
    return df_std
