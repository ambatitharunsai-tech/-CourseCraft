const form = document.getElementById("curriculumForm");
const resultBox = document.getElementById("result");
const loader = document.getElementById("loader");
form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const stream = document.getElementById("stream").value.trim();
    const duration = document.getElementById("duration").value;

    if (!stream || !duration) {
        resultBox.innerHTML = "<p style='color:red;'>Please fill all fields.</p>";
        return;
    }

    loader.style.display = "block";
    resultBox.innerHTML = "";

    let data;

try {
    const response = await fetch("/generate", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
        skill: stream,
        duration: duration
    })
});
    if (!response.ok) {
        throw new Error("Server error");
    }

    data = await response.json();

    if (!data || data.error) {
        loader.style.display = "none";
        resultBox.innerHTML = "<p style='color:red;'>Failed to generate curriculum.</p>";
        return;
    }

} catch (error) {
    loader.style.display = "none";
    resultBox.innerHTML = "<p style='color:red;'>Server error. Please try again.</p>";
    alert("⚠️ Server error. Please try again.");
    return;
}

    loader.style.display = "none";

    let html = `<div class="result-card"><h3>${stream.toUpperCase()} Curriculum</h3>`;

    for (const semester in data) {
        html += `<button class="accordion">${semester}</button>`;
        html += `<div class="panel"><ul>`;

        data[semester].forEach(course => {
            html += `<li><strong>${course.course_title}</strong><ul>`;
            course.topics.forEach(topic => {
                html += `<li>${topic}</li>`;
            });
            html += `</ul></li>`;
        });

        html += `</ul></div>`;
    }

    html += `</div>`;
    const form = document.createElement("form");
form.method = "POST";
form.action = "/view";
form.target = "_blank";

const inputData = document.createElement("input");
inputData.type = "hidden";
inputData.name = "curriculum";
inputData.value = JSON.stringify(data);

const inputSkill = document.createElement("input");
inputSkill.type = "hidden";
inputSkill.name = "skill";
inputSkill.value = stream;

form.appendChild(inputData);
form.appendChild(inputSkill);

document.body.appendChild(form);
form.submit();

    // accordion
    document.querySelectorAll(".accordion").forEach(btn => {
        btn.addEventListener("click", function () {
            const panel = this.nextElementSibling;
            panel.style.display =
                panel.style.display === "block" ? "none" : "block";
        });
    });
}
);

const toggleBtn = document.getElementById("themeToggle");

toggleBtn.addEventListener("click", function () {
    document.body.classList.toggle("dark");

    if (document.body.classList.contains("dark")) {
        toggleBtn.textContent = "☀ Light Mode";
    } else {
        toggleBtn.textContent = "🌙 Dark Mode";
    }
});
