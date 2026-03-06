**CourseCraft - AI Learning Path Generator**
CourseCraft is an AI-powered web application that generates structured, highly customized learning paths for any skill. 
Built with Flask and the Groq API (Llama 3), it takes the guesswork out of learning by providing phased curriculums complete 
with objectives, topics, and practical projects.

**Features**

🧠 AI-Powered Generation: Instantly builds comprehensive curriculums based on skill, duration, and experience level.

🔐 Google Authentication: Secure user login using Google Identity Services.

📊 Private History Tracking: Logged-in users can save, view, search, and delete their past generated curriculums.

⏳ Guest Quotas: Unregistered users get 3 free generations before being prompted to sign in.

📄 PDF Export: Download any generated curriculum as a clean, beautifully formatted PDF.

🌓 Dark/Light Mode: Premium "Aurora Tech" UI theme that automatically adapts to system preferences.

⚡ Spell Checking: Built-in typo correction for skill inputs.

🛠️ Tech Stack

**Frontend**

HTML5, CSS3, Vanilla JavaScript

html2pdf.js (for PDF generation)

Google Identity Services API

Backend:

Python 3.x

Flask (Web Framework)

Flask-SQLAlchemy (SQLite Database for users and history)

Requests (API calls)

**AI Engine:**
Groq API utilizing llama-3.3-70b-versatile

 **Prerequisites**

Before you begin, ensure you have the following:

Python 3.8+ installed on your machine.

A Groq API Key (Get one free at console.groq.com).

A Google OAuth Client ID (Get one from the Google Cloud Console).

**Installation & Setup**
1. Clone the repository

git clone [https://github.com/ambatitharunsai-tech/coursecraft.git](https://github.com/ambatitharunsai-tech/coursecraft.git)
cd coursecraft




**📂 Project Structure**
coursecraft/
│
├── app.py                  # Main Flask backend application
├── requirements.txt        # Python dependencies
├── instance/
│   └── history.db          # SQLite Database (Auto-generated)
│
├── static/
│   ├── style.css           # UI Styling
│   ├── script.js           # Frontend logic & API calls
│   └── dictionaries/       # Typo.js dictionary files
│
└── templates/
    └── index.html          # Main application interface


**Contributing**
Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

**📝 License**
This project is open-source and available under the MIT License.
