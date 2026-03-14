import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from courses.models import Course
from ai_engine.services.question_generator import generate_questions
from .models import Question, QuizAttempt

@login_required
def quiz_setup(request, course_id):
    course = get_object_or_404(Course, pk=course_id, user=request.user)
    topics = course.get_topics_list()
    recent = QuizAttempt.objects.filter(
        user=request.user, course=course
    ).order_by('-created_at')[:5]
    return render(request, 'quizzes/quiz_setup.html', {
        'course': course,
        'topics': topics,
        'recent': recent,
    })

@login_required
def quiz_attempt(request, course_id):
    course = get_object_or_404(Course, pk=course_id, user=request.user)
    topics = course.get_topics_list()
    
    topic = request.GET.get('topic', topics[0] if topics else 'General')
    difficulty = request.GET.get('difficulty', 'medium')
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
            # FIX: Ensure field names match your question_generator.py schema
            correct_val = q.get('correct_answer', '') # Changed from 'answer' to 'correct_answer'
            
            if len(options) >= 4:
                obj = Question.objects.create(
                    course=course,
                    topic=topic,
                    question_text=q.get('question', 'No question text'),
                    option_a=options[0],
                    option_b=options[1],
                    option_c=options[2],
                    option_d=options[3],
                    correct_answer=correct_val,
                    explanation=q.get('explanation', ''),
                    difficulty=difficulty,
                )
                question_list.append({
                    'id': obj.id,
                    'question': obj.question_text,
                    'options': [obj.option_a, obj.option_b, obj.option_c, obj.option_d],
                    'correct': obj.correct_answer,
                    'explanation': obj.explanation,
                })

    if not question_list:
        messages.error(request, 'Failed to generate quiz questions. Please check your API quota.')
        return redirect('quizzes:setup', course_id=course_id)

    return render(request, 'quizzes/quiz_attempt.html', {
        'course': course,
        'topic': topic,
        'difficulty': difficulty,
        'questions_json': json.dumps(question_list),
        'total': len(question_list),
    })

@login_required
@require_POST
def quiz_submit(request):
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        topic = data.get('topic', '')
        answers = data.get('answers', {})
        time_taken = data.get('time_taken', 0)

        course = get_object_or_404(Course, pk=course_id, user=request.user)

        correct = 0
        total = len(answers)
        results = []

        for qid, selected in answers.items():
            try:
                q = Question.objects.get(pk=int(qid))
                
                # RECTIFIED: More flexible comparison (case-insensitive and trimmed)
                user_ans = str(selected).strip().lower()
                correct_ans = str(q.correct_answer).strip().lower()
                
                is_correct = user_ans == correct_ans
                
                if is_correct:
                    correct += 1
                
                results.append({
                    'question': q.question_text,
                    'selected': selected,
                    'correct': q.correct_answer,
                    'explanation': q.explanation,
                    'is_correct': is_correct,
                })
            except (Question.DoesNotExist, ValueError):
                continue

        score_percent = round((correct / total) * 100, 1) if total > 0 else 0

        attempt = QuizAttempt.objects.create(
            user=request.user,
            course=course,
            topic=topic,
            total_questions=total,
            correct_answers=correct,
            score_percent=score_percent,
            time_taken_seconds=time_taken,
        )

        return JsonResponse({
            'success': True,
            'score': score_percent,
            'correct': correct,
            'total': total,
            'results': results,
            'attempt_id': attempt.id,
        })
    except Exception as e:
        # Added print for terminal debugging
        print(f"Error in quiz_submit: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def quiz_history(request, course_id):
    course = get_object_or_404(Course, pk=course_id, user=request.user)
    attempts = QuizAttempt.objects.filter(
        user=request.user, course=course
    ).order_by('-created_at')
    
    avg = 0
    if attempts.exists():
        avg = round(sum(a.score_percent for a in attempts) / attempts.count(), 1)
        
    return render(request, 'quizzes/quiz_history.html', {
        'course': course,
        'attempts': attempts,
        'avg': avg,
    })