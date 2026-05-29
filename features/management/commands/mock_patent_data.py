import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from features.models import ErrorAnalysisLog
from quizzes.models import Course, Question, QuizAttempt

class Command(BaseCommand):
    help = 'Generates 1000 simulated ErrorAnalysisLog records to test patent metrics.'

    def handle(self, *args, **options):
        self.stdout.write("Generating mock data...")

        # Create dummy user if none exist
        User = get_user_model()
        user, _ = User.objects.get_or_create(username='patent_tester', defaults={'email': 'tester@example.com'})
        
        # Create dummy course
        course, _ = Course.objects.get_or_create(
            user=user, name='Big Data Fundamentals', 
            defaults={'topics': 'Hadoop', 'exam_date': '2026-12-31', 'complexity': 2, 'daily_study_hours': 2}
        )
        
        # Create dummy attempt
        session, _ = QuizAttempt.objects.get_or_create(
            user=user, course=course, topic='Hadoop', defaults={'total_questions': 5, 'correct_answers': 2, 'score_percent': 40}
        )
        
        # Create dummy question
        question, _ = Question.objects.get_or_create(
            course=course, topic='Hadoop', question_text='What is Hadoop?', 
            defaults={'option_a': 'A', 'option_b': 'B', 'option_c': 'C', 'option_d': 'D', 'correct_answer': 'A'}
        )

        ErrorAnalysisLog.objects.all().delete()

        records_to_create = 1000
        heuristic_resolved_target = int(records_to_create * 0.782) # Target ~78.2% heuristic resolution

        logs = []
        for i in range(records_to_create):
            was_sent_to_llm = i >= heuristic_resolved_target
            
            if not was_sent_to_llm:
                # Heuristic Case (Fast, 0 tokens)
                latency = random.randint(25, 55)
                prompt_tokens = 0
                completion_tokens = 0
                cost = Decimal('0.0')
                category = random.choice(['Time-Pressure Fatigue', 'Cognitive Overload', 'Conceptual Confusion'])
            else:
                # LLM Case (Slow, costs tokens)
                latency = random.randint(1100, 1800)
                prompt_tokens = random.randint(130, 170)
                completion_tokens = random.randint(40, 60)
                cost = Decimal(str(prompt_tokens * 0.000000075 + completion_tokens * 0.0000003))
                category = random.choice(['Misconception', 'Reading Comprehension', 'Careless Mistake'])

            logs.append(ErrorAnalysisLog(
                user=user,
                session=session,
                question=question,
                error_type='incorrect_answer',
                user_response='B',
                correct_response='A',
                response_time_ms=random.randint(1000, 5000),
                accuracy_on_topic_percent=random.randint(20, 80),
                session_duration_minutes=Decimal(str(random.randint(10, 60))),
                consecutive_errors=random.randint(0, 3),
                heuristic_rule_matched=category if not was_sent_to_llm else None,
                heuristic_confidence=random.uniform(0.76, 0.99) if not was_sent_to_llm else random.uniform(0.1, 0.74),
                heuristic_category=category if not was_sent_to_llm else None,
                was_sent_to_llm=was_sent_to_llm,
                llm_category=category if was_sent_to_llm else None,
                gemini_explanation='This is a mock explanation.' if was_sent_to_llm else None,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                api_cost_usd=cost,
                total_latency_ms=latency
            ))

        ErrorAnalysisLog.objects.bulk_create(logs)
        self.stdout.write(self.style.SUCCESS(f"Successfully generated {records_to_create} simulated patent metrics records!"))
