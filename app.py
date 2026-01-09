import os
import uuid
from flask import Flask, render_template, request, jsonify, send_file, url_for
from werkzeug.utils import secure_filename
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Securely get the API Key
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GENAI_API_KEY:
    print("❌ WARNING: GEMINI_API_KEY not found in .env")

# Initialize Client (for text generation only now)
client = genai.Client(api_key=GENAI_API_KEY)

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
BLOG_FILE = os.path.join(TEMPLATES_DIR, "generated_blog.html")

# Allowed file types for security
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'mp4', 'mov', 'webm'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('builder.html')

@app.route('/preview')
def preview():
    if not os.path.exists(BLOG_FILE):
        return "<div style='text-align:center; padding:50px; font-family:sans-serif;'><h1>No blog yet.</h1></div>"
    # Add a timestamp to force browser to load latest version
    return render_template('generated_blog.html', t=uuid.uuid4().hex)

# --- NEW: ASSET UPLOAD ROUTE ---
@app.route('/upload_asset', methods=['POST'])
def upload_asset():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Generate unique name to prevent overwrites (e.g., mycat.jpg -> mycat_a1b2c3.jpg)
        unique_filename = f"{filename.rsplit('.', 1)[0]}_{uuid.uuid4().hex[:6]}.{filename.rsplit('.', 1)[1].lower()}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Determine HTML snippet based on file type
        web_path = f"/static/uploads/{unique_filename}"
        if filename.rsplit('.', 1)[1].lower() in ['mp4', 'mov', 'webm']:
             snippet = f'<video controls width="100%"><source src="{web_path}" type="video/mp4">Your browser does not support the video tag.</video>'
        else:
             snippet = f'<img src="{web_path}" alt="Uploaded Image" style="max-width:100%; height:auto;">'

        return jsonify({
            "success": True, 
            "path": web_path, 
            "snippet": snippet,
            "filename": unique_filename
        })
    
    return jsonify({"success": False, "error": "File type not allowed"})

# --- EXISTING AI & SAVE ROUTES ---
@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    user_prompt = data.get('prompt')
    current_code = ""
    if os.path.exists(BLOG_FILE):
        with open(BLOG_FILE, "r", encoding="utf-8") as f: current_code = f.read()

    system_instruction = f"""
    You are an expert AI Web Developer. 
    User Request: "{user_prompt}"
    Current Code Context: {current_code if current_code else "None"}

    INSTRUCTIONS:
    1. Output the COMPLETE HTML file.
    2. If the user asks to insert an image or video snippet they provide, place it exactly where requested.
    3. Return ONLY raw HTML code. No markdown.
    """
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=system_instruction)
        clean_code = response.text.replace("```html", "").replace("```", "").strip()
        with open(BLOG_FILE, "w", encoding="utf-8") as f: f.write(clean_code)
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)})

@app.route('/save_code', methods=['POST'])
def save_code():
    new_code = request.json.get('code')
    with open(BLOG_FILE, "w", encoding="utf-8") as f: f.write(new_code)
    return jsonify({"success": True})

@app.route('/get_code', methods=['GET'])
def get_code():
    if os.path.exists(BLOG_FILE):
        with open(BLOG_FILE, "r", encoding="utf-8") as f: return jsonify({"code": f.read()})
    return jsonify({"code": ""})

@app.route('/download')
def download_file():
    if os.path.exists(BLOG_FILE):
        return send_file(BLOG_FILE, as_attachment=True, download_name='my_ai_blog.html')
    return "No file", 404

if __name__ == '__main__':
    # Using port 5002 to avoid AirPlay conflict on Macs
    print("--- AI Builder with Uploads running on http://127.0.0.1:5002 ---")
    app.run(debug=True, port=5002)