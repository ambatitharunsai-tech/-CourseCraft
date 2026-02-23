document.addEventListener("DOMContentLoaded", () => {

const form = document.getElementById("curriculumForm");
const resultBox = document.getElementById("result");
const loader = document.getElementById("loader");
const toggleBtn = document.getElementById("themeToggle");
const header = document.querySelector(".header-area");

const historyPopup = document.getElementById("historyPopup");
const historyList = document.getElementById("historyList");
const historySearch = document.getElementById("historySearch");

let historyData = [];
let sortMode = "newest";

/* =========================
   SPELL CHECKER
========================= */
let dictionary;

fetch("/static/dictionaries/en_US.aff")
  .then(res => {
      if (!res.ok) throw new Error("Dictionary affix file not found");
      return fetch("/static/dictionaries/en_US.dic");
  })
  .then(res => {
      if (!res.ok) throw new Error("Dictionary words file not found");
      dictionary = new Typo("en_US",
        "/static/dictionaries/en_US.aff",
        "/static/dictionaries/en_US.dic",
        { platform: "any" }
      );
  })
  .catch(err => console.warn("Spellchecker initialization failed, continuing without it:", err));

function checkSpelling(word){
  if(!dictionary || dictionary.check(word)) return word;
  const suggestions = dictionary.suggest(word);
  return suggestions.length ? suggestions[0] : word;
}

/* =========================
   DARK MODE
========================= */
const setDarkMode = (dark) => {
    document.body.classList.toggle("dark", dark);
    if(toggleBtn) toggleBtn.textContent = dark ? "☀ Light Mode" : "🌙 Dark Mode";
    localStorage.setItem("theme", dark ? "dark" : "light");
};

// Check for system preference if localStorage is empty
const savedTheme = localStorage.getItem("theme");
const systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
const isDark = savedTheme === "dark" || (savedTheme === null && systemPrefersDark);

setDarkMode(isDark);

if(toggleBtn) {
    toggleBtn.onclick = () => setDarkMode(!document.body.classList.contains("dark"));
}

/* =========================
   HISTORY POPUP
========================= */
document.querySelectorAll(".dropdown-content a").forEach(link=>{
    if(link.textContent.trim()==="History"){
        link.onclick=(e)=>{
            e.preventDefault();
            historyPopup.style.display="flex";
            loadHistory();
        }
    }
});

if(document.getElementById("closeHistory")) {
    document.getElementById("closeHistory").onclick=()=>{
        historyPopup.style.display="none";
    };
}

/* =========================
   LOAD HISTORY
========================= */
async function loadHistory(){
    try{
        const resp = await fetch("/history");
        historyData = await resp.json();
        renderHistory();
    }catch{
        historyList.innerHTML="<p>Unable to load history</p>";
    }
}

/* =========================
   RENDER HISTORY
========================= */
function renderHistory(){
    historyList.innerHTML="";

    if(!historyData.length){
        historyList.innerHTML="<p style='text-align:center;'>No history yet</p>";
        return;
    }

    let data = [...historyData];

    // Safely parse dates from backend (replaces space with 'T' for Safari compatibility)
    const parseDate = (dateStr) => new Date(dateStr.replace(" ", "T"));

    data.sort((a,b)=>{
        return sortMode === "newest"
            ? parseDate(b.timestamp) - parseDate(a.timestamp)
            : parseDate(a.timestamp) - parseDate(b.timestamp);
    });

    data.forEach(item=>{
        const div=document.createElement("div");
        div.className="history-item";
        div.style.display = "flex";
        div.style.justifyContent = "space-between";
        div.style.alignItems = "center";

        div.innerHTML=`
            <div class="item-info" style="cursor: pointer; flex-grow: 1;">
                ⭐ ${item.skill}
                <br>
                <small>${item.duration} • ${item.timestamp}</small>
            </div>
            <button class="delete-btn" style="background: transparent; border: none; color: #ff4d4d; font-size: 1.2rem; cursor: pointer; padding: 5px; margin-left: 10px;" title="Delete Entry">🗑</button>
        `;

        // Load curriculum on click
        div.querySelector('.item-info').onclick=()=>{
            render({curriculum:item.curriculum}, item.skill);
            historyPopup.style.display="none";
        };

        // Delete Individual item on click
        div.querySelector('.delete-btn').onclick= async (e)=>{
            e.stopPropagation(); // Prevents loading the curriculum
            if(confirm(`Are you sure you want to delete '${item.skill}' from history?`)){
                await deleteHistoryItem(item.id);
            }
        };

        historyList.appendChild(div);
    });
}

/* =========================
   DELETE INDIVIDUAL ITEM
========================= */
async function deleteHistoryItem(id) {
    try {
        const resp = await fetch(`/delete-history/${id}`, { method: "POST" });
        if (resp.ok) {
            // Only remove from UI if backend confirms deletion
            historyData = historyData.filter(item => item.id !== id);
            renderHistory();
        } else {
            // Safely handle errors if the server sends back HTML instead of JSON
            let errorMessage = `Server Error (${resp.status})`;
            try {
                const data = await resp.json();
                errorMessage = data.error || errorMessage;
            } catch(e) {
                console.warn("Could not parse error response from server.");
            }
            alert(`Could not delete item. ${errorMessage}\n\nMake sure your app.py is fully updated and running.`);
        }
    } catch (err) {
        console.error("Failed to delete item:", err);
        alert("Failed to communicate with the server. Is the Python backend running?");
    }
}

/* =========================
   CLEAR ALL HISTORY
========================= */
if(document.getElementById("clearHistory")) {
    document.getElementById("clearHistory").onclick = async () => {
        if(!historyData.length) return;
        
        if(confirm("Are you sure you want to clear ALL history? This cannot be undone.")){
            try {
                const resp = await fetch("/clear-history", { method: "POST" });
                if (resp.ok) {
                    // Only clear UI if backend confirms DB table is cleared
                    historyData = [];
                    renderHistory();
                } else {
                    let errorMessage = `Server Error (${resp.status})`;
                    try {
                        const data = await resp.json();
                        errorMessage = data.error || errorMessage;
                    } catch(e) {
                        console.warn("Could not parse error response from server.");
                    }
                    alert(`Could not clear history. ${errorMessage}\n\nMake sure your app.py is fully updated and running.`);
                }
            } catch (err) {
                console.error("Failed to clear history:", err);
                alert("Failed to communicate with the server. Is the Python backend running?");
            }
        }
    };
}

/* =========================
   SEARCH HISTORY
========================= */
if(historySearch) {
    historySearch.oninput=(e)=>{
        const val=e.target.value.toLowerCase();
        document.querySelectorAll(".history-item").forEach(item=>{
            item.style.display=item.innerText.toLowerCase().includes(val)?"flex":"none";
        });
    };
}

/* =========================
   SORT BUTTONS
========================= */
if(document.getElementById("sortNewest")) {
    document.getElementById("sortNewest").onclick=()=>{
        sortMode="newest";
        renderHistory();
    };
}

if(document.getElementById("sortOldest")) {
    document.getElementById("sortOldest").onclick=()=>{
        sortMode="oldest";
        renderHistory();
    };
}

/* =========================
   EXPORT HISTORY
========================= */
if(document.getElementById("exportHistory")) {
    document.getElementById("exportHistory").onclick=()=>{
        const blob=new Blob([JSON.stringify(historyData,null,2)],{type:"application/json"});
        const a=document.createElement("a");
        a.href=URL.createObjectURL(blob);
        a.download="history.json";
        a.click();
    };
}

/* =========================
   FORM SUBMIT
========================= */
if(form) {
    form.addEventListener("submit",async e=>{
        e.preventDefault();
        const submitBtn = form.querySelector('button[type="submit"]');

        let skill=document.getElementById("stream").value.trim();
        skill = checkSpelling(skill);
        document.getElementById("stream").value = skill;
        const duration=document.getElementById("duration").value;
        
        // Handle level defensively in case it's missing from DOM
        const levelSelect=document.getElementById("level");
        const level = levelSelect ? levelSelect.value : "Beginner";

        if(!skill) return;

        submitBtn.disabled = true;
        loader.style.display="block";
        resultBox.innerHTML="";

        try{
            const resp=await fetch("/generate",{
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify({skill,duration,level})
            });

            const data = await resp.json();

            loader.style.display="none";
            header.style.display="none";
            submitBtn.disabled = false;

            if(!resp.ok){
                resultBox.innerHTML="<p style='color:#ff4d4d; text-align:center;'>Error: " + (data.error || "Server error") + "</p>";
                return;
            }

            render(data,skill);

        }catch{
            loader.style.display="none";
            submitBtn.disabled = false;
            resultBox.innerHTML="<p style='color:#ff4d4d; text-align:center;'>Cannot connect to server. Is app.py running?</p>";
        }
    });
}

/* =========================
   RENDER CURRICULUM
========================= */
function render(data,skill){

    if(!data || !data.curriculum){
        resultBox.innerHTML="<p style='text-align:center;'>Error generating curriculum</p>";
        return;
    }

    let curr = data.curriculum;
    if (typeof curr === 'string') {
        try { curr = JSON.parse(curr); } catch(e) {}
    }
    if (curr && curr.curriculum) curr = curr.curriculum; // Handle double-wrapping

    // Wrap the curriculum in a specific container for the web display
    let html = `
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 2px solid #667eea; padding-bottom: 10px; margin-bottom: 20px;">
            <h2 style="margin:0;">${skill} Path</h2>
            <button id="pdfBtn" style="padding:8px 15px; border-radius:8px; cursor:pointer; background: linear-gradient(to right, #667eea, #764ba2); color: white; border: none; font-weight: bold; font-size: 0.9rem;">
                📄 Download PDF
            </button>
        </div>
        <div id="pdfContent">
    `;

    curr.forEach(phase=>{
        let phaseTitle = phase.phase_title || phase.title || phase.name || "Learning Phase";
        html+=`<div class="phase-title" style="margin-top: 20px; font-weight: bold; padding: 10px; background: rgba(102, 126, 234, 0.1); border-left: 4px solid #667eea; border-radius: 4px;">${phaseTitle}</div>`;
        
        let courses = phase.courses || phase.modules || phase.topics;
        if (Array.isArray(courses)) {
            courses.forEach(c=>{
                let courseTitle = c.course_title || c.title || c.name || "Course Topic";
                html+=`<div style="margin-left: 10px;">`;
                html+=`<h4 style="margin-bottom: 5px; margin-top: 15px; color: var(--text);">${courseTitle}</h4><ul style="margin-top: 0; color: var(--text);">`;
                
                if (Array.isArray(c.topics)) {
                    c.topics.forEach(t=> html+=`<li style="margin-bottom: 4px;">${t}</li>`);
                } else if (typeof c.topics === "string") {
                    html+=`<li style="margin-bottom: 4px;">${c.topics}</li>`;
                }
                html+=`</ul></div>`;
            });
        }
    });

    html += `</div>`; // Close pdfContent wrapper
    resultBox.innerHTML=html;

    /* =========================
       DOWNLOAD PDF (IMPROVED)
    ========================= */
    const pdfBtn = document.getElementById("pdfBtn");
    if(pdfBtn) {
        pdfBtn.onclick = (e) => {
            e.preventDefault();
            
            if (typeof html2pdf === 'undefined') {
                alert("PDF generation library is not loaded. Ensure you have the html2pdf.js CDN in your index.html!");
                return;
            }

            const originalText = pdfBtn.textContent;
            pdfBtn.textContent = "⌛ Generating...";
            pdfBtn.disabled = true;

            // 1. Build a "Virtual Container" specifically formatted for printing.
            // This prevents Dark Mode, scrollbars, or weird screen sizes from messing up the PDF.
            const printContainer = document.createElement("div");
            let printHtml = `
                <div style="font-family: Arial, sans-serif; color: #333; padding: 20px; max-width: 800px; margin: 0 auto;">
                    <h1 style="text-align: center; color: #4a5568; margin-bottom: 30px; font-size: 28px; border-bottom: 2px solid #cbd5e0; padding-bottom: 10px;">
                        ${skill} Learning Path
                    </h1>
            `;

            curr.forEach(phase => {
                let pTitle = phase.phase_title || phase.title || phase.name || "Learning Phase";
                // page-break-inside: avoid ensures phases aren't chopped in half
                printHtml += `
                    <div style="page-break-inside: avoid; margin-bottom: 25px;">
                        <h2 style="background-color: #edf2f7; color: #2d3748; padding: 12px; border-left: 5px solid #667eea; border-radius: 4px; font-size: 20px; margin-top: 0;">
                            ${pTitle}
                        </h2>
                        <div style="padding-left: 15px;">
                `;
                
                let coursesList = phase.courses || phase.modules || phase.topics || [];
                if (Array.isArray(coursesList)) {
                    coursesList.forEach(c => {
                        let cTitle = c.course_title || c.title || c.name || "Course Topic";
                        printHtml += `
                            <div style="page-break-inside: avoid; margin-bottom: 15px;">
                                <h3 style="color: #2b6cb0; font-size: 16px; margin-bottom: 8px;">
                                    ${cTitle}
                                </h3>
                                <ul style="margin: 0; padding-left: 20px; color: #4a5568; font-size: 14px; line-height: 1.6;">
                        `;
                        
                        let topicsList = Array.isArray(c.topics) ? c.topics : typeof c.topics === "string" ? [c.topics] : ["General Concepts"];
                        topicsList.forEach(t => {
                            printHtml += `<li style="margin-bottom: 4px;">${t}</li>`;
                        });
                        
                        printHtml += `</ul></div>`;
                    });
                }
                printHtml += `</div></div>`;
            });
            printHtml += `</div>`;
            printContainer.innerHTML = printHtml;

            // 2. Configure robust PDF settings
            const opt = {
                margin:       [0.5, 0.5, 0.5, 0.5],
                filename:     `${skill.replace(/\s+/g, '_')}_Curriculum.pdf`,
                image:        { type: 'jpeg', quality: 1 },
                html2canvas:  { 
                    scale: 2,               // High resolution
                    useCORS: true, 
                    letterRendering: true   // Fixes text overlap/mangling issues
                },
                jsPDF:        { unit: 'in', format: 'a4', orientation: 'portrait' },
                pagebreak:    { mode: ['avoid-all', 'css', 'legacy'] } // Strictly enforces page breaks
            };

            setTimeout(() => {
                html2pdf().set(opt).from(printContainer).save().then(() => {
                    pdfBtn.textContent = "✅ Downloaded";
                    setTimeout(() => {
                        pdfBtn.textContent = originalText;
                        pdfBtn.disabled = false;
                    }, 3000);
                }).catch(err => {
                    console.error("PDF generation failed:", err);
                    pdfBtn.textContent = "❌ Error";
                    setTimeout(() => {
                        pdfBtn.textContent = originalText;
                        pdfBtn.disabled = false;
                    }, 3000);
                });
            }, 100);
        };
    }
}

/* =========================
   SERVICE WORKER
========================= */
if('serviceWorker' in navigator){
    navigator.serviceWorker.register('/sw.js').catch(err => {
        // Suppress warning if sw.js simply hasn't been created yet
    });
}

});
