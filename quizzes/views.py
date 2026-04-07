import json
import random
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from courses.models import Course
from ai_engine.services.question_generator import generate_questions
from .models import Question, QuizAttempt, SurpriseTest

logger = logging.getLogger(__name__)


@login_required
def quiz_setup(request, course_id):
    course = get_object_or_404(Course, pk=course_id, user=request.user)
    topics = course.get_topics_list()
    recent = QuizAttempt.objects.filter(user=request.user, course=course).order_by('-created_at')[:5]
    return render(request, 'quizzes/quiz_setup.html', {
        'course': course, 'topics': topics, 'recent': recent,
    })


@login_required
def quiz_attempt(request, course_id):
    course = get_object_or_404(Course, pk=course_id, user=request.user)
    topics = course.get_topics_list()
    topic = request.GET.get('topic', topics[0] if topics else 'General')
    difficulty = request.GET.get('difficulty', 'medium')
    is_surprise = request.GET.get('surprise', '0') == '1'
    try:
        count = min(int(request.GET.get('count', 5)), 20)
    except (ValueError, TypeError):
        count = 5

    raw_data = generate_questions(topic, course.name, difficulty, count)

    if isinstance(raw_data, str):
        try:
            raw_questions = json.loads(raw_data)
        except json.JSONDecodeError:
            raw_questions = []
    else:
        raw_questions = raw_data

    question_list = []
    if isinstance(raw_questions, list):
        for q in raw_questions:
            if not isinstance(q, dict):
                continue
            options = q.get('options', [])
            correct_val = q.get('correct_answer', '')
            if len(options) >= 4:
                obj = Question.objects.create(
                    course=course, topic=topic,
                    question_text=q.get('question', 'No question text'),
                    option_a=options[0], option_b=options[1],
                    option_c=options[2], option_d=options[3],
                    correct_answer=correct_val,
                    explanation=q.get('explanation', ''),
                    difficulty=difficulty,
                )
                question_list.append({
                    'id': obj.id, 'question': obj.question_text,
                    'options': [obj.option_a, obj.option_b, obj.option_c, obj.option_d],
                    'correct': obj.correct_answer, 'explanation': obj.explanation,
                })

    if not question_list:
        messages.error(request, 'Failed to generate quiz questions. Please check your API quota.')
        return redirect('quizzes:setup', course_id=course_id)

    return render(request, 'quizzes/quiz_attempt.html', {
        'course': course, 'topic': topic, 'difficulty': difficulty,
        'questions_json': json.dumps(question_list),
        'total': len(question_list),
        'is_surprise': is_surprise,
    })


@login_required
@require_POST
def quiz_submit(request):
    try:
        data = json.loads(request.body)
        course_id   = data.get('course_id')
        topic       = data.get('topic', '')
        answers     = data.get('answers', {})
        time_taken  = data.get('time_taken', 0)
        is_surprise = data.get('is_surprise', False)

        course = get_object_or_404(Course, pk=course_id, user=request.user)

        correct = 0
        total   = len(answers)
        results = []

        for qid, selected in answers.items():
            try:
                q = Question.objects.get(pk=int(qid))
                is_correct = str(selected).strip().lower() == str(q.correct_answer).strip().lower()
                if is_correct:
                    correct += 1
                results.append({
                    'question': q.question_text, 'selected': selected,
                    'correct': q.correct_answer, 'explanation': q.explanation,
                    'is_correct': is_correct,
                })
            except (Question.DoesNotExist, ValueError):
                continue

        score_percent = round((correct / total) * 100, 1) if total > 0 else 0

        attempt = QuizAttempt.objects.create(
            user=request.user, course=course, topic=topic,
            total_questions=total, correct_answers=correct,
            score_percent=score_percent, time_taken_seconds=time_taken,
            is_surprise=is_surprise,
            results_data=results,
        )

        # ── Auto-update Spaced Repetition card ──
        try:
            from ai_engine.services.spaced_repetition import record_quiz_attempt as sr_update
            sr_update(request.user, course, topic, score_percent)
        except Exception as sr_err:
            logger.warning(f"SR update skipped: {sr_err}")

        # Link attempt to the open surprise test if it exists
        if is_surprise:
            st = SurpriseTest.objects.filter(
                user=request.user, course=course, attempt__isnull=True, dismissed=False
            ).order_by('-triggered_at').first()
            if st:
                st.attempt = attempt
                st.save()

        label, level = attempt.confidence_label()
        return JsonResponse({
            'success': True, 'score': score_percent,
            'correct': correct, 'total': total,
            'results': results, 'attempt_id': attempt.id,
            'is_surprise': is_surprise,
            'confidence_label': label, 'confidence_level': level,
        })
    except Exception as e:
        logger.error(f"Error in quiz_submit: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def quiz_detail(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user)
    return render(request, 'quizzes/quiz_detail.html', {
        'attempt': attempt,
        'results': attempt.results_data or [],
    })


@login_required
def quiz_history(request, course_id):
    course = get_object_or_404(Course, pk=course_id, user=request.user)
    attempts = QuizAttempt.objects.filter(user=request.user, course=course).order_by('-created_at')
    avg = 0
    if attempts.exists():
        avg = round(sum(a.score_percent for a in attempts) / attempts.count(), 1)
    return render(request, 'quizzes/quiz_history.html', {
        'course': course, 'attempts': attempts, 'avg': avg,
    })


@login_required
@require_POST
def dismiss_surprise(request):
    """Dismiss a surprise test without taking it."""
    st_id = request.POST.get('st_id')
    if st_id:
        SurpriseTest.objects.filter(pk=st_id, user=request.user).update(dismissed=True)
    return redirect('dashboard:home')