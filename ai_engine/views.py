import json
import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from courses.models import Course, ScheduleHistory
from quizzes.models import QuizAttempt
from .services.question_generator import generate_questions
from .services.schedule_advisor import generate_schedule
from .services.global_scheduler import generate_global_schedule
from .services.tutor_chat import ask_tutor
from .services.score_predictor import predict_exam_score
from .services.mistake_analyzer import analyze_mistakes
from .services.spaced_repetition import get_review_stats, bootstrap_cards_for_course, get_due_cards
from .services.cognitive_load import update_cognitive_load, summarize_session, get_user_load_history
from .services.knowledge_graph import build_knowledge_graph
from .services.concept_linker import find_concept_links

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
#  EXISTING VIEWS (unchanged)
# ═══════════════════════════════════════════

@login_required
def view_schedule(request, course_id):
    course = get_object_or_404(Course, pk=course_id, user=request.user)
    days_left = course.days_until_exam()
    is_exam_over = days_left < 0
    schedule = course.ai_schedule
    history = ScheduleHistory.objects.filter(course=course)

    if request.method == 'POST' and not is_exam_over:
        from quizzes.models import QuizAttempt
        attempts = QuizAttempt.objects.filter(course=course)
        topic_scores = {}
        for a in attempts:
            topic_scores.setdefault(a.topic, []).append(a.score_percent)
        historical_perf = {t: f"{round(sum(v)/len(v), 1)}% avg score" for t, v in topic_scores.items()}

        schedule = generate_schedule(
            course.name, course.topics, str(course.exam_date),
            max(days_left, 1), course.complexity, course.daily_study_hours,
            historical_performance=historical_perf
        )
        course.ai_schedule = schedule
        course.save()
        ScheduleHistory.objects.create(
            course=course,
            schedule_data=schedule,
            label=f"Generated {timezone.now():%d %b %Y %H:%M}"
        )
        history = ScheduleHistory.objects.filter(course=course)

        return render(request, 'ai_engine/schedule.html', {
            'course': course,
            'schedule': schedule,
            'is_exam_over': is_exam_over,
            'history': history,
            'all_courses': Course.objects.filter(user=request.user),
        })

    return render(request, 'ai_engine/schedule.html', {
        'course': course,
        'schedule': schedule,
        'is_exam_over': is_exam_over,
        'history': history,
        'all_courses': Course.objects.filter(user=request.user),
    })


@login_required
def global_schedule_view(request):
    courses = Course.objects.filter(user=request.user)
    upcoming_courses = list(courses)
    schedule = request.session.get('global_schedule')

    if request.method == 'POST' and upcoming_courses:
        courses_data = []
        for c in upcoming_courses:
            topic_scores = {}
            for a in QuizAttempt.objects.filter(course=c):
                topic_scores.setdefault(a.topic, []).append(a.score_percent)
            hist_perf = {t: round(sum(v)/len(v), 1) for t, v in topic_scores.items()}
            days = c.days_until_exam()
            courses_data.append({
                "name": c.name,
                "topics": c.topics,
                "complexity": c.complexity,
                "days_left": days if days > 0 else 1,
                "historical_performance": hist_perf
            })
        total_hours = sum(c.daily_study_hours for c in upcoming_courses)
        schedule = generate_global_schedule(courses_data, min(total_hours, 10))
        request.session['global_schedule'] = schedule

    return render(request, 'ai_engine/global_schedule.html', {
        'schedule': schedule,
        'upcoming_courses': upcoming_courses,
    })


@login_required
@require_POST
def api_generate_questions(request):
    try:
        data = json.loads(request.body)
        course = get_object_or_404(Course, pk=data.get('course_id'), user=request.user)
        questions = generate_questions(
            data.get('topic', ''), course.name,
            data.get('difficulty', 'medium'), int(data.get('count', 5))
        )
        return JsonResponse({'success': True, 'questions': questions})
    except Exception as e:
        logger.error(f"Quiz Generation Error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def generate_questions_view(request, course_id):
    course = get_object_or_404(Course, pk=course_id, user=request.user)
    topics = course.get_topics_list()
    return render(request, 'ai_engine/generate_questions.html', {
        'course': course, 'topics': topics
    })


@login_required
def tutor_chat_view(request, course_id):
    course = get_object_or_404(Course, pk=course_id, user=request.user)
    topics = course.get_topics_list()
    return render(request, 'ai_engine/chat.html', {
        'course': course, 'topics': topics,
    })


@login_required
@require_POST
def api_tutor_chat(request):
    try:
        data = json.loads(request.body)
        question = data.get('question', '')
        course_id = data.get('course_id')
        topic = data.get('topic', 'General')
        history = data.get('history') or []
        course = get_object_or_404(Course, pk=course_id, user=request.user)
        answer = ask_tutor(question, course.name, topic, history)
        return JsonResponse({'success': True, 'answer': answer})
    except Exception as e:
        logger.error(f"Tutor Chat Error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def toggle_task_completion(request):
    try:
        data = json.loads(request.body)
        history_id = data.get('history_id')
        day_idx = int(data.get('day_idx', 0))
        task_idx = int(data.get('task_idx', 0))
        history = get_object_or_404(ScheduleHistory, pk=history_id, course__user=request.user)
        schedule_data = history.schedule_data

        if 0 <= day_idx < len(schedule_data):
            day_obj = schedule_data[day_idx]
            tasks = day_obj.get('tasks', [])
            if 0 <= task_idx < len(tasks):
                task = tasks[task_idx]
                if isinstance(task, str):
                    task = {"title": task, "completed": True}
                    tasks[task_idx] = task
                else:
                    task['completed'] = not task.get('completed', False)
                history.schedule_data = schedule_data
                history.save()
                if history == history.course.schedule_history.first():
                    history.course.ai_schedule = schedule_data
                    history.course.save()
                return JsonResponse({'success': True, 'completed': task['completed']})

        return JsonResponse({'success': False, 'error': 'Invalid indices'}, status=400)
    except Exception as e:
        logger.error(f"Toggle Task Error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def delete_schedule(request, history_id):
    try:
        history = get_object_or_404(ScheduleHistory, pk=history_id, course__user=request.user)
        course = history.course
        
        # Check if this is the currently active schedule in Course model
        is_active = (course.ai_schedule == history.schedule_data)
        
        history.delete()
        
        # If we deleted the active one, pick the next available from history or clear it
        if is_active:
            next_hist = course.schedule_history.first() # newest remaining
            course.ai_schedule = next_hist.schedule_data if next_hist else None
            course.save()
            
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Delete Schedule Error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ═══════════════════════════════════════════
#  FEATURE 1: Predictive Exam Score Estimator
# ═══════════════════════════════════════════

@login_required
def predict_score_view(request, course_id):
    course = get_object_or_404(Course, pk=course_id, user=request.user)
    prediction = predict_exam_score(course, request.user)
    all_attempts = QuizAttempt.objects.filter(user=request.user, course=course).order_by('created_at')
    # Sparkline data (last 15 attempts)
    sparkline = [round(a.score_percent, 1) for a in list(all_attempts)[-15:]]
    return render(request, 'ai_engine/score_prediction.html', {
        'course':     course,
        'prediction': prediction,
        'sparkline':  json.dumps(sparkline),
        'days_left':  course.days_until_exam(),
    })


@login_required
@require_POST
def api_predict_score(request):
    try:
        data = json.loads(request.body)
        course = get_object_or_404(Course, pk=data.get('course_id'), user=request.user)
        prediction = predict_exam_score(course, request.user)
        return JsonResponse({'success': True, 'prediction': prediction})
    except Exception as e:
        logger.error(f"Predict Score Error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ═══════════════════════════════════════════
#  FEATURE 2: Mistake Pattern Analyzer
# ═══════════════════════════════════════════

@login_required
def mistake_analysis_view(request, course_id):
    course   = get_object_or_404(Course, pk=course_id, user=request.user)
    refresh  = request.GET.get('refresh') == '1'
    patterns = analyze_mistakes(course, request.user, force_refresh=refresh)
    attempts = QuizAttempt.objects.filter(user=request.user, course=course)

    # Heatmap: topic × difficulty grid
    heatmap  = _build_heatmap(attempts)

    return render(request, 'ai_engine/mistake_analysis.html', {
        'course':    course,
        'patterns':  patterns,
        'heatmap':   json.dumps(heatmap),
        'total_attempts': attempts.count(),
    })


def _build_heatmap(attempts):
    from collections import defaultdict
    grid = defaultdict(lambda: defaultdict(list))
    for a in attempts:
        grid[a.topic]['all'].append(a.score_percent)
    result = []
    for topic, data in grid.items():
        scores = data['all']
        avg    = sum(scores) / len(scores)
        result.append({'topic': topic, 'avg': round(avg, 1), 'count': len(scores)})
    return sorted(result, key=lambda x: x['avg'])


# ═══════════════════════════════════════════
#  FEATURE 3: Spaced Repetition Queue
# ═══════════════════════════════════════════

@login_required
def review_queue_view(request):
    courses = Course.objects.filter(user=request.user)

    # Auto-bootstrap cards for courses that have none yet
    for course in courses:
        if not course.sr_cards.filter(user=request.user).exists():
            bootstrap_cards_for_course(request.user, course)

    stats = get_review_stats(request.user)
    return render(request, 'ai_engine/review_queue.html', {
        'stats':   stats,
        'courses': courses,
    })


@login_required
@require_POST
def api_review_complete(request):
    """Mark a review card as completed (called after quiz from review queue)."""
    try:
        from .services.spaced_repetition import record_quiz_attempt
        data       = json.loads(request.body)
        course     = get_object_or_404(Course, pk=data.get('course_id'), user=request.user)
        topic      = data.get('topic', '')
        score      = float(data.get('score_percent', 0))
        card       = record_quiz_attempt(request.user, course, topic, score)
        return JsonResponse({
            'success':          True,
            'next_review':      str(card.next_review_date),
            'interval_days':    card.interval_days,
            'easiness_factor':  card.easiness_factor,
        })
    except Exception as e:
        logger.error(f"SR Review Complete Error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ═══════════════════════════════════════════
#  FEATURE 4: Cognitive Load Optimizer
# ═══════════════════════════════════════════

@login_required
@require_POST
def api_cognitive_update(request):
    """Called after each question answer during a quiz session."""
    try:
        data          = json.loads(request.body)
        is_correct    = bool(data.get('is_correct', False))
        time_taken    = int(data.get('time_taken_seconds', 30))
        difficulty    = data.get('difficulty', 'medium')
        session_state = request.session.get('cognitive_state', {
            'load': 0.5, 'streak_c': 0, 'streak_w': 0, 'events': []
        })

        new_state, recommendation = update_cognitive_load(
            session_state, is_correct, time_taken, difficulty
        )
        request.session['cognitive_state'] = new_state
        request.session.modified = True

        return JsonResponse({'success': True, 'recommendation': recommendation})
    except Exception as e:
        logger.error(f"Cognitive Update Error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def api_cognitive_summarize(request):
    """Called at end of quiz — persist session and return summary."""
    try:
        data          = json.loads(request.body)
        course        = get_object_or_404(Course, pk=data.get('course_id'), user=request.user)
        topic         = data.get('topic', '')
        session_state = request.session.pop('cognitive_state', {})
        summary       = summarize_session(session_state, request.user, course, topic)
        return JsonResponse({'success': True, 'summary': summary})
    except Exception as e:
        logger.error(f"Cognitive Summarize Error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ═══════════════════════════════════════════
#  FEATURE 5: Knowledge Graph
# ═══════════════════════════════════════════

@login_required
def knowledge_graph_view(request, course_id):
    course      = get_object_or_404(Course, pk=course_id, user=request.user)
    refresh     = request.GET.get('refresh') == '1'
    graph_data  = build_knowledge_graph(course, force_refresh=refresh)
    attempts    = QuizAttempt.objects.filter(user=request.user, course=course)
    topic_stats = {}
    for a in attempts:
        topic_stats.setdefault(a.topic, []).append(a.score_percent)
    topic_avg   = {t: round(sum(v)/len(v), 1) for t, v in topic_stats.items()}

    return render(request, 'ai_engine/knowledge_graph.html', {
        'course':     course,
        'graph_json': json.dumps(graph_data),
        'graph_dict': graph_data,
        'topic_avg':  topic_avg,
        'node_count': len(graph_data.get('nodes', [])),
        'edge_count': len(graph_data.get('edges', [])),
    })


@login_required
@require_POST
def api_build_graph(request):
    try:
        data       = json.loads(request.body)
        course     = get_object_or_404(Course, pk=data.get('course_id'), user=request.user)
        graph_data = build_knowledge_graph(course, force_refresh=True)
        return JsonResponse({'success': True, 'graph': graph_data})
    except Exception as e:
        logger.error(f"Build Graph Error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ═══════════════════════════════════════════
#  FEATURE 6: Cross-Course Concept Linker
# ═══════════════════════════════════════════

@login_required
def concept_links_view(request):
    refresh  = request.GET.get('refresh') == '1'
    links    = find_concept_links(request.user, force_refresh=refresh)
    courses  = Course.objects.filter(user=request.user)
    return render(request, 'ai_engine/concept_links.html', {
        'links':        links,
        'courses':      courses,
        'links_json':   json.dumps(links),
        'has_links':    len(links) > 0,
    })


@login_required
@require_POST
def api_find_links(request):
    try:
        links = find_concept_links(request.user, force_refresh=True)
        return JsonResponse({'success': True, 'links': links})
    except Exception as e:
        logger.error(f"Find Links Error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)