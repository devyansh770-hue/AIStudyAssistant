from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

class HeuristicGate:
    """
    Stage 1 of error analysis: classify errors without calling Gemini.
    Target: 70-85% of errors resolved here, only 15-30% need LLM.
    """
    
    CONFIDENCE_GATE_THRESHOLD = 0.75  # If max_confidence > 0.75, use heuristic
    
    TIME_PRESSURE_RULE_CONFIDENCE = 0.82
    TIME_PRESSURE_RESPONSE_THRESHOLD_MS = 2000
    TIME_PRESSURE_ACCURACY_THRESHOLD = 0.40
    
    COGNITIVE_OVERLOAD_RULE_CONFIDENCE = 0.78
    COGNITIVE_OVERLOAD_SESSION_MINUTES = 40
    COGNITIVE_OVERLOAD_ERROR_THRESHOLD = 2
    
    CONCEPTUAL_CONFUSION_RULE_CONFIDENCE = 0.88
    CONCEPTUAL_CONFUSION_ENTROPY_THRESHOLD = 0.65
    
    @staticmethod
    def rule_1_time_pressure_detection(
        response_time_ms: int,
        accuracy_on_topic_last_10: float
    ) -> tuple:
        time_pressed = response_time_ms < HeuristicGate.TIME_PRESSURE_RESPONSE_THRESHOLD_MS
        low_accuracy = accuracy_on_topic_last_10 < HeuristicGate.TIME_PRESSURE_ACCURACY_THRESHOLD
        
        if time_pressed and low_accuracy:
            return "Time-Pressure Fatigue", HeuristicGate.TIME_PRESSURE_RULE_CONFIDENCE
        else:
            return None, 0.0
    
    @staticmethod
    def rule_2_cognitive_overload_detection(
        session_duration_minutes: float,
        consecutive_errors: int,
        response_time_trend: str
    ) -> tuple:
        long_session = session_duration_minutes > HeuristicGate.COGNITIVE_OVERLOAD_SESSION_MINUTES
        many_errors = consecutive_errors > HeuristicGate.COGNITIVE_OVERLOAD_ERROR_THRESHOLD
        slowing_down = response_time_trend == "increasing"
        
        if long_session and many_errors and slowing_down:
            return "Cognitive Overload", HeuristicGate.COGNITIVE_OVERLOAD_RULE_CONFIDENCE
        else:
            return None, 0.0
    
    @staticmethod
    def rule_3_conceptual_confusion_detection(
        error_pattern_entropy: float,
        concept_id: int,
        user_id: int,
        recent_errors_on_concept: int,
        prerequisite_gap_correlation: float
    ) -> tuple:
        high_entropy = error_pattern_entropy > HeuristicGate.CONCEPTUAL_CONFUSION_ENTROPY_THRESHOLD
        repeated = recent_errors_on_concept > 1
        gap_correlation = prerequisite_gap_correlation > 0.70
        
        if high_entropy and repeated and gap_correlation:
            return "Conceptual Confusion", HeuristicGate.CONCEPTUAL_CONFUSION_RULE_CONFIDENCE
        else:
            return None, 0.0
    
    @staticmethod
    def apply_heuristic_gate(
        user_id: int,
        concept_id: int,
        error_data: dict
    ) -> dict:
        cat_1, conf_1 = HeuristicGate.rule_1_time_pressure_detection(
            error_data.get('response_time_ms', 3000),
            error_data.get('accuracy_on_topic_last_10', 0.5)
        )
        
        cat_2, conf_2 = HeuristicGate.rule_2_cognitive_overload_detection(
            error_data.get('session_duration_minutes', 0),
            error_data.get('consecutive_errors', 0),
            error_data.get('response_time_trend', 'stable')
        )
        
        cat_3, conf_3 = HeuristicGate.rule_3_conceptual_confusion_detection(
            error_data.get('error_pattern_entropy', 0),
            concept_id,
            user_id,
            error_data.get('recent_errors_on_concept', 0),
            error_data.get('prerequisite_gap_correlation', 0)
        )
        
        results = [
            (cat_1, conf_1, "Time-Pressure Fatigue"),
            (cat_2, conf_2, "Cognitive Overload"),
            (cat_3, conf_3, "Conceptual Confusion")
        ]
        
        valid_results = [(cat, conf, rule) for cat, conf, rule in results if cat is not None]
        
        if not valid_results:
            return {
                'category': None,
                'confidence': 0.0,
                'rule_matched': None,
                'should_send_to_llm': True
            }
        
        best_result = max(valid_results, key=lambda x: x[1])
        category, max_confidence, rule_name = best_result
        
        should_use_llm = max_confidence <= HeuristicGate.CONFIDENCE_GATE_THRESHOLD
        
        return {
            'category': category if not should_use_llm else None,
            'confidence': max_confidence,
            'rule_matched': rule_name if not should_use_llm else None,
            'should_send_to_llm': should_use_llm,
            'all_rule_results': {
                'time_pressure': (cat_1, conf_1),
                'cognitive_overload': (cat_2, conf_2),
                'conceptual_confusion': (cat_3, conf_3)
            }
        }
