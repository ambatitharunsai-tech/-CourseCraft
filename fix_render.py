import re

with open('static/script.js', 'r') as f:
    js = f.read()

# Extract everything up to the function render(data, skill) {
render_start = js.find('function render(data, skill) {')
if render_start != -1:
    js_pre = js[:render_start]
    
    # We will replace the entire render function.
    new_render = """function render(data, skill) {
        if (!data || !data.curriculum) { resultBox.innerHTML = "<p>Error displaying data.</p>"; return; }

        let curr = data.curriculum;
        if (typeof curr === 'string') { try { curr = JSON.parse(curr); } catch (e) { } }
        if (curr && curr.curriculum) curr = curr.curriculum;

        let html = `<div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 2px solid var(--aurora-1); padding-bottom: 10px; margin-bottom: 20px;">
            <h2 style="margin:0;">${skill} Path</h2>
            <div style="display: flex; gap: 10px;">
                <button id="pdfBtn" style="padding:8px 15px; border-radius:8px; cursor:pointer; background: linear-gradient(to right, var(--aurora-1), var(--aurora-2)); color: white; border: none; font-weight: bold; font-size: 0.9rem;">
                    📄 PDF
                </button>
                <button id="mdBtn" style="padding:8px 15px; border-radius:8px; cursor:pointer; background: transparent; border: 2px solid var(--aurora-1); color: var(--aurora-1); font-weight: bold; font-size: 0.9rem;">
                    ⬇️ Markdown
                </button>
            </div>
        </div><div id="pdfContent">`;

        curr.forEach(phase => {
            let phaseTitle = phase.phase_title || phase.title || phase.name || "Phase";
            html += `<div style="margin-top: 20px; font-weight: bold; padding: 10px; background: var(--input-bg); border-left: 4px solid var(--aurora-1); border-radius: 4px;">${phaseTitle}</div>`;
            if (phase.phase_objective) html += `<div style="font-style: italic; opacity: 0.85; margin-bottom: 15px; padding-left: 10px; font-size: 0.95rem;">🎯 <strong>Objective:</strong> ${phase.phase_objective}</div>`;

            let courses = phase.courses || phase.modules || phase.topics;
            if (Array.isArray(courses)) {
                courses.forEach(c => {
                    let cTitle = c.course_title || c.title || c.name || "Topic";
                    html += `<div style="margin-left: 10px;"><h4 style="margin-bottom: 5px; margin-top: 15px;">${cTitle}</h4>`;
                    if (c.practical_project) html += `<div style="background: var(--input-bg); border-left: 3px solid var(--aurora-2); padding: 8px 10px; margin: 5px 0 10px 0; border-radius: 4px; font-size: 0.9rem;">🛠️ <strong>Project:</strong> ${c.practical_project}</div>`;
                    
                    let tops = Array.isArray(c.topics) ? c.topics : [c.topics || "General"];
                    tops.forEach(t => {
                        html += `<div style="display: flex; align-items: flex-start; margin-bottom: 6px; gap: 8px;"><input type="checkbox" class="topic-checkbox" data-skill="${skill}" data-topic="${t.replace(/"/g, '&quot;')}" style="margin-top: 4px; cursor: pointer; width: 16px; height: 16px; accent-color: var(--aurora-1);"> <span style="line-height: 1.4;">${t}</span></div>`;
                    });
                    html += `</div>`;
                });
            }
        });

        html += `</div>`;
        resultBox.innerHTML = html;

        // PDF Binder
        document.getElementById("pdfBtn").onclick = (e) => {
            e.preventDefault();
            const btn = document.getElementById("pdfBtn");
            const element = document.getElementById("pdfContent");
            const opt = {
                margin: 0.5, filename: `${skill.replace(/\\s+/g, '_')}_Curriculum.pdf`,
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2, useCORS: true },
                jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
            };
            btn.textContent = "⏳..."; btn.disabled = true;
            html2pdf().set(opt).from(element).save().then(() => {
                btn.textContent = "✅"; setTimeout(() => { btn.textContent = "📄 PDF"; btn.disabled = false }, 2000);
            });
        };

        // Markdown Binder
        document.getElementById("mdBtn").onclick = () => {
            let md = `# ${skill} Learning Curriculum\\n\\n`;
            curr.forEach(phase => {
                md += `## ${phase.phase_title || phase.title || phase.name || "Phase"}\\n`;
                if (phase.phase_objective) md += `*Objective: ${phase.phase_objective}*\\n\\n`;
                let courses = phase.courses || phase.modules || phase.topics;
                if (Array.isArray(courses)) {
                    courses.forEach(c => {
                        md += `### ${c.course_title || c.title || c.name || "Topic"}\\n`;
                        if (c.practical_project) md += `**Project:** ${c.practical_project}\\n\\n`;
                        let tops = Array.isArray(c.topics) ? c.topics : [c.topics || "General"];
                        tops.forEach(t => md += `- [ ] ${t}\\n`);
                        md += `\\n`;
                    });
                }
            });
            const blob = new Blob([md], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url;
            a.download = `${skill.replace(/\\s+/g, '_')}_Curriculum.md`;
            a.click(); URL.revokeObjectURL(url);
        };

        // Checkbox Binder
        const progressKey = 'courseCraft_progress_' + skill;
        const saved = JSON.parse(localStorage.getItem(progressKey) || '{}');
        document.querySelectorAll('.topic-checkbox').forEach(cb => {
            if (saved[cb.dataset.topic]) {
                cb.checked = true;
                cb.nextElementSibling.style.textDecoration = 'line-through';
                cb.nextElementSibling.style.opacity = '0.6';
            }
            cb.addEventListener('change', (e) => {
                const isChecked = e.target.checked;
                saved[cb.dataset.topic] = isChecked;
                localStorage.setItem(progressKey, JSON.stringify(saved));
                if (isChecked) {
                    cb.nextElementSibling.style.textDecoration = 'line-through';
                    cb.nextElementSibling.style.opacity = '0.6';
                } else {
                    cb.nextElementSibling.style.textDecoration = 'none';
                    cb.nextElementSibling.style.opacity = '1';
                }
            });
        });
    }
});
"""
    
    # We need to append the theme toggle function again in case it was stripped
    theme_js = """
    window.toggleTheme = () => {
        const isDark = document.body.classList.toggle("dark");
        localStorage.setItem("theme", isDark ? "dark" : "light");
        const btn = document.getElementById("themeToggleBtn");
        if (btn) btn.innerHTML = isDark ? "☀️ Light Mode" : "🌙 Dark Mode";
    };
"""
    
    final_js = js_pre + new_render + theme_js
    with open('static/script.js', 'w') as f:
        f.write(final_js)
