import json
import logging
from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)

def generate_questions(topic, course_name, difficulty, count):
    # 1. Initialize the client using your settings API key
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    prompt = (
        f"Create a set of {count} multiple-choice questions for the course '{course_name}' "
        f"specifically on the topic of '{topic}'. The difficulty level should be {difficulty}."
    )

    try:
        # 2. Rectified model name to the stable 2.0 version
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
        
        # 3. Return the parsed content or fallback to raw text parsing
        if response.parsed:
            return response.parsed
        elif response.text:
            return json.loads(response.text)
        return []

    except Exception as e:
        logger.error(f"Quiz Generation Error: {e}", exc_info=True)
        return []