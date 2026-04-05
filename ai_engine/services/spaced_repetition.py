"""
Feature 3: Spaced Repetition Neural Scheduler (Modified SM-2 Algorithm)
SuperMemo-2 adapted to use quiz score_percent as the quality signal.
"""
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# SM-2 Constants
EF_MIN = 1.3
EF_DEFAULT = 2.5


# ─────────────────────────────────────────────
# SM-2 Core
# ─────────────────────────────────────────────

def score_to_quality(score_percent):
    """Map quiz score (0-100) to SM-2 quality (0-5)."""
    if score_percent >= 90: return 5
    if score_percent >= 75: return 4
    if score_percent >= 60: return 3
    if score_percent >= 45: return 2
    if score_percent >= 25: return 1
    return 0


def sm2_update(card, quality):
    """
    Update a SpacedRepetitionCard in-place using SM-2 algorithm.
    quality: 0-5 integer
    """
    today = date.today()

    # Update easiness factor
    ef = card.easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    card.easiness_factor = max(EF_MIN, round(ef, 3))

    # Update interval
    if quality < 3:
        # Failed: reset to 1 day
        card.interval_days = 1
        card.repetition_count = 0
    else:
        # Passed
        if card.repetition_count == 0:
            card.interval_days = 1
        elif card.repetition_count == 1:
            card.interval_days = 3
        else:
            card.interval_days = round(card.interval_days * card.easiness_factor)
        card.repetition_count += 1

    card.last_quality     = quality
    card.last_review_date = today
    card.next_review_date = today + timedelta(days=card.interval_days)
    card.save()
    return card


# ─────────────────────────────────────────────
# Card Management
# ─────────────────────────────────────────────

def get_or_create_card(user, course, topic):
    """Get existing SR card or create one due today."""
    from ai_engine.models import SpacedRepetitionCard
    card, created = SpacedRepetitionCard.objects.get_or_create(
        user=user, course=course, topic=topic,
        defaults={
            'next_review_date': date.today(),
            'easiness_factor':  EF_DEFAULT,
            'interval_days':    1,
            'repetition_count': 0,
        }
    )
    return card, created


def record_quiz_attempt(user, course, topic, score_percent):
    """
    Called after every quiz attempt. Updates the SR card for the topic.
    Returns the updated card.
    """
    card, _ = get_or_create_card(user, course, topic)
    quality  = score_to_quality(score_percent)
    sm2_update(card, quality)
    logger.debug(f"SR updated: {user.username}/{topic} → quality={quality}, next={card.next_review_date}")
    return card


def get_due_cards(user, courses=None):
    """
    Returns all SR cards due for review today (or overdue).
    courses: optional queryset to filter by
    """
    from ai_engine.models import SpacedRepetitionCard
    today = date.today()
    qs = SpacedRepetitionCard.objects.filter(user=user, next_review_date__lte=today)
    if courses is not None:
        qs = qs.filter(course__in=courses)
    return qs.select_related('course').order_by('next_review_date', 'last_quality')


def get_review_stats(user):
    """
    Returns aggregate stats for the review queue page.
    """
    from ai_engine.models import SpacedRepetitionCard
    from courses.models import Course
    from django.utils import timezone

    today     = date.today()
    all_cards = SpacedRepetitionCard.objects.filter(user=user)
    due_today = all_cards.filter(next_review_date__lte=today)
    upcoming  = all_cards.filter(next_review_date__gt=today).order_by('next_review_date')[:10]

    mastered  = all_cards.filter(interval_days__gte=14).count()
    learning  = all_cards.filter(interval_days__lt=14, repetition_count__gt=0).count()
    new_cards = all_cards.filter(repetition_count=0).count()

    return {
        'due_count':    due_today.count(),
        'due_cards':    due_today.select_related('course'),
        'upcoming':     upcoming.select_related('course'),
        'total_cards':  all_cards.count(),
        'mastered':     mastered,
        'learning':     learning,
        'new_cards':    new_cards,
    }


def bootstrap_cards_for_course(user, course):
    """
    Create SR cards for all topics in a course that don't have cards yet.
    Sets next_review_date staggered over the next 3 days.
    """
    from ai_engine.models import SpacedRepetitionCard
    topics  = course.get_topics_list()
    created = 0
    for i, topic in enumerate(topics):
        _, was_created = SpacedRepetitionCard.objects.get_or_create(
            user=user, course=course, topic=topic,
            defaults={
                'next_review_date': date.today() + timedelta(days=i % 3),
                'easiness_factor':  EF_DEFAULT,
                'interval_days':    1,
                'repetition_count': 0,
            }
        )
        if was_created:
            created += 1
    return created
