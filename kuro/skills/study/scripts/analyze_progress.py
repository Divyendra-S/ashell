"""Analyze study session history and return progress summary."""

import json
from collections import defaultdict
from pathlib import Path

from kuro.skills import read_skill_data


def analyze_progress(user_id: str) -> dict:
    """Read study sessions.jsonl and return a progress summary.

    Returns dict with:
      - total_sessions: int
      - topics: {topic: {sessions, avg_score, last_date, trend, weak_areas}}
      - weakest_topics: list of topics needing review
      - strongest_topics: list of mastered topics
    """
    records = read_skill_data("study", "sessions.jsonl", user_id=user_id)
    if not records:
        return {"total_sessions": 0, "topics": {}, "weakest_topics": [], "strongest_topics": []}

    topic_data = defaultdict(list)
    for r in records:
        topic = r.get("topic", "unknown")
        topic_data[topic].append(r)

    topics = {}
    weakest = []
    strongest = []

    for topic, sessions in topic_data.items():
        scores = []
        for s in sessions:
            score_str = s.get("score", "0/5")
            if "/" in str(score_str):
                num, denom = str(score_str).split("/")
                scores.append(int(num) / int(denom))
            elif isinstance(score_str, (int, float)):
                scores.append(float(score_str))

        avg = sum(scores) / len(scores) if scores else 0
        trend = "improving" if len(scores) >= 2 and scores[-1] > scores[-2] else "stable"
        if len(scores) >= 2 and scores[-1] < scores[-2]:
            trend = "declining"

        weak_areas = []
        for s in sessions:
            weak_areas.extend(s.get("weak_areas", []))
        # Deduplicate, keep most recent mentions
        seen = set()
        unique_weak = []
        for w in reversed(weak_areas):
            if w not in seen:
                seen.add(w)
                unique_weak.append(w)
        unique_weak.reverse()

        topics[topic] = {
            "sessions": len(sessions),
            "avg_score": round(avg, 2),
            "last_date": sessions[-1].get("date", "unknown"),
            "trend": trend,
            "weak_areas": unique_weak[:5],
        }

        if avg < 0.6:
            weakest.append(topic)
        elif avg >= 0.8:
            strongest.append(topic)

    return {
        "total_sessions": len(records),
        "topics": topics,
        "weakest_topics": weakest,
        "strongest_topics": strongest,
    }
