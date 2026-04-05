"""
Feature 2: Intelligent Mistake Pattern Analyzer
Clusters wrong answers by type, then uses Gemini to generate natural-language insights.
"""
import json
import logging
from collections import defaultdict
from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────

def analyze_mistakes(course, user, force_refresh=False):
    """
    Returns a list of pattern dicts:
    [
      {
        'pattern_type': str,
        'title': str,
        'icon': str,
        'severity': 'high'|'medium'|'low',
        'details': dict,
        'gemini_insight': str,
        'actionable_fix': str,
      }
    ]
    """
    from quizzes.models import Question, QuizAttempt
    from ai_engine.models import MistakePattern

    # ── Check cache ──
    if not force_refresh:
        cached = MistakePattern.objects.filter(user=user, course=course).order_by('-updated_at')
        if cached.exists():
            from django.utils import timezone
            import datetime
            latest = cached.first()
            if (timezone.now() - latest.updated_at) < datetime.timedelta(hours=6):
                return _serialize_patterns(cached)

    # ── Gather wrong answers ──
    mistakes = _collect_mistakes(user, course)

    if not mistakes:
        return []

    # ── Local statistical analysis ──
    patterns = []
    patterns += _analyze_topic_weakness(mistakes, course)
    patterns += _analyze_difficulty_ceiling(mistakes)
    patterns += _analyze_time_pressure(mistakes, user, course)
    patterns += _analyze_conceptual_confusion(mistakes)

    # ── Gemini NLP enrichment ──
    for p in patterns:
        p['gemini_insight'] = _gemini_insight(p, course)

    # ── Persist to cache ──
    MistakePattern.objects.filter(user=user, course=course).delete()
    for p in patterns:
        MistakePattern.objects.create(
            user=user,
            course=course,
            pattern_type=p['pattern_type'],
            details=p['details'],
            gemini_insight=p.get('gemini_insight', ''),
        )

    return patterns


# ─────────────────────────────────────────────
# Data Collection
# ─────────────────────────────────────────────

def _collect_mistakes(user, course):
    """Returns structured wrong-answer records."""
    from quizzes.models import Question, QuizAttempt

    attempts = QuizAttempt.objects.filter(user=user, course=course)
    mistakes = []
    for attempt in attempts:
        questions = Question.objects.filter(course=course, topic=attempt.topic)
        for q in questions:
            mistakes.append({
                'topic':       attempt.topic,
                'difficulty':  q.difficulty,
                'question':    q.question_text[:150],
                'correct':     q.correct_answer,
                'score':       attempt.score_percent,
                'time':        attempt.time_taken_seconds,
                'total_qs':    attempt.total_questions,
            })
    return mistakes


# ─────────────────────────────────────────────
# Pattern Detectors
# ─────────────────────────────────────────────

def _analyze_topic_weakness(mistakes, course):
    topic_errors = defaultdict(list)
    for m in mistakes:
        if m['score'] < 60:
            topic_errors[m['topic']].append(m['score'])

    if not topic_errors:
        return []

    worst_topics = sorted(topic_errors, key=lambda t: sum(topic_errors[t]) / len(topic_errors[t]))[:3]
    details = {
        'weak_topics': [
            {'topic': t,
             'avg_score': round(sum(topic_errors[t]) / len(topic_errors[t]), 1),
             'error_count': len(topic_errors[t])}
            for t in worst_topics
        ]
    }
    severity = 'high' if details['weak_topics'] and details['weak_topics'][0]['avg_score'] < 40 else 'medium'
    return [{
        'pattern_type':   'topic_weakness',
        'title':          'Consistent Topic Weaknesses',
        'icon':           '📉',
        'severity':       severity,
        'details':        details,
        'actionable_fix': f"Focus your next 3 study sessions on: {', '.join(worst_topics)}",
    }]


def _analyze_difficulty_ceiling(mistakes):
    difficulty_errors = defaultdict(list)
    for m in mistakes:
        if m['score'] < 60:
            difficulty_errors[m['difficulty']].append(m['score'])

    if not difficulty_errors:
        return []

    # Determine the ceiling (highest difficulty with failures)
    order = ['easy', 'medium', 'hard']
    ceiling = None
    for lvl in reversed(order):
        if lvl in difficulty_errors:
            ceiling = lvl
            break

    if not ceiling:
        return []

    details = {
        'difficulty_ceiling': ceiling,
        'error_rates': {
            lvl: {'count': len(difficulty_errors[lvl]),
                  'avg_score': round(sum(difficulty_errors[lvl]) / len(difficulty_errors[lvl]), 1)}
            for lvl in difficulty_errors
        }
    }
    return [{
        'pattern_type':   'difficulty_ceiling',
        'title':          f'Difficulty Ceiling at {ceiling.capitalize()} Level',
        'icon':           '🧱',
        'severity':       'high' if ceiling == 'easy' else 'medium',
        'details':        details,
        'actionable_fix': f"Practice more {ceiling}-difficulty questions until you consistently score ≥70%.",
    }]


def _analyze_time_pressure(mistakes, user, course):
    from quizzes.models import QuizAttempt
    timed_attempts = QuizAttempt.objects.filter(
        user=user, course=course, time_taken_seconds__gt=0
    )

    if timed_attempts.count() < 3:
        return []

    rushed = [a for a in timed_attempts
              if a.total_questions > 0
              and a.time_taken_seconds / a.total_questions < 20
              and a.score_percent < 65]

    if len(rushed) < 2:
        return []

    avg_rush_score = sum(a.score_percent for a in rushed) / len(rushed)
    details = {
        'rushed_attempts': len(rushed),
        'avg_rushed_score': round(avg_rush_score, 1),
        'threshold_seconds_per_q': 20,
    }
    return [{
        'pattern_type':   'time_pressure',
        'title':          'Rushing Under Time Pressure',
        'icon':           '⏱️',
        'severity':       'medium',
        'details':        details,
        'actionable_fix': 'Slow down — aim for at least 30 seconds per question. Accuracy beats speed.',
    }]


def _analyze_conceptual_confusion(mistakes):
    """Detect near-miss patterns — low scores on specific concepts repeated across attempts."""
    concept_failures = defaultdict(int)
    for m in mistakes:
        if m['score'] < 50:
            # Use first 5 words of question as a proxy concept key
            key = ' '.join(m['question'].lower().split()[:5])
            concept_failures[key] += 1

    repeated = {k: v for k, v in concept_failures.items() if v >= 2}
    if not repeated:
        return []

    top_confusions = sorted(repeated, key=repeated.get, reverse=True)[:3]
    details = {'repeated_failure_concepts': [
        {'hint': k, 'occurrences': repeated[k]} for k in top_confusions
    ]}
    return [{
        'pattern_type':   'conceptual_confusion',
        'title':          'Recurring Conceptual Confusion',
        'icon':           '🔄',
        'severity':       'high',
        'details':        details,
        'actionable_fix': 'Ask the AI Tutor to re-explain these concepts from scratch with examples.',
    }]


# ─────────────────────────────────────────────
# Gemini NLP Enrichment
# ─────────────────────────────────────────────

def _gemini_insight(pattern, course):
    """Generate 2-3 sentence natural-language insight using Gemini."""
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        prompt = (
            f"A student studying '{course.name}' has the following learning pattern: "
            f"Pattern type: {pattern['pattern_type']}. Details: {json.dumps(pattern['details'])}. "
            f"In 2-3 sentences, explain WHY this pattern occurs and give one specific, actionable tip to fix it. "
            f"Be encouraging but honest. Do not use bullet points."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.4),
        )
        return response.text.strip()
    except Exception as e:
        logger.warning(f"Gemini insight failed for pattern {pattern['pattern_type']}: {e}")
        return pattern.get('actionable_fix', '')


# ─────────────────────────────────────────────
# Serializer
# ─────────────────────────────────────────────

_PATTERN_META = {
    'topic_weakness':       ('📉', 'Consistent Topic Weaknesses'),
    'difficulty_ceiling':   ('🧱', 'Difficulty Ceiling'),
    'time_pressure':        ('⏱️', 'Rushing Under Time Pressure'),
    'conceptual_confusion': ('🔄', 'Recurring Conceptual Confusion'),
}

def _serialize_patterns(qs):
    result = []
    for p in qs:
        icon, title = _PATTERN_META.get(p.pattern_type, ('🔍', p.pattern_type))
        # Derive severity from details
        details = p.details or {}
        weak_topics = details.get('weak_topics', [])
        severity = 'medium'
        if weak_topics and weak_topics[0].get('avg_score', 100) < 40:
            severity = 'high'
        result.append({
            'pattern_type':   p.pattern_type,
            'title':          title,
            'icon':           icon,
            'severity':       severity,
            'details':        details,
            'gemini_insight': p.gemini_insight,
            'actionable_fix': p.gemini_insight,
        })
    return result
