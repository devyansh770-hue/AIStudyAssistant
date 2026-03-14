import json
from google import genai
from google.genai import types
from django.conf import settings

def generate_questions(topic, course_name, difficulty, count):
    # Initialize using the new SDK client pattern
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    prompt = f"Generate {count} multiple-choice questions for {course_name} on {topic}. Difficulty: {difficulty}."

    try:
        # Use the stable model name that worked for your scheduler
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are an expert exam creator. Return ONLY a JSON array of questions.",
                response_mime_type='application/json',
                response_schema={
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "question": {"type": "STRING"},
                            "options": {"type": "ARRAY", "items": {"type": "STRING"}},
                            "correct_answer": {"type": "STRING"},
                            "explanation": {"type": "STRING"}
                        },
                        "required": ["question", "options", "correct_answer", "explanation"]
                    }
                }
            )
        )
        # Directly return the parsed list of dictionaries
        return response.parsed 

    except Exception as e:
        print(f"Quiz Generation Error: {e}")
        return []