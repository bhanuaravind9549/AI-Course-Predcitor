# AI-Course-Predcitor
A personalized course recommendation web app built using a **React + Flask** stack. The system suggests relevant university courses based on your career goals, degree type, major, credit load, and weekly availability.


---

## Features

-  Input your career goal and get relevant course suggestions  
-  Select your weekly availability (days + times)  
-  Choose degree type and major  
-  Full-time or part-time credit load support  
-  Fast, dynamic frontend (React + Bootstrap)  
-  Powered by LLM (Mistral via Ollama) to match goals with courses  

---

##  Tech Stack

| Frontend            | Backend       | AI Model              | Data Source                        |
|---------------------|---------------|-----------------------|------------------------------------|
| React + Bootstrap   | Flask (Python)| Mistral (via Ollama)  | IU Course Catalog (CSV/JSON files) |

---

## 🛠 Installation & Setup

###  Backend (Flask)

1. Navigate to the backend folder:
   ```bash
   cd backend

2. Create and activate a virtual environment
   python -m venv venv
  source venv/bin/activate  # Windows: venv\Scripts\activate

3. Install dependencies:
   pip install -r requirements.txt

4. Start the Flask server:
   python app.py


Frontend (React)
1. Navigate to the frontend folder:
   cd frontend

2. Install dependencies:
   npm install

3. Start the React app:
   npm start


How It Works:
User submits form with career goal, degree, major, credit status, and availability

React sends the data to the Flask API

Flask filters relevant courses and generates a prompt

Mistral (via Ollama) returns recommended courses

The frontend displays them with reasoning and schedule info


To run the LLM locally:
  ollama run mistral



