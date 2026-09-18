import re

with open('templates/index.html', 'r') as f:
    html = f.read()

search_box = r'(<input type="text" id="skillInput" placeholder="What do you want to learn\? e.g., Python, UI Design, Marketing" style="flex-grow: 1; padding: 15px; border: none; border-radius: 8px; font-size: 1.1rem; outline: none; background: rgba\(255,255,255,0.1\); color: white;" onkeypress="if\(event.key === \'Enter\'\) generateCurriculum\(\)">)'

new_search = r"""<select id="levelInput" style="padding: 15px; border: none; border-radius: 8px; font-size: 1.1rem; outline: none; background: rgba(255,255,255,0.1); color: white; cursor: pointer; margin-right: 10px;">
                    <option value="Beginner" style="color: black;">Beginner</option>
                    <option value="Intermediate" style="color: black;">Intermediate</option>
                    <option value="Advanced" style="color: black;">Advanced</option>
                </select>
                \1"""

html = re.sub(search_box, new_search, html)
with open('templates/index.html', 'w') as f:
    f.write(html)
