import json
import logging
import time
from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)

# Simulated cost per token (based on typical Flash pricing)
# Gemini 1.5/2.5 Flash is currently free for students, but tracking cost is vital for the patent claim!
COST_PER_PROMPT_TOKEN = 0.000000075
COST_PER_COMPLETION_TOKEN = 0.0000003

def process_llm_classification(question_text: str, user_response: str, correct_answer: str, heuristic_category: str, error_data: dict) -> dict:
    """
    Feature #2: LLM Error Classification (Stage 2)
    Called only if the Heuristic Gate fails to confidently categorize the error.
    """
    start_time = time.time()
    
    prompt = (
        f"A student got a question wrong.\n"
        f"Question: {question_text}\n"
        f"Correct Answer: {correct_answer}\n"
        f"Student Answer: {user_response}\n\n"
        f"Based on their error pattern (Heuristic guess: {heuristic_category}), analyze WHY they got this wrong and provide a 1-sentence encouraging explanation."
    )
    
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are an expert tutor analyzing student errors. Return ONLY JSON.",
                response_mime_type='application/json',
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "category": {"type": "STRING", "description": "E.g., Misconception, Careless Mistake, Reading Comprehension"},
                        "explanation": {"type": "STRING", "description": "A 1-sentence encouraging explanation for the student."}
                    },
                    "required": ["category", "explanation"]
                }
            )
        )
        
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        # Parse the structured response
        if response.parsed:
            result = response.parsed
        else:
            result = json.loads(response.text)
            
        # Estimate API Cost for Patent Tracking (assuming 150 prompt tokens, 50 completion tokens avg)
        # Note: Even if you use the free tier, this calculates what the enterprise cost *would* be.
        prompt_tokens = 150
        completion_tokens = 50
        estimated_cost = (prompt_tokens * COST_PER_PROMPT_TOKEN) + (completion_tokens * COST_PER_COMPLETION_TOKEN)
            
        return {
            'category': result.get('category', 'Unknown'),
            'explanation': result.get('explanation', 'No explanation provided.'),
            'api_cost': estimated_cost,
            'total_latency_ms': latency_ms,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens
        }
        
    except Exception as e:
        logger.error(f"LLM Classification Error: {e}", exc_info=True)
        end_time = time.time()
        return {
            'category': 'LLM Timeout/Error',
            'explanation': f"The correct answer is {correct_answer}. Let's review this together later!",
            'api_cost': 0.0,
            'total_latency_ms': int((end_time - start_time) * 1000),
            'prompt_tokens': 0,
            'completion_tokens': 0
        }
