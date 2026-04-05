"""
Feature 1: Predictive Exam Score Estimator
Uses weighted regression + trend analysis on existing QuizAttempt data.
No external ML library required — pure Python math.
"""
import math
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Core Prediction Engine
# ─────────────────────────────────────────────

def predict_exam_score(course, user):
    """
    Returns a dict:
    {
      'predicted_score': float (0-100),
      'confidence': str ('Low' | 'Medium' | 'High'),
      'confidence_pct': float,
      'topic_readiness': { topic: { score, trend, attempts } },
      'coverage_pct': float,
      'trend': str ('improving' | 'stable' | 'declining'),
      'weak_topics': [str],
      'strong_topics': [str],
      'recommendation': str,
      'has_data': bool,
    }
    """
    from quizzes.models import QuizAttempt

    attempts = list(QuizAttempt.objects.filter(
        user=user, course=course
    ).order_by('created_at'))

    if not attempts:
        return _no_data_result(course)

    topics = course.get_topics_list()
    today  = date.today()

    # ── 1. Per-topic weighted averages ──
    topic_data = {}
    for t in topics:
        t_attempts = [a for a in attempts if a.topic.strip().lower() == t.strip().lower()]
        if t_attempts:
            topic_data[t] = _topic_stats(t_attempts, today)
        else:
            topic_data[t] = {'score': None, 'trend': 0.0, 'attempts': 0, 'weighted_avg': 0.0}

    # ── 2. Coverage bonus ──
    covered = sum(1 for t in topics if topic_data[t]['attempts'] > 0)
    coverage_pct = (covered / len(topics) * 100) if topics else 0

    # ── 3. Global trend (last 10 attempts) ──
    recent = attempts[-10:]
    global_trend = _linear_slope([a.score_percent for a in recent])
    trend_label = 'improving' if global_trend > 1 else ('declining' if global_trend < -1 else 'stable')

    # ── 4. Composite predicted score ──
    topic_weights = _compute_topic_weights(course)
    weighted_sum  = 0.0
    weight_total  = 0.0
    for t in topics:
        w = topic_weights.get(t, 1.0)
        td = topic_data[t]
        if td['attempts'] > 0:
            weighted_sum  += td['weighted_avg'] * w
            weight_total  += w
        else:
            # No data → pessimistic estimate based on complexity
            penalty = {1: 55, 2: 45, 3: 35}.get(course.complexity, 45)
            weighted_sum  += penalty * w
            weight_total  += w

    base_score = (weighted_sum / weight_total) if weight_total > 0 else 0

    # Trend bonus/penalty
    trend_bonus  = global_trend * 0.5   # ±0.5 per %/attempt slope
    # Coverage bonus
    cov_bonus    = (coverage_pct - 50) * 0.1  # up to ±5 pts
    predicted    = min(100, max(0, base_score + trend_bonus + cov_bonus))

    # ── 5. Confidence level ──
    n_attempts   = len(attempts)
    if n_attempts >= 10 and coverage_pct >= 70:
        confidence, confidence_pct = 'High', 85.0
    elif n_attempts >= 5 and coverage_pct >= 40:
        confidence, confidence_pct = 'Medium', 65.0
    else:
        confidence, confidence_pct = 'Low', 40.0

    # ── 6. Weak / strong topics ──
    scored_topics = {t: topic_data[t]['weighted_avg']
                     for t in topics if topic_data[t]['attempts'] > 0}
    weak   = sorted([t for t, s in scored_topics.items() if s < 60],  key=lambda t: scored_topics[t])[:3]
    strong = sorted([t for t, s in scored_topics.items() if s >= 75], key=lambda t: scored_topics[t], reverse=True)[:3]

    # ── 7. Recommendation ──
    recommendation = _build_recommendation(predicted, weak, trend_label, coverage_pct, course)

    return {
        'predicted_score':  round(predicted, 1),
        'confidence':       confidence,
        'confidence_pct':   confidence_pct,
        'topic_readiness':  topic_data,
        'coverage_pct':     round(coverage_pct, 1),
        'trend':            trend_label,
        'trend_slope':      round(global_trend, 2),
        'weak_topics':      weak,
        'strong_topics':    strong,
        'recommendation':   recommendation,
        'has_data':         True,
        'n_attempts':       n_attempts,
    }


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _topic_stats(t_attempts, today):
    """Compute exponentially-weighted average + linear trend for a topic."""
    scores  = []
    weights = []
    for a in t_attempts:
        days_ago = (today - a.created_at.date()).days
        w = math.exp(-0.05 * days_ago)   # exponential decay
        scores.append(a.score_percent)
        weights.append(w)

    weighted_avg = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
    trend        = _linear_slope(scores)
    return {
        'score':        round(weighted_avg, 1),
        'weighted_avg': weighted_avg,
        'trend':        round(trend, 2),
        'attempts':     len(t_attempts),
    }


def _linear_slope(values):
    """Simple linear regression slope over index positions."""
    n = len(values)
    if n < 2:
        return 0.0
    xs   = list(range(n))
    x_m  = sum(xs) / n
    y_m  = sum(values) / n
    num  = sum((xs[i] - x_m) * (values[i] - y_m) for i in range(n))
    den  = sum((xs[i] - x_m) ** 2 for i in range(n))
    return num / den if den != 0 else 0.0


def _compute_topic_weights(course):
    """Topics first in the list get slightly higher weight (exam focus heuristic)."""
    topics = course.get_topics_list()
    n      = len(topics)
    return {t: 1.0 + (n - i) * 0.1 for i, t in enumerate(topics)}


def _build_recommendation(score, weak_topics, trend, coverage_pct, course):
    days_left = course.days_until_exam()
    if days_left <= 0:
        return "The exam date has passed. Review your results and plan for future exams."
    if score >= 80 and trend != 'declining':
        return f"You're well-prepared! Keep your current study pace and do 1–2 revision quizzes per day."
    elif score >= 65:
        topics_str = ', '.join(weak_topics) if weak_topics else 'your weaker topics'
        return f"Good progress! Focus on {topics_str} and attempt at least 1 quiz per topic before the exam."
    else:
        topics_str = ', '.join(weak_topics[:2]) if weak_topics else 'all topics'
        urgency    = "immediately" if days_left <= 5 else "as soon as possible"
        return (f"You need to intensify your revision {urgency}. "
                f"Prioritize {topics_str} — your quiz coverage is only {coverage_pct:.0f}%.")


def _no_data_result(course):
    return {
        'predicted_score':  None,
        'confidence':       'Low',
        'confidence_pct':   0.0,
        'topic_readiness':  {},
        'coverage_pct':     0.0,
        'trend':            'stable',
        'trend_slope':      0.0,
        'weak_topics':      [],
        'strong_topics':    [],
        'recommendation':   'Take at least one quiz per topic to enable score prediction.',
        'has_data':         False,
        'n_attempts':       0,
    }
