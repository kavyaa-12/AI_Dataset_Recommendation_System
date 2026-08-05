import os
import difflib
import numpy as np
import pandas as pd
from modules.preprocessing import clean_column_names

def find_primary_key(df_a, df_b):
    """
    Attempts to identify a common key column (e.g. 'id', 'uuid', 'code', 'date')
    present in both DataFrames.
    """
    a_cols = set(df_a.columns)
    b_cols = set(df_b.columns)
    common = a_cols.intersection(b_cols)
    
    key_candidates = ['id', 'uuid', 'code', 'date', 'index', 'key', 'pk']
    for candidate in key_candidates:
        # Check direct match
        if candidate in common:
            return candidate
        # Check suffix/prefix match
        for col in common:
            if col.endswith(f'_{candidate}') or col.startswith(f'{candidate}_'):
                return col
                
    # If no standard candidate, check if there's any column with high uniqueness in both
    for col in common:
        if df_a[col].nunique() == len(df_a) and df_b[col].nunique() == len(df_b):
            return col
            
    return None

def calculate_compatibility(filepath_a, filepath_b):
    """
    Computes pairwise compatibility metrics between Dataset A and Dataset B.
    Reads the raw datasets to perform statistical and schema overlaps.
    Returns:
        - compatibility_score (float, 0-100)
        - details (dict)
    """
    if not os.path.exists(filepath_a) or not os.path.exists(filepath_b):
        raise FileNotFoundError("One or both datasets could not be located.")
        
    try:
        df_a = clean_column_names(pd.read_csv(filepath_a))
        df_b = clean_column_names(pd.read_csv(filepath_b))
    except Exception as e:
        raise ValueError(f"Failed to read datasets for compatibility: {str(e)}")
        
    cols_a = set(df_a.columns)
    cols_b = set(df_b.columns)
    
    # 1. Schema Similarity (Jaccard similarity of column names)
    intersection_cols = cols_a.intersection(cols_b)
    union_cols = cols_a.union(cols_b)
    schema_similarity = (len(intersection_cols) / len(union_cols)) * 100.0 if union_cols else 0.0
    
    # 2. Fuzzy Column Name Similarity
    # Compare column names pairwise using difflib
    fuzzy_matches = []
    for c_a in cols_a:
        best_ratio = 0
        for c_b in cols_b:
            ratio = difflib.SequenceMatcher(None, c_a, c_b).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
        fuzzy_matches.append(best_ratio)
    column_name_similarity = (sum(fuzzy_matches) / len(fuzzy_matches)) * 100.0 if fuzzy_matches else 0.0

    # 3. Data Type Compatibility for overlapping columns
    type_matches = 0
    common_cols = list(intersection_cols)
    for col in common_cols:
        type_a = df_a[col].dtype
        type_b = df_b[col].dtype
        # check if both numeric or both categorical
        is_num_a = np.issubdtype(type_a, np.number)
        is_num_b = np.issubdtype(type_b, np.number)
        if is_num_a == is_num_b:
            type_matches += 1
            
    dtype_compatibility = (type_matches / len(common_cols)) * 100.0 if common_cols else 0.0
    
    # 4. Common Columns Ratio
    common_ratio = (len(common_cols) / max(len(cols_a), len(cols_b))) * 100.0 if cols_a or cols_b else 0.0
    
    # 5. Unique Feature Gain
    # Percentage of new features dataset B would bring if merged with dataset A (outer columns minus A)
    new_features_b = cols_b - cols_a
    unique_feature_gain = (len(new_features_b) / len(cols_a)) * 100.0 if cols_a else 0.0

    # 6. Row / Key Overlap
    key_col = find_primary_key(df_a, df_b)
    row_overlap_score = 0.0
    key_info = "No common identifier column found."
    if key_col:
        keys_a = set(df_a[key_col].dropna().unique())
        keys_b = set(df_b[key_col].dropna().unique())
        if keys_a or keys_b:
            overlap = keys_a.intersection(keys_b)
            union_keys = keys_a.union(keys_b)
            row_overlap_score = (len(overlap) / len(union_keys)) * 100.0
            key_info = f"Matched primary key '{key_col}' with {len(overlap)} overlapping records."
    else:
        # If no key, compare distributions of values in common columns as a fallback
        overlaps = []
        for col in common_cols:
            if np.issubdtype(df_a[col].dtype, np.number) and np.issubdtype(df_b[col].dtype, np.number):
                # distribution overlap approximation using simple hist overlap or unique overlap
                u_a = set(df_a[col].dropna().unique())
                u_b = set(df_b[col].dropna().unique())
                col_overlap = len(u_a.intersection(u_b)) / max(len(u_a), len(u_b)) if u_a or u_b else 0.0
                overlaps.append(col_overlap)
        row_overlap_score = (sum(overlaps) / len(overlaps)) * 100.0 if overlaps else 0.0
        
    # 7. Correlation Structure Similarity
    # Check if the relationship structure between common numeric columns is consistent
    corr_similarity = 100.0
    numeric_common = [col for col in common_cols if np.issubdtype(df_a[col].dtype, np.number) and np.issubdtype(df_b[col].dtype, np.number)]
    if len(numeric_common) > 1:
        corr_a = df_a[numeric_common].corr().fillna(0.0)
        corr_b = df_b[numeric_common].corr().fillna(0.0)
        diff = np.abs(corr_a.values - corr_b.values)
        avg_diff = np.mean(diff)
        # Scale to 0-100 (where 0 diff is 100% similarity, and max difference of 2.0 is 0%)
        corr_similarity = max(0.0, 100.0 * (1.0 - (avg_diff / 2.0)))

    # 8. Missing Value Overlap (Jaccard similarity of missing row indices on common columns)
    null_overlap_scores = []
    for col in common_cols:
        null_a = df_a[col].isnull()
        null_b = df_b[col].isnull()
        
        # If neither has missing values, they are perfectly aligned (no issues)
        if null_a.sum() == 0 and null_b.sum() == 0:
            null_overlap_scores.append(100.0)
        else:
            # Check length alignment, pad if necessary to do index comparison or just check ratio
            overlap_nulls = int((null_a & null_b).sum())
            union_nulls = int((null_a | null_b).sum())
            null_overlap_scores.append((overlap_nulls / union_nulls) * 100.0 if union_nulls > 0 else 100.0)
            
    missing_value_overlap = sum(null_overlap_scores) / len(null_overlap_scores) if null_overlap_scores else 100.0

    # Overall Weighted Compatibility Score
    # We weigh these components based on their impact:
    # Schema (25%), DType Compatibility (15%), Common Columns (15%), Name Similarity (15%), Row Overlap (15%), Correlation (15%)
    weights = {
        'schema_similarity': 0.25,
        'dtype_compatibility': 0.15,
        'common_columns': 0.15,
        'column_name_similarity': 0.15,
        'row_overlap': 0.15,
        'correlation_similarity': 0.15
    }
    
    comp_score = (
        weights['schema_similarity'] * schema_similarity +
        weights['dtype_compatibility'] * dtype_compatibility +
        weights['common_columns'] * common_ratio +
        weights['column_name_similarity'] * column_name_similarity +
        weights['row_overlap'] * row_overlap_score +
        weights['correlation_similarity'] * corr_similarity
    )
    
    # Bound check
    comp_score = min(100.0, max(0.0, comp_score))

    details = {
        "schema_similarity": round(schema_similarity, 2),
        "column_name_similarity": round(column_name_similarity, 2),
        "dtype_compatibility": round(dtype_compatibility, 2),
        "common_columns_ratio": round(common_ratio, 2),
        "unique_feature_gain": round(unique_feature_gain, 2),
        "row_overlap": round(row_overlap_score, 2),
        "correlation_similarity": round(corr_similarity, 2),
        "missing_value_overlap": round(missing_value_overlap, 2),
        "primary_key": key_col,
        "key_info": key_info,
        "common_columns_list": common_cols,
        "new_columns_list": list(new_features_b)
    }
    
    return round(comp_score, 2), details
