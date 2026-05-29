import json
import random
import logging
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from courses.models import Course
from ai_engine.services.question_generator import generate_questions
from .models import Question, QuizAttempt, SurpriseTest, QuizAnswer

from features.adaptive_load_optimizer.algorithms import process_user_interaction
from features.hybrid_nlp_analyzer.heuristic_gate import HeuristicGate
from features.hybrid_nlp_analyzer.llm_stage import process_llm_classification
from features.models import ErrorAnalysisLog, Concept

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

    # Create pending QuizAttempt for real-time tracking
    attempt = QuizAttempt.objects.create(
        user=request.user, course=course, topic=topic,
        total_questions=len(question_list), correct_answers=0,
        score_percent=0, time_taken_seconds=0,
        is_surprise=is_surprise, results_data=[]
    )

    return render(request, 'quizzes/quiz_attempt.html', {
        'course': course, 'topic': topic, 'difficulty': difficulty,
        'questions_json': json.dumps(question_list),
        'total': len(question_list),
        'is_surprise': is_surprise,
        'session_id': attempt.id,
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

@login_required
@require_POST
def submit_quiz_answer(request):
    """
    MODIFIED ENDPOINT - Integrates Features #1 & #2
    """
    try:
        data = json.loads(request.body)
        user = request.user
        user_id = user.id
        session_id = data.get('session_id')
        question_id = data.get('question_id')
        user_response = data.get('user_response')
        response_time_ms = data.get('response_time_ms', 3000)
        session_duration_minutes = data.get('session_duration_minutes', 0)
        
        quiz_session = get_object_or_404(QuizAttempt, id=session_id, user=user)
        question = get_object_or_404(Question, id=question_id)
        is_correct = (str(user_response).lower().strip() == str(question.correct_answer).lower().strip())
        
        answers_so_far = QuizAnswer.objects.filter(session=quiz_session)
        correct_so_far = answers_so_far.filter(is_correct=True).count()
        
        # ============ FEATURE #1: ADAPTIVE LOAD OPTIMIZER ============
        engagement_result = process_user_interaction(user_id, {
            'session_id': session_id,
            'question_id': question_id,
            'is_correct': is_correct,
            'response_time_ms': response_time_ms,
            'session_duration_minutes': session_duration_minutes,
            'questions_attempted_so_far': answers_so_far.count() + 1,
            'correct_answers_so_far': correct_so_far + (1 if is_correct else 0)
        })
        
        quiz_answer = QuizAnswer.objects.create(
            session=quiz_session,
            question=question,
            user_response=user_response,
            is_correct=is_correct,
            response_time_ms=response_time_ms,
            engagement_score=engagement_result.get('engagement_score'),
            load_variable=engagement_result.get('load_variable')
        )
        
        response_data = {
            'is_correct': is_correct,
            'correct_answer': question.correct_answer,
            'explanation': question.explanation,
            'engagement_score': engagement_result.get('engagement_score'),
            'in_flow_zone': engagement_result.get('is_in_flow_zone'),
            'difficulty_adjustment': engagement_result.get('difficulty_adjustment'),
            'should_break': engagement_result.get('should_break')
        }
        
        # ============ FEATURE #2: ERROR ANALYSIS ============
        if not is_correct:
            # We assume Concept mappings are handled outside in real implementation, but for the spec we fake concept_id
            fake_concept_id = 1
            error_data = {
                'response_time_ms': response_time_ms,
                'session_duration_minutes': session_duration_minutes,
                'accuracy_on_topic_last_10': calculate_accuracy_on_topic(user_id, question.topic, last_n=10),
                'consecutive_errors': count_consecutive_errors(user_id, session_id),
                'response_time_trend': analyze_response_time_trend(user_id, session_id),
                'error_pattern_entropy': calculate_error_entropy(user_id, fake_concept_id),
                'recent_errors_on_concept': count_recent_errors_on_concept(user_id, fake_concept_id),
                'prerequisite_gap_correlation': calculate_prerequisite_gap(user_id, fake_concept_id)
            }
            
            heuristic_result = HeuristicGate.apply_heuristic_gate(user_id, fake_concept_id, error_data)
            
            error_log = ErrorAnalysisLog.objects.create(
                user=user,
                session=quiz_session,
                question=question,
                error_type='incorrect_answer',
                user_response=user_response,
                correct_response=question.correct_answer,
                response_time_ms=response_time_ms,
                accuracy_on_topic_percent=int(error_data['accuracy_on_topic_last_10'] * 100),
                session_duration_minutes=Decimal(str(session_duration_minutes)),
                consecutive_errors=error_data['consecutive_errors'],
                heuristic_rule_matched=heuristic_result.get('rule_matched'),
                heuristic_confidence=heuristic_result.get('confidence'),
                heuristic_category=heuristic_result.get('category'),
                was_sent_to_llm=heuristic_result.get('should_send_to_llm')
            )
            
            if heuristic_result.get('should_send_to_llm'):
                llm_result = process_llm_classification(
                    question.question_text, user_response, question.correct_answer,
                    heuristic_result.get('category'), error_data
                )
                error_log.was_sent_to_llm = True
                error_log.llm_category = llm_result.get('category')
                error_log.gemini_explanation = llm_result.get('explanation')
                error_log.api_cost_usd = Decimal(str(llm_result.get('api_cost', 0)))
                error_log.total_latency_ms = llm_result.get('total_latency_ms')
                error_log.prompt_tokens = llm_result.get('prompt_tokens', 0)
                error_log.completion_tokens = llm_result.get('completion_tokens', 0)
                error_log.save()
                
                response_data['error_category'] = llm_result.get('category')
                response_data['explanation'] = llm_result.get('explanation')
                response_data['was_explained_by_llm'] = True
            else:
                response_data['error_category'] = heuristic_result.get('category')
                response_data['explanation'] = get_heuristic_explanation(heuristic_result.get('category'), question, error_data)
                response_data['was_explained_by_llm'] = False
            
            response_data['error_analysis'] = {
                'category': heuristic_result.get('category'),
                'confidence': heuristic_result.get('confidence'),
                'rule_matched': heuristic_result.get('rule_matched'),
                'sent_to_llm': heuristic_result.get('should_send_to_llm')
            }
        
        return JsonResponse(response_data)
    
    except Exception as e:
        logger.error(f"Error in submit_quiz_answer: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=400)


def calculate_accuracy_on_topic(user_id, topic, last_n=10):
    answers = QuizAnswer.objects.filter(session__user_id=user_id, question__topic=topic).order_by('-id')[:last_n]
    if not answers:
        return 0.5
    correct = answers.filter(is_correct=True).count()
    return correct / len(answers)

def count_consecutive_errors(user_id, session_id):
    answers = QuizAnswer.objects.filter(session__user_id=user_id, session_id=session_id).order_by('-id')
    count = 0
    for answer in answers:
        if not answer.is_correct:
            count += 1
        else:
            break
    return count

def analyze_response_time_trend(user_id, session_id):
    answers = QuizAnswer.objects.filter(session__user_id=user_id, session_id=session_id).order_by('id')[-5:]
    if len(answers) < 2:
        return 'stable'
    times = [a.response_time_ms for a in answers]
    trend = times[-1] - times[0]
    if trend > 500:
        return 'increasing'
    elif trend < -500:
        return 'decreasing'
    return 'stable'

def calculate_error_entropy(user_id, concept_id):
    return 0.5

def count_recent_errors_on_concept(user_id, concept_id):
    # Using 0 since Concept mappings are fully implemented in Phase 3
    return 0

def calculate_prerequisite_gap(user_id, concept_id):
    return 0.0

def get_heuristic_explanation(category, question, error_data):
    explanations = {
        'Time-Pressure Fatigue': f"It looks like you rushed this answer! Take your time. The correct answer is: {question.correct_answer}",
        'Cognitive Overload': f"You've been studying for a while - maybe take a break! The answer is: {question.correct_answer}",
        'Conceptual Confusion': f"This might indicate you're confused on a core concept. Review this topic. The answer is: {question.correct_answer}"
    }
    return explanations.get(category, question.explanation)