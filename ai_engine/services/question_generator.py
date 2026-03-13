import json
from google import genai
from django.conf import settings

def generate_questions(topic, course_name, difficulty, count):
    # Initialize the client with your key from settings
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    prompt = f"""
    You are an expert tutor for the course {course_name}. 
    Generate {count} {difficulty} level practice questions about {topic}.
    Format the output as a clean list.
    """

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash", # Use the stable name
            contents=prompt,
            config={'response_mime_type': 'application/json'} # Force JSON
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return "Sorry, I couldn't generate questions right now."