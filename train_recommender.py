import os
import json
import random
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import joblib

# Import existing rule-based recommender to generate labels
from modules.recommender import RuleBasedRecommender

def extract_features(profile_a, profile_b, comp_details, comp_score):
    """Extracts a flat feature dictionary from profiles and compatibility details."""
    features = {
        "q_a": profile_a.get("quality_score", 0),
        "q_b": profile_b.get("quality_score", 0),
        "schema_similarity": comp_details.get("schema_similarity", 0),
        "column_name_similarity": comp_details.get("column_name_similarity", 0),
        "dtype_compatibility": comp_details.get("dtype_compatibility", 0),
        "common_columns_ratio": comp_details.get("common_columns_ratio", 0),
        "unique_feature_gain": comp_details.get("unique_feature_gain", 0),
        "row_overlap": comp_details.get("row_overlap", 0),
        "correlation_similarity": comp_details.get("correlation_similarity", 0),
        "has_primary_key": 1 if comp_details.get("primary_key") else 0,
        "comp_score": comp_score
    }
    
    # Missing and duplicate ratios from quality breakdown
    qb_a = profile_a.get("quality_breakdown", {})
    qb_b = profile_b.get("quality_breakdown", {})
    
    # Note: Quality breakdown stores 100 - (ratio * 100). Higher is better.
    features["missing_score_a"] = qb_a.get("missing_values", 100)
    features["missing_score_b"] = qb_b.get("missing_values", 100)
    features["dup_score_a"] = qb_a.get("duplicate_rows", 100)
    features["dup_score_b"] = qb_b.get("duplicate_rows", 100)
    features["completeness_a"] = qb_a.get("data_completeness", 100)
    features["completeness_b"] = qb_b.get("data_completeness", 100)
    
    features["num_rows_a"] = profile_a.get("num_rows", 1000)
    features["num_rows_b"] = profile_b.get("num_rows", 1000)
    features["num_cols_a"] = profile_a.get("num_cols", 10)
    features["num_cols_b"] = profile_b.get("num_cols", 10)
    
    return features

def generate_synthetic_data(num_samples=1000):
    rule_recommender = RuleBasedRecommender()
    
    X = []
    y_rec = []
    y_strat = []
    
    scenarios = ["highly_compatible", "partially_overlapping", "incompatible", "noisy", "different_schemas", "fk_relationship"]
    
    for _ in range(num_samples):
        scenario = random.choice(scenarios)
        
        # Base templates
        p_a = {
            "num_rows": random.randint(100, 10000),
            "num_cols": random.randint(5, 50),
            "quality_score": random.uniform(60, 100),
            "quality_breakdown": {
                "missing_values": random.uniform(80, 100),
                "duplicate_rows": random.uniform(90, 100),
                "data_completeness": random.uniform(80, 100),
                "feature_diversity": random.uniform(80, 100),
                "outlier_ratio": random.uniform(80, 100),
            }
        }
        p_b = {
            "num_rows": random.randint(100, 10000),
            "num_cols": random.randint(5, 50),
            "quality_score": random.uniform(60, 100),
            "quality_breakdown": {
                "missing_values": random.uniform(80, 100),
                "duplicate_rows": random.uniform(90, 100),
                "data_completeness": random.uniform(80, 100),
                "feature_diversity": random.uniform(80, 100),
                "outlier_ratio": random.uniform(80, 100),
            }
        }
        
        comp_details = {
            "schema_similarity": 0,
            "column_name_similarity": 0,
            "dtype_compatibility": 0,
            "common_columns_ratio": 0,
            "unique_feature_gain": random.uniform(10, 100),
            "row_overlap": 0,
            "correlation_similarity": 0,
            "primary_key": None
        }
        
        if scenario == "highly_compatible":
            comp_details["schema_similarity"] = random.uniform(85, 100)
            comp_details["column_name_similarity"] = random.uniform(90, 100)
            comp_details["dtype_compatibility"] = random.uniform(90, 100)
            comp_details["common_columns_ratio"] = random.uniform(80, 100)
            comp_score = random.uniform(85, 100)
            
        elif scenario == "partially_overlapping":
            comp_details["schema_similarity"] = random.uniform(30, 70)
            comp_details["column_name_similarity"] = random.uniform(40, 80)
            comp_details["dtype_compatibility"] = random.uniform(60, 100)
            comp_details["primary_key"] = "id" if random.random() > 0.3 else None
            comp_details["row_overlap"] = random.uniform(20, 80)
            comp_score = random.uniform(50, 80)
            
        elif scenario == "incompatible":
            comp_details["schema_similarity"] = random.uniform(0, 20)
            comp_details["column_name_similarity"] = random.uniform(0, 30)
            comp_details["dtype_compatibility"] = random.uniform(0, 40)
            comp_details["row_overlap"] = random.uniform(0, 10)
            p_a["quality_score"] = random.uniform(40, 80)
            p_b["quality_score"] = random.uniform(40, 80)
            comp_score = random.uniform(0, 30)
            
        elif scenario == "noisy":
            comp_details["schema_similarity"] = random.uniform(40, 80)
            comp_details["primary_key"] = "id"
            comp_details["row_overlap"] = random.uniform(40, 90)
            p_b["quality_score"] = random.uniform(20, 50)
            p_b["quality_breakdown"]["missing_values"] = random.uniform(10, 40)
            comp_score = random.uniform(40, 70)
            
        elif scenario == "different_schemas":
            comp_details["schema_similarity"] = random.uniform(0, 10)
            comp_details["column_name_similarity"] = random.uniform(0, 10)
            comp_details["primary_key"] = None
            comp_details["row_overlap"] = 0
            comp_score = random.uniform(0, 20)
            
        elif scenario == "fk_relationship":
            comp_details["schema_similarity"] = random.uniform(10, 30)
            comp_details["primary_key"] = "user_id"
            comp_details["row_overlap"] = random.uniform(80, 100)
            comp_score = random.uniform(60, 90)
            
        # Ensure values are sensible for internal rule-based quality estimator requirements
        p_a["column_names"] = [f"col_{i}" for i in range(p_a["num_cols"])]
        p_b["column_names"] = [f"col_{i}" for i in range(p_b["num_cols"])]
        p_a["column_stats"] = {c: {"null_count": 0} for c in p_a["column_names"]}
        p_b["column_stats"] = {c: {"null_count": 0} for c in p_b["column_names"]}
        
        # Get labels from RuleBasedRecommender
        rec_details = rule_recommender.recommend(p_a, p_b, comp_details, comp_score)
        
        # Extract features
        features = extract_features(p_a, p_b, comp_details, comp_score)
        
        X.append(features)
        y_rec.append(rec_details["recommendation"])
        y_strat.append(rec_details["suggested_strategy"])
        
    return pd.DataFrame(X), np.array(y_rec), np.array(y_strat)

def main():
    print("Generating synthetic dataset (N=3000)...")
    X, y_rec, y_strat = generate_synthetic_data(3000)
    
    feature_names = list(X.columns)
    
    # Train-test split
    X_train, X_test, y_rec_train, y_rec_test, y_strat_train, y_strat_test = train_test_split(
        X, y_rec, y_strat, test_size=0.2, random_state=42
    )
    
    print("\nTraining Recommendation Classifier (USE_A, USE_B, FUSE)...")
    clf_rec = RandomForestClassifier(n_estimators=100, random_state=42)
    clf_rec.fit(X_train, y_rec_train)
    
    rec_preds = clf_rec.predict(X_test)
    print("--- Recommendation Evaluation ---")
    print(f"Accuracy:  {accuracy_score(y_rec_test, rec_preds):.4f}")
    print(f"Precision: {precision_score(y_rec_test, rec_preds, average='weighted', zero_division=0):.4f}")
    print(f"Recall:    {recall_score(y_rec_test, rec_preds, average='weighted', zero_division=0):.4f}")
    print(f"F1-Score:  {f1_score(y_rec_test, rec_preds, average='weighted', zero_division=0):.4f}")
    print("Confusion Matrix:")
    print(confusion_matrix(y_rec_test, rec_preds))
    
    print("\nTraining Strategy Classifier (union, left_join, right_join, inner_join, outer_join, concat)...")
    clf_strat = RandomForestClassifier(n_estimators=100, random_state=42)
    clf_strat.fit(X_train, y_strat_train)
    
    strat_preds = clf_strat.predict(X_test)
    print("--- Strategy Evaluation ---")
    print(f"Accuracy:  {accuracy_score(y_strat_test, strat_preds):.4f}")
    print(f"Precision: {precision_score(y_strat_test, strat_preds, average='weighted', zero_division=0):.4f}")
    print(f"Recall:    {recall_score(y_strat_test, strat_preds, average='weighted', zero_division=0):.4f}")
    print(f"F1-Score:  {f1_score(y_strat_test, strat_preds, average='weighted', zero_division=0):.4f}")
    print("Confusion Matrix:")
    print(confusion_matrix(y_strat_test, strat_preds))
    
    # Save models and features
    os.makedirs("models", exist_ok=True)
    joblib.dump(clf_rec, "models/rf_recommendation.pkl")
    joblib.dump(clf_strat, "models/rf_strategy.pkl")
    with open("models/feature_names.json", "w") as f:
        json.dump(feature_names, f)
        
    print("\nModels and feature names saved to 'models/' directory successfully.")

if __name__ == "__main__":
    main()
