from flask import Flask, request, jsonify, send_file, render_template, session
import requests, json, re, os, io, datetime
from flask_sqlalchemy import SQLAlchemy

# Google Auth Imports
try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    import google.auth.jwt
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

app = Flask(__name__)

# ---------------- SECURITY & DATABASE ----------------
app.secret_key = os.getenv("SECRET_KEY", "super_secret_development_key_123")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    searches_count = db.Column(db.Integer, default=0)

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.String(50), nullable=False)
    skill = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    curriculum = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()

# ---------------- HELPERS ----------------

def save_history(user_id, skill, duration, curriculum):
    record = SearchHistory(
        user_id=user_id,
        timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        skill=skill,
        duration=duration,
        curriculum=json.dumps(curriculum)
    )
    db.session.add(record)
    db.session.commit()

def parse_curriculum(text):
    try:
        text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```\s*', '', text)
        match = re.search(r'\{.*\}', text, re.S)
        if not match: return None
        return json.loads(match.group())
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return None

def generate_curriculum(prompt):
    api_key = os.getenv("GROQ_API_KEY").strip()
    if not api_key:
        return {"error": "Missing GROQ_API_KEY"}

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return {"error": "LLM request failed or timed out"}

# ---------------- AUTHENTICATION ROUTES ----------------

@app.route("/api/user", methods=["GET"])
def get_user():
    """Returns current user status and quotas"""
    user_id = session.get("user_id")
    if user_id:
        user = db.session.get(User, user_id)
        if user:
            return jsonify({
                "logged_in": True,
                "name": user.name,
                "email": user.email,
                "searches": user.searches_count
            })
    
    # Guest user logic
    guest_searches = session.get("guest_searches", 0)
    return jsonify({
        "logged_in": False,
        "guest_left": max(0, 3 - guest_searches)
    })

@app.route("/auth/google", methods=["POST"])
def auth_google():
    """Validates Google JWT and creates/logs in the user"""
    data = request.json
    token = data.get("token")
    is_dev_bypass = data.get("dev_bypass")

    # Developer bypass for testing without actual Google Credentials
    if is_dev_bypass:
        user = User.query.filter_by(google_id="dev-123").first()
        if not user:
            user = User(google_id="dev-123", email="test@example.com", name="Test Explorer")
            db.session.add(user)
            db.session.commit()
        session['user_id'] = user.id
        return jsonify({"success": True, "name": user.name})

    if not GOOGLE_AUTH_AVAILABLE:
        return jsonify({"error": "google-auth library not installed on server"}), 500

    try:
        # REPLACE 'YOUR_GOOGLE_CLIENT_ID' WITH YOUR ACTUAL CLIENT ID FROM GCP
        CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID")
        
        if CLIENT_ID == "YOUR_GOOGLE_CLIENT_ID":
            # Insecure fallback strictly for demonstration if Client ID isn't set
            idinfo = google.auth.jwt.decode(token, verify=False)
        else:
            # Secure verification
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), CLIENT_ID)

        google_id = idinfo['sub']
        user = User.query.filter_by(google_id=google_id).first()
        
        if not user:
            user = User(google_id=google_id, email=idinfo.get('email'), name=idinfo.get('name'))
            db.session.add(user)
        
        db.session.commit()
        session['user_id'] = user.id
        return jsonify({"success": True, "name": user.name})

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/auth/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"success": True})

# ---------------- APP ROUTES ----------------

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    # 1. Check Limits & Authentication
    user_id = session.get("user_id")
    
    if not user_id:
        guest_searches = session.get("guest_searches", 0)
        if guest_searches >= 3:
            return jsonify({"error": "limit_reached", "message": "Free limit reached. Sign in to continue."}), 403
        session["guest_searches"] = guest_searches + 1
    else:
        user = db.session.get(User, user_id)
        user.searches_count += 1
        db.session.commit()

    # 2. Generation logic
    data = request.json
    skill = data.get("skill", "").strip()
    duration = data.get("duration", "6 Months")

    if not skill:
        return jsonify({"error": "Skill cannot be empty"}), 400

    prompt = f"Create a structured learning curriculum for {skill}.\nRules:\n- Provide clear phases\n- Each phase includes courses with topics\n- Return ONLY valid JSON\nFormat:\n{{\"curriculum\":[{{\"phase_title\":\"Phase 1\",\"courses\":[{{\"course_title\":\"Course\",\"topics\":[\"topic1\"]}}]}}]}}"
    
    ai_response = generate_curriculum(prompt)

    if isinstance(ai_response, dict) and "error" in ai_response:
        return jsonify(ai_response), 500

    structured = parse_curriculum(ai_response)
    if not structured: return jsonify({"error": "Invalid AI response"}), 500

    # 3. Save History ONLY for logged-in users
    if user_id:
        save_history(user_id, skill, duration, structured["curriculum"])

    return jsonify(structured)

@app.route("/history", methods=["GET"])
def history():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized", "message": "Please log in to view history"}), 401

    records = SearchHistory.query.filter_by(user_id=user_id).order_by(SearchHistory.id.desc()).all()
    history_list = []
    
    for r in records:
        try:
            curr_data = json.loads(r.curriculum)
        except json.JSONDecodeError:
            curr_data = []

        history_list.append({
            "id": r.id, "timestamp": r.timestamp, "skill": r.skill,
            "duration": r.duration, "curriculum": curr_data
        })

    return jsonify(history_list)

@app.route("/clear-history", methods=["POST"])
def clear_history():
    user_id = session.get("user_id")
    if not user_id: return jsonify({"error": "unauthorized"}), 401
    try:
        SearchHistory.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/delete-history/<int:item_id>", methods=["POST"])
def delete_history_item(item_id):
    user_id = session.get("user_id")
    if not user_id: return jsonify({"error": "unauthorized"}), 401
    try:
        item = db.session.get(SearchHistory, item_id)
        if item and item.user_id == user_id:
            db.session.delete(item)
            db.session.commit()
            return jsonify({"success": True})
        return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Server running at http://localhost:5051")
    app.run(host="0.0.0.0", port=5051)
