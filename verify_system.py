import os
import pandas as pd
import numpy as np
import json
from config import UPLOAD_FOLDER, PROFILE_FOLDER, FUSED_FOLDER, REPORT_FOLDER, RESULT_FOLDER
from modules.metadata import extract_metadata
from modules.profiling import generate_profile
from modules.compatibility import calculate_compatibility
from modules.recommender import RuleBasedRecommender
from modules.fusion import execute_fusion
from modules.report_generator import generate_pdf_report

def create_synthetic_datasets():
    """
    Creates two mock datasets in the uploads/ folder for testing.
    - Dataset A: Customer details (columns: id, name, age, signup_date)
    - Dataset B: Customer transactions (columns: id, purchase_amount, date, category)
    Note that they share 'id' as a key column, date/signup_date are somewhat similar.
    """
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Dataset A
    data_a = {
        'id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eva', 'Frank', 'Grace', 'Henry', 'Ivy', 'Jack'],
        'age': [25, 30, np.nan, 22, 28, 35, 40, np.nan, 29, 31], # some nulls
        'signup_date': ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05',
                       '2026-01-06', '2026-01-07', '2026-01-08', '2026-01-09', '2026-01-10']
    }
    df_a = pd.DataFrame(data_a)
    path_a = os.path.join(UPLOAD_FOLDER, 'test_customers.csv')
    df_a.to_csv(path_a, index=False)
    
    # Dataset B (shares some keys, has different features, different length)
    data_b = {
        'id': [1, 2, 3, 4, 5, 11, 12], # id 11, 12 are new keys
        'purchase_amount': [100.50, 20.00, np.nan, 150.75, 45.00, 200.00, 85.20],
        'date': ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05', '2026-01-11', '2026-01-12'],
        'category': ['Electronics', 'Books', 'Clothing', 'Electronics', 'Books', 'Clothing', 'Home']
    }
    df_b = pd.DataFrame(data_b)
    path_b = os.path.join(UPLOAD_FOLDER, 'test_purchases.csv')
    df_b.to_csv(path_b, index=False)
    
    return path_a, path_b

def run_tests():
    print("=== STARTING SYSTEM INTEGRATION TESTS ===")
    
    # 1. Setup mock files
    print("\n[Step 1] Creating synthetic datasets...")
    path_a, path_b = create_synthetic_datasets()
    print(f"Dataset A: {path_a}")
    print(f"Dataset B: {path_b}")
    
    # 2. Extract metadata
    print("\n[Step 2] Extracting structural metadata...")
    meta_a = extract_metadata(path_a)
    meta_b = extract_metadata(path_b)
    print(f"Meta A columns: {meta_a['column_names']}")
    print(f"Meta B columns: {meta_b['column_names']}")
    assert meta_a['num_rows'] == 10, "Dataset A row count mismatch"
    assert meta_b['num_rows'] == 7, "Dataset B row count mismatch"
    
    # 3. Generate detailed profile
    print("\n[Step 3] Generating detailed profiles...")
    profile_a = generate_profile(path_a)
    profile_b = generate_profile(path_b)
    print(f"Profile A Quality Score: {profile_a['quality_score']}/100")
    print(f"Profile B Quality Score: {profile_b['quality_score']}/100")
    assert os.path.exists(os.path.join(PROFILE_FOLDER, 'test_customers.csv.json')), "Profile A JSON not saved"
    assert os.path.exists(os.path.join(PROFILE_FOLDER, 'test_purchases.csv.json')), "Profile B JSON not saved"
    
    # 4. Calculate compatibility
    print("\n[Step 4] Running pairwise compatibility analysis...")
    comp_score, comp_details = calculate_compatibility(path_a, path_b)
    print(f"Compatibility Score: {comp_score}/100")
    print(f"Detected common key: '{comp_details['primary_key']}'")
    assert comp_details['primary_key'] == 'id', "Failed to detect primary key 'id'"
    
    # 5. Evaluate Recommender
    print("\n[Step 5] Triggering Pluggable AI Recommender...")
    recommender = RuleBasedRecommender()
    rec_details = recommender.recommend(profile_a, profile_b, comp_details, comp_score)
    print(f"Recommendation Action: {rec_details['recommendation']}")
    print(f"Confidence Level: {rec_details['confidence_score']}%")
    print(f"Estimated Fusion Gain Score: {rec_details['fusion_gain_score']} points")
    print(f"Suggested strategy: '{rec_details['suggested_strategy']}'")
    
    # 6. Execute Fusion (Left Join)
    print("\n[Step 6] Running dataset fusion merge (strategy: left_join)...")
    stats, paths = execute_fusion(path_a, path_b, strategy='left_join', key_col='id', impute=True)
    print(f"Fused rows: {stats['rows_after']} | columns: {stats['cols_after']}")
    print(f"Generated CSV path: {paths['csv']}")
    print(f"Generated XLSX path: {paths['xlsx']}")
    print(f"Generated JSON path: {paths['json']}")
    
    assert os.path.exists(paths['csv']), "Fused CSV not created"
    assert os.path.exists(paths['json']), "Fused JSON not created"
    
    # 7. Generate PDF report
    print("\n[Step 7] Compiling report as PDF...")
    pdf_path, pdf_name = generate_pdf_report(profile_a, profile_b, comp_details, rec_details, stats, paths)
    print(f"PDF generated: {pdf_path}")
    assert os.path.exists(pdf_path), "PDF report file not created"
    
    print("\n=== ALL SYSTEM TESTS COMPLETED SUCCESSFULLY ===")

if __name__ == '__main__':
    run_tests()
