from flask import Flask, request, jsonify, send_file, render_template
import requests
import json
import re
import os
from jsonschema import validate, ValidationError
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# --- SETUP & HELPERS ---

# Load JSON schema
try:
    with open("schema.json") as f:
        schema = json.load(f)
except FileNotFoundError:
    print("Warning: schema.json not found. Ensure it is in the same directory.")
    schema = {}

app = Flask(__name__)

def get_semester_details(duration_input):
    """Maps user timeframes to semester counts."""
    duration_input = str(duration_input).lower().strip()
    
    # 3 Months -> Half Semester
    if duration_input in ["3 months", "3 month", "3", "0.5", "half"]:
        return True, "0.5"
        
    # 6 Months -> 1 Semester
    elif duration_input in ["6 months", "6 month", "6"]:
        return False, "1"
        
    # 1 Year -> 2 Semesters
    elif duration_input in ["1 year", "1 yr", "1", "12 months", "12", "2 semesters"]:
        return False, "2"
        
    # Default fallback
    else:
        return False, "2"

def curriculum_to_json(text):
    """Parses LLM text output into structured JSON."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    curriculum = {}
    current_semester = None
    current_course = None
    used_courses = set()

    for line in lines:
        line = line.replace("**", "")

        if "Semester" in line:
            current_semester = line.replace(":", "").strip()
            curriculum[current_semester] = []
            continue

        clean_line = re.sub(r"^[•*+\-\s]+", "", line)

        if clean_line.lower().startswith("key topics"):
            topics_text = clean_line.split(":", 1)[1]
            topics = re.split(r",|\)|\(", topics_text)
            topics = [t.strip() for t in topics if t.strip()]

            if current_course:
                current_course["topics"] = topics
            continue

        if clean_line.lower().startswith(("note", "here is", "this is")):
            continue

        if current_semester:
            course_name = clean_line.rstrip(".")

            if course_name.lower() in used_courses:
                continue

            used_courses.add(course_name.lower())

            current_course = {
                "course_title": course_name,
                "topics": []
            }
            curriculum[current_semester].append(current_course)

    return curriculum

def generate_curriculum(prompt):
    """Connects to the local Ollama LLM."""
    url = "http://localhost:11434/api/generate"
    data = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        result = response.json()

        if "response" in result:
            return result["response"]
        elif "message" in result:
            return result["message"]["content"]
        else:
            return str(result)
    except requests.exceptions.RequestException as e:
        print(f"Ollama Connection Error: {e}")
        return ""

# --- PDF GENERATION LOGIC ---

def draw_border(canvas, doc):
    """Draws a double border on PDF pages."""
    width, height = doc.pagesize
    margin = 15

    canvas.setLineWidth(2)
    canvas.rect(margin, margin, width - 2*margin, height - 2*margin)

    canvas.setLineWidth(1)
    canvas.rect(margin+6, margin+6, width - 2*(margin+6), height - 2*(margin+6))

def create_pdf(curriculum, filename="curriculum.pdf"):
    """Builds the PDF document using ReportLab."""
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    elements = []

    for semester, courses in curriculum.items():
        elements.append(Paragraph(semester, styles["Heading1"]))
        elements.append(Spacer(1, 12))

        for course in courses:
            elements.append(Paragraph(course["course_title"], styles["Heading2"]))
            topics = ", ".join(course.get("topics", []))
            elements.append(Paragraph(f"Key topics: {topics}", styles["Normal"]))
            elements.append(Spacer(1, 12))

    doc.build(elements, onFirstPage=draw_border, onLaterPages=draw_border)
    return filename

# --- FLASK ROUTES ---

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    if not data or "skill" not in data:
        return jsonify({"error": "Please provide a skill"}), 400
        
    skill = data["skill"]
    duration_input = data.get("duration", "1 year")
    
    half_semester, semesters = get_semester_details(duration_input)

    if half_semester:
        prompt = f"""
        Create a HALF semester curriculum for {skill}.
        Rules:
        - Include ONLY 2 to 3 courses.
        - Focus on fundamentals.
        - Each course must include key topics.

        Format EXACTLY like this:
        Semester 1:
        Course Name
        Key topics: topic1, topic2
        """
    else:
        prompt = f"""
        Create a {semesters} semester curriculum for {skill}.
        Rules:
        - Provide exactly {semesters} semester(s).
        - Each semester must include 3 to 5 courses.
        - Each course must include key topics.

        Format EXACTLY like this:
        Semester 1:
        Course Name
        Key topics: topic1, topic2
        """

    raw_text = generate_curriculum(prompt)
    if not raw_text:
        return jsonify({"error": "Failed to connect to local LLM"}), 500
        
    structured_data = curriculum_to_json(raw_text)

    if structured_data and schema:
        try:
            validate(instance=structured_data, schema=schema)
        except ValidationError as e:
            return jsonify({
                "error": "LLM output failed schema validation", 
                "details": e.message
            }), 500
    elif not structured_data:
        return jsonify({"error": "Failed to parse curriculum into JSON"}), 500

    return jsonify(structured_data)

@app.route("/view", methods=["POST"])
def view():
    try:
        curriculum = json.loads(request.form["curriculum"])
        skill = request.form["skill"]

        return render_template(
            "result.html",
            data=curriculum,
            skill=skill
        )
    except (KeyError, json.JSONDecodeError) as e:
        return f"Error processing request: {str(e)}", 400

@app.route("/download-pdf", methods=["POST"])
def download_pdf():
    data = request.get_json()

    if not data or "skill" not in data:
        return jsonify({"error": "Please provide a skill"}), 400

    skill = data["skill"]
    duration_input = data.get("duration", "1 year")
    
    half_semester, semesters = get_semester_details(duration_input)

    if half_semester:
        prompt = f"""
        Create a HALF semester curriculum for {skill}.
        Rules:
        - Include ONLY 2 to 3 courses.
        - Focus on fundamentals.
        - Each course must include key topics.

        Format EXACTLY like this:
        Semester 1:
        Course Name
        Key topics: topic1, topic2
        """
    else:
        prompt = f"""
        Create a {semesters} semester curriculum for {skill}.
        Rules:
        - Provide exactly {semesters} semester(s).
        - Each semester must include 3 to 5 courses.
        - Each course must include key topics.

        Format EXACTLY like this:
        Semester 1:
        Course Name
        Key topics: topic1, topic2
        """

    raw_text = generate_curriculum(prompt)
    if not raw_text:
        return jsonify({"error": "Failed to connect to local LLM"}), 500
        
    structured_data = curriculum_to_json(raw_text)
    
    if not structured_data:
        return jsonify({"error": "Failed to parse curriculum into JSON"}), 500

    filename = f"{skill.replace(' ', '_')}_curriculum.pdf"
    pdf_path = create_pdf(structured_data, filename=filename)

    return send_file(pdf_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)