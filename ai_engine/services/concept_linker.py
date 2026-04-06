"""
Feature 6: Cross-Course Concept Linker
Uses TF-IDF cosine similarity (pure Python, no sklearn needed) + Gemini semantic linking
to find shared concepts across a user's courses.
"""
import json
import math
import logging
from collections import defaultdict
from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Main Entry
# ─────────────────────────────────────────────

def find_concept_links(user, force_refresh=False):
    """
    Returns list of ConceptLink-like dicts for all course pairs.
    [
      {
        'source': course_name,
        'target': course_name,
        'shared': [ {concept, similarity, tip} ],
        'strength': float 0-1,
      }
    ]
    """
    from courses.models import Course
    from ai_engine.models import ConceptLink

    courses = list(Course.objects.filter(user=user))
    if len(courses) < 2:
        return []

    # ── Check cache ──
    if not force_refresh:
        cached = ConceptLink.objects.filter(user=user).select_related('source_course', 'target_course')
        if cached.exists():
            from django.utils import timezone
            import datetime
            if (timezone.now() - cached.first().last_updated) < datetime.timedelta(hours=12):
                return _serialize_links(cached)

    # ── Build TF-IDF vectors for each course ──
    corpus  = {c.id: _course_text(c) for c in courses}
    tfidf   = _build_tfidf(corpus)
    results = []

    # ── Compare every pair ──
    for i in range(len(courses)):
        for j in range(i + 1, len(courses)):
            ca, cb = courses[i], courses[j]
            sim    = _cosine_similarity(tfidf[ca.id], tfidf[cb.id])

            if sim < 0.01 and len(courses) > 2:
                # Only skip if extremely low overlap AND user has many courses to avoid API spam.
                # For 2 courses, we'll try our best.
                continue

            # Give a minimum floor of 0.2 to sim so Gemini always has something to work with.
            effective_sim = max(0.2, sim)
            shared = _gemini_concept_links(ca, cb, effective_sim)
            strength = min(1.0, effective_sim * 2)   # normalize 0-1

            # Persist
            ConceptLink.objects.update_or_create(
                user=user,
                source_course=ca,
                target_course=cb,
                defaults={'shared_concepts': shared}
            )

            results.append({
                'source':   ca.name,
                'target':   cb.name,
                'source_id': ca.id,
                'target_id': cb.id,
                'shared':   shared,
                'strength': round(strength, 2),
                'sim_score': round(sim, 3),
            })

    return sorted(results, key=lambda x: x['strength'], reverse=True)


# ─────────────────────────────────────────────
# TF-IDF (Pure Python)
# ─────────────────────────────────────────────

def _course_text(course):
    """Combine all text signals for a course into one document."""
    parts = [course.name, course.description or '', course.topics]
    # Add question texts
    from quizzes.models import Question
    qs = Question.objects.filter(course=course).values_list('question_text', 'topic')
    for q_text, q_topic in qs[:50]:
        parts.extend([q_text, q_topic])
    return ' '.join(parts).lower()


def _tokenize(text):
    """Simple word tokenizer — strips punctuation."""
    import re
    return re.findall(r'\b[a-z]{3,}\b', text.lower())


def _build_tfidf(corpus):
    """
    corpus: {doc_id: text_string}
    Returns: {doc_id: {term: tfidf_score}}
    """
    # Stopwords
    STOP = {
        'the', 'and', 'for', 'are', 'that', 'this', 'with', 'from', 'what',
        'how', 'you', 'your', 'not', 'but', 'its', 'can', 'will', 'was',
        'has', 'have', 'been', 'which', 'they', 'their', 'when', 'where',
        'who', 'why', 'all', 'each', 'more', 'also', 'about',
    }

    docs = {doc_id: [t for t in _tokenize(text) if t not in STOP]
            for doc_id, text in corpus.items()}

    # Term frequency per doc
    tf = {}
    for doc_id, tokens in docs.items():
        freq = defaultdict(int)
        for t in tokens:
            freq[t] += 1
        total = len(tokens) or 1
        tf[doc_id] = {t: count / total for t, count in freq.items()}

    # Inverse document frequency
    all_terms = set(t for tokens in docs.values() for t in tokens)
    N = len(docs)
    idf = {}
    for term in all_terms:
        df = sum(1 for tokens in docs.values() if term in tokens)
        idf[term] = math.log(N / (1 + df)) + 1

    # TF-IDF
    tfidf = {}
    for doc_id in corpus:
        tfidf[doc_id] = {t: tf[doc_id].get(t, 0) * idf[t] for t in all_terms}

    return tfidf


def _cosine_similarity(v1, v2):
    """Cosine similarity between two TF-IDF dicts."""
    common_terms = set(v1) & set(v2)
    if not common_terms:
        return 0.0
    dot    = sum(v1[t] * v2[t] for t in common_terms)
    norm1  = math.sqrt(sum(x ** 2 for x in v1.values()))
    norm2  = math.sqrt(sum(x ** 2 for x in v2.values()))
    return dot / (norm1 * norm2) if norm1 and norm2 else 0.0


# ─────────────────────────────────────────────
# Gemini Semantic Linking
# ─────────────────────────────────────────────

def _gemini_concept_links(course_a, course_b, similarity):
    """Ask Gemini to identify specific shared concepts and how they relate."""
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        prompt = f"""
Two academic courses share conceptual overlap (similarity score: {similarity:.2f}).

Course A: "{course_a.name}" — Topics: {course_a.topics}
Course B: "{course_b.name}" — Topics: {course_b.topics}

Identify up to 5 specific concepts that appear in BOTH courses.
For each concept, explain in one sentence how it appears differently in each course.
Return ONLY JSON.
"""
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
                            "concept":     {"type": "STRING"},
                            "in_course_a": {"type": "STRING"},
                            "in_course_b": {"type": "STRING"},
                            "tip":         {"type": "STRING"},
                            "similarity":  {"type": "NUMBER"},
                        },
                        "required": ["concept", "in_course_a", "in_course_b", "tip", "similarity"]
                    }
                },
                temperature=0.3,
            )
        )
        return json.loads(response.text)
    except Exception as ex:
        logger.warning(f"Gemini concept linking failed: {ex}")
        # Fallback: extract top shared keywords from topics
        return _keyword_fallback(course_a, course_b)


def _keyword_fallback(course_a, course_b):
    """Simple keyword overlap when Gemini fails."""
    words_a = set(_tokenize(course_a.topics))
    words_b = set(_tokenize(course_b.topics))
    shared  = words_a & words_b
    return [
        {'concept': w, 'in_course_a': course_a.name, 'in_course_b': course_b.name,
         'tip': f"Both courses use '{w}' — review it in context of each subject.",
         'similarity': 0.5}
        for w in list(shared)[:5]
    ]


def _serialize_links(qs):
    result = []
    for link in qs:
        result.append({
            'source':    link.source_course.name,
            'target':    link.target_course.name,
            'source_id': link.source_course.id,
            'target_id': link.target_course.id,
            'shared':    link.shared_concepts,
            'strength':  min(1.0, len(link.shared_concepts) / 5),
            'sim_score': round(len(link.shared_concepts) / 5, 2),
        })
    return result
