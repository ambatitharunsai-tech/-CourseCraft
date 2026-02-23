from flask import Flask, request, jsonify, send_file, render_template
import requests
import json
import re
import os
import io
import datetime
from flask_sqlalchemy import SQLAlchemy

# Initialize Flask
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
    
    # Auto-cleanup: Keep only the latest 50 searches
    count = SearchHistory.query.count()
    if count > 50:
        oldest_records = SearchHistory.query.order_by(SearchHistory.id.asc()).limit(count - 50).all()
        for old in oldest_records:
            db.session.delete(old)
            
    db.session.commit()


def parse_curriculum(text):
    """Extract JSON safely from AI response"""
    try:
        # Clean out markdown code blocks that LLMs frequently output
        text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```\s*', '', text)
        
        match = re.search(r'\{.*\}', text, re.S)
        if not match:
            return None
            
        data = json.loads(match.group())
        
        # Standardize format
        if "curriculum" in data:
            return data
        elif isinstance(data, list):
            return {"curriculum": data}
        return {"curriculum": [data]}
    except Exception as e:
        print(f"Error parsing curriculum JSON: {e}")
        return None


def generate_curriculum(prompt):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"error": "Missing GROQ_API_KEY environment variable. Please set it in Render."}

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "response_format": {"type": "json_object"} 
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=90)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]

    except requests.exceptions.RequestException as e:
        error_details = f"LLM request failed: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json().get("error", {}).get("message", str(e))
            except:
                error_details = f"HTTP {e.response.status_code}: {e.response.reason}"
                
        return {"error": error_details}


# ---------------- JSON SCHEMA DEFINITION ----------------
# We define this strictly outside the route to avoid python f-string curly-brace escaping issues
STRICT_SCHEMA = """
{
  "type": "object",
  "properties": {
    "curriculum": {
      "type": "array",
      "description": "Chronological learning phases. Strictly progress from beginner to advanced.",
      "items": {
        "type": "object",
        "properties": {
          "phase_title": {
            "type": "string",
            "description": "Format: 'Phase X: [Dynamic Descriptive Title]'. Flawless spelling."
          },
          "phase_objective": {
            "type": "string",
            "description": "A dynamic, engaging 1-sentence summary of what the user will build or achieve."
          },
          "courses": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "course_title": {
                  "type": "string",
                  "description": "Professional, accurate real-world subject name."
                },
                "practical_project": {
                  "type": "string",
                  "description": "Specific hands-on mini-project idea to apply concepts."
                },
                "topics": {
                  "type": "array",
                  "items": {
                    "type": "string",
                    "description": "Concise, actionable sub-topic. 5-10 words maximum. Standard professional vocabulary."
                  }
                }
              },
              "required": ["course_title", "topics"]
            }
          }
        },
        "required": ["phase_title", "courses"]
      }
    }
  },
  "required": ["curriculum"]
}
"""


# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.json

    skill = data.get("skill", "").strip()
    duration = data.get("duration", "6 Months")
    level = data.get("level", "Beginner")

    if not skill:
        return jsonify({"error": "Skill cannot be empty"}), 400

    # DYNAMIC TIME AND LEVEL INSTRUCTIONS
    phase_instructions = ""
    if "3" in duration:
        phase_instructions = "This is a fast-paced, Intensive 3-Month Bootcamp. Create exactly 1 to 2 phases max. Focus on rapid skill acquisition."
    elif "1" in duration or "year" in duration.lower():
        phase_instructions = "This is a Comprehensive 1-Year Masterclass. Create exactly 4 to 6 phases. Build from foundations to highly advanced mastery."
    else:
        phase_instructions = "This is a Standard 6-Month Track. Create exactly 2 to 3 phases. Balance theory with practical implementation."

    prompt = f"""
    Create a highly structured, dynamic learning curriculum for a {level}-level student learning '{skill}'.

    CRITICAL INSTRUCTIONS:
    - {phase_instructions}
    - Tailor the difficulty strictly to a '{level}' learner.
    - YOU MUST USE STRICT, FLAWLESS ENGLISH TERMINOLOGY. ABSOLUTELY NO GIBBERISH OR TYPOS (e.g., no made up words like 'inkilligance').
    - Output ONLY perfectly valid JSON that strictly adheres to the provided JSON Schema below. 
    - Do not include markdown formatting or any chat text outside the JSON.

    REQUIRED JSON SCHEMA:
    {STRICT_SCHEMA}
    """

    print(f"Sending dynamic prompt to AI for {skill} ({duration} | {level})...")
    ai_response = generate_curriculum(prompt)

    if isinstance(ai_response, dict) and "error" in ai_response:
        return jsonify(ai_response), 500

    structured = parse_curriculum(ai_response)

    if not structured or "curriculum" not in structured:
        return jsonify({"error": "Invalid AI response. The model did not return valid JSON."}), 500

    save_history(skill, duration, structured["curriculum"])

    return jsonify(structured)


@app.route("/history", methods=["GET"])
def history():
    records = SearchHistory.query.order_by(SearchHistory.id.desc()).all()

    history_list = []
    for r in records:
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
    # Dynamically bind port for cloud server environments (like Render)
    port = int(os.environ.get("PORT", 5050))
    print(f"Server running on port {port}")
    app.run(host="0.0.0.0", port=port)
