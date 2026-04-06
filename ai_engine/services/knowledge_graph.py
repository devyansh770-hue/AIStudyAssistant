"""
Feature 5: Knowledge Graph Auto-Constructor
Uses Gemini to extract concepts + relationships from course topics & questions,
then stores as a graph for vis.js rendering.
"""
import json
import logging
from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)


def build_knowledge_graph(course, force_refresh=False):
    """
    Returns graph_data dict: { nodes: [...], edges: [...] }
    Nodes: { id, label, type, mastery }
    Edges: { from, to, label, arrows }
    """
    from ai_engine.models import KnowledgeGraph
    from quizzes.models import QuizAttempt, Question

    # ── Check cache ──
    if not force_refresh:
        try:
            kg = KnowledgeGraph.objects.get(course=course)
            from django.utils import timezone
            import datetime
            if (timezone.now() - kg.last_updated) < datetime.timedelta(hours=12):
                return _enrich_with_mastery(kg.graph_data, course)
        except KnowledgeGraph.DoesNotExist:
            pass

    # ── Gather data for Gemini ──
    topics = course.get_topics_list()
    sample_questions = list(
        Question.objects.filter(course=course)
        .values_list('question_text', flat=True)[:30]
    )

    graph_data = _call_gemini_graph(course.name, topics, sample_questions, course.description)

    if not graph_data or not graph_data.get('nodes'):
        # Fallback: build simple linear topic graph
        graph_data = _fallback_graph(topics)

    # ── Persist ──
    KnowledgeGraph.objects.update_or_create(
        course=course,
        defaults={'graph_data': graph_data}
    )

    return _enrich_with_mastery(graph_data, course)


def _call_gemini_graph(course_name, topics, questions, description):
    """Call Gemini with structured output to extract concepts and relationships."""
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        topics_str = ', '.join(topics)
        q_sample   = ' | '.join(questions[:15])

        prompt = f"""
You are a knowledge graph expert. Analyze the course "{course_name}".

Topics: {topics_str}
Description: {description or 'N/A'}
Sample Questions: {q_sample}

Extract:
1. Key concepts (nodes) — include both the main topics and important sub-concepts found in questions.
2. Relationships between concepts (edges) — e.g., "requires", "leads_to", "part_of", "related_to".

Rules:
- Maximum 25 nodes total (include all main topics + important sub-concepts).
- Each node must have a unique id (short snake_case), a readable label, and a type ('topic' | 'concept' | 'skill').
- Each edge must have: from (node id), to (node id), and a short relationship label.
- Return ONLY valid JSON.
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "nodes": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "id":    {"type": "STRING"},
                                    "label": {"type": "STRING"},
                                    "type":  {"type": "STRING"},
                                    "description": {"type": "STRING", "description": "A 1-2 sentence quick summary defining this concept for last minute revision."}
                                },
                                "required": ["id", "label", "type", "description"]
                            }
                        },
                        "edges": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "from":  {"type": "STRING"},
                                    "to":    {"type": "STRING"},
                                    "label": {"type": "STRING"},
                                },
                                "required": ["from", "to", "label"]
                            }
                        }
                    },
                    "required": ["nodes", "edges"]
                },
                temperature=0.2,
            )
        )
        data = json.loads(response.text)
        # Add arrows to edges for vis.js
        for e in data.get('edges', []):
            e['arrows'] = 'to'
        return data

    except Exception as ex:
        logger.error(f"Knowledge Graph Gemini error: {ex}", exc_info=True)
        return None


def _enrich_with_mastery(graph_data, course):
    """Add mastery color to each node based on quiz scores."""
    from quizzes.models import QuizAttempt

    attempts = QuizAttempt.objects.filter(course=course)
    topic_scores = {}
    for a in attempts:
        topic_scores.setdefault(a.topic.lower(), []).append(a.score_percent)

    topic_avg = {t: sum(v) / len(v) for t, v in topic_scores.items()}

    nodes = []
    for node in graph_data.get('nodes', []):
        label_lower = node['label'].lower()
        score = topic_avg.get(label_lower)
        if score is None:
            # Try partial match
            for t, avg in topic_avg.items():
                if t in label_lower or label_lower in t:
                    score = avg
                    break

        mastery = _mastery_color(score)
        nodes.append({
            **node,
            'mastery':    score,
            'color':      mastery['color'],
            'borderWidth': 2,
            'size':       _node_size(node.get('type', 'concept')),
        })

    return {**graph_data, 'nodes': nodes}


def _mastery_color(score):
    if score is None:
        return {'color': {'background': '#475569', 'border': '#64748b'}}   # grey = not attempted
    elif score >= 75:
        return {'color': {'background': '#10b981', 'border': '#059669'}}   # green = mastered
    elif score >= 50:
        return {'color': {'background': '#f59e0b', 'border': '#d97706'}}   # yellow = learning
    else:
        return {'color': {'background': '#ef4444', 'border': '#dc2626'}}   # red = weak


def _node_size(node_type):
    return {'topic': 30, 'concept': 20, 'skill': 18}.get(node_type, 20)


def _fallback_graph(topics):
    """Simple linear chain graph when Gemini fails."""
    nodes = [{'id': f't{i}', 'label': t, 'type': 'topic'} for i, t in enumerate(topics)]
    edges = [
        {'from': f't{i}', 'to': f't{i+1}', 'label': 'leads_to', 'arrows': 'to'}
        for i in range(len(topics) - 1)
    ]
    return {'nodes': nodes, 'edges': edges}
