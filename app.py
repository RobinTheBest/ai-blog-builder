import os
import uuid
import datetime
import shutil
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- CONFIG ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
BACKUP_DIR = os.path.join(BASE_DIR, "backups") # New Backup Folder
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'mp4', 'mov', 'webm'}

# Ensure directories exist
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# API KEY SETUP
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GENAI_API_KEY)

# --- HELPER FUNCTIONS ---
def get_project_path(filename):
    safe_name = secure_filename(filename)
    if not safe_name.endswith('.html'): safe_name += '.html'
    return os.path.join(PROJECTS_DIR, safe_name)

def create_backup(filename, label="AutoSave"):
    """Saves a copy of the current file to backups/projectname/timestamp_label.html"""
    source = get_project_path(filename)
    if not os.path.exists(source): return

    # Create folder for this specific project's backups
    project_backup_dir = os.path.join(BACKUP_DIR, filename.replace('.html', ''))
    os.makedirs(project_backup_dir, exist_ok=True)

    # Timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = secure_filename(label.replace(" ", "_"))
    
    # Backup Filename: 20240109_123000_AI_Update.html
    backup_name = f"{timestamp}__{safe_label}.html"
    destination = os.path.join(project_backup_dir, backup_name)
    
    shutil.copy2(source, destination)

# --- ROUTES ---

@app.route('/')
def index(): return render_template('builder.html')

# 1. LIST PROJECTS
@app.route('/projects')
def list_projects():
    files = [f for f in os.listdir(PROJECTS_DIR) if f.endswith('.html')]
    return jsonify({"projects": files})

# 2. CREATE NEW PROJECT
@app.route('/create_project', methods=['POST'])
def create_project():
    name = request.json.get('name')
    if not name: return jsonify({"success": False})
    
    filepath = get_project_path(name)
    if os.path.exists(filepath): return jsonify({"success": False, "error": "Project exists"})
    
    starter_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {{ --primary: #6366f1; --bg: #f8fafc; --text: #334155; }}
        body {{ background: var(--bg); color: var(--text); font-family: sans-serif; padding: 40px; }}
        h1 {{ color: var(--primary); }}
    </style>
</head>
<body>
    <h1>{name}</h1>
    <p>Start building...</p>
</body>
</html>"""
    
    with open(filepath, "w", encoding="utf-8") as f: f.write(starter_html)
    return jsonify({"success": True, "filename": os.path.basename(filepath)})

# 3. HISTORY & RESTORE (NEW)
@app.route('/history/<filename>')
def get_history(filename):
    project_backup_dir = os.path.join(BACKUP_DIR, filename.replace('.html', ''))
    if not os.path.exists(project_backup_dir):
        return jsonify({"history": []})
    
    # Get list of files, sorted by time (newest first)
    backups = []
    for f in sorted(os.listdir(project_backup_dir), reverse=True):
        if f.endswith('.html'):
            # Parse filename: YYYYMMDD_HHMMSS__Label.html
            parts = f.split('__')
            if len(parts) >= 2:
                ts_str = parts[0] # YYYYMMDD_HHMMSS
                label = parts[1].replace('.html', '').replace('_', ' ')
                
                # Format time nicely
                try:
                    dt = datetime.datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                    nice_time = dt.strftime("%I:%M:%S %p") # 10:30:05 PM
                except:
                    nice_time = ts_str

                backups.append({"file": f, "time": nice_time, "label": label})
    
    return jsonify({"history": backups})

@app.route('/restore', methods=['POST'])
def restore_version():
    data = request.json
    filename = data.get('filename')
    backup_file = data.get('backup_file')
    
    project_path = get_project_path(filename)
    backup_path = os.path.join(BACKUP_DIR, filename.replace('.html', ''), backup_file)
    
    if os.path.exists(backup_path):
        # Create a backup of the current state before restoring (Safety Net)
        create_backup(filename, "Pre_Restore_Safety_Save")
        
        # Overwrite
        shutil.copy2(backup_path, project_path)
        return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "Backup not found"})


# 4. PREVIEW & CODE
@app.route('/preview/<filename>')
def preview(filename):
    filepath = get_project_path(filename)
    if not os.path.exists(filepath): return "Project not found", 404
    return send_file(filepath)

@app.route('/get_code/<filename>')
def get_code(filename):
    filepath = get_project_path(filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f: return jsonify({"code": f.read()})
    return jsonify({"code": ""})

@app.route('/save_code', methods=['POST'])
def save_code():
    data = request.json
    filename = data.get('filename')
    code = data.get('code')
    
    # BACKUP BEFORE SAVE
    create_backup(filename, "Manual_Edit")
    
    with open(get_project_path(filename), "w", encoding="utf-8") as f: f.write(code)
    return jsonify({"success": True})

# 5. ASSET UPLOAD
@app.route('/upload_asset', methods=['POST'])
def upload_asset():
    if 'file' not in request.files: return jsonify({"success": False})
    file = request.files['file']
    filename = secure_filename(file.filename)
    unique = f"{uuid.uuid4().hex[:6]}_{filename}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique))
    path = f"/static/uploads/{unique}"
    snippet = f'<img src="{path}" style="max-width:100%">'
    if filename.endswith(('mp4','mov')): snippet = f'<video controls src="{path}"></video>'
    return jsonify({"success": True, "snippet": snippet})

@app.route('/download/<filename>')
def download(filename):
    return send_file(get_project_path(filename), as_attachment=True)

# 6. AI GENERATION
@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    filename = data.get('filename')
    prompt = data.get('prompt')
    use_news = data.get('use_news', False)
    
    # BACKUP BEFORE AI GENERATION
    # Truncate prompt for label
    short_prompt = (prompt[:15] + '..') if len(prompt) > 15 else prompt
    create_backup(filename, f"AI_{short_prompt}")
    
    filepath = get_project_path(filename)
    current_code = ""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f: current_code = f.read()

    sys_instr = f"""
    You are an AI Web Developer. 
    User Request: "{prompt}"
    Current Code: {current_code}
    RULES: Output FULL HTML only. No Markdown. Keep CSS Variables.
    """
    tools = [types.Tool(google_search=types.GoogleSearch())] if use_news else []

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=sys_instr,
            config=types.GenerateContentConfig(tools=tools)
        )
        clean_code = response.text.replace("```html", "").replace("```", "").strip()
        with open(filepath, "w", encoding="utf-8") as f: f.write(clean_code)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    print("--- AI Builder + Time Machine Running on http://127.0.0.1:5002 ---")
    app.run(debug=True, port=5002)