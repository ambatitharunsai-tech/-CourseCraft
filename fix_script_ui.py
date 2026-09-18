import re

with open('static/script.js', 'r') as f:
    js = f.read()

# Add Share button to history item
history_item_regex = r'(<button class="delete-btn".*?🗑</button>)'
share_btn = r'<button class="share-btn" style="background: transparent; border: none; color: var(--aurora-1); font-size: 1.2rem; cursor: pointer; margin-right: 10px;" title="Copy Share Link">🔗</button>\n                \1'
js = re.sub(history_item_regex, share_btn, js)

# Bind the Share button logic
bind_regex = r"(div\.querySelector\('\.delete-btn'\)\.onclick = async \(e\) => \{)"
bind_share = r"""div.querySelector('.share-btn').onclick = (e) => {
                e.stopPropagation();
                const shareUrl = window.location.origin + '/shared/' + item.id;
                navigator.clipboard.writeText(shareUrl).then(() => {
                    const btn = e.target;
                    btn.textContent = '✅';
                    setTimeout(() => btn.textContent = '🔗', 2000);
                });
            };
            \1"""
js = re.sub(bind_regex, bind_share, js)

# Add Download Markdown Button to render()
render_btn_regex = r'(<button id="pdfBtn".*?</button>)'
md_btn = r'\1\n            <button id="mdBtn" style="padding:8px 15px; border-radius:8px; cursor:pointer; background: transparent; border: 2px solid var(--aurora-1); color: var(--aurora-1); font-weight: bold; font-size: 0.9rem; margin-left: 10px;">\n                ⬇️ Markdown\n            </button>'
js = re.sub(render_btn_regex, md_btn, js)

with open('static/script.js', 'w') as f:
    f.write(js)
