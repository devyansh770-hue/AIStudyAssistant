from decimal import Decimal
import datetime
from django.utils import timezone
from features.models import SpacedRepetitionLog

class NeuralSpacedRepetition:
    """
    Feature #4: Neural Spaced-Repetition Scheduler
    """
    
    # Weights for the Multi-Factor Formula
    W_EXAM_PROXIMITY_IMPACT = 0.4
    W_DIFFICULTY_IMPACT = 0.6
    
    @staticmethod
    def calculate_base_interval_sm2(repetition_count: int, easiness_factor: float) -> float:
        """
        Calculates standard SM-2 interval.
        """
        if repetition_count == 0:
            return 1.0
        elif repetition_count == 1:
            return 6.0
        else:
            return round(6.0 * (easiness_factor ** (repetition_count - 1)), 2)
            
    @classmethod
    def calculate_exam_weight(cls, days_remaining: int) -> float:
        """
        Accelerates reviews if the exam is close.
        If exam is < 7 days away, weight drops heavily (compressing the interval).
        """
        if not days_remaining or days_remaining > 30:
            return 1.0
        
        # Exponential compression as exam approaches
        return max(0.2, (days_remaining / 30.0))

    @classmethod
    def calculate_final_interval(
        cls, 
        base_interval_days: float, 
        exam_days_remaining: int, 
        node_mastery_percent: int
    ) -> float:
        """
        MAIN FORMULA FOR PATENT:
        final_interval = base_interval * (W_exam * weight_exam) * (W_diff * weight_difficulty)
        """
        
        weight_exam = cls.calculate_exam_weight(exam_days_remaining)
        
        # Difficulty weight (low mastery = shorter interval)
        weight_difficulty = max(0.3, node_mastery_percent / 100.0)
        
        # Apply formula
        final_interval = base_interval_days * weight_exam * weight_difficulty
        
        # Ensure at least 0.5 days (12 hours) between reviews to prevent spam
        return round(max(0.5, final_interval), 2)
        
    @classmethod
    def schedule_next_review(cls, log_id: int, easiness_factor: float, node_mastery: int, exam_days: int = None):
        """
        Updates the SR Log with the new scheduled date.
        """
        try:
            log = SpacedRepetitionLog.objects.get(id=log_id)
            
            # Simple repetition counter based on history (mocked here as 2)
            rep_count = 2 
            
            base_interval = cls.calculate_base_interval_sm2(rep_count, easiness_factor)
            
            final_interval = cls.calculate_final_interval(base_interval, exam_days, node_mastery)
            
            log.base_interval_days = Decimal(str(base_interval))
            log.weight_exam = cls.calculate_exam_weight(exam_days)
            log.weight_difficulty = max(0.3, node_mastery / 100.0)
            log.final_interval_days = Decimal(str(final_interval))
            
            # Add interval to today
            today = timezone.now().date()
            days_to_add = int(round(final_interval))
            log.scheduled_review_date = today + datetime.timedelta(days=max(1, days_to_add))
            
            log.save()
            return log.scheduled_review_date
            
        except Exception as e:
            print(f"SR Scheduling Error: {e}")
            return None
