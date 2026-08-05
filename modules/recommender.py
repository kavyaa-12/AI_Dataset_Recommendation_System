import abc
from config import QUALITY_WEIGHTS

class BaseRecommender(abc.ABC):
    """
    Abstract base class for recommendation engines.
    Makes the architecture future-ready for XGBoost or other ML models.
    """
    @abc.abstractmethod
    def recommend(self, profile_a, profile_b, compatibility_details, compatibility_score):
        """
        Takes dataset profiles and compatibility details to generate a recommendation.
        """
        pass

class RuleBasedRecommender(BaseRecommender):
    """
    Explainable rule-based recommendation engine for V1.
    Uses quality and compatibility metrics to output recommendations, confidence, and reasons.
    """
    
    def estimate_fused_quality(self, profile_a, profile_b, comp_details, strategy):
        """
        Simulates the quality score of the fused dataset based on the strategy.
        Formula: Q_fused calculated using weighted metrics on simulated dataset parameters.
        """
        # Baseline variables
        n_a, n_b = profile_a["num_rows"], profile_b["num_rows"]
        c_a, c_b = profile_a["num_cols"], profile_b["num_cols"]
        
        # Calculate simulated parameters
        sim_rows = n_a
        sim_cols = c_a
        sim_null_ratio = 0.0
        sim_dup_ratio = 0.0
        
        # Primary key & row overlap
        pk = comp_details.get("primary_key")
        row_overlap_pct = comp_details.get("row_overlap", 0.0) / 100.0
        
        # Approximate overlap row count
        overlap_rows = int(min(n_a, n_b) * row_overlap_pct)
        if overlap_rows == 0 and pk:
            overlap_rows = int(min(n_a, n_b) * 0.1) # low fallback
            
        if strategy == "union":
            sim_rows = n_a + n_b - overlap_rows
            sim_cols = len(set(profile_a["column_names"]).union(profile_b["column_names"]))
            
            # Nulls will increase for columns that are in A but not in B, and vice-versa
            nulls_a = sum(s["null_count"] for s in profile_a["column_stats"].values())
            nulls_b = sum(s["null_count"] for s in profile_b["column_stats"].values())
            
            # Non-overlapping columns from A will have nulls for all B rows
            cols_not_in_b = len(set(profile_a["column_names"]) - set(profile_b["column_names"]))
            cols_not_in_a = len(set(profile_b["column_names"]) - set(profile_a["column_names"]))
            
            extra_nulls_a = cols_not_in_a * n_a
            extra_nulls_b = cols_not_in_b * n_b
            
            total_sim_nulls = nulls_a + nulls_b + extra_nulls_a + extra_nulls_b
            sim_null_ratio = total_sim_nulls / (sim_rows * sim_cols) if sim_rows > 0 else 0.0
            
        elif strategy in ["left_join", "right_join", "inner_join", "outer_join"]:
            sim_cols = c_a + c_b - (1 if pk else 0)
            
            if strategy == "inner_join":
                sim_rows = max(1, overlap_rows)
                # Nulls should be low as we only keep matching keys
                nulls_a_ratio = sum(s["null_count"] for s in profile_a["column_stats"].values()) / (n_a * c_a)
                nulls_b_ratio = sum(s["null_count"] for s in profile_b["column_stats"].values()) / (n_b * c_b)
                sim_null_ratio = (nulls_a_ratio + nulls_b_ratio) / 2.0
                
            elif strategy == "left_join":
                sim_rows = n_a
                # B columns that don't match key are filled with nulls
                nulls_a = sum(s["null_count"] for s in profile_a["column_stats"].values())
                nulls_b_overlap = (sum(s["null_count"] for s in profile_b["column_stats"].values()) / n_b) * overlap_rows
                nulls_b_missing = (c_b - 1) * (n_a - overlap_rows)
                sim_null_ratio = (nulls_a + nulls_b_overlap + nulls_b_missing) / (sim_rows * sim_cols)
                
            elif strategy == "right_join":
                sim_rows = n_b
                nulls_b = sum(s["null_count"] for s in profile_b["column_stats"].values())
                nulls_a_overlap = (sum(s["null_count"] for s in profile_a["column_stats"].values()) / n_a) * overlap_rows
                nulls_a_missing = (c_a - 1) * (n_b - overlap_rows)
                sim_null_ratio = (nulls_b + nulls_a_overlap + nulls_a_missing) / (sim_rows * sim_cols)
                
            else: # outer_join
                sim_rows = n_a + n_b - overlap_rows
                nulls_a_base = sum(s["null_count"] for s in profile_a["column_stats"].values())
                nulls_b_base = sum(s["null_count"] for s in profile_b["column_stats"].values())
                nulls_a_missing = (c_a - 1) * (n_b - overlap_rows)
                nulls_b_missing = (c_b - 1) * (n_a - overlap_rows)
                sim_null_ratio = (nulls_a_base + nulls_b_base + nulls_a_missing + nulls_b_missing) / (sim_rows * sim_cols)
                
        else: # concat
            sim_rows = max(n_a, n_b)
            sim_cols = c_a + c_b
            # simple side-by-side, shorter dataset padded with nulls
            nulls_a = sum(s["null_count"] for s in profile_a["column_stats"].values())
            nulls_b = sum(s["null_count"] for s in profile_b["column_stats"].values())
            padding_nulls = abs(n_a - n_b) * (c_a if n_a < n_b else c_b)
            sim_null_ratio = (nulls_a + nulls_b + padding_nulls) / (sim_rows * sim_cols)
            
        # Standardize simulated scores
        score_missing = max(0.0, 100.0 * (1.0 - sim_null_ratio))
        score_duplicates = 100.0 # Fusion automatically removes duplicate rows
        score_completeness = max(0.0, 100.0 * (1.0 - (sim_null_ratio * 1.5))) # completeness proxy
        
        # Diversity: combining datasets general maintains or improves feature diversity
        score_diversity = min(100.0, max(profile_a["quality_breakdown"]["feature_diversity"], 
                                         profile_b["quality_breakdown"]["feature_diversity"]) + 5.0)
                                         
        # Outliers ratio remains similar to average
        score_outliers = (profile_a["quality_breakdown"]["outlier_ratio"] + profile_b["quality_breakdown"]["outlier_ratio"]) / 2.0
        
        # Consistency & Validity: We assume fusion enforces consistency and validity
        score_consistency = 95.0
        score_validity = 95.0
        
        q_fused = (
            QUALITY_WEIGHTS['missing_values'] * score_missing +
            QUALITY_WEIGHTS['duplicate_rows'] * score_duplicates +
            QUALITY_WEIGHTS['data_completeness'] * score_completeness +
            QUALITY_WEIGHTS['feature_diversity'] * score_diversity +
            QUALITY_WEIGHTS['outlier_ratio'] * score_outliers +
            QUALITY_WEIGHTS['data_consistency'] * score_consistency +
            QUALITY_WEIGHTS['data_type_validity'] * score_validity
        )
        
        return round(q_fused, 2)

    def determine_strategy(self, profile_a, profile_b, comp_details):
        """
        Heuristically chooses the best fusion strategy.
        """
        pk = comp_details.get("primary_key")
        schema_sim = comp_details.get("schema_similarity", 0.0)
        row_overlap = comp_details.get("row_overlap", 0.0)
        
        if schema_sim > 80.0:
            return "union"
        elif pk:
            # If primary key matches and there is row overlap
            if row_overlap > 75.0:
                return "inner_join"
            elif row_overlap > 20.0:
                # Left join is preferred to keep primary dataset (A) complete
                return "left_join"
            else:
                return "outer_join"
        else:
            # If no primary key but columns are different, stack horizontally
            return "concat"

    def recommend(self, profile_a, profile_b, compatibility_details, compatibility_score):
        """
        Executes explainable recommendation logic.
        Outputs a structured dictionary with decision details.
        """
        q_a = profile_a["quality_score"]
        q_b = profile_b["quality_score"]
        
        # Step 1: Detect strategy
        strategy = self.determine_strategy(profile_a, profile_b, compatibility_details)
        
        # Step 2: Estimate quality of fused dataset
        q_fused = self.estimate_fused_quality(profile_a, profile_b, compatibility_details, strategy)
        
        # Step 3: Compute Fusion Gain Score
        q_max = max(q_a, q_b)
        gain_score = round(q_fused - q_max, 2)
        
        # Step 4: Make recommendation decision
        recommendation = "FUSE"
        reasons = []
        confidence = 50.0 # base confidence
        
        # Heuristic rules
        pk = compatibility_details.get("primary_key")
        schema_sim = compatibility_details.get("schema_similarity", 0.0)
        
        if compatibility_score < 30.0 and gain_score < 0:
            # If datasets are highly incompatible and fusion decreases quality
            if q_a >= q_b:
                recommendation = "USE_A"
                confidence = min(95.0, 60.0 + (q_a - q_b) + (40.0 - compatibility_score))
                reasons.append(f"Dataset A has a higher quality score ({q_a}) compared to Dataset B ({q_b}).")
                reasons.append("Compatibility between datasets is extremely low, meaning a fusion would introduce excessive missing values (sparsity).")
            else:
                recommendation = "USE_B"
                confidence = min(95.0, 60.0 + (q_b - q_a) + (40.0 - compatibility_score))
                reasons.append(f"Dataset B has a higher quality score ({q_b}) compared to Dataset A ({q_a}).")
                reasons.append("Compatibility between datasets is too low for a successful fusion.")
        else:
            # Fusion recommended
            recommendation = "FUSE"
            confidence = min(98.0, 50.0 + (compatibility_score * 0.4) + (max(0, gain_score) * 2.0))
            
            reasons.append(f"Fusion strategy '{strategy.upper()}' is recommended.")
            
            if strategy == "union":
                reasons.append(f"High schema similarity ({schema_sim}%) allows row concatenation without major structural loss.")
                reasons.append(f"Fusing increases row count from {profile_a['num_rows']} (A) and {profile_b['num_rows']} (B) to an estimated {profile_a['num_rows'] + profile_b['num_rows'] - int(min(profile_a['num_rows'], profile_b['num_rows']) * (compatibility_details.get('row_overlap', 0)/100))} rows.")
            elif pk:
                reasons.append(f"Identified matching primary key '{pk}' allowing a relational merge.")
                reasons.append(f"Adding columns from Dataset B expands features from {profile_a['num_cols']} to {profile_a['num_cols'] + compatibility_details.get('unique_feature_gain', 0)/100 * profile_a['num_cols']:.0f} features.")
            else:
                reasons.append("Fusing side-by-side (horizontal concatenation) combines distinct feature domains.")
                
            if gain_score > 0:
                reasons.append(f"Fusing yields a positive quality gain of +{gain_score} points, improving completeness and overall coverage.")
            else:
                reasons.append(f"Warning: Fusing results in a slight quality score change of {gain_score} points due to induced missing cells, but provides a richer column layout.")
                
        # Additional comparisons
        reasons.append(f"Quality comparison: Dataset A ({q_a}/100) vs Dataset B ({q_b}/100).")
        reasons.append(f"Compatibility score is {compatibility_score}/100 based on schema and data type alignments.")
        
        return {
            "recommendation": recommendation,
            "confidence_score": round(confidence, 1),
            "reasoning": reasons,
            "fusion_gain_score": gain_score,
            "estimated_fused_quality": q_fused,
            "suggested_strategy": strategy
        }
