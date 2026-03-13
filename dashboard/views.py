from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from courses.models import Course
from quizzes.models import QuizAttempt


@login_required
def home(request):
    today = timezone.now().date()
    courses = Course.objects.filter(user=request.user)
    all_attempts = QuizAttempt.objects.filter(user=request.user)

    total_courses  = courses.count()
    total_quizzes  = all_attempts.count()
    avg_score      = 0
    if total_quizzes > 0:
        avg_score = round(
            sum(a.score_percent for a in all_attempts) / total_quizzes, 1
        )

    upcoming_exams = courses.filter(exam_date__gte=today).order_by('exam_date')[:4]
    recent_attempts = all_attempts.order_by('-created_at')[:6]

    # Best and worst topics
    topic_scores = {}
    for a in all_attempts:
        if a.topic not in topic_scores:
            topic_scores[a.topic] = []
        topic_scores[a.topic].append(a.score_percent)

    topic_avg = {t: round(sum(v)/len(v), 1) for t, v in topic_scores.items()}
    best_topic  = max(topic_avg, key=topic_avg.get) if topic_avg else None
    worst_topic = min(topic_avg, key=topic_avg.get) if topic_avg else None

    # Total hours studied
    total_hours = sum(c.hours_spent for c in courses)

    return render(request, 'dashboard/home.html', {
        'courses': courses,
        'recent_attempts': recent_attempts,
        'total_courses': total_courses,
        'total_quizzes': total_quizzes,
        'avg_score': avg_score,
        'upcoming_exams': upcoming_exams,
        'today': today,
        'best_topic': best_topic,
        'worst_topic': worst_topic,
        'topic_avg': topic_avg,
        'total_hours': total_hours,
    })