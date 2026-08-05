import os

# Base directory setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Folder settings (relative to project root)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
PROFILE_FOLDER = os.path.join(BASE_DIR, 'dataset_profiles')
FUSED_FOLDER = os.path.join(BASE_DIR, 'fused')
REPORT_FOLDER = os.path.join(BASE_DIR, 'reports')
RESULT_FOLDER = os.path.join(BASE_DIR, 'results')

# Allowed extensions
ALLOWED_EXTENSIONS = {'csv'}

# Max file upload size (16MB)
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# Quality metric weights (sum must be 1.0)
QUALITY_WEIGHTS = {
    'missing_values': 0.20,
    'duplicate_rows': 0.15,
    'data_completeness': 0.15,
    'feature_diversity': 0.15,
    'outlier_ratio': 0.15,
    'data_consistency': 0.10,
    'data_type_validity': 0.10
}

# Auto-create necessary directories
for folder in [UPLOAD_FOLDER, PROFILE_FOLDER, FUSED_FOLDER, REPORT_FOLDER, RESULT_FOLDER]:
    os.makedirs(folder, exist_ok=True)
