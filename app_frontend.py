import streamlit as st
import requests

st.set_page_config(page_title="Smart Course Recommender", layout="centered")
st.title(" Smart AI Course Selector")

with st.form("course_form"):
    career = st.text_input("What's your Career Goal", placeholder="e.g., data scientist, software engineer")
    degree = st.selectbox("What's your Degree", ["undergraduate", "graduate"])
    major = st.selectbox("Tell us your Major", ["data science", "computer science", "cybersecurity", "AI", "others"])
    credit_status = st.radio("What's your Credit Load", ["full-time", "part-time"], index=0)

    st.markdown(" **Select Preferred Availability:**")
    days = st.multiselect("Day(s) of the week", ["M", "T", "W", "R", "F"])
    times = st.multiselect("Time slots", ["9-10", "10-11", "11-12", "1-2", "2-3", "3-4"])

    submitted = st.form_submit_button("💡 Get Recommendations")

if submitted:
    with st.spinner("Thinking..."):
        availability = [f"{d}-{t}" for d in days for t in times]
        payload = {
            "career": career,
            "degree": degree,
            "major": major,
            "credit_status": credit_status,
            "availability": ", ".join(availability)
        }

        try:
            res = requests.post("http://127.0.0.1:5000/chat", json=payload)
            response = res.json()

            if response.get("courses"):
                st.success("✅ Recommended Courses:")
                for i, course in enumerate(response["courses"], 1):
                    st.markdown(f"""
                    **{i}. {course['title']}**
                    - 🕒 Time: {course.get('time', 'N/A')}
                    - 💳 Credits: {course.get('credits', 'N/A')}
                    - 💡 Reason: {course.get('reason', 'N/A')}
                    """)
            else:
                st.warning("🤔 No courses found. Try a different goal or time range.")

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
