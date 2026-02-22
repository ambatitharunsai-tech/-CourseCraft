document.addEventListener("DOMContentLoaded", () => {

const form = document.getElementById("curriculumForm");
const resultBox = document.getElementById("result");
const loader = document.getElementById("loader");
const toggleBtn = document.getElementById("themeToggle");
const header = document.querySelector(".header-area");
const downloadBtn = document.getElementById("downloadBtn");

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
    toggleBtn.textContent = dark ? "☀ Light Mode" : "🌙 Dark Mode";
    localStorage.setItem("theme", dark ? "dark" : "light");
};

// Check for system preference if localStorage is empty
const savedTheme = localStorage.getItem("theme");
const systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
const isDark = savedTheme === "dark" || (savedTheme === null && systemPrefersDark);

setDarkMode(isDark);
toggleBtn.onclick = () => setDarkMode(!document.body.classList.contains("dark"));

/* =========================
   DOWNLOAD PDF
========================= */
downloadBtn.onclick = (e) => {
    e.preventDefault();
    const element = document.getElementById("result");
    
    if (!element || element.innerText.trim() === "") {
        alert("Please generate a curriculum first!");
        return;
    }

    const opt = {
        margin:       0.5,
        filename:     'Curriculum_Plan.pdf',
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true },
        jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
    };

    html2pdf().set(opt).from(element).save();
};

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

document.getElementById("closeHistory").onclick=()=>{
    historyPopup.style.display="none";
};

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
                // Safely handle errors if the server sends back HTML instead of JSON
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

/* =========================
   SEARCH HISTORY
========================= */
historySearch.oninput=(e)=>{
 const val=e.target.value.toLowerCase();
 document.querySelectorAll(".history-item").forEach(item=>{
    item.style.display=item.innerText.toLowerCase().includes(val)?"flex":"none";
 });
};

/* =========================
   SORT BUTTONS
========================= */
document.getElementById("sortNewest").onclick=()=>{
    sortMode="newest";
    renderHistory();
};

document.getElementById("sortOldest").onclick=()=>{
    sortMode="oldest";
    renderHistory();
};

/* =========================
   EXPORT HISTORY
========================= */
document.getElementById("exportHistory").onclick=()=>{
 const blob=new Blob([JSON.stringify(historyData,null,2)],{type:"application/json"});
 const a=document.createElement("a");
 a.href=URL.createObjectURL(blob);
 a.download="history.json";
 a.click();
};

/* =========================
   FORM SUBMIT
========================= */
form.addEventListener("submit",async e=>{
 e.preventDefault();
 const submitBtn = form.querySelector('button[type="submit"]');

 let skill=document.getElementById("stream").value.trim();
 skill = checkSpelling(skill);
 document.getElementById("stream").value = skill;
 const duration=document.getElementById("duration").value;
 const level=document.getElementById("level").value;

 if(!skill) return;

 submitBtn.disabled = true;
 loader.style.display="block";
 resultBox.innerHTML="";
 downloadBtn.style.display="none";

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
   resultBox.innerHTML=".."+(data.error || "Server error");
   return;
 }

 render(data,skill);

 }catch{
   loader.style.display="none";
   submitBtn.disabled = false;
   resultBox.innerHTML="Cannot connect to server";
 }
});

/* =========================
   RENDER CURRICULUM
========================= */
function render(data,skill){

 if(!data || !data.curriculum){
   resultBox.innerHTML="<p>Error generating curriculum</p>";
   downloadBtn.style.display="none";
   return;
 }

 downloadBtn.style.display="block";

 let html=`<h2 style="text-align:center;">${skill} Path</h2>`;

 data.curriculum.forEach(phase=>{
   html+=`<div class="phase-title" style="margin-top: 20px; font-weight: bold; border-bottom: 2px solid #667eea;">${phase.phase_title}</div>`;
   phase.courses.forEach(c=>{
     html+=`<h4 style="margin-bottom: 5px;">${c.course_title}</h4><ul style="margin-top: 0;">`;
     c.topics.forEach(t=> html+=`<li>${t}</li>`);
     html+=`</ul>`;
   });
 });

 resultBox.innerHTML=html;
}

/* =========================
   SERVICE WORKER
========================= */
if('serviceWorker' in navigator){
 navigator.serviceWorker.register('/sw.js');
}

});