import json
import logging
import time
from google import genai
from google.genai import types
from django.conf import settings
from features.models import Concept, KnowledgeGraphMetrics

logger = logging.getLogger(__name__)

class KnowledgeGraphBuilder:
    """
    Feature #3: Autonomous Knowledge Graph Construction
    Performs Entity-Relationship Extraction (ERE).
    """
    
    @staticmethod
    def extract_entities_and_relations(text: str) -> dict:
        """
        Uses Gemini to extract Concepts (Nodes) and Prerequisites (Edges) from unstructured text.
        """
        prompt = f"Analyze the following educational text and extract the core concepts and their prerequisites:\n\n{text}"
        
        try:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You are an Entity-Relationship Extraction model. Extract educational concepts. Return ONLY JSON.",
                    response_mime_type='application/json',
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "concepts": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "name": {"type": "STRING"},
                                        "description": {"type": "STRING"},
                                        "prerequisites": {
                                            "type": "ARRAY",
                                            "items": {"type": "STRING"}
                                        }
                                    },
                                    "required": ["name", "prerequisites"]
                                }
                            }
                        },
                        "required": ["concepts"]
                    }
                )
            )
            
            if response.parsed:
                return response.parsed
            else:
                return json.loads(response.text)
                
        except Exception as e:
            logger.error(f"ERE Extraction Error: {e}")
            return {"concepts": []}

    @staticmethod
    def get_node_color(mastery_percent: int) -> str:
        """
        Determine node color based on mastery percentage for visualization.
        """
        if mastery_percent < 30:
            return "RED"
        elif mastery_percent < 70:
            return "YELLOW"
        else:
            return "GREEN"
            
    @classmethod
    def calculate_prerequisite_strength(cls, user_id: int, concept_id: int) -> float:
        """
        Calculates the average mastery of all prerequisites for a given concept.
        """
        try:
            concept = Concept.objects.get(id=concept_id)
            prerequisites = concept.prerequisites.all()
            
            if not prerequisites:
                return 1.0 # No prerequisites means 100% strength
                
            total_mastery = 0
            for prereq in prerequisites:
                metrics = KnowledgeGraphMetrics.objects.filter(user_id=user_id, concept=prereq).first()
                if metrics:
                    total_mastery += (metrics.mastery_percent / 100.0)
                    
            return total_mastery / len(prerequisites)
        except Exception:
            return 0.5
