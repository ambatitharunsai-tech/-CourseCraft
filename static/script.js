document.addEventListener("DOMContentLoaded", () => {

    // Core Elements
    const form = document.getElementById("curriculumForm");
    const resultBox = document.getElementById("result");
    const loader = document.getElementById("loader");
    const toggleBtn = document.getElementById("themeToggle");
    const header = document.querySelector(".header-area");
    
    // History & User elements
    const historyPopup = document.getElementById("historyPopup");
    const historyList = document.getElementById("historyList");
    const loginModal = document.getElementById("loginModal");
    const profilePopup = document.getElementById("profilePopup");
    const profileContent = document.getElementById("profileContent");
    const openHistoryBtn = document.getElementById("openHistoryBtn");

    let historyData = [];
    let sortMode = "newest";
    let currentUserState = { logged_in: false, guest_left: 3 };

    /* =========================
       INITIALIZE GOOGLE AUTH
    ========================= */
    window.onload = function() {
        if (typeof google !== 'undefined') {
            google.accounts.id.initialize({
                client_id: "1052463353443-ovsiemfnpl7hka2ejk62co1915ilgq7e.apps.googleusercontent.com", // REPLACE WITH REAL CLIENT ID
                callback: handleCredentialResponse
            });
            // Render inside login limit modal
            google.accounts.id.renderButton(
                document.getElementById("googleSignInModalTarget"),
                { theme: "outline", size: "large" }
            );
            // Render inside profile popup
            google.accounts.id.renderButton(
                document.getElementById("googleSignInProfileTarget"),
                { theme: "outline", size: "large" }
            );
        }
        checkAuthStatus(); // Load initial profile state
    };

    async function handleCredentialResponse(response) {
        try {
            const res = await fetch('/auth/google', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: response.credential })
            });
            const data = await res.json();
            if(data.success) {
                loginModal.style.display = 'none';
                alert(`Welcome, ${data.name}! Your progress will now be saved.`);
                checkAuthStatus();
            } else {
                alert("Login Error: " + data.error);
            }
        } catch (err) {
            console.error(err);
        }
    }

    // Bypass for users testing without real Google Client Credentials
    window.devBypassLogin = async function() {
        try {
            const res = await fetch('/auth/google', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dev_bypass: true })
            });
            const data = await res.json();
            if(data.success) {
                loginModal.style.display = 'none';
                alert(`Test Login Success! Welcome, ${data.name}!`);
                checkAuthStatus();
            }
        } catch(err) { console.error(err); }
    };

    /* =========================
       CHECK USER QUOTA & STATUS
    ========================= */
    async function checkAuthStatus() {
        try {
            const res = await fetch('/api/user');
            currentUserState = await res.json();
            updateProfileUI();
        } catch (e) {
            console.error("Failed to fetch user state", e);
        }
    }

    function updateProfileUI() {
        const targetGoogleBtn = document.getElementById("googleSignInProfileTarget");
        
        if (currentUserState.logged_in) {
            profileContent.innerHTML = `
                <h2 style="margin: 0 0 5px 0; font-size: 1.8rem;">${currentUserState.name}</h2>
                <p style="margin: 0 0 25px 0; color: #64748b;">${currentUserState.email || 'Verified Student'}</p>
                <div style="background: var(--input-bg); padding: 20px; border-radius: 20px; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: var(--aurora-2); font-size: 1.6rem;">${currentUserState.searches}</h3>
                    <p style="margin: 0; font-size: 0.9rem; color: #64748b; font-weight: 600;">Total Curriculums Built</p>
                </div>
                <button onclick="logout()" style="padding: 12px 25px; border-radius: 50px; cursor: pointer; background: transparent; color: #ff4d4d; border: 2px solid #ff4d4d; font-weight: bold; width: 100%;">Logout</button>
            `;
            targetGoogleBtn.style.display = "none";
        } else {
            profileContent.innerHTML = `
                <h2 style="margin: 0 0 5px 0; font-size: 1.8rem;">Guest Explorer</h2>
                <p style="margin: 0 0 25px 0; color: #64748b;">Log in to unlock unlimited history tracking</p>
                <div style="background: var(--input-bg); padding: 20px; border-radius: 20px; margin-bottom: 10px;">
                    <h3 style="margin: 0; color: var(--aurora-1); font-size: 1.6rem;">${currentUserState.guest_left} / 3</h3>
                    <p style="margin: 0; font-size: 0.9rem; color: #64748b; font-weight: 600;">Free Searches Left</p>
                </div>
            `;
            targetGoogleBtn.style.display = "flex";
        }
    }

    window.logout = async function() {
        await fetch('/auth/logout', { method: 'POST' });
        profilePopup.style.display = "none";
        alert("You have been logged out.");
        checkAuthStatus();
        resultBox.innerHTML = ""; // Clear screen
    }

    /* =========================
       THEME & SPELLING
    ========================= */
    const setDarkMode = (dark) => {
        document.body.classList.toggle("dark", dark);
        toggleBtn.textContent = dark ? "☀ Light Mode" : "🌙 Dark Mode";
        localStorage.setItem("theme", dark ? "dark" : "light");
    };
    const savedTheme = localStorage.getItem("theme");
    const isDark = savedTheme === "dark" || (savedTheme === null && window.matchMedia('(prefers-color-scheme: dark)').matches);
    setDarkMode(isDark);
    toggleBtn.onclick = () => setDarkMode(!document.body.classList.contains("dark"));

    /* =========================
       FORM SUBMISSION
    ========================= */
    if (form) {
        form.addEventListener("submit", async e => {
            e.preventDefault();
            const submitBtn = form.querySelector('button[type="submit"]');

            let skill = document.getElementById("stream").value.trim();
            const duration = document.getElementById("duration").value;
            const level = document.getElementById("level").value;

            if (!skill) return;

            submitBtn.disabled = true;
            loader.style.display = "block";
            resultBox.innerHTML = "";

            try {
                const resp = await fetch("/generate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ skill, duration, level })
                });
                
                let data;
                try {
                    data = await resp.json();
                } catch (jsonErr) {
                    throw new Error(`Server crashed and returned HTML (Status ${resp.status}). Check your python terminal.`);
                }

                loader.style.display = "none";
                submitBtn.disabled = false;

                // Handle limit reached scenario
                if (resp.status === 403 && data && data.error === "limit_reached") {
                    loginModal.style.display = "flex";
                    return; 
                }

                if (!resp.ok) {
                    resultBox.innerHTML = "<p style='color:#ff4d4d; text-align:center;'>Error: " + (data.error || "Server error") + "</p>";
                    return;
                }

                header.style.display = "none";
                render(data, skill);
                checkAuthStatus(); // Update count
            } catch (err) {
                console.error("Fetch Error:", err);
                loader.style.display = "none";
                submitBtn.disabled = false;
                resultBox.innerHTML = `<p style='color:#ff4d4d; text-align:center;'>Connection Error: ${err.message}</p>`;
            }
        });
    }

    /* =========================
       HISTORY LOGIC
    ========================= */
    openHistoryBtn.onclick = (e) => {
        e.preventDefault();
        document.getElementById('myDropdown').classList.remove('show');
        historyPopup.style.display = "flex";
        
        if (!currentUserState.logged_in) {
            document.getElementById("historyAuthWarning").style.display = "block";
            document.getElementById("historyContentBlock").style.display = "none";
        } else {
            document.getElementById("historyAuthWarning").style.display = "none";
            document.getElementById("historyContentBlock").style.display = "block";
            loadHistory();
        }
    };

    document.getElementById("closeHistory").onclick = () => { historyPopup.style.display = "none"; };

    async function loadHistory() {
        try {
            const resp = await fetch("/history");
            if (resp.status === 401) return; // Unauthorized handled by UI
            historyData = await resp.json();
            renderHistory();
        } catch {
            historyList.innerHTML = "<p>Unable to load history</p>";
        }
    }

    function renderHistory() {
        historyList.innerHTML = "";
        if (!historyData.length) {
            historyList.innerHTML = "<p style='text-align:center; padding: 20px;'>No curriculums generated yet.</p>";
            return;
        }

        let data = [...historyData];
        const parseDate = (dateStr) => new Date(dateStr.replace(" ", "T"));
        data.sort((a, b) => sortMode === "newest" ? parseDate(b.timestamp) - parseDate(a.timestamp) : parseDate(a.timestamp) - parseDate(b.timestamp));

        data.forEach(item => {
            const div = document.createElement("div");
            div.style.cssText = "display: flex; justify-content: space-between; align-items: center; padding: 15px; background: rgba(100,116,139,0.05); border-radius: 12px; border: 1px solid rgba(100,116,139,0.1);";
            div.className = "history-item";

            div.innerHTML = `
                <div class="item-info" style="cursor: pointer; flex-grow: 1;">
                    <strong style="color: var(--aurora-2)">${item.skill}</strong><br>
                    <small style="opacity: 0.7">${item.duration} • ${item.timestamp}</small>
                </div>
                <button class="delete-btn" style="background: transparent; border: none; color: #ff4d4d; font-size: 1.2rem; cursor: pointer;">🗑</button>
            `;

            div.querySelector('.item-info').onclick = () => {
                header.style.display = "none";
                render({ curriculum: item.curriculum }, item.skill);
                historyPopup.style.display = "none";
            };

            div.querySelector('.delete-btn').onclick = async (e) => {
                e.stopPropagation();
                if (confirm(`Delete '${item.skill}' from history?`)) {
                    await fetch(`/delete-history/${item.id}`, { method: "POST" });
                    loadHistory();
                }
            };

            historyList.appendChild(div);
        });
    }

    if (document.getElementById("clearHistory")) {
        document.getElementById("clearHistory").onclick = async () => {
            if (!historyData.length) return;
            if (confirm("Clear all your saved curriculums?")) {
                await fetch("/clear-history", { method: "POST" });
                loadHistory();
            }
        };
    }

    // PDF/Render logic from original
    function render(data, skill) {
        if (!data || !data.curriculum) { resultBox.innerHTML = "<p>Error displaying data.</p>"; return; }

        let curr = data.curriculum;
        if (typeof curr === 'string') { try { curr = JSON.parse(curr); } catch (e) {} }
        if (curr && curr.curriculum) curr = curr.curriculum; 

        let html = `<div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 2px solid #667eea; padding-bottom: 10px; margin-bottom: 20px;">
            <h2 style="margin:0;">${skill} Path</h2>
            <button id="pdfBtn" style="padding:8px 15px; border-radius:8px; cursor:pointer; background: linear-gradient(to right, #667eea, #764ba2); color: white; border: none; font-weight: bold; font-size: 0.9rem;">
                📄 Download PDF
            </button></div><div id="pdfContent">`;

        curr.forEach(phase => {
            let phaseTitle = phase.phase_title || phase.title || phase.name || "Phase";
            html += `<div style="margin-top: 20px; font-weight: bold; padding: 10px; background: rgba(102, 126, 234, 0.1); border-left: 4px solid #667eea; border-radius: 4px;">${phaseTitle}</div>`;
            if (phase.phase_objective) html += `<div style="font-style: italic; opacity: 0.85; margin-bottom: 15px; padding-left: 10px; font-size: 0.95rem;">🎯 <strong>Objective:</strong> ${phase.phase_objective}</div>`;

            let courses = phase.courses || phase.modules || phase.topics;
            if (Array.isArray(courses)) {
                courses.forEach(c => {
                    let cTitle = c.course_title || c.title || c.name || "Topic";
                    html += `<div style="margin-left: 10px;"><h4 style="margin-bottom: 5px; margin-top: 15px;">${cTitle}</h4>`;
                    if (c.practical_project) html += `<div style="background: rgba(102, 126, 234, 0.1); border-left: 3px solid #764ba2; padding: 8px 10px; margin: 5px 0 10px 0; border-radius: 4px; font-size: 0.9rem;">🛠️ <strong>Project:</strong> ${c.practical_project}</div>`;
                    html += `<ul style="margin-top: 0;">`;
                    let tops = Array.isArray(c.topics) ? c.topics : [c.topics || "General"];
                    tops.forEach(t => html += `<li style="margin-bottom: 4px;">${t}</li>`);
                    html += `</ul></div>`;
                });
            }
        });

        html += `</div>`;
        resultBox.innerHTML = html;

        // Simplified PDF binder hook
        document.getElementById("pdfBtn").onclick = (e) => {
            e.preventDefault();
            const btn = document.getElementById("pdfBtn");
            const element = document.getElementById("pdfContent");
            const opt = {
                margin: 0.5, filename: `${skill.replace(/\s+/g, '_')}_Curriculum.pdf`,
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2, useCORS: true },
                jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
            };
            btn.textContent = "⏳ Generating..."; btn.disabled = true;
            html2pdf().set(opt).from(element).save().then(()=> {
                btn.textContent = "Downloaded"; setTimeout(()=>{btn.textContent="📄 Download PDF"; btn.disabled=false}, 2000);
            });
        };
    }
});


