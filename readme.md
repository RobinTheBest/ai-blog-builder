# 🚀 AI Blog Builder Pro

_Updated: includes Asset Uploads and Visual Edit features._

A powerful "Text-to-Website" generator powered by **Google Gemini 2.5 Flash**. 
Build, edit, and publish modern blogs using natural language prompts, or tweak the code manually with a built-in visual editor.

## ✨ Features

- **⚡️ AI Generation:** Create full HTML/CSS/JS blogs from a simple text prompt (e.g., "Make a cyberpunk tech blog").
- **🧠 Context Aware:** The AI reads your existing project HTML and updates the site based on your prompt.
- **📁 Asset Uploads (Images & Videos):** Upload images or videos from the sidebar; the app saves them to `static/uploads/` and returns an embeddable HTML snippet (img/video) you can paste into prompts or the code editor.
- **✏️ Visual Edit Mode:** Toggle Visual Edit to click-and-edit text inside the live preview. Save visual edits back to the generated HTML file.
- **💻 Code Editor:** Edit the full HTML directly in the sidebar and save changes instantly.
- **🔁 Live Preview & Download:** Preview changes live and download the generated HTML via the Download button.
- **🔒 Secure:** Store your Gemini API key in a `.env` file (`GEMINI_API_KEY`) — the app reads it via `python-dotenv`.

## 🛠️ Tech Stack

* **Backend:** Python, Flask
* **AI Model:** Gemini 2.5 Flash (via `google-genai` SDK)
* **Frontend:** HTML5, CSS3, JavaScript

## 📦 Installation

### 1. Clone the repository
```bash
git clone [https://github.com/YOUR_USERNAME/ai-blog-builder.git](https://github.com/YOUR_USERNAME/ai-blog-builder.git)
cd ai-blog-builder