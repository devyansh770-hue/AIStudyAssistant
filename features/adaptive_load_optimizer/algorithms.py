from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from features.models import UserEngagementMetrics

class AdaptiveLoadOptimizer:
    """
    Calculate real-time engagement metrics for each user interaction.
    Patent evidence: All calculations logged with exact constants.
    """
    
    # HARDCODED CONSTANTS - Document why these were chosen!
    RESPONSE_QUALITY_WEIGHT = 0.4
    INTERACTION_FREQ_WEIGHT = 0.3
    TIME_PRESSURE_WEIGHT = 0.3
    
    FATIGUE_DENOMINATOR = 45  # minutes - session duration threshold
    
    LOAD_ENGAGEMENT_MULTIPLIER = 0.07   # How much engagement affects load
    LOAD_FATIGUE_PENALTY = 0.12         # How much fatigue reduces load
    LOAD_ERROR_DECAY_BONUS = 0.15       # How much improvement helps load
    
    FLOW_ZONE_MIN = 0.70
    FLOW_ZONE_MAX = 0.80
    
    SESSION_BREAK_THRESHOLD = 45  # minutes
    LOW_ENGAGEMENT_BREAK = 0.3
    
    @staticmethod
    def calculate_response_quality(correct_answers: int, total_questions: int) -> float:
        """
        response_quality = correct_answers / total_questions
        Range: 0.0 to 1.0
        """
        if total_questions == 0:
            return 0.5  # neutral default
        return min(1.0, max(0.0, correct_answers / total_questions))
    
    @staticmethod
    def calculate_interaction_frequency(interaction_count: int, session_duration_minutes: float) -> float:
        """
        interaction_frequency = interactions / session_duration_minutes
        Normalized to 0.0-1.0 range
        """
        if session_duration_minutes == 0:
            return 0.5
        # Assume ~10 interactions/minute is maximum (1.0)
        freq = interaction_count / (session_duration_minutes * 10)
        return min(1.0, max(0.0, freq))
    
    @staticmethod
    def calculate_time_pressure(user_avg_response_time_ms: float, optimal_response_time_ms: float) -> float:
        """
        time_pressure = user_avg_response_time / optimal_response_time
        Range: 0.0 to 2.0+
        """
        if optimal_response_time_ms == 0:
            return 1.0
        pressure = user_avg_response_time_ms / optimal_response_time_ms
        return min(2.0, max(0.0, pressure))
    
    @classmethod
    def calculate_engagement_score(
        cls,
        response_quality: float,
        interaction_frequency: float,
        time_pressure: float
    ) -> float:
        raw_score = (
            (cls.RESPONSE_QUALITY_WEIGHT * response_quality) +
            (cls.INTERACTION_FREQ_WEIGHT * interaction_frequency) -
            (cls.TIME_PRESSURE_WEIGHT * time_pressure)
        )
        
        normalized_score = max(0.0, min(1.0, raw_score))
        return round(normalized_score, 4)
    
    @staticmethod
    def calculate_historical_error_rate(recent_questions: list) -> float:
        if not recent_questions or len(recent_questions) == 0:
            return 0.5
        
        errors = sum(1 for q in recent_questions if not q.get('is_correct', False))
        return errors / len(recent_questions)
    
    @classmethod
    def calculate_fatigue_factor(
        cls,
        session_duration_minutes: float,
        historical_error_rate: float
    ) -> float:
        time_factor = session_duration_minutes / cls.SESSION_BREAK_THRESHOLD
        return round(time_factor * historical_error_rate, 4)
    
    @staticmethod
    def calculate_error_decay(error_rates_last_5_sessions: list) -> float:
        if len(error_rates_last_5_sessions) < 2:
            return 0.0
        trend = error_rates_last_5_sessions[0] - error_rates_last_5_sessions[-1]
        return round(trend, 4)
    
    @classmethod
    def calculate_load_variable(
        cls,
        L_previous: float,
        engagement_score: float,
        fatigue_factor: float,
        error_decay: float
    ) -> float:
        change = (
            (cls.LOAD_ENGAGEMENT_MULTIPLIER * engagement_score) -
            (cls.LOAD_FATIGUE_PENALTY * fatigue_factor) +
            (cls.LOAD_ERROR_DECAY_BONUS * error_decay)
        )
        new_load = L_previous + change
        return round(max(0.0, min(2.0, new_load)), 4)
    
    @classmethod
    def is_in_flow_zone(cls, engagement_score: float) -> bool:
        return cls.FLOW_ZONE_MIN <= engagement_score <= cls.FLOW_ZONE_MAX
    
    @classmethod
    def get_difficulty_adjustment(cls, load_variable: float) -> str:
        if load_variable < 0.30:
            return "reduce"
        elif cls.FLOW_ZONE_MIN <= load_variable <= cls.FLOW_ZONE_MAX:
            return "maintain"
        elif load_variable > 0.85:
            return "increase"
        else:
            return "maintain"
    
    @classmethod
    def should_force_break(cls, session_duration_minutes: float, engagement_score: float) -> bool:
        if session_duration_minutes > cls.SESSION_BREAK_THRESHOLD:
            return True
        if engagement_score < cls.LOW_ENGAGEMENT_BREAK:
            return True
        return False


def process_user_interaction(user_id: int, interaction_data: dict) -> dict:
    try:
        session_id = interaction_data.get('session_id')
        is_correct = interaction_data.get('is_correct', False)
        response_time_ms = interaction_data.get('response_time_ms', 3000)
        session_duration_minutes = interaction_data.get('session_duration_minutes', 0)
        correct_answers = interaction_data.get('correct_answers_so_far', 0)
        total_questions = interaction_data.get('questions_attempted_so_far', 1)
        
        try:
            prev_metric = UserEngagementMetrics.objects.filter(
                user_id=user_id,
                session_id=session_id
            ).latest('timestamp')
            L_previous = prev_metric.load_variable_L or 0.5
        except:
            L_previous = 0.5
        
        response_quality = AdaptiveLoadOptimizer.calculate_response_quality(correct_answers, total_questions)
        interaction_frequency = AdaptiveLoadOptimizer.calculate_interaction_frequency(total_questions, max(session_duration_minutes, 0.1))
        time_pressure = AdaptiveLoadOptimizer.calculate_time_pressure(response_time_ms, 3000)
        engagement_score = AdaptiveLoadOptimizer.calculate_engagement_score(response_quality, interaction_frequency, time_pressure)
        
        error_rate = 1 - (correct_answers / max(total_questions, 1))
        fatigue_factor = AdaptiveLoadOptimizer.calculate_fatigue_factor(session_duration_minutes, error_rate)
        error_decay = AdaptiveLoadOptimizer.calculate_error_decay([error_rate])
        
        load_variable = AdaptiveLoadOptimizer.calculate_load_variable(L_previous, engagement_score, fatigue_factor, error_decay)
        is_in_flow = AdaptiveLoadOptimizer.is_in_flow_zone(engagement_score)
        difficulty_adj = AdaptiveLoadOptimizer.get_difficulty_adjustment(load_variable)
        should_break = AdaptiveLoadOptimizer.should_force_break(session_duration_minutes, engagement_score)
        
        metric = UserEngagementMetrics.objects.create(
            user_id=user_id,
            session_id=session_id,
            response_time_ms=response_time_ms,
            is_correct=is_correct,
            total_questions_in_session=total_questions,
            correct_answers_in_session=correct_answers,
            session_duration_minutes=Decimal(str(session_duration_minutes)),
            response_quality=Decimal(str(response_quality)),
            interaction_frequency=Decimal(str(interaction_frequency)),
            time_pressure=Decimal(str(time_pressure)),
            engagement_score=Decimal(str(engagement_score)),
            fatigue_factor=Decimal(str(fatigue_factor)),
            error_decay=Decimal(str(error_decay)),
            load_variable_L=Decimal(str(load_variable)),
            is_in_flow_zone=is_in_flow,
            difficulty_adjustment=difficulty_adj,
            break_recommended=should_break
        )
        
        return {
            'engagement_score': float(engagement_score),
            'load_variable': float(load_variable),
            'is_in_flow_zone': is_in_flow,
            'fatigue_factor': float(fatigue_factor),
            'difficulty_adjustment': difficulty_adj,
            'should_break': should_break,
            'metrics_logged': True,
            'metric_id': metric.id
        }
    except Exception as e:
        print(f"Error in process_user_interaction: {str(e)}")
        return {
            'error': str(e),
            'metrics_logged': False
        }
