import re

with open('templates/index.html', 'r') as f:
    html = f.read()

old_hist = r'<h2>Your History</h2>'
new_hist = r'<h2>Your History</h2>\n            <input type="text" id="historySearch" placeholder="Search history..." onkeyup="filterHistory()" style="width:100%; padding: 10px; margin-bottom: 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.1); color: inherit; outline: none; font-size: 0.95rem;">'
html = html.replace(old_hist, new_hist)

with open('templates/index.html', 'w') as f:
    f.write(html)

with open('static/script.js', 'r') as f:
    js = f.read()

hist_search_func = """
    window.filterHistory = () => {
        const query = document.getElementById("historySearch").value.toLowerCase();
        const items = document.querySelectorAll(".history-item");
        items.forEach(item => {
            const text = item.querySelector("strong").textContent.toLowerCase();
            item.style.display = text.includes(query) ? "flex" : "none";
        });
    };
"""
js += hist_search_func

with open('static/script.js', 'w') as f:
    f.write(js)
