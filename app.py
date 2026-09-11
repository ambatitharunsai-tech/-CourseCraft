from flask import Flask, request, jsonify, send_file, render_template, session, redirect, url_for
import requests, json, re, os, io, datetime
from werkzeug.security import generate_password_hash, check_password_hash
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
    google_id = db.Column(db.String(100), unique=True, nullable=True) # Now nullable
    email = db.Column(db.String(100), unique=True, nullable=False) # Now required & unique
    password_hash = db.Column(db.String(256), nullable=True) # Nullable for google-only users
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
        if not match: 
            print("No JSON braces found in text")
            return None
        parsed = json.loads(match.group())
        
        if not isinstance(parsed, dict) or "curriculum" not in parsed:
            print("Missing 'curriculum' key in parsed JSON")
            return None
        if not isinstance(parsed["curriculum"], list):
            print("'curriculum' is not a list")
            return None
            
        return parsed
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return None

def generate_curriculum(prompt):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"error_type": "internal", "error": "Missing GROQ_API_KEY"}
    api_key = api_key.strip()

    model = os.getenv("GROQ_MODEL", "llama3-8b-8192")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=(10, 50))
        if response.status_code == 429:
            return {"error_type": "upstream", "error": "Rate limit exceeded. Please try again later."}
        
        response.raise_for_status()
        json_data = response.json()
        
        if not json_data.get("choices") or not isinstance(json_data["choices"], list):
            return {"error_type": "upstream", "error": "Malformed response structure from Groq"}
            
        message = json_data["choices"][0].get("message", {})
        content = message.get("content")
        
        if not content:
            return {"error_type": "upstream", "error": "Empty response from Groq"}
            
        return {"content": content}
        
    except requests.exceptions.Timeout:
        return {"error_type": "upstream", "error": "LLM request timed out"}
    except requests.exceptions.RequestException as e:
        error_details = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_details += f" | Body: {e.response.text}"
        print(f"LLM request error: {error_details}")
        return {"error_type": "upstream", "error": f"LLM request failed: {error_details}"}
    except Exception as e:
        print(f"Unexpected LLM error: {e}")
        return {"error_type": "internal", "error": "Internal unexpected error"}

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
    data = request.json or {}
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
        email = idinfo.get('email')
        
        user = User.query.filter_by(google_id=google_id).first()
        
        if not user and email:
            # Check if user registered with email/password first
            user = User.query.filter_by(email=email).first()
            if user:
                # Link google account
                user.google_id = google_id
            else:
                user = User(google_id=google_id, email=email, name=idinfo.get('name'))
                db.session.add(user)
        elif not user:
            # Fallback if no email (unlikely for google auth)
            user = User(google_id=google_id, email=f"google_{google_id}@example.com", name=idinfo.get('name'))
            db.session.add(user)
            
        db.session.commit()
        session['user_id'] = user.id
        return jsonify({"success": True, "name": user.name})

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    
    data = request.json or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    
    if not name or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400
        
    hashed_pw = generate_password_hash(password)
    user = User(email=email, name=name, password_hash=hashed_pw)
    db.session.add(user)
    db.session.commit()
    
    session['user_id'] = user.id
    return jsonify({"success": True, "name": user.name})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
        
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400
        
    user = User.query.filter_by(email=email).first()
    if not user or not user.password_hash or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401
        
    session['user_id'] = user.id
    return jsonify({"success": True, "name": user.name})

@app.route("/auth/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"success": True})

# ---------------- APP ROUTES ----------------

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    # 1. Check Authentication
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized", "message": "Sign in to continue."}), 401
        
    # 2. Validate Input
    data = request.json or {}
    skill = data.get("skill", "")
    if skill:
        skill = skill.strip()
    duration = data.get("duration", "6 Months")

    if not skill:
        return jsonify({"error": "Skill cannot be empty"}), 400

    prompt = f"Create a structured learning curriculum for {skill}.\nRules:\n- Provide clear phases\n- Each phase includes courses with topics\n- Return ONLY valid JSON\nFormat:\n{{\"curriculum\":[{{\"phase_title\":\"Phase 1\",\"courses\":[{{\"course_title\":\"Course\",\"topics\":[\"topic1\"]}}]}}]}}"
    
    # 3. Request LLM Generation
    ai_response = generate_curriculum(prompt)

    if "error" in ai_response:
        status_code = 502 if ai_response.get("error_type") == "upstream" else 500
        return jsonify({"error": ai_response["error"]}), status_code

    # 4. JSON Validation
    structured = parse_curriculum(ai_response["content"])
    if not structured:
        return jsonify({"error": "Invalid AI response format"}), 502

    # 5. Persist and Consume Quota AFTER successful generation
    try:
        user = db.session.get(User, user_id)
        if user:
            user.searches_count += 1
            # Wait, db.session.commit() for user and save_history can be batched
            
        save_history(user_id, skill, duration, structured["curriculum"])
        # save_history commits internally, which also persists user quota increment
    except Exception as e:
        db.session.rollback()
        print(f"Database error saving curriculum: {e}")
        return jsonify({"error": "Failed to save curriculum history"}), 500

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
    print("Server running at http://localhost:5050")
    app.run(host="0.0.0.0", port=5050)