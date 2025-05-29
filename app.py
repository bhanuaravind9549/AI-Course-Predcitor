from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import requests
import json
import hashlib

app = Flask(__name__)
CORS(app)

OLLAMA_URL = "http://localhost:11434/api/generate"
CACHE = {}

# Load course dataset
df = pd.read_csv("courses_with_aggressive_skill_matching.csv")

@app.route('/')
@app.route('/health')
def health():
    return jsonify({
        "status": "✅ API running",
        "model": "mistral",
        "courses_loaded": len(df)
    })

@app.route('/courses')
def show_courses():
    return jsonify({
        "sample_courses": df[['Name', 'Description', 'Credits', 'Formatted TimeSlot']].head(5).to_dict(orient='records'),
        "total_courses": len(df)
    })

def log_request(payload, response):
    with open("requests_log.jsonl", "a") as f:
        f.write(json.dumps({"request": payload, "response": response}) + "\n")

def get_cache_key(data):
    key = f"{data.get('career')}_{data.get('availability')}_{data.get('credit_status')}"
    return hashlib.md5(key.encode()).hexdigest()

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    career = data.get("career", "")
    degree = data.get("degree", "")
    major = data.get("major", "")
    availability = data.get("availability", "")
    credit_status = data.get("credit_status", "full-time")

    min_credits = 8 if credit_status == "full-time" else 4

    cache_key = get_cache_key(data)
    if cache_key in CACHE:
        print("⚡ Cache hit")
        return jsonify(CACHE[cache_key])

    # Filter courses by description
    filtered_df = df[df['Description'].str.lower().str.contains(career.lower(), na=False)]
    subset_df = filtered_df.head(10) if not filtered_df.empty else df.sample(5)


    prompt = f"""
You are a smart course recommendation assistant, recommend courses for people based on their mainly on 
career goal and major, but also consider things like time availability, part-time or full-time student. 
To see if the course is a good match for them, you can look into the description of the courses and try to match with
the career goal and major.

Student career goal: {career}
Degree: {degree}
Major: {major}
Availability: {availability}
Credit Load: {credit_status.upper()} — must recommend at least {min_credits} total credits.

Here are available courses:
{subset_df[['Name', 'Description', 'Credits', 'Formatted TimeSlot']].to_json(orient='records', indent=2)}

Select 3–5 courses totaling AT LEAST {min_credits} credits.

Respond ONLY in this format:
{{
  "courses": [
    {{
      "title": "Course Name",
      "time": "Formatted TimeSlot",
      "reason": "Why it's a good fit",
      "credits": 3
    }}
  ]
}}
"""

    payload = {
        "model": "mistral",
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 250}
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        result = response.json()
        llama_output = result.get("response", "")
        print("🧠 Raw LLaMA output:", llama_output)

        parsed = json.loads(llama_output)
        CACHE[cache_key] = parsed
        log_request(data, parsed)
        return jsonify(parsed)

    except Exception as e:
        error_response = {'courses': [], 'error': f'Failed to parse LLaMA output: {str(e)}'}
        log_request(data, error_response)
        return jsonify(error_response)

if __name__ == '__main__':
    app.run(debug=True)
