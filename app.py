from flask import Flask, request, jsonify, send_file, render_template
import requests, json, re, os, io, datetime
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ---------------- DATABASE ----------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(50), nullable=False)
    skill = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    curriculum = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()

# ---------------- HELPERS ----------------

def save_history(skill, duration, curriculum):
    record = SearchHistory(
        timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        skill=skill,
        duration=duration,
        curriculum=json.dumps(curriculum)
    )
    db.session.add(record)
    db.session.commit()


def parse_curriculum(text):
    """Extract JSON safely from AI response"""
    try:
        # Improved stability: Clean out markdown code blocks that LLMs frequently output
        text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```\s*', '', text)
        
        match = re.search(r'\{.*\}', text, re.S)
        if not match:
            return None
        return json.loads(match.group())
    except Exception as e:
        print(f"Error parsing curriculum JSON: {e}")
        return None


def generate_curriculum(prompt):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"error": "Missing GROQ_API_KEY"}

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)

        print("Status:", response.status_code)
        print("Response:", response.text[:300])

        response.raise_for_status()
        result = response.json()

        return result["choices"][0]["message"]["content"]

    except requests.exceptions.RequestException as e:
        print("Groq Error:", e)
        return {"error": "LLM request failed or timed out"}

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.json

    skill = data.get("skill", "").strip()
    duration = data.get("duration", "6 Months")

    if not skill:
        return jsonify({"error": "Skill cannot be empty"}), 400

    prompt = f"""
Create a structured learning curriculum for {skill}.

Rules:
- Provide clear phases
- Each phase includes courses with topics
- Return ONLY valid JSON

Format:
{{
 "curriculum":[
   {{
     "phase_title":"Phase 1",
     "courses":[
       {{
         "course_title":"Course",
         "topics":["topic1","topic2"]
       }}
     ]
   }}
 ]
}}
"""

    ai_response = generate_curriculum(prompt)

    if isinstance(ai_response, dict) and "error" in ai_response:
        return jsonify(ai_response), 500

    structured = parse_curriculum(ai_response)

    if not structured:
        return jsonify({"error": "Invalid AI response"}), 500

    save_history(skill, duration, structured["curriculum"])

    return jsonify(structured)


@app.route("/history", methods=["GET"])
def history():
    records = SearchHistory.query.order_by(SearchHistory.id.desc()).all()

    history_list = []
    for r in records:
        # Improved stability: Prevent crash if DB contains malformed JSON
        try:
            curr_data = json.loads(r.curriculum)
        except json.JSONDecodeError:
            curr_data = []

        history_list.append({
            "id": r.id,
            "timestamp": r.timestamp,
            "skill": r.skill,
            "duration": r.duration,
            "curriculum": curr_data
        })

    return jsonify(history_list)


@app.route("/clear-history", methods=["POST"])
def clear_history():
    """Clear all history from the database"""
    try:
        db.session.query(SearchHistory).delete()
        db.session.commit()
        return jsonify({"success": True, "message": "All history cleared"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/delete-history/<int:item_id>", methods=["POST"])
def delete_history_item(item_id):
    """Delete a specific history item from the database"""
    try:
        item = SearchHistory.query.get(item_id)
        if item:
            db.session.delete(item)
            db.session.commit()
            return jsonify({"success": True, "message": "Item deleted"})
        return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ---------------- START SERVER ----------------

if __name__ == "__main__":
    print("Server running at http://localhost:5051")
    app.run(host="0.0.0.0", port=5051)