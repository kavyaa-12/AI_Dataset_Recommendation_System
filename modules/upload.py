import os
from werkzeug.utils import secure_filename
from config import ALLOWED_EXTENSIONS, UPLOAD_FOLDER

def allowed_file(filename):
    """
    Checks if a filename has an allowed extension.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file):
    """
    Validates and saves an uploaded file.
    Returns the secure filename and the full path where it was saved.
    Raises ValueError if invalid file or format.
    """
    if not file or file.filename == '':
        raise ValueError("No file selected")
    
    if not allowed_file(file.filename):
        raise ValueError("Invalid file format. Only CSV files are supported.")
    
    filename = secure_filename(file.filename)
    # Ensure uploads directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    return filename, filepath
