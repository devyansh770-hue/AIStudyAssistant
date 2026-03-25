import json
import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from courses.models import Course
from .services.question_generator import generate_questions
from .services.schedule_advisor import generate_schedule
from .services.tutor_chat import ask_tutor

logger = logging.getLogger(__name__)

@login_required
def view_schedule(request, course_id):
    course = get_object_or_404(Course, pk=course_id, user=request.user)
    days_left = course.days_until_exam()
    is_exam_over = days_left < 0
    
    # Load cached schedule if it exists
    schedule = course.ai_schedule
    
    if request.method == 'POST':
        if not is_exam_over:
            # Generate new schedule and save it
            schedule = generate_schedule(
                course.name,
                course.topics,
                str(course.exam_date),
                max(days_left, 1),
                course.complexity,
                course.daily_study_hours
            )
            course.ai_schedule = schedule
            course.save()

    return render(request, 'ai_engine/schedule.html', {
        'course': course,
        'schedule': schedule,
        'is_exam_over': is_exam_over,
    })

@login_required
@require_POST
def api_generate_questions(request):
    try:
        data = json.loads(request.body)
        course = get_object_or_404(Course, pk=data.get('course_id'), user=request.user)
        
        questions = generate_questions(
            data.get('topic', ''), 
            course.name, 
            data.get('difficulty', 'medium'), 
            int(data.get('count', 5))
        )

        # Return questions as part of a dict; JsonResponse handles this well
        return JsonResponse({'success': True, 'questions': questions})
    except Exception as e:
        logger.error(f"Quiz Generation Error: {e}") # Log to terminal
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def generate_questions_view(request, course_id):
    course = get_object_or_404(Course, pk=course_id, user=request.user)
    topics = course.get_topics_list()
    return render(request, 'ai_engine/generate_questions.html', {
        'course': course, 
        'topics': topics
    })

@login_required
def tutor_chat_view(request, course_id):
    course = get_object_or_404(Course, pk=course_id, user=request.user)
    topics = course.get_topics_list()
    return render(request, 'ai_engine/chat.html', {
        'course': course,
        'topics': topics,
    })

@login_required
@require_POST
def api_tutor_chat(request):
    try:
        data = json.loads(request.body)
        question = data.get('question', '')
        course_id = data.get('course_id')
        topic = data.get('topic', 'General')
        # Ensure history is a list even if front-end sends nothing
        history = data.get('history') or []

        course = get_object_or_404(Course, pk=course_id, user=request.user)
        answer = ask_tutor(question, course.name, topic, history)

        return JsonResponse({'success': True, 'answer': answer})
    except Exception as e:
        logger.error(f"Tutor Chat Error: {e}") # Log to terminal
        return JsonResponse({'success': False, 'error': str(e)}, status=400)