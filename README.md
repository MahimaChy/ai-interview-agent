# ai-interview-agent
A mock interview web app that generates 10 personalized technical questions from the user's role, skills, and experience — and scores every answer with AI feedback. Built with Flask, Google Gemini, and SQLite.

The user enters their role, skills, and years of experience. The app asks Google Gemini to generate 10 unique technical questions tailored to that profile, with a fallback list to guarantee 10 questions even under API rate-limits. Each answer is evaluated by Gemini and returned with a score from 0 to 10, the ideal answer, and written feedback. Empty, too-short, and obvious gibberish answers (like asdf or qwerty) are filtered out locally before calling the API to save tokens. Every question, answer, correct answer, and score is stored in SQLite, so past sessions can be reviewed at /history or cleared via /delete-history.

How to run
# 1. Go into the project folder
cd ai-interview-agent

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Gemini API key
echo "GOOGLE_API_KEY=your_key_here" > .env

# 5. Run the server
cd backend
python app.py
Then open http://127.0.0.1:5000/ in your browser.

Get a free Gemini API key at https://aistudio.google.com/app/apikey.
