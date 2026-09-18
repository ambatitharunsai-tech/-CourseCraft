import re

with open('templates/index.html', 'r') as f:
    html = f.read()

# Add Dark Mode Toggle to header
header_btn_regex = r'(<button class="menu-btn" onclick="openProfile\(\)">Profile</button>)'
toggle_html = r'<button class="menu-btn" onclick="toggleTheme()" id="themeToggleBtn">🌙 Dark Mode</button>\n            \1'
html = re.sub(header_btn_regex, toggle_html, html)

# Add "Share" button to history popup
history_item_regex = r'(<button class="delete-btn".*?🗑</button>)'
share_btn = r'<button class="share-btn" style="background: transparent; border: none; color: var(--aurora-1); font-size: 1.2rem; cursor: pointer; margin-right: 10px;" title="Copy Share Link">🔗</button>\n                \1'

with open('templates/index.html', 'w') as f:
    f.write(html)
