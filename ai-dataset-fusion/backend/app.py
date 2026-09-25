from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import pandas as pd
import json
from datetime import datetime
import warnings
import urllib.parse
import numpy as np
import re
warnings.filterwarnings('ignore')

# Import fusion module
from fusion import DatasetFusionAnalyzer

# ============================================
# CREATE APP & CONFIGURATION
# ============================================

app = Flask(__name__)
CORS(app)

# Define upload folder FIRST
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Make sure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============================================
# HELPER: Convert NaN to None for JSON
# ============================================

def convert_nan_to_none(obj):
    """Recursively convert NaN values to None for JSON serialization"""
    if isinstance(obj, dict):
        return {k: convert_nan_to_none(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_nan_to_none(v) for v in obj]
    elif isinstance(obj, float) and np.isnan(obj):
        return None
    elif isinstance(obj, pd.Series):
        return obj.replace({np.nan: None}).tolist()
    elif isinstance(obj, pd.DataFrame):
        return obj.replace({np.nan: None}).to_dict('records')
    else:
        return obj

# ============================================
# INITIALIZE FUSION ANALYZER
# ============================================

fusion_analyzer = DatasetFusionAnalyzer(UPLOAD_FOLDER)

# ============================================
# STORE PROJECT DATA
# ============================================

project_data = {
    'project_description': '',
    'project_type': 'regression',
    'datasets': [],
    'analysis_results': {}
}

# ============================================
# HELPER FUNCTIONS
# ============================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_filename(filename):
    """Make filename safe for URL"""
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Remove special characters
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '', filename)
    return filename

def df_to_json_safe(df):
    """Convert DataFrame to JSON-safe format with NaN as None"""
    df_clean = df.replace({np.nan: None})
    return df_clean

# ============================================
# ROUTES
# ============================================

# HOME ROUTE - Check if server is working
@app.route('/')
def home():
    return jsonify({
        "message": "AI Dataset Fusion API is running! 🚀",
        "status": "online",
        "version": "1.0.0"
    })

# ============================================
# STEP 1: Save project description
# ============================================

@app.route('/api/project', methods=['POST'])
def set_project():
    try:
        data = request.json
        project_data['project_description'] = data.get('description', '')
        project_data['project_type'] = data.get('type', 'regression')
        
        return jsonify({
            "status": "success",
            "message": "Project description saved!",
            "project": project_data['project_description'],
            "type": project_data['project_type']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# STEP 2: Upload datasets
# ============================================

@app.route('/api/upload', methods=['POST'])
def upload_files():
    try:
        if 'files' not in request.files:
            return jsonify({"error": "No files uploaded"}), 400
        
        files = request.files.getlist('files')
        uploaded_files = []
        
        for file in files:
            if file and allowed_file(file.filename):
                clean_name = safe_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], clean_name)
                
                # Handle duplicate filenames
                counter = 1
                base_name = clean_name.rsplit('.', 1)[0]
                ext = clean_name.rsplit('.', 1)[1] if '.' in clean_name else ''
                while os.path.exists(filepath):
                    clean_name = f"{base_name}_{counter}.{ext}" if ext else f"{base_name}_{counter}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], clean_name)
                    counter += 1
                
                file.save(filepath)
                uploaded_files.append(clean_name)
        
        if len(uploaded_files) == 0:
            return jsonify({"error": "No valid files uploaded"}), 400
        
        project_data['datasets'] = uploaded_files
        
        return jsonify({
            "status": "success",
            "message": f"Uploaded {len(uploaded_files)} files!",
            "files": uploaded_files
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# STEP 3: Analyze a dataset (IMPROVED)
# ============================================

@app.route('/api/analyze/<path:filename>', methods=['GET'])
def analyze_dataset(filename):
    try:
        # URL decode the filename
        filename = urllib.parse.unquote(filename)
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        print(f"Looking for file: {filepath}")
        
        if not os.path.exists(filepath):
            # Try to find file with similar name
            all_files = os.listdir(app.config['UPLOAD_FOLDER'])
            for f in all_files:
                if f.lower() == filename.lower() or filename.lower() in f.lower():
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f)
                    filename = f
                    break
            else:
                return jsonify({"error": f"File not found: {filename}"}), 404
        
        # Read the file with better error handling
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                # For Excel, try different engines and skip empty rows
                try:
                    df = pd.read_excel(filepath, engine='openpyxl')
                except:
                    df = pd.read_excel(filepath)
        except Exception as e:
            return jsonify({"error": f"Failed to read file: {str(e)}"}), 400
        
        # Check if dataframe is empty
        if df.empty:
            return jsonify({"error": "Dataset is completely empty"}), 400
        
        # ============================================
        # 🔧 IMPROVED CLEANING - Less aggressive
        # ============================================
        
        original_rows = len(df)
        original_cols = len(df.columns)
        
        # STEP 1: Remove columns that are ALL NaN (completely empty)
        df = df.dropna(axis=1, how='all')
        
        # STEP 2: Remove rows that are ALL NaN (completely empty)
        df = df.dropna(axis=0, how='all')
        
        # STEP 3: Remove columns with "Unnamed" AND all values are NaN
        unnamed_cols = [col for col in df.columns if 'Unnamed' in str(col)]
        for col in unnamed_cols:
            if df[col].isna().all():
                df = df.drop(columns=[col])
        
        # STEP 4: If still no columns, try to read the first row as header
        if len(df.columns) == 0:
            try:
                if filename.endswith('.csv'):
                    df = pd.read_csv(filepath, header=0)
                else:
                    df = pd.read_excel(filepath, header=0)
                df = df.dropna(axis=1, how='all')
                df = df.dropna(axis=0, how='all')
            except:
                pass
        
        # STEP 5: If still no columns, return error with helpful message
        if len(df.columns) == 0:
            return jsonify({
                "error": "No valid columns found in this dataset. Please check your file format.",
                "details": {
                    "original_rows": original_rows,
                    "original_columns": original_cols,
                    "suggestion": "Try saving your Excel file as CSV or remove empty rows/columns"
                }
            }), 400
        
        # STEP 6: Remove columns where ALL values are the same (no information)
        if len(df.columns) > 1:
            cols_to_drop = []
            for col in df.columns:
                if df[col].nunique() <= 1 and df[col].count() > 0:
                    cols_to_drop.append(col)
            df = df.drop(columns=cols_to_drop)
        
        # If dataframe is empty after cleaning, return error
        if df.empty or len(df.columns) == 0:
            return jsonify({
                "error": "Dataset has no valid columns after cleaning",
                "suggestion": "Make sure your data has meaningful column names and values"
            }), 400
        
        # Replace NaN with None for JSON serialization
        df_clean = df.replace({np.nan: None})
        
        # Get preview with NaN replaced
        preview_data = df_clean.head(10).to_dict('records')
        
        # Get statistics with NaN replaced (only for numeric columns)
        stats_dict = {}
        if len(df.columns) > 0:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                try:
                    stats_df = df[numeric_cols].describe()
                    stats_dict = stats_df.replace({np.nan: None}).to_dict()
                except:
                    stats_dict = {}
        
        # Get missing values count
        missing_dict = df.isnull().sum().to_dict()
        
        # Get data types
        dtype_dict = df.dtypes.astype(str).to_dict()
        
        # Basic analysis
        analysis = {
            'filename': filename,
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': list(df.columns),
            'missing_values': missing_dict,
            'data_types': dtype_dict,
            'statistics': stats_dict,
            'preview': preview_data,
            'cleaned': True,
            'original_rows': original_rows,
            'original_columns': original_cols,
            'cleaning_info': {
                'rows_removed': original_rows - len(df),
                'columns_removed': original_cols - len(df.columns)
            }
        }
        
        # Save analysis
        project_data['analysis_results'][filename] = analysis
        
        return jsonify(analysis)
    except Exception as e:
        print(f"Error analyzing {filename}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ============================================
# DEBUG: Inspect Excel file structure
# ============================================

@app.route('/api/debug/excel/<path:filename>', methods=['GET'])
def debug_excel(filename):
    try:
        filename = urllib.parse.unquote(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({"error": "File not found"}), 404
        
        # Read the file
        if filename.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
        
        # Get info
        info = {
            'filename': filename,
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'column_names': list(df.columns),
            'first_5_rows': df.head(5).replace({np.nan: None}).to_dict('records'),
            'empty_columns': [col for col in df.columns if df[col].isna().all()],
            'rows_with_all_nan': df.isna().all(axis=1).sum(),
            'data_types': df.dtypes.astype(str).to_dict(),
            'sample_data': df.iloc[:3].replace({np.nan: None}).to_dict('records') if len(df) > 0 else []
        }
        
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# STEP 4: Check Fusion with XGBoost
# ============================================

@app.route('/api/fusion/check', methods=['POST'])
def check_fusion():
    try:
        data = request.json
        dataset_names = data.get('datasets', [])
        project_description = data.get('project', '')
        project_type = data.get('projectType', 'regression')
        
        if len(dataset_names) < 2:
            return jsonify({
                'error': 'Need at least 2 datasets',
                'recommended': False,
                'score': 0
            }), 400
        
        # Run fusion analysis
        result = fusion_analyzer.analyze_fusion(
            dataset_names,
            project_description,
            project_type
        )
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'recommended': False,
            'score': 0
        }), 500

# ============================================
# STEP 5: Fuse Datasets
# ============================================

@app.route('/api/fusion/fuse', methods=['POST'])
def fuse_datasets():
    try:
        data = request.json
        dataset_names = data.get('datasets', [])
        
        if len(dataset_names) < 2:
            return jsonify({'error': 'Need at least 2 datasets'}), 400
        
        # Fuse datasets
        fused_df, metadata = fusion_analyzer.fuse_datasets(dataset_names)
        
        if fused_df is None:
            return jsonify({'error': 'Failed to fuse datasets'}), 500
        
        # Save fused dataset
        fused_filename = f"fused_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        fused_path = os.path.join(UPLOAD_FOLDER, fused_filename)
        fused_df.to_csv(fused_path, index=False)
        
        # Get preview with NaN replaced
        preview_data = fused_df.head(10).replace({np.nan: None}).to_dict('records')
        
        return jsonify({
            'success': True,
            'filename': fused_filename,
            'metadata': metadata,
            'preview': preview_data
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# STEP 6: Download Fused Dataset
# ============================================

@app.route('/api/fusion/download/<path:filename>', methods=['GET'])
def download_fused(filename):
    try:
        filename = urllib.parse.unquote(filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# LIST UPLOADED FILES (Utility)
# ============================================

@app.route('/api/files', methods=['GET'])
def list_files():
    try:
        files = os.listdir(UPLOAD_FOLDER)
        return jsonify({
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# DELETE FILE (Utility)
# ============================================

@app.route('/api/files/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        filename = urllib.parse.unquote(filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'message': f'Deleted {filename}'})
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# DEBUG: Check uploads folder
# ============================================

@app.route('/api/debug/files', methods=['GET'])
def debug_files():
    """Debug endpoint to see what files are in uploads"""
    try:
        files = os.listdir(UPLOAD_FOLDER)
        return jsonify({
            'upload_folder': UPLOAD_FOLDER,
            'files': files,
            'count': len(files),
            'folder_exists': os.path.exists(UPLOAD_FOLDER),
            'absolute_path': os.path.abspath(UPLOAD_FOLDER)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# RUN THE SERVER
# ============================================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 AI Dataset Fusion API Server")
    print("=" * 50)
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📍 Server URL: http://localhost:5000")
    print(f"📋 API Endpoints:")
    print(f"   GET  / - Health check")
    print(f"   POST /api/project - Save project")
    print(f"   POST /api/upload - Upload datasets")
    print(f"   GET  /api/analyze/<file> - Analyze dataset")
    print(f"   GET  /api/debug/excel/<file> - Debug Excel file")
    print(f"   POST /api/fusion/check - Check fusion")
    print(f"   POST /api/fusion/fuse - Fuse datasets")
    print(f"   GET  /api/fusion/download/<file> - Download")
    print(f"   GET  /api/debug/files - Debug uploaded files")
    print("=" * 50)
    print("✅ Server starting... Press Ctrl+C to stop")
    print("=" * 50)
    app.run(debug=True, port=5000)