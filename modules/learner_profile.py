"""
Persistent Student Learning Profile for EduSense AI.

Fulfills Assessment Requirement 14:
- Topics studied
- Progress & learning history
- Assessment scores
- Weak and strong concepts
- Persistent misconception tracking
- Context injection for personalizing future teaching sessions
"""

import json
import os
from datetime import datetime

PROFILE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PROFILE_PATH = os.path.join(PROFILE_DIR, "learner_profile.json")


def get_default_profile():
    """Return an empty default learner profile."""
    return {
        "student_name": "Student",
        "level": "Beginner",
        "preferred_language": "English",
        "total_sessions": 0,
        "total_study_minutes": 0,
        "last_active": "",
        "topics_studied": [],
        "concept_mastery": {},
        "strong_concepts": [],
        "weak_concepts": [],
        "misconceptions": [],
        "learning_history": [],
        "current_learning_path": None
    }


def load_profile():
    """Load the learner profile from disk, creating default if missing."""
    if not os.path.exists(PROFILE_PATH):
        profile = get_default_profile()
        save_profile(profile)
        return profile
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure all default keys exist
            defaults = get_default_profile()
            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"Error loading learner profile: {e}")
        return get_default_profile()


def save_profile(profile):
    """Save the learner profile to disk safely."""
    try:
        os.makedirs(PROFILE_DIR, exist_ok=True)
        with open(PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving learner profile: {e}")
        return False


def record_session_result(
    topic,
    level,
    language,
    duration_minutes,
    learning_summary,
    final_score=0,
    total_quiz_questions=0
):
    """
    Update the learner profile with results from a completed lesson or quiz.
    Reconciles concept scores, strong/weak areas, and misconceptions.
    """
    profile = load_profile()
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    profile["last_active"] = today
    profile["total_sessions"] = profile.get("total_sessions", 0) + 1
    try:
        dur = int(duration_minutes) if isinstance(duration_minutes, (int, float)) else 20
    except Exception:
        dur = 20
    profile["total_study_minutes"] = profile.get("total_study_minutes", 0) + dur
    profile["level"] = level
    profile["preferred_language"] = language

    # Record topic in studied list if not present or update
    existing_topics = profile.get("topics_studied", [])
    topic_entry = next((t for t in existing_topics if t.get("topic") == topic), None)
    quiz_pct = (final_score / total_quiz_questions * 100) if total_quiz_questions > 0 else 0
    if not topic_entry:
        existing_topics.append({
            "topic": topic,
            "first_studied": today,
            "last_studied": today,
            "best_score": round(quiz_pct, 1),
            "sessions_count": 1
        })
    else:
        topic_entry["last_studied"] = today
        topic_entry["best_score"] = max(topic_entry.get("best_score", 0), round(quiz_pct, 1))
        topic_entry["sessions_count"] = topic_entry.get("sessions_count", 1) + 1
    profile["topics_studied"] = existing_topics

    # Update concept mastery
    concept_perf = learning_summary.get("concept_performance", {})
    mastery = profile.setdefault("concept_mastery", {})
    for concept, score in concept_perf.items():
        concept_str = str(concept).strip()
        if not concept_str:
            continue
        # Moving average
        prev = mastery.get(concept_str, score)
        mastery[concept_str] = round((prev + score) / 2, 2)

    # Recompute strong / weak concepts based on accumulated mastery
    strong = []
    weak = []
    for concept, score in mastery.items():
        if score >= 0.75:
            strong.append(concept)
        elif score < 0.5:
            weak.append(concept)
    profile["strong_concepts"] = strong
    profile["weak_concepts"] = weak

    # Record detected misconceptions
    new_misconceptions = learning_summary.get("misconceptions", [])
    existing_misc = profile.setdefault("misconceptions", [])
    for item in new_misconceptions:
        misc_str = item.get("misconception", "") if isinstance(item, dict) else str(item)
        conc_str = item.get("concept", "") if isinstance(item, dict) else ""
        if misc_str and misc_str.lower() not in ("none", "n/a"):
            if not any(m.get("misconception") == misc_str for m in existing_misc):
                existing_misc.append({
                    "concept": conc_str,
                    "misconception": misc_str,
                    "date": today
                })
    profile["misconceptions"] = existing_misc

    # Add to learning history log
    profile.setdefault("learning_history", []).append({
        "topic": topic,
        "date": today,
        "duration": dur,
        "score_pct": round(quiz_pct, 1),
        "strong_identified": learning_summary.get("strong_concepts", []),
        "weak_identified": learning_summary.get("weak_concepts", [])
    })

    save_profile(profile)
    return profile


def get_profile_personalization_context():
    """
    Format a concise string representation of the student's profile
    for injection into LLM prompts (lesson planning, teacher explanations).
    """
    profile = load_profile()
    weak = profile.get("weak_concepts", [])
    strong = profile.get("strong_concepts", [])
    misconceptions = profile.get("misconceptions", [])

    if not weak and not strong and not misconceptions:
        return ""

    context_parts = ["STUDENT LEARNING PROFILE (FROM PREVIOUS SESSIONS):"]
    if weak:
        context_parts.append(f"- Student has previously struggled with: {', '.join(weak[:5])}. (Provide extra scaffolding)")
    if strong:
        context_parts.append(f"- Student has demonstrated mastery in: {', '.join(strong[:5])}.")
    if misconceptions:
        recent_misc = [f"'{m['concept']}': {m['misconception']}" for m in misconceptions[-3:] if m.get("misconception")]
        if recent_misc:
            context_parts.append(f"- Recent misconceptions detected: {'; '.join(recent_misc)}.")

    return "\n".join(context_parts)
