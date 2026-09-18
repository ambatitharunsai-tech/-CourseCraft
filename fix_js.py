import re

with open('static/script.js', 'r') as f:
    js = f.read()

# 1. Update generateCurriculum() to send level
old_gen = r'const skill = document.getElementById\("skillInput"\).value.trim\(\);\n\s+if \(!skill\) \{ alert\("Please enter a skill!"\); return; \}'
new_gen = """const skill = document.getElementById("skillInput").value.trim();
        const level = document.getElementById("levelInput") ? document.getElementById("levelInput").value : "Beginner";
        if (!skill) { alert("Please enter a skill!"); return; }"""
js = re.sub(old_gen, new_gen, js)

old_fetch = r'body: JSON.stringify\(\{ skill \}\)'
new_fetch = r'body: JSON.stringify({ skill, level })'
js = re.sub(old_fetch, new_fetch, js)

# 2. Add YouTube/Google icons in render()
old_checkbox = r'(<div style="display: flex; align-items: flex-start; margin-bottom: 6px; gap: 8px;"><input type="checkbox"[^>]+> <span style="line-height: 1\.4;">\$\{t\}</span>)(</div>)'
new_checkbox = r"""\1 <div style="margin-left: auto; display: flex; gap: 6px;">
                            <a href="https://www.youtube.com/results?search_query=${encodeURIComponent(skill + ' ' + t)}" target="_blank" title="Search YouTube" style="text-decoration:none; filter:grayscale(1); opacity:0.6; transition:0.2s;" onmouseover="this.style.filter='none';this.style.opacity='1'" onmouseout="this.style.filter='grayscale(1)';this.style.opacity='0.6'">🎥</a>
                            <a href="https://www.google.com/search?q=${encodeURIComponent(skill + ' ' + t)}" target="_blank" title="Search Google" style="text-decoration:none; filter:grayscale(1); opacity:0.6; transition:0.2s;" onmouseover="this.style.filter='none';this.style.opacity='1'" onmouseout="this.style.filter='grayscale(1)';this.style.opacity='0.6'">🔍</a>
                        </div>\2"""
js = re.sub(old_checkbox, new_checkbox, js)

with open('static/script.js', 'w') as f:
    f.write(js)
