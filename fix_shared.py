import re

with open('templates/shared.html', 'r') as f:
    html = f.read()

old_checkbox = r'(<div style="display: flex; align-items: flex-start; margin-bottom: 6px; gap: 8px;"><input type="checkbox"[^>]+> <span style="line-height: 1\.4;">\$\{t\}</span>)(</div>)'
new_checkbox = r"""\1 <div style="margin-left: auto; display: flex; gap: 6px;">
                            <a href="https://www.youtube.com/results?search_query=${encodeURIComponent(skill + ' ' + t)}" target="_blank" title="Search YouTube" style="text-decoration:none; filter:grayscale(1); opacity:0.6; transition:0.2s;" onmouseover="this.style.filter='none';this.style.opacity='1'" onmouseout="this.style.filter='grayscale(1)';this.style.opacity='0.6'">🎥</a>
                            <a href="https://www.google.com/search?q=${encodeURIComponent(skill + ' ' + t)}" target="_blank" title="Search Google" style="text-decoration:none; filter:grayscale(1); opacity:0.6; transition:0.2s;" onmouseover="this.style.filter='none';this.style.opacity='1'" onmouseout="this.style.filter='grayscale(1)';this.style.opacity='0.6'">🔍</a>
                        </div>\2"""
html = re.sub(old_checkbox, new_checkbox, html)

with open('templates/shared.html', 'w') as f:
    f.write(html)
