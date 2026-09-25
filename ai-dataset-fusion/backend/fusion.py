import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_squared_error, accuracy_score, r2_score
import warnings
warnings.filterwarnings('ignore')
import os
import json
from datetime import datetime

class DatasetFusionAnalyzer:
    def __init__(self, upload_folder='uploads'):
        self.upload_folder = upload_folder
        self.scaler = StandardScaler()
        self.label_encoders = {}
        
    def load_dataset(self, filename):
        """Load dataset from uploads folder"""
        filepath = os.path.join(self.upload_folder, filename)
        if filename.endswith('.csv'):
            return pd.read_csv(filepath)
        else:
            return pd.read_excel(filepath)
    
    def preprocess_dataset(self, df):
        """Clean and preprocess dataset for XGBoost"""
        df_clean = df.copy()
        
        # Drop columns with > 50% missing values
        missing_threshold = 0.5
        for col in df_clean.columns:
            if df_clean[col].isnull().mean() > missing_threshold:
                df_clean = df_clean.drop(columns=[col])
        
        # Fill remaining missing values
        for col in df_clean.columns:
            if df_clean[col].dtype in ['int64', 'float64']:
                # Fill numeric with median
                df_clean[col].fillna(df_clean[col].median(), inplace=True)
            else:
                # Fill categorical with mode
                df_clean[col].fillna(df_clean[col].mode()[0] if len(df_clean[col].mode()) > 0 else 'Unknown', inplace=True)
        
        # Encode categorical columns
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                df_clean[col] = self.label_encoders[col].fit_transform(df_clean[col].astype(str))
        
        return df_clean
    
    def get_dataset_quality_score(self, df):
        """Calculate quality score of a dataset"""
        score = 100
        
        # Penalize missing values
        missing_pct = df.isnull().sum().sum() / (df.shape[0] * df.shape[1])
        score -= missing_pct * 50
        
        # Penalize too few rows
        if df.shape[0] < 50:
            score -= 30
        elif df.shape[0] < 100:
            score -= 15
            
        # Penalize too many categorical columns (hard to predict)
        cat_cols = df.select_dtypes(include=['object']).columns
        if len(cat_cols) / df.shape[1] > 0.5:
            score -= 20
            
        # Bonus for numeric columns
        num_cols = df.select_dtypes(include=['int64', 'float64']).columns
        if len(num_cols) / df.shape[1] > 0.3:
            score += 10
            
        return max(0, min(100, score))
    
    def calculate_feature_overlap(self, df1, df2):
        """Calculate how much features overlap between datasets"""
        cols1 = set(df1.columns)
        cols2 = set(df2.columns)
        
        overlap = len(cols1.intersection(cols2))
        total = len(cols1.union(cols2))
        
        if total == 0:
            return 0
        
        overlap_score = (overlap / total) * 100
        
        # Analyze data type overlap
        type_match = 0
        for col in cols1.intersection(cols2):
            if df1[col].dtype == df2[col].dtype:
                type_match += 1
        
        type_score = (type_match / overlap * 100) if overlap > 0 else 0
        
        return {
            'overlap_percentage': overlap_score,
            'type_match_percentage': type_score,
            'common_columns': list(cols1.intersection(cols2)),
            'unique_to_ds1': list(cols1 - cols2),
            'unique_to_ds2': list(cols2 - cols1)
        }
    
    def calculate_complementarity(self, df1, df2):
        """Calculate how complementary datasets are (different but useful)"""
        # Check correlation between columns
        numeric_cols1 = df1.select_dtypes(include=['int64', 'float64']).columns
        numeric_cols2 = df2.select_dtypes(include=['int64', 'float64']).columns
        
        complementarity_score = 0
        total_comparisons = 0
        
        # If both have numeric columns, check correlation
        if len(numeric_cols1) > 0 and len(numeric_cols2) > 0:
            # Sample for performance
            sample_df1 = df1[numeric_cols1].iloc[:min(1000, len(df1))]
            sample_df2 = df2[numeric_cols2].iloc[:min(1000, len(df2))]
            
            # Calculate correlation between random pairs
            import random
            sample_cols1 = random.sample(list(numeric_cols1), min(3, len(numeric_cols1)))
            sample_cols2 = random.sample(list(numeric_cols2), min(3, len(numeric_cols2)))
            
            for col1 in sample_cols1:
                for col2 in sample_cols2:
                    try:
                        corr = sample_df1[col1].corr(sample_df2[col2])
                        if not np.isnan(corr):
                            # Low correlation means they provide different info
                            complementarity_score += (1 - abs(corr)) * 100
                            total_comparisons += 1
                    except:
                        pass
        
        # Also consider unique columns
        unique_cols1 = set(df1.columns) - set(df2.columns)
        unique_cols2 = set(df2.columns) - set(df1.columns)
        
        # More unique columns = more complementary
        unique_bonus = min(30, (len(unique_cols1) + len(unique_cols2)) / max(len(df1.columns), len(df2.columns)) * 50)
        
        avg_complementarity = (complementarity_score / total_comparisons) if total_comparisons > 0 else 50
        final_score = min(100, avg_complementarity + unique_bonus)
        
        return {
            'complementarity_score': final_score,
            'unique_cols_ds1': len(unique_cols1),
            'unique_cols_ds2': len(unique_cols2)
        }
    
    def xgboost_fusion_test(self, df1, df2, target_col=None):
        """
        Test if fusing datasets improves XGBoost prediction
        """
        # Preprocess both datasets
        df1_clean = self.preprocess_dataset(df1)
        df2_clean = self.preprocess_dataset(df2)
        
        # If no target specified, try to find numeric columns
        if target_col is None:
            # Find numeric columns that might be targets
            numeric_cols1 = df1_clean.select_dtypes(include=['int64', 'float64']).columns
            numeric_cols2 = df2_clean.select_dtypes(include=['int64', 'float64']).columns
            
            # Use first numeric column as target
            if len(numeric_cols1) > 0:
                target_col = numeric_cols1[0]
            elif len(numeric_cols2) > 0:
                target_col = numeric_cols2[0]
            else:
                return {'error': 'No numeric target column found'}
        
        results = {}
        
        # Test 1: Train on Dataset 1 only
        try:
            X1 = df1_clean.drop(columns=[target_col], errors='ignore')
            y1 = df1_clean[target_col] if target_col in df1_clean.columns else None
            
            if y1 is not None and len(X1) > 10:
                # Split data
                X_train1, X_test1, y_train1, y_test1 = train_test_split(
                    X1, y1, test_size=0.2, random_state=42
                )
                
                # Train XGBoost
                model1 = xgb.XGBRegressor(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=5,
                    random_state=42
                )
                model1.fit(X_train1, y_train1)
                
                # Predict
                y_pred1 = model1.predict(X_test1)
                score1 = r2_score(y_test1, y_pred1)
                mse1 = mean_squared_error(y_test1, y_pred1)
                
                results['ds1_only'] = {
                    'r2_score': round(score1, 4),
                    'mse': round(mse1, 4),
                    'samples': len(X_train1)
                }
        except Exception as e:
            results['ds1_only'] = {'error': str(e)}
        
        # Test 2: Train on Dataset 2 only
        try:
            X2 = df2_clean.drop(columns=[target_col], errors='ignore')
            y2 = df2_clean[target_col] if target_col in df2_clean.columns else None
            
            if y2 is not None and len(X2) > 10:
                X_train2, X_test2, y_train2, y_test2 = train_test_split(
                    X2, y2, test_size=0.2, random_state=42
                )
                
                model2 = xgb.XGBRegressor(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=5,
                    random_state=42
                )
                model2.fit(X_train2, y_train2)
                
                y_pred2 = model2.predict(X_test2)
                score2 = r2_score(y_test2, y_pred2)
                mse2 = mean_squared_error(y_test2, y_pred2)
                
                results['ds2_only'] = {
                    'r2_score': round(score2, 4),
                    'mse': round(mse2, 4),
                    'samples': len(X_train2)
                }
        except Exception as e:
            results['ds2_only'] = {'error': str(e)}
        
        # Test 3: Train on Fused Dataset
        try:
            # Align columns for fusion
            common_cols = list(set(df1_clean.columns) & set(df2_clean.columns))
            
            if target_col in common_cols:
                common_cols.remove(target_col)
            
            # Make sure both have the same columns for fusion
            if len(common_cols) > 0:
                # Create fused dataset (union)
                if target_col in df1_clean.columns and target_col in df2_clean.columns:
                    # Both have target - combine
                    fused_X = pd.concat([
                        df1_clean[common_cols + [target_col]],
                        df2_clean[common_cols + [target_col]]
                    ], ignore_index=True)
                else:
                    # Only one has target
                    if target_col in df1_clean.columns:
                        df2_clean[target_col] = np.nan
                    else:
                        df1_clean[target_col] = np.nan
                    
                    fused_X = pd.concat([
                        df1_clean[common_cols + [target_col]],
                        df2_clean[common_cols + [target_col]]
                    ], ignore_index=True)
                
                # Remove rows with NaN target
                fused_X = fused_X.dropna(subset=[target_col])
                
                if len(fused_X) > 10:
                    X_fused = fused_X.drop(columns=[target_col])
                    y_fused = fused_X[target_col]
                    
                    X_train_f, X_test_f, y_train_f, y_test_f = train_test_split(
                        X_fused, y_fused, test_size=0.2, random_state=42
                    )
                    
                    # Scale features for better performance
                    X_train_f_scaled = self.scaler.fit_transform(X_train_f)
                    X_test_f_scaled = self.scaler.transform(X_test_f)
                    
                    model_f = xgb.XGBRegressor(
                        n_estimators=100,
                        learning_rate=0.1,
                        max_depth=5,
                        random_state=42
                    )
                    model_f.fit(X_train_f_scaled, y_train_f)
                    
                    y_pred_f = model_f.predict(X_test_f_scaled)
                    score_f = r2_score(y_test_f, y_pred_f)
                    mse_f = mean_squared_error(y_test_f, y_pred_f)
                    
                    results['fused'] = {
                        'r2_score': round(score_f, 4),
                        'mse': round(mse_f, 4),
                        'samples': len(X_train_f),
                        'common_features': len(common_cols)
                    }
        except Exception as e:
            results['fused'] = {'error': str(e)}
        
        # Calculate improvement
        if 'ds1_only' in results and 'fused' in results:
            if 'r2_score' in results['ds1_only'] and 'r2_score' in results['fused']:
                improvement = (results['fused']['r2_score'] - results['ds1_only']['r2_score']) / (abs(results['ds1_only']['r2_score']) + 0.001) * 100
                results['improvement_vs_ds1'] = round(improvement, 2)
        
        if 'ds2_only' in results and 'fused' in results:
            if 'r2_score' in results['ds2_only'] and 'r2_score' in results['fused']:
                improvement2 = (results['fused']['r2_score'] - results['ds2_only']['r2_score']) / (abs(results['ds2_only']['r2_score']) + 0.001) * 100
                results['improvement_vs_ds2'] = round(improvement2, 2)
        
        results['target_column'] = target_col
        
        return results
    
    def analyze_fusion(self, dataset_names, project_description='', project_type='regression'):
        """Main function to analyze fusion compatibility"""
        
        if len(dataset_names) < 2:
            return {
                'error': 'Need at least 2 datasets for fusion analysis',
                'recommended': False,
                'score': 0
            }
        
        # Load datasets
        datasets = {}
        for name in dataset_names:
            datasets[name] = self.load_dataset(name)
        
        # Calculate various scores
        all_scores = {
            'quality_scores': {},
            'overlap_scores': [],
            'complementarity_scores': [],
            'xgboost_results': []
        }
        
        # Quality scores
        for name, df in datasets.items():
            all_scores['quality_scores'][name] = self.get_dataset_quality_score(df)
        
        # Pairwise comparisons
        names = list(datasets.keys())
        for i in range(len(names)):
            for j in range(i+1, len(names)):
                df1 = datasets[names[i]]
                df2 = datasets[names[j]]
                
                # Feature overlap
                overlap = self.calculate_feature_overlap(df1, df2)
                all_scores['overlap_scores'].append({
                    'pair': f"{names[i]} & {names[j]}",
                    **overlap
                })
                
                # Complementarity
                complementarity = self.calculate_complementarity(df1, df2)
                all_scores['complementarity_scores'].append({
                    'pair': f"{names[i]} & {names[j]}",
                    **complementarity
                })
                
                # XGBoost test (on a sample for speed)
                # Sample data if too large
                sample_df1 = df1.sample(min(1000, len(df1)), random_state=42) if len(df1) > 1000 else df1
                sample_df2 = df2.sample(min(1000, len(df2)), random_state=42) if len(df2) > 1000 else df2
                
                xgb_result = self.xgboost_fusion_test(sample_df1, sample_df2)
                all_scores['xgboost_results'].append({
                    'pair': f"{names[i]} & {names[j]}",
                    **xgb_result
                })
        
        # Calculate overall fusion score
        # Weight: Quality (30%) + Overlap (20%) + Complementarity (30%) + XGBoost (20%)
        
        avg_quality = np.mean(list(all_scores['quality_scores'].values()))
        avg_overlap = np.mean([s['overlap_percentage'] for s in all_scores['overlap_scores']])
        avg_complementarity = np.mean([s['complementarity_score'] for s in all_scores['complementarity_scores']])
        
        # XGBoost improvement
        xgb_scores = []
        for result in all_scores['xgboost_results']:
            if 'improvement_vs_ds1' in result:
                xgb_scores.append(result['improvement_vs_ds1'])
        
        avg_xgb_improvement = np.mean(xgb_scores) if xgb_scores else 0
        
        # Higher overlap is good (features align) but too high means redundant
        # Optimal overlap: 30-70%
        overlap_score = 100 - abs(50 - avg_overlap)
        
        # Overall score
        overall_score = (
            avg_quality * 0.25 +
            overlap_score * 0.15 +
            avg_complementarity * 0.30 +
            max(0, min(100, 50 + avg_xgb_improvement)) * 0.30
        )
        
        overall_score = min(100, max(0, overall_score))
        
        # Generate recommendation
        recommended = overall_score >= 65
        
        # Generate reasons
        reasons = []
        
        if avg_quality > 70:
            reasons.append(f"✅ Datasets have good quality (avg score: {avg_quality:.1f}%)")
        else:
            reasons.append(f"⚠️ Datasets need cleaning (avg score: {avg_quality:.1f}%)")
        
        if 30 <= avg_overlap <= 70:
            reasons.append(f"✅ Good feature overlap ({avg_overlap:.1f}%) - complementary information")
        elif avg_overlap > 70:
            reasons.append(f"⚠️ High feature overlap ({avg_overlap:.1f}%) - may be redundant")
        else:
            reasons.append(f"⚠️ Low feature overlap ({avg_overlap:.1f}%) - may be incompatible")
        
        if avg_complementarity > 50:
            reasons.append(f"✅ Strong complementarity ({avg_complementarity:.1f}%)")
        else:
            reasons.append(f"⚠️ Weak complementarity ({avg_complementarity:.1f}%)")
        
        if avg_xgb_improvement > 10:
            reasons.append(f"✅ XGBoost accuracy improves by {avg_xgb_improvement:.1f}% with fusion")
        elif avg_xgb_improvement > 0:
            reasons.append(f"📈 XGBoost shows slight improvement ({avg_xgb_improvement:.1f}%)")
        else:
            reasons.append(f"📉 XGBoost may not improve with fusion ({avg_xgb_improvement:.1f}%)")
        
        if recommended:
            reasons.append("🎯 Overall: FUSION RECOMMENDED for your project!")
        else:
            reasons.append("⚠️ Overall: FUSION NOT RECOMMENDED - consider different datasets")
        
        # Prepare final result
        result = {
            'recommended': recommended,
            'score': round(overall_score, 2),
            'reasons': reasons,
            'details': {
                'quality_scores': all_scores['quality_scores'],
                'average_quality': round(avg_quality, 2),
                'average_overlap': round(avg_overlap, 2),
                'average_complementarity': round(avg_complementarity, 2),
                'xgboost_improvement': round(avg_xgb_improvement, 2),
                'pairwise_analysis': {
                    'overlap': all_scores['overlap_scores'],
                    'complementarity': all_scores['complementarity_scores'],
                    'xgboost': all_scores['xgboost_results']
                }
            },
            'project': project_description,
            'project_type': project_type,
            'timestamp': datetime.now().isoformat()
        }
        
        return result
    
    def fuse_datasets(self, dataset_names):
        """Actually fuse the datasets into one"""
        if len(dataset_names) < 2:
            return None, "Need at least 2 datasets to fuse"
        
        # Load all datasets
        datasets = {}
        for name in dataset_names:
            datasets[name] = self.load_dataset(name)
        
        # Find common columns
        common_cols = set(datasets[dataset_names[0]].columns)
        for name in dataset_names[1:]:
            common_cols = common_cols.intersection(set(datasets[name].columns))
        
        # If no common columns, use all columns (outer join)
        if len(common_cols) == 0:
            # Use all columns with NaN filling
            fused_df = pd.DataFrame()
            for name, df in datasets.items():
                # Add a source column to track where data came from
                df_copy = df.copy()
                df_copy['_source_dataset'] = name
                fused_df = pd.concat([fused_df, df_copy], ignore_index=True)
        else:
            # Use inner join on common columns
            # Standardize column names and types
            for name, df in datasets.items():
                for col in common_cols:
                    if col in df.columns:
                        # Make sure numeric columns are actually numeric
                        try:
                            df[col] = pd.to_numeric(df[col], errors='ignore')
                        except:
                            pass
            
            # Start with first dataset
            fused_df = datasets[dataset_names[0]].copy()
            
            # Merge others
            for name in dataset_names[1:]:
                # Get unique columns in this dataset
                unique_cols = set(datasets[name].columns) - set(fused_df.columns)
                
                if len(unique_cols) > 0:
                    # Add unique columns
                    for col in unique_cols:
                        # Align with existing data
                        try:
                            # Try to align using common columns
                            alignment_df = datasets[name][list(common_cols) + [col]]
                            # Merge on common columns
                            if len(common_cols) > 0:
                                fused_df = fused_df.merge(
                                    alignment_df,
                                    on=list(common_cols),
                                    how='outer',
                                    suffixes=('', f'_{name}')
                                )
                            else:
                                # Just concatenate
                                fused_df[col] = np.nan
                                # Fill where possible
                                for idx in range(min(len(fused_df), len(datasets[name]))):
                                    if col in datasets[name].columns:
                                        fused_df.loc[idx, col] = datasets[name].iloc[idx][col]
                        except Exception as e:
                            print(f"Error merging {col}: {e}")
                            continue
        
        # Clean up
        # Remove duplicate columns
        fused_df = fused_df.loc[:, ~fused_df.columns.duplicated()]
        
        # Drop columns that are all NaN
        fused_df = fused_df.dropna(axis=1, how='all')
        
        # Fill remaining NaN with appropriate values
        for col in fused_df.columns:
            if fused_df[col].dtype in ['int64', 'float64']:
                fused_df[col].fillna(fused_df[col].median(), inplace=True)
            else:
                fused_df[col].fillna('Unknown', inplace=True)
        
        # Generate metadata
        metadata = {
            'original_datasets': dataset_names,
            'total_rows': len(fused_df),
            'total_columns': len(fused_df.columns),
            'columns': list(fused_df.columns),
            'fused_date': datetime.now().isoformat()
        }
        
        return fused_df, metadata