# 🚀 AI Blog Builder Pro

_Updated: includes Asset Uploads, Visual Edit, Live App runner, backups, and more._

A powerful "Text-to-Website" generator powered by **Google Gemini 2.5 Flash**. Build, edit, and publish modern blogs using natural language prompts, or tweak the code manually with a built-in visual editor and live app runner.

## ✨ Key Features

- **⚡️ AI Full-Stack Generation:** Update or regenerate both `app.py` and `templates/index.html` from a single natural-language prompt. The AI is context-aware and receives your current files.
- **📁 Asset Uploads (Images & Videos):** Upload files via the sidebar; assets are saved to `static/uploads/` and the app returns an embeddable snippet (image or video) you can paste into prompts or the editor.
- **✏️ Visual Edit Mode:** Toggle Visual Edit to click-edit text in the live preview. Edits are saved back to `templates/index.html` while preserving interactive elements (buttons/links are temporarily replaced during editing).
- **🔁 Live Preview & Live App Runner:** Preview static HTML or run the project's `app.py` locally from the builder. Start/stop the user's Flask app from the UI and view it in the embedded iframe.
- **🧰 Code Editor:** Built-in editor for `index.html` and `app.py` with manual save and instant preview reload.
- **🎨 Theme Color Editor:** Detects `:root` CSS variables in `index.html` and exposes color pickers to update theme colors live.
- **🗂️ Backup & History:** Automatic backups are created before saves, generates, restores, and deletes. Use the Time Machine to restore previous versions (backups stored under `backups/`).
- **🛡️ Safety & Auto-Patching:** The AI generator enforces safety checks (won't overwrite with empty outputs). The tool also auto-patches imported apps to include sane `__main__` run blocks and `PORT` handling.
- **🌍 News Mode:** Optional tool support for fetching news/context when generating content (enableable per generate request).
- **📦 Export/Download ZIP:** Download a project's full filesystem as a ZIP from the UI.
- **🔒 Secure Keys:** Store `GEMINI_API_KEY` in a `.env` file; the app reads it using `python-dotenv`.

## 🛠️ Tech Stack

- **Backend:** Python, Flask
- **AI Model:** Gemini 2.5 Flash (via `google-genai` SDK)
- **Frontend:** HTML5, CSS3, JavaScript

## Quick Start

1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-blog-builder.git
cd ai-blog-builder
```

2. Install dependencies (example)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Create a `.env` file with your Gemini key

```
GEMINI_API_KEY=your_api_key_here
```

4. Run the builder

```bash
python app.py
```

Open the builder in your browser (usually http://127.0.0.1:5002) to create projects, upload assets, edit visually, or run a project's Flask app from the UI.

---
If you'd like, I can also add a `requirements.txt` and a short demo project, or run the app locally to verify the README steps — tell me which you prefer.
