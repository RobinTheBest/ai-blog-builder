import os
import uuid
import re
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
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'mp4', 'mov', 'webm'}

# Ensure directories exist
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# API KEY SETUP
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GENAI_API_KEY:
    print("❌ ERROR: GEMINI_API_KEY is missing from .env")
client = genai.Client(api_key=GENAI_API_KEY)

# --- HELPER FUNCTIONS ---
def get_project_path(filename):
    safe_name = secure_filename(filename)
    if not safe_name.endswith('.html'): safe_name += '.html'
    return os.path.join(PROJECTS_DIR, safe_name)

# --- ROUTES ---

@app.route('/')
def index(): 
    return render_template('builder.html')

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
    
    # Starter Template with CSS Variables for Color Picker
    starter_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {{
            --primary: #6366f1;
            --secondary: #ec4899;
            --background: #f8fafc;
            --text: #334155;
            --surface: #ffffff;
        }}
        body {{ background: var(--background); color: var(--text); font-family: system-ui, sans-serif; padding: 40px; line-height: 1.6; }}
        header {{ background: var(--surface); padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 30px; }}
        h1 {{ color: var(--primary); margin: 0; }}
        button {{ background: var(--secondary); color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; cursor: pointer; }}
        button:hover {{ opacity: 0.9; }}
    </style>
</head>
<body>
    <header>
        <h1>{name}</h1>
        <p>Your AI-generated journey starts here.</p>
    </header>
    <main>
        <p>Edit this text visually or ask AI to change it.</p>
        <button onclick="alert('Hello!')">Click Me</button>
    </main>
</body>
</html>"""
    
    with open(filepath, "w", encoding="utf-8") as f: f.write(starter_html)
    return jsonify({"success": True, "filename": os.path.basename(filepath)})

# 3. PREVIEW & CODE
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
    with open(get_project_path(data['filename']), "w", encoding="utf-8") as f: f.write(data['code'])
    return jsonify({"success": True})

# 4. ASSET UPLOAD
@app.route('/upload_asset', methods=['POST'])
def upload_asset():
    if 'file' not in request.files: return jsonify({"success": False})
    file = request.files['file']
    if file.filename == '': return jsonify({"success": False})
    
    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex[:6]}_{filename}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
    
    web_path = f"/static/uploads/{unique_name}"
    snippet = f'<img src="{web_path}" style="max-width:100%; border-radius:8px;">'
    if filename.lower().endswith(('mp4','mov','webm')): 
        snippet = f'<video controls src="{web_path}" style="max-width:100%; border-radius:8px;"></video>'
        
    return jsonify({"success": True, "snippet": snippet})

@app.route('/download/<filename>')
def download(filename):
    filepath = get_project_path(filename)
    if os.path.exists(filepath): return send_file(filepath, as_attachment=True)
    return "Not found", 404

# 5. AI GENERATION (With News Grounding)
@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    filename = data.get('filename')
    user_prompt = data.get('prompt')
    use_news = data.get('use_news', False)
    
    filepath = get_project_path(filename)
    current_code = ""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f: current_code = f.read()

    system_instruction = f"""
    You are an AI Web Developer. 
    User Request: "{user_prompt}"
    Current Code: {current_code}
    
    CRITICAL RULES:
    1. Output FULL HTML code only. NO Markdown.
    2. Maintain CSS Variables (:root) for the Color Picker.
    3. If News Mode is ON, research the topic and write real content.
    """

    tools = []
    if use_news:
        print("🌍 News Mode: Searching Google...")
        tools = [types.Tool(google_search=types.GoogleSearch())]

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=system_instruction,
            config=types.GenerateContentConfig(tools=tools)
        )
        
        clean_code = response.text.replace("```html", "").replace("```", "").strip()
        with open(filepath, "w", encoding="utf-8") as f: f.write(clean_code)
        return jsonify({"success": True})
        
    except Exception as e:
        print("AI Error:", e)
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    print("--- AI Builder Running on http://127.0.0.1:5002 ---")
    app.run(debug=True, port=5002)