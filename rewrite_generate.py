import re

with open('app.py', 'r') as f:
    content = f.read()

def replace_between(start_str, end_str, new_str, text):
    start = text.find(start_str)
    if start == -1: return text
    end = text.find(end_str, start)
    if end == -1: end = start + len(start_str) # fall back to just replacing start_str if end not found
    else: end += len(end_str)
    return text[:start] + new_str + text[end:]

# Replace save_history and parse_curriculum
old_helpers_start = "def save_history(user_id, skill, duration, curriculum):"
old_helpers_end = "        return None" # end of parse_curriculum

new_helpers = """def save_history(user_id, skill, duration, curriculum):
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
        return None"""

content = replace_between(old_helpers_start, old_helpers_end, new_helpers, content)


# Replace generate_curriculum
old_gen_curr_start = "def generate_curriculum(prompt):"
old_gen_curr_end = "        return {\"error\": \"LLM request failed or timed out\"}"

new_gen_curr = """def generate_curriculum(prompt):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"error_type": "internal", "error": "Missing GROQ_API_KEY"}
    api_key = api_key.strip()

    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
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
        print(f"LLM request error: {e}")
        return {"error_type": "upstream", "error": "LLM request failed"}
    except Exception as e:
        print(f"Unexpected LLM error: {e}")
        return {"error_type": "internal", "error": "Internal unexpected error"}"""

content = replace_between(old_gen_curr_start, old_gen_curr_end, new_gen_curr, content)

# Replace generate route
old_gen_route_start = "@app.route(\"/generate\", methods=[\"POST\"])"
old_gen_route_end = "    return jsonify(structured)"

new_gen_route = """@app.route("/generate", methods=["POST"])
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

    prompt = f"Create a structured learning curriculum for {skill}.\\nRules:\\n- Provide clear phases\\n- Each phase includes courses with topics\\n- Return ONLY valid JSON\\nFormat:\\n{{\\"curriculum\\":[{{\\"phase_title\\":\\"Phase 1\\",\\"courses\\":[{{\\"course_title\\":\\"Course\\",\\"topics\\":[\\"topic1\\"]}}]}}]}}"
    
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

    return jsonify(structured)"""

content = replace_between(old_gen_route_start, old_gen_route_end, new_gen_route, content)

with open('app.py', 'w') as f:
    f.write(content)

