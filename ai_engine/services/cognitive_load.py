"""
Feature 4: Adaptive Cognitive Load Optimizer
Tracks per-question load in real-time during a quiz session and
recommends difficulty adjustments. Called via AJAX from the quiz page.
"""
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
ZONE_TOO_EASY  = (0.0, 0.3)
ZONE_FLOW      = (0.3, 0.7)
ZONE_OVERLOAD  = (0.7, 1.0)

CORRECT_BOOST  = 0.07
WRONG_PENALTY  = 0.12
FAST_BONUS     = 0.03   # answered in < 15s correctly
SLOW_PENALTY   = 0.02   # correct but took > 120s (possible confusion)


# ─────────────────────────────────────────────
# Load Calculator
# ─────────────────────────────────────────────

def update_cognitive_load(session_state, is_correct, time_taken_seconds, question_difficulty='medium'):
    """
    Updates the running cognitive load for a session.

    session_state: dict  { load: float, streak_c: int, streak_w: int, events: list }
    Returns updated session_state + recommendation dict.
    """
    load        = session_state.get('load', 0.5)
    streak_c    = session_state.get('streak_c', 0)
    streak_w    = session_state.get('streak_w', 0)
    events      = session_state.get('events', [])

    # Difficulty multiplier
    diff_mult   = {'easy': 0.7, 'medium': 1.0, 'hard': 1.4}.get(question_difficulty, 1.0)

    if is_correct:
        delta     = CORRECT_BOOST * diff_mult
        # Fast correct answer → student confident
        if 0 < time_taken_seconds < 15:
            delta += FAST_BONUS
        # Very slow correct answer → possible struggle
        elif time_taken_seconds > 120:
            delta -= SLOW_PENALTY

        load      = min(1.0, load + delta)
        streak_c += 1
        streak_w  = 0
    else:
        delta     = WRONG_PENALTY * diff_mult
        load      = max(0.0, load - delta)
        streak_w += 1
        streak_c  = 0

    zone = _get_zone(load)

    events.append({
        'load':        round(load, 3),
        'correct':     is_correct,
        'time_s':      time_taken_seconds,
        'difficulty':  question_difficulty,
        'zone':        zone,
    })

    session_state.update({
        'load':     round(load, 3),
        'streak_c': streak_c,
        'streak_w': streak_w,
        'events':   events,
    })

    recommendation = _recommend(load, streak_c, streak_w, zone)
    return session_state, recommendation


def _get_zone(load):
    if load <= ZONE_TOO_EASY[1]:
        return 'too_easy'
    elif load <= ZONE_FLOW[1]:
        return 'flow'
    else:
        return 'overload'


def _recommend(load, streak_c, streak_w, zone):
    """Returns a recommendation dict for the frontend."""
    if zone == 'too_easy':
        msg   = "You're breezing through this! Try harder questions to challenge yourself. 🚀"
        color = '#10b981'
        action = 'increase_difficulty'
    elif zone == 'flow':
        msg   = "You're in the Flow Zone! Perfect learning pace. 🔥 Keep going!"
        color = '#6366f1'
        action = 'maintain'
    else:  # overload
        msg   = "Feeling overloaded? Take a 2-minute break before the next question. 😤"
        color = '#f43f5e'
        action = 'take_break' if streak_w >= 3 else 'slow_down'

    return {
        'zone':     zone,
        'load':     round(load, 3),
        'load_pct': round(load * 100),
        'message':  msg,
        'color':    color,
        'action':   action,
        'streak_c': streak_c,
        'streak_w': streak_w,
    }


# ─────────────────────────────────────────────
# Session Summary
# ─────────────────────────────────────────────

def summarize_session(session_state, user, course, topic=''):
    """
    Persists the session to CognitiveLoadSession model and
    returns a summary dict for the post-quiz page.
    """
    from ai_engine.models import CognitiveLoadSession

    events = session_state.get('events', [])
    if not events:
        return {}

    loads    = [e['load'] for e in events]
    avg_load = sum(loads) / len(loads)
    in_flow  = sum(1 for e in events if e['zone'] == 'flow')
    flow_pct = (in_flow / len(events)) * 100

    CognitiveLoadSession.objects.create(
        user=user,
        course=course,
        topic=topic,
        session_data=events,
        avg_cognitive_load=round(avg_load, 3),
        flow_zone_percent=round(flow_pct, 1),
    )

    return {
        'avg_load':    round(avg_load * 100),
        'flow_pct':    round(flow_pct, 1),
        'zone_label':  _get_zone(avg_load),
        'peak_load':   round(max(loads) * 100),
        'min_load':    round(min(loads) * 100),
        'total_events': len(events),
    }


def get_user_load_history(user, course=None, limit=10):
    """Returns recent cognitive load sessions for a user."""
    from ai_engine.models import CognitiveLoadSession
    qs = CognitiveLoadSession.objects.filter(user=user)
    if course:
        qs = qs.filter(course=course)
    return qs[:limit]
