from flask import Flask, request, jsonify, send_file, render_template, session, redirect, url_for
import requests, json, re, os, io, datetime, logging
from dotenv import load_dotenv
from sqlalchemy import text as sql_text
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

load_dotenv()
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

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
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = bool(os.getenv("RENDER_EXTERNAL_URL"))

# SQLite is convenient for local development. Configure DATABASE_URL on Render
# to use persistent PostgreSQL (for example, a dedicated Supabase database).
database_url = os.getenv("DATABASE_URL", "sqlite:///history.db").strip()
if database_url.startswith("postgres://"):
    database_url = "postgresql+psycopg://" + database_url[len("postgres://"):]
elif database_url.startswith("postgresql://"):
    database_url = "postgresql+psycopg://" + database_url[len("postgresql://"):]

engine_options = {"pool_pre_ping": True}
if database_url.startswith("postgresql+psycopg://"):
    engine_options.update({"pool_recycle": 300, "pool_size": 3, "max_overflow": 2})

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options
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

def parse_curriculum(raw_text):
    """Parse and validate the minimum curriculum contract expected by the UI."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        return None

    candidate = raw_text.strip()
    candidate = re.sub(r"^\`\`\`(?:json)?\s*|\s*\`\`\`$", "", candidate, flags=re.IGNORECASE).strip()

    try:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            # Compatibility fallback for providers that wrap JSON with prose.
            start, end = candidate.find("{"), candidate.rfind("}")
            if start < 0 or end <= start:
                return None
            parsed = json.loads(candidate[start:end + 1])

        if not isinstance(parsed, dict):
            return None
        curriculum = parsed.get("curriculum")
        if not isinstance(curriculum, list) or not curriculum:
            return None

        for phase in curriculum:
            if not isinstance(phase, dict):
                return None
            if not isinstance(phase.get("phase_title"), str) or not phase["phase_title"].strip():
                return None
            courses = phase.get("courses")
            if not isinstance(courses, list) or not courses:
                return None
            for course in courses:
                if not isinstance(course, dict):
                    return None
                if not isinstance(course.get("course_title"), str) or not course["course_title"].strip():
                    return None
                topics = course.get("topics")
                if not isinstance(topics, list) or not topics:
                    return None
                if any(not isinstance(topic, str) or not topic.strip() for topic in topics):
                    return None

        return {"curriculum": curriculum}
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("Could not parse curriculum JSON (%s)", type(exc).__name__)
        return None


def generate_curriculum(prompt):
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return {
            "error_type": "configuration",
            "error": "AI generation is not configured. Set GROQ_API_KEY in the server environment."
        }

    model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b").strip()
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a curriculum designer. Return only one valid JSON object with a top-level curriculum array. Do not include Markdown fences or extra commentary."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 3000,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=(10, 50))
        if response.status_code == 429:
            logger.warning("Groq rate limit returned HTTP 429")
            return {"error_type": "upstream", "error": "The AI provider is rate-limiting requests. Please retry shortly."}

        if not response.ok:
            logger.warning("Groq returned HTTP %s: %s", response.status_code, response.text[:600])
            if response.status_code in (401, 403):
                message = "AI provider authentication failed. Check GROQ_API_KEY."
            elif response.status_code == 400:
                message = "AI provider rejected the model or request. Check GROQ_MODEL and model access."
            else:
                message = f"AI provider request failed (HTTP {response.status_code})."
            return {"error_type": "upstream", "error": message}

        try:
            body = response.json()
        except ValueError:
            logger.warning("Groq returned a non-JSON HTTP response")
            return {"error_type": "upstream", "error": "AI provider returned an unreadable response."}

        choices = body.get("choices") if isinstance(body, dict) else None
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            logger.warning("Groq response has no valid choices array")
            return {"error_type": "upstream", "error": "AI provider returned an invalid response structure."}

        message = choices[0].get("message") or {}
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            logger.warning("Groq response had empty content")
            return {"error_type": "upstream", "error": "AI provider returned an empty response."}

        return {"content": content}

    except requests.exceptions.Timeout:
        logger.warning("Groq request timed out")
        return {"error_type": "upstream", "error": "AI generation timed out. Please try again."}
    except requests.exceptions.RequestException as exc:
        logger.warning("Groq request failed (%s)", type(exc).__name__)
        return {"error_type": "upstream", "error": "Could not reach the AI provider. Please try again shortly."}
    except Exception as exc:
        logger.exception("Unexpected error during Groq request (%s)", type(exc).__name__)
        return {"error_type": "internal", "error": "An unexpected server error occurred during AI generation."}


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
    """Verify a Google ID token and create or sign in the corresponding user."""
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()

    if not isinstance(token, str) or not token:
        return jsonify({"error": "Missing Google credential"}), 400
    if not client_id:
        return jsonify({"error": "Google sign-in is not configured. Use email and password or configure GOOGLE_CLIENT_ID."}), 503
    if not GOOGLE_AUTH_AVAILABLE:
        return jsonify({"error": "Google sign-in dependencies are unavailable"}), 503

    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
        if not idinfo.get("email_verified"):
            return jsonify({"error": "Google account email is not verified"}), 401

        google_id = idinfo.get("sub")
        email = (idinfo.get("email") or "").strip().lower()
        name = (idinfo.get("name") or email.split("@")[0]).strip()[:100]
        if not google_id or not email:
            return jsonify({"error": "Google did not provide a verified email"}), 401

        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            user = User.query.filter_by(email=email).first()
            if user:
                if user.google_id and user.google_id != google_id:
                    return jsonify({"error": "This email is linked to a different Google account"}), 409
                user.google_id = google_id
            else:
                user = User(google_id=google_id, email=email, name=name or email)
                db.session.add(user)

        db.session.commit()
        session.clear()
        session["user_id"] = user.id
        return jsonify({"success": True, "name": user.name})

    except Exception as exc:
        db.session.rollback()
        logger.warning("Google sign-in verification failed (%s)", type(exc).__name__)
        return jsonify({"error": "Google sign-in could not be verified. Try again or use email and password."}), 401


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""))

    data = request.get_json(silent=True) or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not all(isinstance(value, str) for value in (name, email, password)):
        return jsonify({"error": "Name, email, and password are required"}), 400
    name, email = name.strip(), email.strip().lower()
    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required"}), 400
    if len(name) > 100 or len(email) > 100:
        return jsonify({"error": "Name or email is too long"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must contain at least 8 characters"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(email=email, name=name, password_hash=generate_password_hash(password))
    try:
        db.session.add(user)
        db.session.commit()
        session.clear()
        session["user_id"] = user.id
        return jsonify({"success": True, "name": user.name})
    except Exception as exc:
        db.session.rollback()
        logger.exception("Registration failed (%s)", type(exc).__name__)
        return jsonify({"error": "Could not create the account. Please try again."}), 500


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""))

    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    if not isinstance(email, str) or not isinstance(password, str) or not email.strip() or not password:
        return jsonify({"error": "Email and password are required"}), 400

    email = email.strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user or not user.password_hash or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    session.clear()
    session["user_id"] = user.id
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
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please sign in to generate and save a curriculum."}), 401

    user = db.session.get(User, user_id)
    if not user:
        session.clear()
        return jsonify({"error": "Your session has expired. Please sign in again."}), 401

    data = request.get_json(silent=True) or {}
    skill = data.get("skill", "")
    duration = data.get("duration") or "6 Months"
    level = data.get("level") or "Beginner"

    if not isinstance(skill, str) or not skill.strip():
        return jsonify({"error": "Skill cannot be empty"}), 400
    if not isinstance(duration, str) or not isinstance(level, str):
        return jsonify({"error": "Duration and experience level must be text"}), 400

    skill = skill.strip()
    duration = duration.strip()[:50]
    level = level.strip()[:40]
    if len(skill) > 120:
        return jsonify({"error": "Please keep the skill or topic under 120 characters"}), 400
    if not duration:
        duration = "6 Months"
    if not level:
        level = "Beginner"

    prompt = f"""Create a practical, progressive learning curriculum.

Skill or goal: {skill}
Target duration: {duration}
Learner's current level: {level}

Requirements:
- Progress from fundamentals toward the requested level.
- Provide 3 to 6 chronological phases sized for the target duration.
- Every phase must include at least one course.
- Every course must have 3 to 8 concise, accurate topics.
- Include a practical_project string for each course when appropriate.
- Use recognized terminology and avoid invented facts.
- Return ONLY a valid JSON object, with no Markdown or extra prose.
- The object must follow this structure:
{{"curriculum":[{{"phase_title":"Phase 1: Fundamentals","courses":[{{"course_title":"Course title","topics":["Topic 1","Topic 2"],"practical_project":"A small practical project"}}]}}]}}
"""

    ai_response = generate_curriculum(prompt)
    if "error" in ai_response:
        error_type = ai_response.get("error_type")
        status_code = {"upstream": 502, "configuration": 503, "internal": 500}.get(error_type, 502)
        return jsonify({"error": ai_response["error"]}), status_code

    structured = parse_curriculum(ai_response.get("content"))
    if not structured:
        return jsonify({"error": "The AI provider returned invalid curriculum data. Please try again."}), 502

    try:
        # The history insert and successful-generation counter increment share a commit.
        user.searches_count = (user.searches_count or 0) + 1
        save_history(user_id, skill, duration, structured["curriculum"])
    except Exception as exc:
        db.session.rollback()
        logger.exception("Database error while saving generated curriculum (%s)", type(exc).__name__)
        return jsonify({"error": "The curriculum was generated but could not be saved. Check database connectivity and try again."}), 500

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


@app.route("/shared/<int:item_id>", methods=["GET"])
def shared_curriculum(item_id):
    item = db.session.get(SearchHistory, item_id)
    if not item:
        return jsonify({"error": "Curriculum not found"}), 404
        
    try:
        curr_data = json.loads(item.curriculum)
    except Exception:
        curr_data = []
        
    return render_template("shared.html", skill=item.skill, curriculum=curr_data)

@app.route("/health", methods=["GET"])
def health():
    """Health check for Render and diagnostics; verifies database connectivity."""
    try:
        db.session.execute(sql_text("SELECT 1"))
        return jsonify({"status": "ok", "database": "connected"}), 200
    except Exception as exc:
        db.session.rollback()
        logger.warning("Health check database failure (%s)", type(exc).__name__)
        return jsonify({"status": "degraded", "database": "unavailable"}), 503


if __name__ == "__main__":
    print("Server running at http://localhost:5050")
    app.run(host="0.0.0.0", port=5050)