import os
import json
import uuid
import shutil
import datetime
import re
import subprocess
import time
import sys
import signal
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
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
USER_APP_PORT = 5005

os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# API KEY
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GENAI_API_KEY)

# --- AUTO-PATCHER ---
def patch_existing_projects():
    for project in os.listdir(PROJECTS_DIR):
        app_path = os.path.join(PROJECTS_DIR, project, "app.py")
        if os.path.exists(app_path):
            with open(app_path, "r", encoding="utf-8") as f: content = f.read()
            modified = False
            if "import os" not in content:
                content = "import os\n" + content; modified = True
            if "os.environ.get('PORT'" not in content:
                new_content = re.sub(r"if __name__ == ['\"]__main__['\"]:\s*app\.run\(.*?\)", f"if __name__ == '__main__':\n    port = int(os.environ.get('PORT', {USER_APP_PORT}))\n    app.run(debug=True, host='0.0.0.0', port=port)", content, flags=re.DOTALL)
                if new_content == content: new_content += f"\n\nif __name__ == '__main__':\n    port = int(os.environ.get('PORT', {USER_APP_PORT}))\n    app.run(debug=True, host='0.0.0.0', port=port)"
                content = new_content; modified = True
            if modified:
                with open(app_path, "w", encoding="utf-8") as f: f.write(content)
patch_existing_projects()

# --- HELPER FUNCTIONS ---
def get_project_dir(name):
    path = os.path.join(PROJECTS_DIR, secure_filename(name))
    if not os.path.exists(path): os.makedirs(os.path.join(path, "templates"), exist_ok=True)
    return path

def create_backup(project_name, label="AutoSave"):
    src = get_project_dir(project_name)
    if not os.path.exists(src): return
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder = os.path.join(BACKUP_DIR, secure_filename(project_name))
    os.makedirs(backup_folder, exist_ok=True)
    zip_name = f"{timestamp}__{secure_filename(label)}" 
    shutil.make_archive(os.path.join(backup_folder, zip_name), 'zip', src)

def clean_ai_json(text):
    text = text.strip()
    text = re.sub(r"^```\w*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    return text.strip()

# --- CLEANUP LOGIC ---
def cleanup_old_backups(project_name):
    backup_folder = os.path.join(BACKUP_DIR, secure_filename(project_name))
    if not os.path.exists(backup_folder): return
    
    now = datetime.datetime.now()
    two_weeks_ago = now - datetime.timedelta(weeks=2)
    
    for f in os.listdir(backup_folder):
        if not f.endswith('.zip'): continue
        
        # SKIP STARRED BACKUPS
        if "_STARRED" in f: continue
        
        try:
            # Parse timestamp from filename: YYYYMMDD_HHMMSS
            ts_str = f.split('__')[0]
            file_time = datetime.datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            
            if file_time < two_weeks_ago:
                os.remove(os.path.join(backup_folder, f))
                print(f"🧹 Cleaned up old backup: {f}")
        except:
            pass # Ignore files with weird names

# --- ROUTES ---

@app.route('/')
def index(): return render_template('builder.html')

@app.route('/projects')
def list_projects():
    projects = [d for d in os.listdir(PROJECTS_DIR) if os.path.isdir(os.path.join(PROJECTS_DIR, d))]
    return jsonify({"projects": sorted(projects)})

@app.route('/create_project', methods=['POST'])
def create_project():
    name = request.json.get('name')
    if not name: return jsonify({"success": False})
    path = get_project_dir(name)
    if os.path.exists(os.path.join(path, "templates", "index.html")): return jsonify({"success": True, "name": name})
    app_code = f"""import os
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', {USER_APP_PORT}))
    app.run(debug=True, host='0.0.0.0', port=port)
"""
    with open(os.path.join(path, "app.py"), "w") as f: f.write(app_code)
    with open(os.path.join(path, "templates", "index.html"), "w") as f:
        f.write(f"<!DOCTYPE html><html><head><style>:root{{--primary:#6366f1;--bg:#ffffff;}}body{{background:var(--bg);font-family:sans-serif;}}</style></head><body><h1>{name}</h1><p>Ready.</p></body></html>")
    return jsonify({"success": True, "name": name})

@app.route('/delete_project', methods=['POST'])
def delete_project():
    name = request.json.get('name')
    path = get_project_dir(name)
    if os.path.exists(path):
        create_backup(name, "Pre_Delete")
        shutil.rmtree(path)
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/get_file', methods=['POST'])
def get_file():
    data = request.json
    base = get_project_dir(data.get('project'))
    path = os.path.join(base, 'templates', 'index.html') if data.get('filename') == 'index.html' else os.path.join(base, 'app.py')
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f: return jsonify({"code": f.read()})
    return jsonify({"code": ""})

@app.route('/save_file', methods=['POST'])
def save_file():
    data = request.json
    base = get_project_dir(data.get('project'))
    path = os.path.join(base, 'templates', 'index.html') if data.get('filename') == 'index.html' else os.path.join(base, 'app.py')
    create_backup(data.get('project'), f"Manual_Save_{data.get('filename')}")
    with open(path, "w", encoding="utf-8") as f: f.write(data.get('code'))
    return jsonify({"success": True})

# --- LIVE SERVER ---
global current_user_process
current_user_process = None

@app.route('/run_app/<project>')
def run_app(project):
    global current_user_process
    
    # Kill ANY running process first to prevent "Zombie Apps"
    if current_user_process:
        try: os.kill(current_user_process.pid, signal.SIGTERM); current_user_process.wait()
        except: pass
        current_user_process = None

    project_path = get_project_dir(project) # Explicitly get the dir for THIS project
    
    if not os.path.exists(os.path.join(project_path, "app.py")): 
        return jsonify({"success": False, "error": "app.py missing"})

    try:
        env = os.environ.copy(); env['PORT'] = str(USER_APP_PORT)
        for k in ['WERKZEUG_SERVER_FD', 'WERKZEUG_RUN_MAIN']: 
            if k in env: del env[k]
            
        # Run python IN the specific project folder
        current_user_process = subprocess.Popen([sys.executable, "app.py"], cwd=project_path, env=env)
        time.sleep(2) 
        return jsonify({"success": True, "url": f"http://127.0.0.1:{USER_APP_PORT}"})
    except Exception as e: return jsonify({"success": False, "error": str(e)})

@app.route('/stop_app')
def stop_app():
    global current_user_process
    if current_user_process:
        try: os.kill(current_user_process.pid, signal.SIGTERM); current_user_process = None
        except: pass
    return jsonify({"success": True})

# --- HISTORY & STARRED ---
@app.route('/history/<project>')
def get_history(project):
    cleanup_old_backups(project) # Auto-cleanup when history is loaded
    
    backup_folder = os.path.join(BACKUP_DIR, secure_filename(project))
    if not os.path.exists(backup_folder): return jsonify({"history": []})
    backups = []
    for f in sorted(os.listdir(backup_folder), reverse=True):
        if f.endswith('.zip'):
            parts = f.split('__')
            if len(parts) >= 2:
                is_starred = "_STARRED" in f
                label = parts[1].replace('.zip', '').replace('_', ' ').replace(' STARRED', '')
                backups.append({"file": f, "label": label, "starred": is_starred})
    return jsonify({"history": backups})

@app.route('/toggle_star', methods=['POST'])
def toggle_star():
    data = request.json
    project = data.get('project')
    filename = data.get('file')
    folder = os.path.join(BACKUP_DIR, secure_filename(project))
    old_path = os.path.join(folder, filename)
    
    if os.path.exists(old_path):
        if "_STARRED" in filename:
            new_name = filename.replace("_STARRED", "")
        else:
            new_name = filename.replace(".zip", "_STARRED.zip")
            
        os.rename(old_path, os.path.join(folder, new_name))
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/restore_project', methods=['POST'])
def restore_project():
    data = request.json
    project = data.get('project')
    project_path = get_project_dir(project)
    backup_path = os.path.join(BACKUP_DIR, secure_filename(project), data.get('backup_file'))
    if os.path.exists(backup_path):
        create_backup(project, "Pre_Restore_Safety")
        shutil.rmtree(project_path)
        os.makedirs(project_path)
        shutil.unpack_archive(backup_path, project_path)
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/preview/<project>')
def preview(project):
    path = os.path.join(get_project_dir(project), 'templates', 'index.html')
    if os.path.exists(path): return send_file(path)
    return "No index.html found", 404

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    project = data.get('project')
    prompt = data.get('prompt')
    
    base = get_project_dir(project)
    app_path = os.path.join(base, 'app.py')
    html_path = os.path.join(base, 'templates', 'index.html')
    
    curr_app = ""
    curr_html = ""
    if os.path.exists(app_path): 
        with open(app_path, "r", encoding="utf-8") as f: curr_app = f.read()
    if os.path.exists(html_path): 
        with open(html_path, "r", encoding="utf-8") as f: curr_html = f.read()
    
    create_backup(project, "AI_Update")

    sys_instr = f"""
    You are an expert Full Stack Python Developer.
    User Request: "{prompt}"
    
    Current app.py:
    {curr_app}
    
    Current index.html:
    {curr_html}
    
    CRITICAL RULES:
    1. Return VALID JSON with keys: "app_code", "html_code".
    2. YOU MUST RETURN THE FULL CODE FOR BOTH FILES.
    3. Ensure imports (import os) are present in app.py.
    4. Main block: port = int(os.environ.get('PORT', {USER_APP_PORT}))
    """
    
    tools = [types.Tool(google_search=types.GoogleSearch())] if data.get('use_news') else []
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=sys_instr,
            config=types.GenerateContentConfig(tools=tools, response_mime_type="application/json")
        )
        result = json.loads(clean_ai_json(response.text))
        
        new_app = result.get('app_code', '').strip()
        new_html = result.get('html_code', '').strip()

        if len(new_app) > 50: 
            with open(app_path, "w", encoding="utf-8") as f: f.write(new_app)
        if len(new_html) > 10: 
            with open(html_path, "w", encoding="utf-8") as f: f.write(new_html)

        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)})

@app.route('/download_zip/<project>')
def download_zip(project):
    src = get_project_dir(project)
    zip_path_base = os.path.join(BACKUP_DIR, f"{project}_download")
    zip_path = shutil.make_archive(zip_path_base, 'zip', src)
    return send_file(zip_path, as_attachment=True, download_name=f"{project}_fullstack.zip")

@app.route('/upload_asset', methods=['POST'])
def upload_asset():
    if 'file' not in request.files: return jsonify({"success": False})
    file = request.files['file']
    unique = f"{uuid.uuid4().hex[:6]}_{secure_filename(file.filename)}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique))
    path = f"/static/uploads/{unique}"
    tag = f'<img src="{path}" style="max-width:100%">' 
    if unique.endswith(('mp4','mov')): tag = f'<video controls src="{path}"></video>'
    return jsonify({"success": True, "snippet": tag})

if __name__ == '__main__':
    print("--- Full Stack AI Builder running on http://127.0.0.1:5002 ---")
    app.run(debug=True, port=5002)