import os
import json
import joblib
import pandas as pd
import numpy as np
from modules.recommender import BaseRecommender, RuleBasedRecommender

class MLRecommender(BaseRecommender):
    def __init__(self, models_dir="models"):
        self.models_dir = models_dir
        self.rec_model_path = os.path.join(models_dir, "rf_recommendation.pkl")
        self.strat_model_path = os.path.join(models_dir, "rf_strategy.pkl")
        self.features_path = os.path.join(models_dir, "feature_names.json")
        
        # Fallback to rule-based for quality estimations
        self.rule_based_fallback = RuleBasedRecommender()
        
        self.rec_model = None
        self.strat_model = None
        self.feature_names = None
        
        self._load_models()

    def _load_models(self):
        if os.path.exists(self.rec_model_path) and os.path.exists(self.strat_model_path):
            self.rec_model = joblib.load(self.rec_model_path)
            self.strat_model = joblib.load(self.strat_model_path)
            with open(self.features_path, 'r') as f:
                self.feature_names = json.load(f)
        else:
            raise RuntimeError(f"ML models not found in {self.models_dir}. Please run train_recommender.py first.")

    def _extract_features(self, profile_a, profile_b, comp_details, comp_score):
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
        
        qb_a = profile_a.get("quality_breakdown", {})
        qb_b = profile_b.get("quality_breakdown", {})
        
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

    def recommend(self, profile_a, profile_b, compatibility_details, compatibility_score):
        features_dict = self._extract_features(profile_a, profile_b, compatibility_details, compatibility_score)
        
        # Convert to DataFrame in the exact order of self.feature_names
        X = pd.DataFrame([features_dict])[self.feature_names]
        
        # Predictions
        recommendation = self.rec_model.predict(X)[0]
        strategy = self.strat_model.predict(X)[0]
        
        # Confidence score based on probabilities
        rec_probs = self.rec_model.predict_proba(X)[0]
        confidence = float(np.max(rec_probs) * 100)
        
        # Calculate Fusion Gain using rule-based formula based on the ML-predicted strategy
        q_fused = self.rule_based_fallback.estimate_fused_quality(profile_a, profile_b, compatibility_details, strategy)
        q_a = profile_a["quality_score"]
        q_b = profile_b["quality_score"]
        q_max = max(q_a, q_b)
        gain_score = round(q_fused - q_max, 2)
        
        # Explainability: Get top 3 important features for this prediction
        # Local explainability approx: feature_value * global_importance
        importances = self.rec_model.feature_importances_
        feature_contributions = []
        for i, col in enumerate(self.feature_names):
            # Scale feature val between 0-1 for rough local contribution
            val = X[col].values[0]
            # normalized value approximation depending on feature type
            norm_val = val / 100.0 if "score" in col or "ratio" in col or "similarity" in col else (val / 10000.0) 
            contrib = importances[i] * norm_val
            feature_contributions.append((col, contrib))
            
        feature_contributions.sort(key=lambda x: x[1], reverse=True)
        top_features = [f[0] for f in feature_contributions[:3]]
        
        reasons = []
        reasons.append(f"ML Model Recommendation: {recommendation} (Confidence: {confidence:.1f}%)")
        reasons.append(f"Suggested strategy: {strategy.upper()}")
        
        # Formulate reasoning text based on top features
        reason_texts = {
            "q_a": f"Dataset A has a high quality score ({q_a}).",
            "q_b": f"Dataset B has a high quality score ({q_b}).",
            "schema_similarity": f"Schema similarity is {compatibility_details.get('schema_similarity', 0)}%.",
            "comp_score": f"Overall compatibility score is {compatibility_score}/100.",
            "row_overlap": f"Row overlap between datasets is {compatibility_details.get('row_overlap', 0)}%.",
            "unique_feature_gain": f"Fusing adds unique features (Gain: {compatibility_details.get('unique_feature_gain', 0)}%).",
            "has_primary_key": f"A primary key ('{compatibility_details.get('primary_key')}') was identified for joining."
        }
        
        reasons.append("Top driving factors for this decision:")
        for tf in top_features:
            if tf in reason_texts:
                reasons.append(" - " + reason_texts[tf])
            else:
                reasons.append(f" - Metric '{tf}' significantly influenced the model.")
                
        if gain_score > 0 and recommendation == "FUSE":
            reasons.append(f"Fusing yields a positive quality gain of +{gain_score} points.")
        elif gain_score <= 0 and recommendation == "FUSE":
            reasons.append(f"Warning: Fusing results in a {gain_score} point change in overall dataset quality.")
            
        return {
            "recommendation": recommendation,
            "confidence_score": round(confidence, 1),
            "reasoning": reasons,
            "fusion_gain_score": gain_score,
            "estimated_fused_quality": q_fused,
            "suggested_strategy": strategy
        }
