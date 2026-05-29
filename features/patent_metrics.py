import logging
from decimal import Decimal
from django.db.models import Sum, Avg, Count, F, Q
from features.models import ErrorAnalysisLog
from quizzes.models import QuizAttempt, Question
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

def log_error_analysis(
    user,
    session,
    question,
    user_response: str,
    correct_response: str,
    response_time_ms: int,
    accuracy_on_topic_percent: int,
    session_duration_minutes: float,
    consecutive_errors: int,
    heuristic_rule_matched: str,
    heuristic_confidence: float,
    heuristic_category: str,
    was_sent_to_llm: bool,
    llm_category: str = None,
    gemini_explanation: str = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    api_cost_usd: float = 0.0,
    total_latency_ms: int = 0
) -> ErrorAnalysisLog:
    """
    Reusable logging function to record a single error analysis event for patent metrics.
    """
    try:
        log = ErrorAnalysisLog.objects.create(
            user=user,
            session=session,
            question=question,
            error_type='incorrect_answer',
            user_response=user_response,
            correct_response=correct_response,
            response_time_ms=response_time_ms,
            accuracy_on_topic_percent=accuracy_on_topic_percent,
            session_duration_minutes=Decimal(str(session_duration_minutes)),
            consecutive_errors=consecutive_errors,
            heuristic_rule_matched=heuristic_rule_matched,
            heuristic_confidence=heuristic_confidence,
            heuristic_category=heuristic_category,
            was_sent_to_llm=was_sent_to_llm,
            llm_category=llm_category,
            gemini_explanation=gemini_explanation,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            api_cost_usd=Decimal(str(api_cost_usd)) if api_cost_usd else Decimal("0.0"),
            total_latency_ms=total_latency_ms
        )
        return log
    except Exception as e:
        logger.error(f"Failed to log error analysis: {e}", exc_info=True)
        return None

def generate_patent_summary() -> str:
    """
    Generates a dynamically formatted paragraph summarizing the system's token optimization 
    and API cost reduction metrics, suitable for direct inclusion in a patent document.
    """
    total_errors = ErrorAnalysisLog.objects.count()
    if total_errors == 0:
        return "No error analysis data available to generate patent summary."

    heuristic_resolved = ErrorAnalysisLog.objects.filter(was_sent_to_llm=False).count()
    llm_invocations = ErrorAnalysisLog.objects.filter(was_sent_to_llm=True).count()
    
    heuristic_rate = (heuristic_resolved / total_errors) * 100
    
    total_prompt_tokens = ErrorAnalysisLog.objects.aggregate(total=Sum('prompt_tokens'))['total'] or 0
    total_completion_tokens = ErrorAnalysisLog.objects.aggregate(total=Sum('completion_tokens'))['total'] or 0
    actual_tokens_used = total_prompt_tokens + total_completion_tokens
    
    # Baseline assumes ALL errors were sent to LLM using the average token usage of the ones that were sent
    llm_logs = ErrorAnalysisLog.objects.filter(was_sent_to_llm=True)
    if llm_logs.exists():
        avg_prompt = llm_logs.aggregate(avg=Avg('prompt_tokens'))['avg'] or 0
        avg_completion = llm_logs.aggregate(avg=Avg('completion_tokens'))['avg'] or 0
        avg_cost = llm_logs.aggregate(avg=Avg('api_cost_usd'))['avg'] or Decimal('0.0')
    else:
        # Fallback to defaults used in llm_stage.py
        avg_prompt = 150
        avg_completion = 50
        COST_PER_PROMPT_TOKEN = Decimal('0.000000075')
        COST_PER_COMPLETION_TOKEN = Decimal('0.0000003')
        avg_cost = (Decimal(str(avg_prompt)) * COST_PER_PROMPT_TOKEN) + (Decimal(str(avg_completion)) * COST_PER_COMPLETION_TOKEN)

    baseline_tokens = total_errors * (avg_prompt + avg_completion)
    token_savings_pct = ((baseline_tokens - actual_tokens_used) / baseline_tokens * 100) if baseline_tokens > 0 else 0

    actual_api_cost = ErrorAnalysisLog.objects.aggregate(total=Sum('api_cost_usd'))['total'] or Decimal('0.0')
    baseline_api_cost = Decimal(str(total_errors)) * avg_cost
    api_cost_reduction_pct = ((baseline_api_cost - actual_api_cost) / baseline_api_cost * 100) if baseline_api_cost > 0 else Decimal('0.0')

    heuristic_latency = ErrorAnalysisLog.objects.filter(was_sent_to_llm=False).aggregate(avg=Avg('total_latency_ms'))['avg'] or 0
    llm_latency = ErrorAnalysisLog.objects.filter(was_sent_to_llm=True).aggregate(avg=Avg('total_latency_ms'))['avg'] or 0
    
    if llm_latency > 0:
        response_time_reduction = ((llm_latency - heuristic_latency) / llm_latency) * 100
    else:
        response_time_reduction = 0

    return (
        f"The claimed hybrid intelligent tutoring system successfully processed {total_errors} "
        f"student errors. The localized rule-based heuristic gate successfully resolved {heuristic_resolved} "
        f"errors without requiring external language model invocation, achieving a heuristic resolution "
        f"rate of {heuristic_rate:.1f}%. This architecture restricted LLM invocations to only {llm_invocations} "
        f"edge cases. As a result of this dynamic routing, the system consumed a total of {actual_tokens_used} "
        f"tokens ({total_prompt_tokens} prompt, {total_completion_tokens} completion) compared to a baseline of "
        f"{baseline_tokens} tokens if a standard uniform LLM architecture had been used, resulting in a token "
        f"savings of {token_savings_pct:.1f}%. Consequently, the total computational API cost was reduced by "
        f"{api_cost_reduction_pct:.1f}% (Actual: ${actual_api_cost:.6f} vs Baseline: ${baseline_api_cost:.6f}). "
        f"Furthermore, the heuristic gate executed with an average latency of {heuristic_latency:.0f}ms compared to "
        f"the LLM average latency of {llm_latency:.0f}ms, yielding a response time reduction of {response_time_reduction:.1f}% "
        f"for locally resolved interactions, thereby demonstrating the efficacy of the adaptive cognitive load management."
    )
