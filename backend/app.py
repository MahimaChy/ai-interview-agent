import os
import re
import sqlite3

from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai

load_dotenv()


# ---------------- FLASK ---------------- #

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)


# ---------------- DATABASE ---------------- #

DATABASE = "interview_history.db"


def init_db():

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        session_id TEXT,

        question TEXT,

        answer TEXT,

        correct_answer TEXT,

        score INTEGER
    )
    """)

    # Migrate existing DBs that predate the correct_answer column.

    try:
        cursor.execute(
            "ALTER TABLE history ADD COLUMN correct_answer TEXT"
        )
    except sqlite3.OperationalError:
        pass

    conn.commit()

    conn.close()


init_db()


# ---------------- GEMINI ---------------- #

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print(
        "WARNING: GOOGLE_API_KEY is not set. "
        "Create a .env file in the project root with "
        "GOOGLE_API_KEY=your-key-here "
        "(get one at https://aistudio.google.com/app/apikey)."
    )
else:
    genai.configure(api_key=GOOGLE_API_KEY)

MODEL = "gemini-2.5-flash-lite"

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = genai.GenerativeModel(MODEL)
    return _model


def ask_ai(prompt):

    if not GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY not configured. Add it to .env "
            "and restart the server."
        )

    try:
        result = _get_model().generate_content(prompt)
    except Exception as e:
        raise RuntimeError(f"Gemini API error: {e}")

    text = getattr(result, "text", None)

    if not text:
        raise RuntimeError(
            f"Gemini returned empty response: {result}"
        )

    return text


# ---------------- HOME ---------------- #

@app.route("/")
def home():

    return render_template("index.html")


# ---------------- GENERATE QUESTIONS ---------------- #

@app.route("/generate-interview-set", methods=["POST"])
def generate_questions():

    try:

        data = request.json

        role = data.get("role", "").strip().lower()

        skills = data.get("skills", "").strip().lower()

        experience = data.get("experience", "").strip().lower()

        # ---------------- VALIDATION ---------------- #

        if len(role) < 4:

            return jsonify({
                "error": "Enter proper role"
            }), 400

        if len(skills) < 2:

            return jsonify({
                "error": "Enter proper skills"
            }), 400

        if len(experience) < 2:

            return jsonify({
                "error": "Enter proper experience"
            }), 400

        # ---------------- AI PROMPT ---------------- #

        prompt = f"""
Generate EXACTLY 10 interview questions.

Role: {role}

Skills: {skills}

Experience: {experience}

Rules:
- Return ONLY numbered questions
- No explanations
- No duplicate questions
- Technical interview questions only

Example:
1. What is Python?
2. Explain OOP concepts.
"""

        response = ask_ai(prompt)

        # ---------------- EXTRACT QUESTIONS ---------------- #

        questions = re.findall(
            r"\d+\.\s*(.+)",
            response
        )

        # CLEAN QUESTIONS

        cleaned = []

        seen = set()

        for q in questions:

            q = q.strip()

            if q and q.lower() not in seen:

                cleaned.append(q)

                seen.add(q.lower())

        # ---------------- FALLBACK ---------------- #

        fallback = [

            f"What is {skills}?",

            f"Explain one project using {skills}.",

            "What is API?",

            "Explain OOP concepts.",

            "Difference between list and tuple.",

            "What is SQL?",

            "Explain database normalization.",

            "What is frontend and backend?",

            "What are your strengths?",

            "Why should we hire you?"
        ]

        # GUARANTEE 10 QUESTIONS

        while len(cleaned) < 10:

            for f in fallback:

                if f not in cleaned:

                    cleaned.append(f)

                if len(cleaned) >= 10:

                    break

        return jsonify({
            "questions": cleaned[:10]
        })

    except Exception as e:

        print("QUESTION ERROR:", e)

        return jsonify({
            "error": f"Question generation failed: {e}"
        }), 500


# ---------------- CHECK ANSWER ---------------- #

@app.route("/check-answer", methods=["POST"])
def check_answer():

    try:

        data = request.json

        question = data.get("question", "")

        answer = data.get("answer", "").strip()

        session_id = data.get(
            "session_id",
            "default"
        )

        # ---------------- EMPTY ---------------- #

        if not answer:

            return jsonify({
                "evaluation": "Answer required",
                "score": 0
            })

        # ---------------- GARBAGE DETECTION ---------------- #

        garbage_words = [

            "asdf",

            "qwerty",

            "zxcv",

            "aaaa",

            "bbbb",

            "nothing",

            "haha",

            "lol"
        ]

        lower = answer.lower()

        for g in garbage_words:

            if g in lower:

                return jsonify({
                    "evaluation":
                    "Garbage answer detected.",

                    "score": 0
                })

        if len(answer.split()) < 3:

            return jsonify({
                "evaluation":
                "Answer too short.",

                "score": 2
            })

        # ---------------- AI EVALUATION ---------------- #

        prompt = f"""
You are a technical interviewer.

Question:
{question}

Candidate Answer:
{answer}

Return EXACTLY in this format:

Correct Answer:
<ideal technical answer>

Feedback:
<feedback about candidate answer>

Score:
<number between 0 and 10>
"""

        evaluation = ask_ai(prompt)

        # ---------------- SCORE ---------------- #

        score = 5

        match = re.search(
            r"Score:\s*(\d+)",
            evaluation
        )

        if match:

            score = int(match.group(1))

            if score > 10:
                score = 10

            if score < 0:
                score = 0

        # ---------------- CORRECT ANSWER ---------------- #

        correct_answer = ""

        ca_match = re.search(
            r"Correct Answer:\s*(.*?)(?=\n\s*(?:Feedback|Score)\s*:|\Z)",
            evaluation,
            re.DOTALL | re.IGNORECASE
        )

        if ca_match:

            correct_answer = ca_match.group(1).strip()

        # ---------------- SAVE DATABASE ---------------- #

        conn = sqlite3.connect(DATABASE)

        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO history
        (session_id, question, answer, correct_answer, score)

        VALUES (?, ?, ?, ?, ?)
        """, (

            session_id,

            question,

            answer,

            correct_answer,

            score
        ))

        conn.commit()

        conn.close()

        return jsonify({

            "evaluation": evaluation,

            "score": score
        })

    except Exception as e:

        print("CHECK ERROR:", e)

        return jsonify({

            "evaluation":
            f"AI evaluation failed: {e}",

            "score": 0
        }), 500


# ---------------- HISTORY ---------------- #

@app.route("/history")
def history():

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    cursor.execute("""
    SELECT question, answer, correct_answer, score
    FROM history
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    history = []

    for row in rows:

        history.append({

            "question": row[0],

            "answer": row[1],

            "correct_answer": row[2] or "",

            "score": row[3]
        })

    return jsonify(history)


# ---------------- DELETE HISTORY ---------------- #

@app.route("/delete-history", methods=["POST"])
def delete_history():

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    cursor.execute("DELETE FROM history")

    conn.commit()

    conn.close()

    return jsonify({
        "message":
        "History deleted"
    })


# ---------------- RUN ---------------- #

if __name__ == "__main__":

    app.run(debug=True)
