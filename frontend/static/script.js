let sessionId = Date.now().toString();
let questions = [];

let currentIndex = 0;

let currentQuestion = "";


// ---------------- MARKDOWN ---------------- //

function renderMarkdown(text) {

    if (!text) return "";

    if (typeof marked !== "undefined") {

        return marked.parse(text);
    }

    // Fallback: escape HTML and preserve line breaks
    // if the marked CDN failed to load.

    const escaped = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    return "<pre>" + escaped + "</pre>";
}


// ---------------- START ---------------- //

async function startInterview() {

    const role =
        document.getElementById("role").value.trim();

    const skills =
        document.getElementById("skills").value.trim();

    const experience =
        document.getElementById("experience").value.trim();

    // ---------------- EMPTY ---------------- //

    if (!role || !skills || !experience) {

        alert("Fill all fields");

        return;
    }

    // ---------------- ROLE ---------------- //

    if (role.length < 4) {

        alert("Enter proper role");

        return;
    }

    // ---------------- SKILLS ---------------- //

    if (skills.length < 2) {

        alert("Enter proper skills");

        return;
    }

    // ---------------- EXPERIENCE ---------------- //

    if (experience.length < 2) {

        alert("Enter proper experience");

        return;
    }

    const btn = event && event.target;
    if (btn) {
        btn.disabled = true;
        btn.textContent = "Generating questions...";
    }

    document.getElementById("questionBox").innerHTML =
        "<p>Generating interview questions...<br>" +
        "<small>This can take 1–2 minutes on the first run " +
        "while the AI model loads.</small></p>";

    try {

        const res = await fetch("/generate-interview-set", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                role,
                skills,
                experience
            })
        });

        const data = await res.json();

        if (!res.ok) {

            document.getElementById("questionBox").innerHTML = "";
            alert(data.error || "Failed to generate questions");
            return;
        }

        questions = data.questions;

        currentIndex = 0;

        showQuestion();

    } catch (err) {

        document.getElementById("questionBox").innerHTML = "";
        alert("Network error: " + err.message);

    } finally {

        if (btn) {
            btn.disabled = false;
            btn.textContent = "Start Interview";
        }
    }
}

// ---------------- SHOW QUESTION ---------------- //

function showQuestion() {

    currentQuestion = questions[currentIndex];

    document.getElementById("questionBox").innerHTML =

        `<h2>${currentQuestion}</h2>`;

    document.getElementById("answerBox").value = "";

    document.getElementById("result").innerHTML = "";

    document.getElementById("nextBtn").style.display =
        "none";
}


// ---------------- SUBMIT ---------------- //

async function submitAnswer() {

    const answer =
        document.getElementById("answerBox").value;

    if (!currentQuestion) {
        alert("Start the interview first");
        return;
    }

    const btn = event && event.target;
    if (btn) {
        btn.disabled = true;
        btn.textContent = "Evaluating...";
    }

    document.getElementById("result").innerHTML =
        "<p>Evaluating your answer...</p>";

    try {

        const res = await fetch("/check-answer", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                session_id: sessionId,

                question: currentQuestion,

                answer
            })
        });

        const data = await res.json();

        document.getElementById("result").innerHTML =

            `
            <div class="evaluation">${renderMarkdown(data.evaluation)}</div>

            <h2 class="score">Score: ${data.score}/10</h2>
            `;

        document.getElementById("nextBtn").style.display =
            "inline-block";

    } catch (err) {

        document.getElementById("result").innerHTML = "";
        alert("Network error: " + err.message);

    } finally {

        if (btn) {
            btn.disabled = false;
            btn.textContent = "Submit Answer";
        }
    }
}


// ---------------- NEXT ---------------- //

function nextQuestion() {

    currentIndex++;

    if (currentIndex >= questions.length) {

        document.getElementById("questionBox").innerHTML =

            "<h1>Interview Finished 🎉</h1>";

        document.getElementById("nextBtn").style.display =
            "none";

        return;
    }

    showQuestion();
}


// ---------------- HISTORY ---------------- //

function viewHistory() {

    fetch("/history")

    .then(res => res.json())

    .then(data => {

        let html = `
        <table border="1" cellpadding="10">

        <tr>

            <th>Question</th>

            <th>Your Answer</th>

            <th>Correct Answer</th>

            <th>Score</th>

        </tr>
        `;

        data.forEach(h => {

            html += `

            <tr>

                <td>${h.question}</td>

                <td>${h.answer}</td>

                <td class="markdown-cell">${h.correct_answer ? renderMarkdown(h.correct_answer) : "—"}</td>

                <td>${h.score}</td>

            </tr>
            `;
        });

        html += "</table>";

        document.getElementById("result").innerHTML =
            html;
    });
}

function deleteHistory() {

    fetch("/delete-history", {

        method: "POST"
    })

    .then(res => res.json())

    .then(data => {

        alert(data.message);

        document.getElementById("result").innerHTML = "";
    });
}
