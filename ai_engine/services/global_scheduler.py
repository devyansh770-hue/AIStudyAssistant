import json
import logging
from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)

def generate_global_schedule(courses_data, total_daily_hours):
    """
    courses_data should be a list of dictionaries containing:
    { "name": str, "topics": str, "complexity": int, "days_left": int, "historical_performance": dict }
    """
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    prompt = f"""
    As an AI Study Assistant, create a comprehensive optimized daily study plan merging multiple subjects.
    You must intelligently split {total_daily_hours} hours per day across these active courses based on days remaining (urgency), complexity, and past performance.
    
    Active Courses Data: {json.dumps(courses_data, indent=2)}
    
    IMPORTANT GUIDELINES:
    - Allocate more time to subjects with fewer 'days_left' and higher 'complexity'.
    - If a subject has a low score in 'historical_performance', prioritize its weak topics.
    - Do not exceed {total_daily_hours} combined hours per day.
    - Create a plan for the next 7 days (or until exams end).
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema={
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "day": {"type": "INTEGER"},
                            "date_label": {"type": "STRING"},
                            "tasks": {
                                "type": "ARRAY", 
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "course_name": {"type": "STRING"},
                                        "title": {"type": "STRING"},
                                        "duration_hours": {"type": "NUMBER"},
                                        "completed": {"type": "BOOLEAN"}
                                    },
                                    "required": ["course_name", "title", "duration_hours", "completed"]
                                }
                            },
                            "daily_motivation": {"type": "STRING"}
                        },
                        "required": ["day", "date_label", "tasks", "daily_motivation"]
                    }
                }
            )
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Global AI Schedule Generation Error: {e}", exc_info=True)
        return []
