import re

with open('app.py', 'r') as f:
    code = f.read()

# Update generate route to accept 'level'
route_old = """def generate():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized", "message": "Sign in to continue."}), 401

    data = request.json or {}
    skill = data.get("skill")"""

route_new = """def generate():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized", "message": "Sign in to continue."}), 401

    data = request.json or {}
    skill = data.get("skill")
    level = data.get("level", "Beginner")"""
code = code.replace(route_old, route_new)

# Update generate_curriculum signature and prompt
gen_old = """def generate_curriculum(skill, api_key, max_retries=2):
    model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")"""

gen_new = """def generate_curriculum(skill, level, api_key, max_retries=2):
    model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")"""
code = code.replace(gen_old, gen_new)

call_old = """ai_response = generate_curriculum(skill, api_key)"""
call_new = """ai_response = generate_curriculum(skill, level, api_key)"""
code = code.replace(call_old, call_new)

prompt_old = """prompt = f"Create a structured learning curriculum for {skill}.\\nRules:\\n- Provide clear phases\\n- Each phase includes courses with topics\\n- Return ONLY valid JSON\\nFormat:\\n{{\\"curriculum\\":[{{\\"phase_title\\":\\"Phase 1\\",\\"courses\\":[{{\\"course_title\\":\\"Course\\",\\"topics\\":[\\"topic1\\"]}}]}}]}}" """
prompt_new = """prompt = f"Create a structured learning curriculum for {skill}, tailored specifically for a {level} level learner.\\nRules:\\n- Provide clear phases\\n- Each phase includes courses with topics\\n- Return ONLY valid JSON\\nFormat:\\n{{\\"curriculum\\":[{{\\"phase_title\\":\\"Phase 1\\",\\"courses\\":[{{\\"course_title\\":\\"Course\\",\\"topics\\":[\\"topic1\\"]}}]}}]}}" """
code = code.replace(prompt_old, prompt_new)

with open('app.py', 'w') as f:
    f.write(code)

