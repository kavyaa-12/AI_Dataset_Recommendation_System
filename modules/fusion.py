import os
import pandas as pd
import numpy as np
from config import FUSED_FOLDER
from modules.preprocessing import clean_column_names, auto_impute, standardize_types
from modules.compatibility import find_primary_key

def execute_fusion(filepath_a, filepath_b, strategy, key_col=None, impute=False):
    """
    Fuses Dataset A and Dataset B according to the selected strategy.
    Strategies: 'union', 'concat', 'inner_join', 'left_join', 'right_join', 'outer_join'
    Saves outputs as CSV, Excel, and JSON in the fused directory.
    Returns:
        - stats (dict of fusion statistics)
        - file_paths (dict of output file paths)
    """
    if not os.path.exists(filepath_a) or not os.path.exists(filepath_b):
        raise FileNotFoundError("One or both datasets could not be located.")
        
    df_a = clean_column_names(pd.read_csv(filepath_a))
    df_b = clean_column_names(pd.read_csv(filepath_b))
    
    # Auto-detect key if not provided
    if not key_col and strategy in ['inner_join', 'left_join', 'right_join', 'outer_join']:
        key_col = find_primary_key(df_a, df_b)
        if not key_col:
            raise ValueError(f"No common key column found for {strategy}. Please choose Concatenation or Union.")
            
    df_fused = None
    
    if strategy == "union":
        # Concatenate rows, aligning column names, padding missing columns with nulls
        # Ensure column order is standardized by sorting columns
        df_a_aligned = df_a.copy()
        df_b_aligned = df_b.copy()
        
        # Sort columns to align order
        all_cols = sorted(list(set(df_a.columns).union(set(df_b.columns))))
        for col in all_cols:
            if col not in df_a_aligned.columns:
                df_a_aligned[col] = np.nan
            if col not in df_b_aligned.columns:
                df_b_aligned[col] = np.nan
                
        df_a_aligned = df_a_aligned[all_cols]
        df_b_aligned = df_b_aligned[all_cols]
        
        df_fused = pd.concat([df_a_aligned, df_b_aligned], ignore_index=True)
        # Drop exact row duplicates introduced by combining
        df_fused.drop_duplicates(inplace=True)
        
    elif strategy == "concat":
        # Simple horizontal concatenation (side by side)
        # Handle index alignment by resetting index
        df_a_reset = df_a.reset_index(drop=True)
        df_b_reset = df_b.reset_index(drop=True)
        
        # Avoid duplicate column names by suffixing
        dup_cols = set(df_a_reset.columns).intersection(set(df_b_reset.columns))
        if dup_cols:
            df_b_reset.rename(columns={c: f"{c}_b" for c in dup_cols}, inplace=True)
            
        df_fused = pd.concat([df_a_reset, df_b_reset], axis=1)
        
    elif strategy in ["left_join", "right_join", "inner_join", "outer_join"]:
        how_map = {
            "left_join": "left",
            "right_join": "right",
            "inner_join": "inner",
            "outer_join": "outer"
        }
        how = how_map[strategy]
        
        # Merge on key_col
        # Suffix duplicate columns from B
        df_fused = pd.merge(df_a, df_b, on=key_col, how=how, suffixes=('', '_b'))
        # Deduplicate rows
        df_fused.drop_duplicates(inplace=True)
        
    else:
        raise ValueError(f"Invalid fusion strategy: {strategy}")
        
    if df_fused is None:
        raise ValueError("Fusion failed to construct DataFrame.")
        
    # Standardize data types
    df_fused = standardize_types(df_fused)
    
    # Optional auto-imputation of nulls
    if impute:
        df_fused = auto_impute(df_fused)
        
    # Define file names
    base_name = f"fused_{strategy}_{os.path.basename(filepath_a).split('.')[0]}_{os.path.basename(filepath_b).split('.')[0]}"
    
    # Ensure folder exists
    os.makedirs(FUSED_FOLDER, exist_ok=True)
    
    csv_path = os.path.join(FUSED_FOLDER, f"{base_name}.csv")
    xlsx_path = os.path.join(FUSED_FOLDER, f"{base_name}.xlsx")
    json_path = os.path.join(FUSED_FOLDER, f"{base_name}.json")
    
    # Save outputs
    df_fused.to_csv(csv_path, index=False)
    
    try:
        df_fused.to_excel(xlsx_path, index=False, engine='openpyxl')
    except Exception as e:
        # Fallback if openpyxl fails
        xlsx_path = None
        
    # JSON output formatted as list of records
    df_fused.to_json(json_path, orient='records', indent=4)
    
    # Compute fusion statistics
    final_rows = len(df_fused)
    final_cols = len(df_fused.columns)
    total_cells = final_rows * final_cols
    null_cells = int(df_fused.isnull().sum().sum())
    missing_ratio = (null_cells / total_cells) * 100 if total_cells > 0 else 0.0
    
    stats = {
        "strategy": strategy,
        "primary_key": key_col,
        "rows_before_a": len(df_a),
        "rows_before_b": len(df_b),
        "cols_before_a": len(df_a.columns),
        "cols_before_b": len(df_b.columns),
        "rows_after": final_rows,
        "cols_after": final_cols,
        "missing_cells": null_cells,
        "missing_ratio": round(missing_ratio, 2),
        "duplicate_rows": int(df_fused.duplicated().sum())
    }
    
    file_paths = {
        "csv": csv_path,
        "csv_filename": f"{base_name}.csv",
        "xlsx": xlsx_path,
        "xlsx_filename": f"{base_name}.xlsx" if xlsx_path else None,
        "json": json_path,
        "json_filename": f"{base_name}.json"
    }
    
    # Save statistics metadata to results for easy retrieval
    results_dir = os.path.join(os.path.dirname(FUSED_FOLDER), 'results')
    os.makedirs(results_dir, exist_ok=True)
    meta_path = os.path.join(results_dir, f"{base_name}_stats.json")
    with open(meta_path, 'w') as f:
        import json as json_lib
        json_lib.dump({"stats": stats, "files": file_paths}, f, indent=4)
        
    return stats, file_paths
