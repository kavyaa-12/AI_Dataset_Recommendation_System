import os
import json
import time
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from config import UPLOAD_FOLDER, PROFILE_FOLDER, FUSED_FOLDER, REPORT_FOLDER, RESULT_FOLDER, MAX_CONTENT_LENGTH
from modules.upload import save_upload
from modules.metadata import extract_metadata
from modules.profiling import generate_profile
from modules.compatibility import calculate_compatibility
from modules.ml_recommender import MLRecommender
from modules.fusion import execute_fusion
from modules.report_generator import generate_pdf_report

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Recommender instantiation
recommender = MLRecommender()

# History Helpers
def load_history():
    history_path = os.path.join(RESULT_FOLDER, 'history.json')
    if not os.path.exists(history_path):
        return []
    try:
        with open(history_path, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_history_entry(entry):
    history_path = os.path.join(RESULT_FOLDER, 'history.json')
    history = load_history()
    # Check if duplicate entry exists (based on files and strategy)
    for idx, e in enumerate(history):
        if e['file_a'] == entry['file_a'] and e['file_b'] == entry['file_b'] and e['strategy'] == entry['strategy']:
            history[idx] = entry
            break
    else:
        history.insert(0, entry) # Insert new records at the beginning
        
    os.makedirs(RESULT_FOLDER, exist_ok=True)
    with open(history_path, 'w') as f:
        json.dump(history, f, indent=4)

def get_recent_uploads():
    """
    Scans the uploads/ directory for uploaded CSV files.
    """
    if not os.path.exists(UPLOAD_FOLDER):
        return []
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.csv')]
    # Sort files by modification time, descending
    files.sort(key=lambda x: os.path.getmtime(os.path.join(UPLOAD_FOLDER, x)), reverse=True)
    return files

@app.route('/')
def index():
    """
    Renders landing page with guided steps and selector dropdowns.
    """
    uploads = get_recent_uploads()
    return render_template('index.html', recent_files=uploads)

@app.route('/upload-page')
def upload_page():
    """
    Dedicated uploads dashboard page.
    """
    uploads = get_recent_uploads()
    
    # Load profile details for each upload if profile exists
    file_cards = []
    for f in uploads:
        profile_path = os.path.join(PROFILE_FOLDER, f"{f}.json")
        size_str = "N/A"
        q_score = "N/A"
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'r') as pf:
                    p_data = json.load(pf)
                    size_str = p_data.get('file_size_str', 'N/A')
                    q_score = p_data.get('quality_score', 'N/A')
            except Exception:
                pass
        file_cards.append({
            "filename": f,
            "size": size_str,
            "quality_score": q_score
        })
        
    return render_template('upload.html', files=file_cards)

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    API endpoint for uploader drag-and-drop / select files.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file chunk found"}), 400
        
    file = request.files['file']
    try:
        filename, filepath = save_upload(file)
        
        # Immediate processing and profiling
        metadata = extract_metadata(filepath)
        profile = generate_profile(filepath)
        
        return jsonify({
            "message": "File processed successfully",
            "filename": filename,
            "quality_score": profile["quality_score"]
        }), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/profile-preview/<filename>')
def profile_preview(filename):
    """
    API returning column list and top 5 rows for HTML uploader preview.
    """
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    try:
        import pandas as pd
        df = pd.read_csv(filepath, nrows=5)
        # fill nan with empty string to avoid JSON parse errors
        records = df.fillna("").to_dict(orient='records')
        columns = list(df.columns)
        return jsonify({"columns": columns, "rows": records})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete-file/<filename>', methods=['POST'])
def delete_file(filename):
    """
    API to delete an uploaded dataset and its profile.
    """
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    profile_path = os.path.join(PROFILE_FOLDER, f"{filename}.json")
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
        if os.path.exists(profile_path):
            os.remove(profile_path)
        return jsonify({"message": "File deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/profiles')
def profiles():
    """
    List of dataset profiles page.
    """
    uploads = get_recent_uploads()
    selected_file = request.args.get('file')
    profile_data = None
    
    if selected_file:
        profile_path = os.path.join(PROFILE_FOLDER, f"{selected_file}.json")
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'r') as f:
                    profile_data = json.load(f)
            except Exception:
                pass
                
    return render_template('profiles.html', files=uploads, selected_file=selected_file, profile=profile_data)

@app.route('/recommend')
def recommend():
    """
    Dedicated AI recommendation page.
    """
    file_a = request.args.get('file_a')
    file_b = request.args.get('file_b')
    
    if not file_a or not file_b:
        return redirect(url_for('index'))
        
    try:
        profile_a_path = os.path.join(PROFILE_FOLDER, f"{file_a}.json")
        profile_b_path = os.path.join(PROFILE_FOLDER, f"{file_b}.json")
        
        # Ensure profiles exist
        if not os.path.exists(profile_a_path):
            generate_profile(os.path.join(UPLOAD_FOLDER, file_a))
        if not os.path.exists(profile_b_path):
            generate_profile(os.path.join(UPLOAD_FOLDER, file_b))
            
        with open(profile_a_path, 'r') as f:
            profile_a = json.load(f)
        with open(profile_b_path, 'r') as f:
            profile_b = json.load(f)
            
        # Calculate compatibility
        comp_score, comp_details = calculate_compatibility(
            os.path.join(UPLOAD_FOLDER, file_a),
            os.path.join(UPLOAD_FOLDER, file_b)
        )
        
        # Get AI recommendation
        rec_details = recommender.recommend(profile_a, profile_b, comp_details, comp_score)
        
        # Log to History
        history_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "file_a": file_a,
            "file_b": file_b,
            "compatibility_score": comp_score,
            "recommendation": rec_details["recommendation"],
            "strategy": rec_details["suggested_strategy"],
            "confidence": rec_details["confidence_score"],
            "gain_score": rec_details["fusion_gain_score"]
        }
        save_history_entry(history_entry)
        
        return render_template(
            'recommendation.html',
            file_a=file_a,
            file_b=file_b,
            profile_a=profile_a,
            profile_b=profile_b,
            comp_score=comp_score,
            comp_details=comp_details,
            rec_details=rec_details
        )
        
    except Exception as e:
        return f"Recommendation execution failed: {str(e)}", 500

@app.route('/fusion-page')
def fusion_page():
    """
    Dedicated Fusion configuration and results page.
    """
    file_a = request.args.get('file_a')
    file_b = request.args.get('file_b')
    strategy = request.args.get('strategy')
    
    if not file_a or not file_b:
        return redirect(url_for('index'))
        
    fusion_stats = None
    file_paths = None
    
    if strategy:
        # Check if already fused
        base_fused_name = f"fused_{strategy}_{file_a.split('.')[0]}_{file_b.split('.')[0]}"
        meta_path = os.path.join(RESULT_FOLDER, f"{base_fused_name}_stats.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r') as mf:
                    saved_f = json.load(mf)
                    fusion_stats = saved_f["stats"]
                    file_paths = saved_f["files"]
            except Exception:
                pass
                
    # Auto-detect key column for joined strategies
    key_col = request.args.get('key_col')
    if not key_col:
        try:
            import pandas as pd
            df_a = pd.read_csv(os.path.join(UPLOAD_FOLDER, file_a), nrows=1)
            df_b = pd.read_csv(os.path.join(UPLOAD_FOLDER, file_b), nrows=1)
            from modules.compatibility import find_primary_key
            key_col = find_primary_key(df_a, df_b) or ""
        except Exception:
            key_col = ""
            
    return render_template(
        'fusion.html',
        file_a=file_a,
        file_b=file_b,
        suggested_strategy=strategy or "union",
        key_col=key_col,
        fusion_stats=fusion_stats,
        file_paths=file_paths
    )

@app.route('/fuse', methods=['POST'])
def fuse_datasets():
    """
    Triggers dataset fusion and PDF generation.
    """
    file_a = request.form.get('file_a')
    file_b = request.form.get('file_b')
    strategy = request.form.get('strategy', 'union')
    key_col = request.form.get('key_col') or None
    impute = request.form.get('impute') == 'true'
    
    if not file_a or not file_b:
        return "Invalid parameters for fusion", 400
        
    try:
        path_a = os.path.join(UPLOAD_FOLDER, file_a)
        path_b = os.path.join(UPLOAD_FOLDER, file_b)
        
        # Execute fusion
        stats, paths = execute_fusion(path_a, path_b, strategy, key_col, impute)
        
        # Load profiles for generating the PDF report
        with open(os.path.join(PROFILE_FOLDER, f"{file_a}.json"), 'r') as f:
            profile_a = json.load(f)
        with open(os.path.join(PROFILE_FOLDER, f"{file_b}.json"), 'r') as f:
            profile_b = json.load(f)
            
        comp_score, comp_details = calculate_compatibility(path_a, path_b)
        rec_details = recommender.recommend(profile_a, profile_b, comp_details, comp_score)
        
        # Generate the PDF report
        generate_pdf_report(profile_a, profile_b, comp_details, rec_details, stats, paths)
        
        # Redirect back to the fusion-page with the strategy query parameter to unlock download cards
        return redirect(url_for('fusion_page', file_a=file_a, file_b=file_b, strategy=strategy))
        
    except Exception as e:
        return f"Fusion execution failed: {str(e)}", 500

@app.route('/reports')
def reports():
    """
    List of PDF and HTML reports page.
    """
    history = load_history()
    # Find matching reports in reports folder
    available_reports = []
    
    if os.path.exists(REPORT_FOLDER):
        for f in os.listdir(REPORT_FOLDER):
            if f.endswith('.pdf'):
                # Extract dataset A and B names from filename "report_A_B.pdf"
                parts = f.split('_')[1:]
                file_a_part = parts[0]
                file_b_part = "_".join(parts[1:]).replace('.pdf', '')
                available_reports.append({
                    "filename": f,
                    "file_a_part": file_a_part,
                    "file_b_part": file_b_part,
                    "path": f"/download/reports/{f}"
                })
                
    return render_template('reports.html', reports=available_reports, history=history)

@app.route('/dashboard')
def dashboard():
    """
    Analytical dashboard showing global KPI counters and history charts.
    """
    history = load_history()
    uploads = get_recent_uploads()
    
    total_datasets = len(uploads)
    total_recs = len(history)
    
    # Calculate average quality score
    quality_sum = 0.0
    quality_count = 0
    for f in uploads:
        profile_path = os.path.join(PROFILE_FOLDER, f"{f}.json")
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'r') as pf:
                    p = json.load(pf)
                    quality_sum += p.get('quality_score', 0)
                    quality_count += 1
            except Exception:
                pass
    avg_quality = round(quality_sum / quality_count, 1) if quality_count > 0 else 0.0
    
    # Count total fused datasets (by scanning fused folder)
    total_fused = 0
    if os.path.exists(FUSED_FOLDER):
        total_fused = len([f for f in os.listdir(FUSED_FOLDER) if f.endswith('.csv')])
        
    return render_template(
        'dashboard.html',
        total_datasets=total_datasets,
        avg_quality=avg_quality,
        total_recs=total_recs,
        total_fused=total_fused,
        history=history[:10] # show last 10 activities on timeline
    )

@app.route('/history')
def history():
    """
    Lists all comparison history.
    """
    history_data = load_history()
    return render_template('history.html', history=history_data)

@app.route('/report')
def report_printable():
    """
    Renders printable HTML report template page.
    """
    file_a = request.args.get('file_a')
    file_b = request.args.get('file_b')
    strategy = request.args.get('strategy')
    
    if not file_a or not file_b:
        return "Missing file parameters for report", 400
        
    try:
        with open(os.path.join(PROFILE_FOLDER, f"{file_a}.json"), 'r') as f:
            profile_a = json.load(f)
        with open(os.path.join(PROFILE_FOLDER, f"{file_b}.json"), 'r') as f:
            profile_b = json.load(f)
            
        comp_score, comp_details = calculate_compatibility(
            os.path.join(UPLOAD_FOLDER, file_a),
            os.path.join(UPLOAD_FOLDER, file_b)
        )
        rec_details = recommender.recommend(profile_a, profile_b, comp_details, comp_score)
        
        fusion_stats = None
        if strategy:
            base_fused_name = f"fused_{strategy}_{file_a.split('.')[0]}_{file_b.split('.')[0]}"
            meta_path = os.path.join(RESULT_FOLDER, f"{base_fused_name}_stats.json")
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as mf:
                    saved_f = json.load(mf)
                    fusion_stats = saved_f["stats"]
                    
        return render_template(
            'report.html',
            profile_a=profile_a,
            profile_b=profile_b,
            comp_details=comp_details,
            rec_details=rec_details,
            fusion_stats=fusion_stats
        )
    except Exception as e:
        return f"Failed to generate printable report: {str(e)}", 500

@app.route('/download/<folder>/<filename>')
def download_file(folder, filename):
    """
    Dynamic file download route.
    """
    if folder not in ['fused', 'reports']:
        return "Access denied to folder path.", 403
        
    target_dir = FUSED_FOLDER if folder == 'fused' else REPORT_FOLDER
    if not os.path.exists(os.path.join(target_dir, filename)):
        return "Requested export file does not exist.", 404
        
    return send_from_directory(target_dir, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
