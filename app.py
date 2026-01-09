import os
from flask import Flask, render_template, request, jsonify, send_file
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Securely get the API Key
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GENAI_API_KEY:
    raise ValueError("❌ Error: GEMINI_API_KEY not found in .env file.")

# Initialize Client
client = genai.Client(api_key=GENAI_API_KEY)

# Define paths
BASE_DIR = "/Users/johnzhang/Downloads/AI webapp2"
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
BLOG_FILE = os.path.join(TEMPLATES_DIR, "generated_blog.html")

@app.route('/')
def index():
    return render_template('builder.html')

@app.route('/preview')
def preview():
    """Renders the generated blog. Adds a script for Visual Editing if needed."""
    if not os.path.exists(BLOG_FILE):
        return "<div style='text-align:center; padding:50px; font-family:sans-serif;'><h1>No blog yet.</h1></div>"
    return render_template('generated_blog.html')

@app.route('/download')
def download_file():
    if os.path.exists(BLOG_FILE):
        return send_file(BLOG_FILE, as_attachment=True, download_name='my_ai_blog.html')
    return "Error: No blog generated yet!", 404

# --- NEW: Get Raw Code (For Import/Manual Edit) ---
@app.route('/get_code', methods=['GET'])
def get_code():
    if os.path.exists(BLOG_FILE):
        with open(BLOG_FILE, "r", encoding="utf-8") as f:
            return jsonify({"code": f.read()})
    return jsonify({"code": ""})

# --- NEW: Save Raw Code (For Manual/Visual Save) ---
@app.route('/save_code', methods=['POST'])
def save_code():
    data = request.json
    new_code = data.get('code')
    
    if new_code:
        with open(BLOG_FILE, "w", encoding="utf-8") as f:
            f.write(new_code)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "No code provided"})

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    user_prompt = data.get('prompt')
    
    # Read existing code (Context)
    current_code = ""
    if os.path.exists(BLOG_FILE):
        with open(BLOG_FILE, "r", encoding="utf-8") as f:
            current_code = f.read()

    # Improved System Prompt for "Adding Articles" and "Style Changes"
    system_instruction = f"""
    You are an expert AI Web Developer. 
    
    User Request: "{user_prompt}"
    
    Current Code Context:
    {current_code if current_code else "No code yet. Start from scratch."}

    INSTRUCTIONS:
    1. If the user asks to "Add an article", APPEND it to the existing blog list (do not delete old ones unless asked).
    2. If the user asks to "Change style", modify ONLY the CSS in the <style> tags.
    3. You must output the COMPLETE, VALID HTML file every time.
    4. Ensure the layout is responsive and modern.
    5. Return ONLY raw HTML code. No markdown.
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=system_instruction
        )
        
        clean_code = response.text.replace("```html", "").replace("```", "").strip()

        with open(BLOG_FILE, "w", encoding="utf-8") as f:
            f.write(clean_code)

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    print(f"--- AI Blog Builder Pro running on http://127.0.0.1:5000 ---")
    app.run(debug=True, port=5000)