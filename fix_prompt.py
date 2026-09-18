import re

with open('app.py', 'r') as f:
    code = f.read()

# Replace skill retrieval
route_old = """    data = request.json or {}
    skill = data.get("skill")
    level = data.get("level", "Beginner")"""

route_new = """    data = request.json or {}
    skill = data.get("skill")
    level = data.get("level", "Beginner")"""

if "level = data.get" not in code:
    code = code.replace("""    data = request.json or {}
    skill = data.get("skill")""", """    data = request.json or {}
    skill = data.get("skill")
    level = data.get("level", "Beginner")""")

# Replace prompt definition
prompt_old = r'prompt = f"Create a structured learning curriculum for \{skill\}\.\\nRules:\\n- Provide clear phases\\n- Each phase includes courses with topics\\n- Return ONLY valid JSON\\nFormat:\\n\{\\"curriculum\\":\[\{\\"phase_title\\":\\"Phase 1\\",\\"courses\\":\[\{\\"course_title\\":\\"Course\\",\\"topics\\":\[\\"topic1\\"\]\}\]\}\]\}\}"'
prompt_new = 'prompt = f"Create a structured learning curriculum for {skill}, tailored for a {level} level learner.\\nRules:\\n- Provide clear phases\\n- Each phase includes courses with topics\\n- Return ONLY valid JSON\\nFormat:\\n{{\\"curriculum\\":[{{\\"phase_title\\":\\"Phase 1\\",\\"courses\\":[{{\\"course_title\\":\\"Course\\",\\"topics\\":[\\"topic1\\"]}}]}}]}}"'
code = re.sub(prompt_old, prompt_new, code)

with open('app.py', 'w') as f:
    f.write(code)
