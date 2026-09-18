import re

with open('static/script.js', 'r') as f:
    js = f.read()

# 1. Update Theme Toggle logic
theme_toggle_func = """
    window.toggleTheme = () => {
        const isDark = document.body.classList.toggle("dark");
        localStorage.setItem("theme", isDark ? "dark" : "light");
        const btn = document.getElementById("themeToggleBtn");
        if (btn) btn.innerHTML = isDark ? "☀️ Light Mode" : "🌙 Dark Mode";
    };
"""
if "window.toggleTheme =" not in js:
    js += "\n" + theme_toggle_func

# 2. Add checkbox logic in render()
# Replace li with checkbox
li_regex = r'(tops\.forEach\(t => html \+= `)(<li style="margin-bottom: 4px;">)(\$\{t\}</li>`;\))'
new_li = r"""\1<div style="display: flex; align-items: flex-start; margin-bottom: 6px; gap: 8px;"><input type="checkbox" class="topic-checkbox" data-skill="${skill}" data-topic="${t.replace(/"/g, '&quot;')}" style="margin-top: 4px; cursor: pointer; width: 16px; height: 16px; accent-color: var(--aurora-1);"> <span style="line-height: 1.4;">${t}</span></div>`;)"""
js = re.sub(li_regex, new_li, js)

# 3. Add Markdown export and Checkbox binding at the end of render()
end_render_regex = r'(resultBox\.innerHTML = html;\n\s+bindPDF\(skill\);\n\s+\})'
new_end_render = r"""resultBox.innerHTML = html;
        bindPDF(skill);
        bindMarkdown(data, skill);
        bindCheckboxes(skill);
    }
    
    function bindCheckboxes(skill) {
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

    function bindMarkdown(data, skill) {
        const btn = document.getElementById("mdBtn");
        if (!btn) return;
        
        btn.onclick = () => {
            let md = `# ${skill} Learning Curriculum\\n\\n`;
            let curr = data.curriculum || data;
            
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
            const a = document.createElement('a');
            a.href = url;
            a.download = `${skill.replace(/\\s+/g, '_')}_Curriculum.md`;
            a.click();
            URL.revokeObjectURL(url);
        };
    }
"""
js = re.sub(end_render_regex, new_end_render, js)

with open('static/script.js', 'w') as f:
    f.write(js)
