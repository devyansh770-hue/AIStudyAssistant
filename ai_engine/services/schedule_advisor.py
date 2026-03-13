import json
from google import genai
from django.conf import settings


def generate_schedule(course_name, topics, exam_date, days_left, complexity, hours):
    # Initialize the client with the API key from settings
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    prompt = f"""
    Create a study schedule for the course: {course_name}.
    Topics: {topics}.
    Days until exam: {days_left}.
    Daily study hours: {hours}.
    Course complexity (1-3): {complexity}.

    Return ONLY a JSON list of objects. Each object must have these keys:
    "day": (integer), "topic": (string), "tasks": (list of strings), "tip": (string), "duration_hours": (integer)
    """
    
    try:
        # Using 'gemini-1.5-flash' to avoid regional v1beta 404 errors
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
            }
        )
        
        # Strip potential markdown backticks if the AI includes them
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        # Convert JSON string to Python list
        return json.loads(raw_text)

    except Exception as e:
        print(f"AI Generation Error: {e}")
        # Fallback list so the template doesn't crash
        return [{
            "day": "!",
            "topic": "API Error",
            "tasks": [f"Details: {str(e)}"],
            "tip": "Verify your API Key in Google AI Studio.",
            "duration_hours": 0
        }]