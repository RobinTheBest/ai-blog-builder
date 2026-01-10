import os
import uuid
from flask import Flask, render_template, request, jsonify, send_file, url_for
from werkzeug.utils import secure_filename
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# CONFIG
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'mp4', 'mov', 'webm'}

# Ensure directories exist
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# API KEY
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GENAI_API_KEY)

# --- HELPER FUNCTIONS ---
def get_project_path(filename):
    # Security: Ensure filename is safe and ends in .html
    safe_name = secure_filename(filename)
    if not safe_name.endswith('.html'):
        safe_name += '.html'
    return os.path.join(PROJECTS_DIR, safe_name)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('builder.html')

# 1. LIST PROJECTS
@app.route('/projects', methods=['GET'])
def list_projects():
    files = [f for f in os.listdir(PROJECTS_DIR) if f.endswith('.html')]
    return jsonify({"projects": files})

# 2. CREATE NEW PROJECT
@app.route('/create_project', methods=['POST'])
def create_project():
    name = request.json.get('name')
    if not name: return jsonify({"success": False, "error": "No name provided"})
    
    filepath = get_project_path(name)
    if os.path.exists(filepath):
        return jsonify({"success": False, "error": "Project already exists"})
    
    # Create empty starter template
    with open(filepath, "w") as f:
        f.write("<!DOCTYPE html><html><body><h1>New Project: " + name + "</h1></body></html>")
        
    return jsonify({"success": True, "filename": os.path.basename(filepath)})

# 3. PREVIEW (Load specific project)
@app.route('/preview/<filename>')
def preview(filename):
    filepath = get_project_path(filename)
    if not os.path.exists(filepath):
        return "Project not found", 404
    return send_file(filepath)

# 4. GET CODE (For Editor)
@app.route('/get_code/<filename>')
def get_code(filename):
    filepath = get_project_path(filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return jsonify({"code": f.read()})
    return jsonify({"code": ""})

# 5. SAVE CODE
@app.route('/save_code', methods=['POST'])
def save_code():
    data = request.json
    filename = data.get('filename')
    code = data.get('code')
    filepath = get_project_path(filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    return jsonify({"success": True})

# 6. GENERATE AI (Aware of current project)
@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    filename = data.get('filename')
    user_prompt = data.get('prompt')
    
    filepath = get_project_path(filename)
    current_code = ""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f: current_code = f.read()

    system_instruction = f"""
    You are an expert AI Web Developer. 
    User Request: "{user_prompt}"
    Current Code: {current_code}

    INSTRUCTIONS:
    1. Output the COMPLETE HTML file.
    2. Do NOT use markdown blocks. Return ONLY raw HTML.
    """
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=system_instruction)
        clean_code = response.text.replace("```html", "").replace("```", "").strip()
        with open(filepath, "w", encoding="utf-8") as f: f.write(clean_code)
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)})

# 7. UPLOAD (Same as before)
@app.route('/upload_asset', methods=['POST'])
def upload_asset():
    if 'file' not in request.files: return jsonify({"success": False})
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex[:6]}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
        web_path = f"/static/uploads/{unique_filename}"
        
        snippet = f'<img src="{web_path}" style="max-width:100%">'
        if filename.endswith(('mp4','mov','webm')):
             snippet = f'<video controls width="100%"><source src="{web_path}"></video>'
             
        return jsonify({"success": True, "snippet": snippet})
    return jsonify({"success": False})

@app.route('/download/<filename>')
def download_file(filename):
    filepath = get_project_path(filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return "Not found", 404

if __name__ == '__main__':
    print("--- Multi-Session AI Builder running on http://127.0.0.1:5002 ---")
    app.run(debug=True, port=5002)