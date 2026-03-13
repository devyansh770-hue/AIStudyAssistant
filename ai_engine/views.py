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
    schedule = None # None means the "Generate" button will show
    
    if request.method == 'POST':
        days_left = course.days_until_exam()
        if days_left <= 0:
            days_left = 7
            
        # Get the schedule from our service
        result = generate_schedule(
            course.name,
            course.topics,
            str(course.exam_date),
            days_left,
            course.complexity,
            course.daily_study_hours
        )
        
        # Double check: if result is still a string (rare), parse it
        if isinstance(result, str):
            try:
                schedule = json.loads(result)
            except:
                schedule = []
        else:
            schedule = result

    return render(request, 'ai_engine/schedule.html', {
        'course': course,
        'schedule': schedule,
    })

# --- Other views remain the same, but here is the logic for Questions ---

@login_required
@require_POST
def api_generate_questions(request):
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        topic = data.get('topic', '')
        difficulty = data.get('difficulty', 'medium')
        count = int(data.get('count', 5))

        course = get_object_or_404(Course, pk=course_id, user=request.user)
        questions = generate_questions(topic, course.name, difficulty, count)

        return JsonResponse({'success': True, 'questions': questions})
    except Exception as e:
        logger.error(f"Question Generation Error: {e}")
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
        history = data.get('history', [])

        course = get_object_or_404(Course, pk=course_id, user=request.user)
        answer = ask_tutor(question, course.name, topic, history)

        return JsonResponse({'success': True, 'answer': answer})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)