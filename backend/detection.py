"""
Detection Layer — Sploink Agent Monitor

Loop Detection:
  Uses sliding-window pairwise similarity on (action_type, input_tokens).
  Jaccard similarity on token sets with action-type bonus.
  Threshold: avg similarity > 0.55 AND 3+ repetitions of same action type.
  Rationale: Pure string equality misses slight variations; 0.55 catches
  "the same thing with different args" without flagging legitimate file ops.

Drift Detection:
  Compares keyword distributions from first vs second half of session.
  Jaccard overlap < 0.20 on content tokens = drift.
  Also checks for dominant action type shift between halves.
  Rationale: 0.20 is conservative — normal tasks have some topic evolution,
  but genuine intent drift shows near-zero semantic overlap.

Failure Detection:
  Two signals: consecutive failures >= 3, OR failure rate > 60% over last 10.
  Rationale: 3 consecutive is a clear retry loop. 60% rate over 10 events
  provides statistical weight while catching non-consecutive failure bursts.
"""

import re
from typing import List, Dict, Tuple
from collections import Counter


STOPWORDS = {
    "the", "a", "an", "is", "in", "of", "to", "and", "or", "with",
    "for", "on", "at", "this", "that", "it", "be", "as", "by", "if",
    "do", "not", "are", "was", "has", "have", "but", "so", "up", "out",
}


def tokenize(text: str) -> set:
    if not text:
        return set()
    tokens = re.findall(r"\b\w+\b", text.lower())
    return {t for t in tokens if len(t) > 2 and t not in STOPWORDS}


def jaccard_similarity(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def event_similarity(e1: dict, e2: dict) -> float:
    """Weighted similarity: 40% action type match + 60% content overlap."""
    action_match = 1.0 if e1.get("action") == e2.get("action") else 0.0
    tokens_a = tokenize(e1.get("input", ""))
    tokens_b = tokenize(e2.get("input", ""))
    content_sim = jaccard_similarity(tokens_a, tokens_b)
    return 0.4 * action_match + 0.6 * content_sim


# ---------------------------------------------------------------------------
# Loop Detection
# ---------------------------------------------------------------------------

def detect_loop(events: List[dict]) -> Tuple[bool, str]:
    """
    Sliding window of last 8 events. Compute pairwise similarity for same-type
    action pairs. Flag if avg similarity > 0.55 AND most-repeated action >= 3x.
    """
    if len(events) < 4:
        return False, ""

    window = events[-8:]
    action_counts = Counter(e.get("action") for e in window)
    most_repeated_count = max(action_counts.values(), default=0)

    if most_repeated_count < 3:
        return False, ""

    same_type_sims = []
    for i in range(len(window)):
        for j in range(i + 1, len(window)):
            if window[i].get("action") == window[j].get("action"):
                sim = event_similarity(window[i], window[j])
                same_type_sims.append(sim)

    if not same_type_sims:
        return False, ""

    avg_sim = sum(same_type_sims) / len(same_type_sims)

    if avg_sim > 0.55:
        dominant = max(action_counts, key=action_counts.get)
        return (
            True,
            f"Loop detected: '{dominant}' repeated {most_repeated_count}× "
            f"with {avg_sim:.0%} avg similarity",
        )

    return False, ""


# ---------------------------------------------------------------------------
# Drift Detection
# ---------------------------------------------------------------------------

def detect_drift(events: List[dict]) -> Tuple[bool, str]:
    """
    Compare keyword distributions from first vs second half of session.
    Jaccard overlap < 0.20 on combined input+output tokens signals drift.
    Also reports action-type shift if dominant action changes between halves.
    """
    if len(events) < 6:
        return False, ""

    mid = len(events) // 2
    first_half = events[:mid]
    second_half = events[mid:]

    def extract_tokens(evts):
        tokens = set()
        for e in evts:
            tokens |= tokenize(e.get("input", "") + " " + e.get("output", ""))
        return tokens

    first_tokens = extract_tokens(first_half)
    second_tokens = extract_tokens(second_half)

    if len(first_tokens) < 4 or len(second_tokens) < 4:
        return False, ""

    overlap = jaccard_similarity(first_tokens, second_tokens)

    
    if overlap < 0.20:
        first_actions = Counter(e.get("action") for e in first_half)
        second_actions = Counter(e.get("action") for e in second_half)
        first_dom = max(first_actions, key=first_actions.get, default=None)
        second_dom = max(second_actions, key=second_actions.get, default=None)

        msg = f"Drift detected: topic overlap dropped to {overlap:.0%}"
        if first_dom != second_dom:
            msg += f" (activity shifted: '{first_dom}' → '{second_dom}')"
        return True, msg

    return False, ""


# ---------------------------------------------------------------------------
# Failure Detection
# ---------------------------------------------------------------------------

def detect_failure(events: List[dict]) -> Tuple[bool, str]:
    """
    Two signals:
    1. 3+ consecutive failures from the tail of the event list.
    2. >60% failure rate over the last 10 events (min 5 events required).
    """
    if not events:
        return False, ""

    # Signal 1: consecutive failures
    consecutive = 0
    for e in reversed(events):
        if e.get("metadata", {}).get("status") == "failure":
            consecutive += 1
        else:
            break

    if consecutive >= 3:
        return True, f"Failure mode: {consecutive} consecutive failures"

    # Signal 2: recent failure rate
    recent = events[-10:]
    if len(recent) < 5:
        return False, ""

    failures = sum(
        1 for e in recent if e.get("metadata", {}).get("status") == "failure"
    )
    rate = failures / len(recent)

    if rate > 0.60:
        return True, f"High failure rate: {rate:.0%} of last {len(recent)} events failed"

    return False, ""


# ---------------------------------------------------------------------------
# Session-level aggregation
# ---------------------------------------------------------------------------

def compute_session_status(events: List[dict]) -> Tuple[str, List[str]]:
    issues = []
    is_loop, loop_msg = detect_loop(events)
    is_drift, drift_msg = detect_drift(events)
    is_failing, fail_msg = detect_failure(events)

    if is_loop:
        issues.append(loop_msg)
    if is_drift:
        issues.append(drift_msg)
    if is_failing:
        issues.append(fail_msg)

    # Priority: failing > looping > drifting > healthy
    if is_failing:
        status = "failing"
    elif is_loop:
        status = "looping"
    elif is_drift:
        status = "drifting"
    else:
        status = "healthy"

    return status, issues


def compute_session_metrics(events: List[dict]) -> dict:
    total = len(events)
    successes = sum(
        1 for e in events if e.get("metadata", {}).get("status", "success") == "success"
    )
    failures = total - successes
    action_dist = Counter(e.get("action") for e in events if e.get("action"))
    return {
        "total_steps": total,
        "success_count": successes,
        "failure_count": failures,
        "action_distribution": dict(action_dist),
        "success_rate": successes / total if total > 0 else 0.0,
    }


def generate_insights(events: List[dict], status: str, issues: List[str]) -> List[str]:
    if not events:
        return ["No events recorded yet."]

    insights = []
    metrics = compute_session_metrics(events)
    action_dist = metrics["action_distribution"]

    if action_dist:
        top = max(action_dist, key=action_dist.get)
        pct = action_dist[top] / metrics["total_steps"] * 100
        insights.append(f"Most frequent action: '{top}' ({pct:.0f}% of steps)")

    rate = metrics["success_rate"]
    if rate < 0.50:
        insights.append(
            f"Low success rate ({rate:.0%}) — agent may be stuck or misconfigured"
        )
    elif rate > 0.90:
        insights.append(f"High success rate ({rate:.0%}) — agent operating efficiently")

    if status == "looping":
        insights.append(
            "Agent appears stuck in a loop — consider adding termination conditions "
            "or checking for cyclic dependencies"
        )
    elif status == "drifting":
        insights.append(
            "Agent changed direction mid-task — may have received conflicting "
            "instructions or hit an unexpected blocker"
        )
    elif status == "failing":
        recent_failures = [
            e for e in events[-5:]
            if e.get("metadata", {}).get("status") == "failure"
        ]
        if recent_failures:
            last = recent_failures[-1]
            out = (last.get("output") or "no output")[:120]
            insights.append(
                f"Most recent failure on '{last.get('action')}': {out}"
            )

    if len(events) >= 2:
        duration = events[-1]["timestamp"] - events[0]["timestamp"]
        if duration > 0:
            insights.append(
                f"Session span: {duration:.1f}s across {len(events)} events"
            )

    return insights
