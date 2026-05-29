from decimal import Decimal
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from datetime import timedelta
from features.models import (
    UserEngagementMetrics,
    ErrorAnalysisLog,
    KnowledgeGraphMetrics,
    SpacedRepetitionLog
)

class SystemMetricsAggregator:
    """
    Phase 3: System-Level Metrics and Feedback Loops
    Calculates macro metrics for the Patent Admin Dashboard.
    """
    
    @staticmethod
    def calculate_learning_velocity(user_id: int, days: int = 7) -> float:
        """
        Velocity = Rate of Concepts moving from RED/YELLOW to GREEN per week.
        """
        cutoff = timezone.now() - timedelta(days=days)
        
        # Simplified for patent spec: Assuming all GREEN nodes updated in last N days
        recently_mastered = KnowledgeGraphMetrics.objects.filter(
            user_id=user_id,
            node_color='GREEN',
            last_mastery_update__gte=cutoff
        ).count()
        
        # Return velocity as concepts per week
        if days == 0: return 0.0
        return round((recently_mastered / days) * 7, 2)
        
    @staticmethod
    def calculate_platform_efficiency() -> dict:
        """
        Platform Efficiency = Errors caught by Heuristic (free) vs Sent to LLM (paid).
        """
        total_errors = ErrorAnalysisLog.objects.count()
        if total_errors == 0:
            return {'heuristic_rate': 0, 'llm_rate': 0, 'cost_saved_usd': 0}
            
        llm_errors = ErrorAnalysisLog.objects.filter(was_sent_to_llm=True).count()
        heuristic_errors = total_errors - llm_errors
        
        # Calculate simulated cost saved
        # Average simulated cost per LLM call was roughly $0.00002625
        avg_cost_per_call = Decimal('0.00002625')
        cost_saved = Decimal(heuristic_errors) * avg_cost_per_call
        
        return {
            'heuristic_rate': round((heuristic_errors / total_errors) * 100, 1),
            'llm_rate': round((llm_errors / total_errors) * 100, 1),
            'cost_saved_usd': round(float(cost_saved), 4)
        }
        
    @staticmethod
    def calculate_time_to_exam_readiness(user_id: int) -> float:
        """
        Predicts weeks until 80%+ mastery across all topics.
        """
        velocity = SystemMetricsAggregator.calculate_learning_velocity(user_id, 30)
        
        unmastered_concepts = KnowledgeGraphMetrics.objects.filter(
            user_id=user_id
        ).exclude(node_color='GREEN').count()
        
        if velocity <= 0:
            return 99.9 # Cannot predict
            
        weeks_remaining = unmastered_concepts / velocity
        return round(weeks_remaining, 1)

    @classmethod
    def get_dashboard_summary(cls, user_id: int) -> dict:
        return {
            'velocity': cls.calculate_learning_velocity(user_id),
            'efficiency': cls.calculate_platform_efficiency(),
            'exam_readiness_weeks': cls.calculate_time_to_exam_readiness(user_id)
        }
