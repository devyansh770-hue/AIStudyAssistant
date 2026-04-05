import json
import logging
from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)

def generate_schedule(course_name, topics, exam_date, days_left, complexity, hours, historical_performance=None):
    # Initialize the client (Uses GEMINI_API_KEY from your settings.py)
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    perf_context = ""
    if historical_performance:
        perf_context = f"\n    Historical Performance (Quiz Scores): {historical_performance}\n    IMPORTANT: Allocate more time, specific tasks, and priority to topics with lower scores."

    prompt = f"""
    As an AI Study Assistant, create a detailed study schedule for: {course_name}.
    Topics to cover: {topics}.
    Days until exam: {days_left} (Exam on {exam_date}).
    Daily study capacity: {hours} hours.
    Subject complexity: {complexity}/3.{perf_context}
    """
    
    try:
        # Use Gemini 3 Flash for speed and reliability in a hackathon
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                # This ensures the AI follows your JSON structure exactly
                response_schema={
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "day": {"type": "INTEGER"},
                            "topic": {"type": "STRING"},
                            "tasks": {
                                "type": "ARRAY", 
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "title": {"type": "STRING"},
                                        "completed": {"type": "BOOLEAN"}
                                    },
                                    "required": ["title", "completed"]
                                }
                            },
                            "tip": {"type": "STRING"},
                            "duration_hours": {"type": "INTEGER"}
                        },
                        "required": ["day", "topic", "tasks", "tip", "duration_hours"]
                    }
                }
            )
        )
        
        # Native structured output is already a clean JSON string
        return json.loads(response.text)

    except Exception as e:
        logger.error(f"AI Schedule Generation Error: {e}", exc_info=True)
        # Fallback to keep the UI from crashing
        return [{
            "day": 1,
            "topic": "Error loading schedule",
            "tasks": ["Check your console logs for API errors", f"Error: {str(e)}"],
            "tip": "Ensure your GEMINI_API_KEY is correct in .env",
            "duration_hours": 0
        }]