import os
import json
import numpy as np
import pandas as pd
from config import QUALITY_WEIGHTS, PROFILE_FOLDER

def generate_profile(filepath, target_col=None):
    """
    Performs full profiling and data quality analysis on a CSV file.
    Saves the profile as a JSON file in the profile directory.
    Returns the profile dict.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise ValueError(f"Could not read CSV file for profiling: {str(e)}")
        
    num_rows = len(df)
    num_cols = len(df.columns)
    total_elements = num_rows * num_cols
    
    if num_rows == 0 or num_cols == 0:
        raise ValueError("Dataset is empty")

    filename = os.path.basename(filepath)
    
    # 1. Base Column profiling & stats
    column_stats = {}
    null_counts = {}
    null_percentages = {}
    dtypes_map = {}
    
    for col in df.columns:
        null_c = int(df[col].isnull().sum())
        null_counts[col] = null_c
        null_percentages[col] = float((null_c / num_rows) * 100)
        
        col_type = df[col].dtype
        stats = {"null_count": null_c, "null_percent": null_percentages[col]}
        
        if np.issubdtype(col_type, np.number):
            dtypes_map[col] = "Numeric"
            stats["type"] = "Numeric"
            stats["mean"] = float(df[col].mean()) if not df[col].isnull().all() else 0.0
            stats["std"] = float(df[col].std()) if not df[col].isnull().all() and len(df[col].dropna()) > 1 else 0.0
            stats["min"] = float(df[col].min()) if not df[col].isnull().all() else 0.0
            stats["max"] = float(df[col].max()) if not df[col].isnull().all() else 0.0
            stats["unique_count"] = int(df[col].nunique())
            
            # Simple outlier detection using IQR
            if not df[col].isnull().all():
                q25 = df[col].quantile(0.25)
                q75 = df[col].quantile(0.75)
                iqr = q75 - q25
                lower_bound = q25 - 1.5 * iqr
                upper_bound = q75 + 1.5 * iqr
                outliers_c = int(((df[col] < lower_bound) | (df[col] > upper_bound)).sum())
                stats["outlier_count"] = outliers_c
                stats["outlier_percent"] = float((outliers_c / num_rows) * 100)
            else:
                stats["outlier_count"] = 0
                stats["outlier_percent"] = 0.0
        else:
            dtypes_map[col] = "Categorical"
            stats["type"] = "Categorical"
            stats["unique_count"] = int(df[col].nunique())
            if not df[col].isnull().all():
                mode_val = df[col].mode()
                stats["mode"] = str(mode_val.iloc[0]) if not mode_val.empty else "N/A"
                stats["mode_freq"] = int(df[col].value_counts().iloc[0]) if not df[col].value_counts().empty else 0
                stats["mode_percent"] = float((stats["mode_freq"] / num_rows) * 100)
            else:
                stats["mode"] = "N/A"
                stats["mode_freq"] = 0
                stats["mode_percent"] = 0.0
            stats["outlier_count"] = 0
            stats["outlier_percent"] = 0.0
            
        column_stats[col] = stats

    # 2. Quality scoring metrics (weighted components)
    
    # Missing Value Penalty (20% weight)
    total_nulls = sum(null_counts.values())
    missing_ratio = total_nulls / total_elements
    score_missing = max(0.0, 100.0 * (1.0 - missing_ratio))
    
    # Duplicate Rows Penalty (15% weight)
    duplicate_rows = int(df.duplicated().sum())
    duplicate_ratio = duplicate_rows / num_rows
    score_duplicates = max(0.0, 100.0 * (1.0 - duplicate_ratio))
    
    # Data Completeness (15% weight) - columns with no missing values
    complete_cols = sum(1 for c in df.columns if null_counts[c] == 0)
    score_completeness = (complete_cols / num_cols) * 100.0
    
    # Feature Diversity (15% weight) - penalize constant columns and ID columns (unique per row for text)
    constant_cols = sum(1 for c in df.columns if column_stats[c]["unique_count"] <= 1)
    # Categorical/string columns where unique values = row count (likely IDs)
    id_cols = sum(1 for c in df.columns if dtypes_map[c] == "Categorical" and column_stats[c]["unique_count"] == num_rows)
    diversity_penalty_ratio = (constant_cols + id_cols) / num_cols
    score_diversity = max(0.0, 100.0 * (1.0 - diversity_penalty_ratio))
    
    # Outlier Ratio (15% weight)
    total_outliers = sum(column_stats[c].get("outlier_count", 0) for c in df.columns)
    outlier_ratio = total_outliers / total_elements
    score_outliers = max(0.0, 100.0 * (1.0 - outlier_ratio))
    
    # Data Consistency (10% weight) - check for mixed data types in object columns
    # We define inconsistency as object columns containing mixed numeric/text values
    inconsistent_cols = 0
    for col in df.columns:
        if dtypes_map[col] == "Categorical":
            non_null_vals = df[col].dropna()
            types = non_null_vals.apply(lambda x: type(x).__name__).nunique()
            if types > 1:
                inconsistent_cols += 1
    score_consistency = max(0.0, 100.0 * (1.0 - (inconsistent_cols / num_cols)))
    
    # Data Type Validity (10% weight) - check if numeric columns contain non-numeric data
    invalid_type_cols = 0
    for col in df.columns:
        if dtypes_map[col] == "Numeric":
            # If pd.to_numeric fails on any values, those are invalid
            converted = pd.to_numeric(df[col], errors='coerce')
            invalid_count = converted.isnull().sum() - df[col].isnull().sum()
            if invalid_count > 0:
                invalid_type_cols += 1
    score_validity = max(0.0, 100.0 * (1.0 - (invalid_type_cols / num_cols)))
    
    # Weighted Final Quality Score
    q_score = (
        QUALITY_WEIGHTS['missing_values'] * score_missing +
        QUALITY_WEIGHTS['duplicate_rows'] * score_duplicates +
        QUALITY_WEIGHTS['data_completeness'] * score_completeness +
        QUALITY_WEIGHTS['feature_diversity'] * score_diversity +
        QUALITY_WEIGHTS['outlier_ratio'] * score_outliers +
        QUALITY_WEIGHTS['data_consistency'] * score_consistency +
        QUALITY_WEIGHTS['data_type_validity'] * score_validity
    )
    
    # 3. Correlation Matrix for Numeric Columns
    numeric_df = df.select_dtypes(include=[np.number])
    correlation_matrix = {}
    if len(numeric_df.columns) > 1:
        corr = numeric_df.corr().fillna(0.0)
        correlation_matrix = {col: corr[col].to_dict() for col in corr.columns}
    
    # 4. Null value heatmap grid (aggregated to 40 bins for rendering performance)
    num_bins = min(40, num_rows)
    bin_size = num_rows // num_bins
    heatmap_data = []
    
    for bin_idx in range(num_bins):
        start_row = bin_idx * bin_size
        end_row = (bin_idx + 1) * bin_size if bin_idx < num_bins - 1 else num_rows
        bin_df = df.iloc[start_row:end_row]
        
        row_heatmap = {}
        for col in df.columns:
            null_pct = (bin_df[col].isnull().sum() / len(bin_df)) * 100
            row_heatmap[col] = float(null_pct)
        heatmap_data.append({
            "bin": f"Rows {start_row}-{end_row-1}",
            "null_percentages": row_heatmap
        })

    # Class Imbalance Analysis (if target column specified)
    class_imbalance = {}
    if target_col and target_col in df.columns:
        counts = df[target_col].value_counts(dropna=False)
        total = len(df)
        class_imbalance = {str(k): {"count": int(v), "percent": float((v / total) * 100)} for k, v in counts.items()}

    # File size and memory usage
    from modules.metadata import get_file_size
    size_bytes, size_str = get_file_size(filepath)
    memory_usage_bytes = df.memory_usage(deep=True).sum()
    memory_usage_str = f"{memory_usage_bytes / 1024:.2f} KB" if memory_usage_bytes < 1024*1024 else f"{memory_usage_bytes / (1024*1024):.2f} MB"

    profile = {
        "filename": filename,
        "num_rows": num_rows,
        "num_cols": num_cols,
        "file_size_bytes": size_bytes,
        "file_size_str": size_str,
        "memory_usage_bytes": int(memory_usage_bytes),
        "memory_usage_str": memory_usage_str,
        "duplicate_rows": duplicate_rows,
        "column_names": list(df.columns),
        "dtypes": dtypes_map,
        "column_stats": column_stats,
        "quality_score": round(q_score, 2),
        "quality_breakdown": {
            "missing_values": round(score_missing, 2),
            "duplicate_rows": round(score_duplicates, 2),
            "data_completeness": round(score_completeness, 2),
            "feature_diversity": round(score_diversity, 2),
            "outlier_ratio": round(score_outliers, 2),
            "data_consistency": round(score_consistency, 2),
            "data_type_validity": round(score_validity, 2)
        },
        "correlation_matrix": correlation_matrix,
        "null_heatmap": heatmap_data,
        "class_imbalance": class_imbalance,
        "target_column": target_col
    }
    
    # Save profile to file-system for fast retrieval
    os.makedirs(PROFILE_FOLDER, exist_ok=True)
    profile_path = os.path.join(PROFILE_FOLDER, f"{filename}.json")
    with open(profile_path, 'w') as f:
        json.dump(profile, f, indent=4)
        
    return profile
