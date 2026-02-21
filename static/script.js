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

    try {
        const response = await fetch("/generate", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                skill: stream,
                duration: duration
            })
        });

        if (!response.ok) throw new Error("Server error");

        const data = await response.json();

        loader.style.display = "none";

        if (!data || data.error) {
            resultBox.innerHTML = "<p style='color:red;'>Failed to generate curriculum.</p>";
            return;
        }

        // open result page
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

    } catch (error) {
        loader.style.display = "none";
        resultBox.innerHTML = "<p style='color:red;'>Server error. Try again.</p>";
    }
});

// DARK MODE
const toggleBtn = document.getElementById("themeToggle");

toggleBtn.addEventListener("click", function () {
    document.body.classList.toggle("dark");
    toggleBtn.textContent =
        document.body.classList.contains("dark") ? "☀ Light Mode" : "🌙 Dark Mode";
});