import random
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from courses.models import Course
from quizzes.models import QuizAttempt, SurpriseTest
from accounts.models import StudyStreak

logger = logging.getLogger(__name__)


@login_required
def home(request):
    today = timezone.now().date()
    courses = Course.objects.filter(user=request.user)
    all_attempts = QuizAttempt.objects.filter(user=request.user)

    total_courses  = courses.count()
    total_quizzes  = all_attempts.count()
    avg_score = 0
    if total_quizzes > 0:
        avg_score = round(sum(a.score_percent for a in all_attempts) / total_quizzes, 1)

    upcoming_exams = courses.filter(exam_date__gte=today).order_by('exam_date')[:4]
    past_exams     = courses.filter(exam_date__lt=today).order_by('-exam_date')
    recent_attempts = all_attempts.order_by('-created_at')[:6]

    # Best and worst topics
    topic_scores = {}
    for a in all_attempts:
        topic_scores.setdefault(a.topic, []).append(a.score_percent)
    topic_avg = {t: round(sum(v)/len(v), 1) for t, v in topic_scores.items()}
    best_topic  = max(topic_avg, key=topic_avg.get) if topic_avg else None
    worst_topic = min(topic_avg, key=topic_avg.get) if topic_avg else None
    best_topic_score  = topic_avg.get(best_topic, 0) if best_topic else 0
    worst_topic_score = topic_avg.get(worst_topic, 0) if worst_topic else 0

    total_hours = sum(c.hours_spent for c in courses)

    # Streak
    streak, _ = StudyStreak.objects.get_or_create(user=request.user)

    # ── Surprise Test Logic ──
    # Check if a surprise test should be triggered (5-30% random chance per upcoming exam)
    surprise_notification = None
    if not request.session.get('surprise_checked_today'):
        request.session['surprise_checked_today'] = str(today)
        for course in upcoming_exams:
            days = course.days_until_exam()
            if 2 <= days <= 14:         # only when exam is 2-14 days away
                already = SurpriseTest.objects.filter(
                    user=request.user, course=course,
                    triggered_at__date=today
                ).exists()
                if not already and random.random() < 0.30:   # 30% daily chance
                    st = SurpriseTest.objects.create(user=request.user, course=course)
                    surprise_notification = st
                    break   # only one surprise at a time
    elif request.session.get('surprise_checked_today') != str(today):
        del request.session['surprise_checked_today']

    # ── Spaced Repetition Due Count ──
    from ai_engine.models import SpacedRepetitionCard
    sr_due_count = SpacedRepetitionCard.objects.filter(user=request.user, next_review_date__lte=today).count()
    # ── Spaced Repetition Due Count ──
    from ai_engine.models import SpacedRepetitionCard
    sr_due_count = SpacedRepetitionCard.objects.filter(user=request.user, next_review_date__lte=today).count()

    return render(request, 'dashboard/home.html', {
        'courses': courses,
        'recent_attempts': recent_attempts,
        'total_courses': total_courses,
        'total_quizzes': total_quizzes,
        'avg_score': avg_score,
        'upcoming_exams': upcoming_exams,
        'past_exams': past_exams,
        'today': today,
        'best_topic': best_topic,
        'worst_topic': worst_topic,
        'best_topic_score': best_topic_score,
        'worst_topic_score': worst_topic_score,
        'total_hours': total_hours,
        'streak': streak,
        'surprise_notification': surprise_notification,
        'sr_due_count': sr_due_count,
    })