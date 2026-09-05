"""
Study Tools: Revision Notes & Flashcards Generator for EduSense AI.

Fulfills Assessment Requirement 18:
- Revision mode
- Automatic study notes
- Flashcard generation
"""

import json
import re
from modules.ai_client import generate_text


def generate_study_notes(lesson_plan, language="English"):
    """
    Generate comprehensive, structured revision notes from the lesson plan.
    Includes key definitions, formulas, and high-yield exam takeaways.
    """
    if not lesson_plan:
        return "No active lesson available to generate study notes."

    topic = lesson_plan.get("topic", "Lesson")
    sections = lesson_plan.get("sections", [])
    objectives = lesson_plan.get("learning_objectives", [])

    notes_parts = [
        f"# 📚 Comprehensive Revision Notes: {topic}",
        f"\n**Level:** {lesson_plan.get('level', 'All Levels')} | **Language:** {language}\n",
        "## 🎯 Key Learning Objectives"
    ]
    for obj in objectives:
        notes_parts.append(f"- {obj}")

    notes_parts.append("\n## 📖 Core Concepts & Definitions")
    for idx, sec in enumerate(sections, start=1):
        title = sec.get("title", f"Section {idx}")
        desc = sec.get("description", "")
        key_points = sec.get("key_points", [])
        notes_parts.append(f"\n### {idx}. {title}")
        if desc:
            notes_parts.append(f"{desc}")
        if key_points:
            notes_parts.append("**Key Takeaways:**")
            for kp in key_points:
                notes_parts.append(f"- {kp}")

    notes_parts.append("\n## 💡 High-Yield Exam Tips")
    notes_parts.append("1. Always connect fundamental definitions to concrete physical or computational examples.")
    notes_parts.append("2. Pay close attention to unit dimensions, boundary conditions, and state transitions.")
    notes_parts.append("3. Review any concepts marked for revision in your personal learning report.")

    return "\n".join(notes_parts)


def generate_flashcards(lesson_plan, max_cards=6):
    """
    Generate flashcards from the lesson plan sections and questions.
    Returns list of dicts: [{"front": str, "back": str, "concept": str}]
    """
    if not lesson_plan:
        return []

    flashcards = []
    # Extract from interactive questions first
    for q in lesson_plan.get("interactive_questions", []):
        concept = q.get("expected_concept", q.get("concept", "Concept"))
        question = q.get("question", "")
        answer = q.get("correct_answer", "") or f"Key concept: {concept}"
        if question:
            flashcards.append({
                "front": question,
                "back": answer,
                "concept": concept
            })
        if len(flashcards) >= max_cards:
            break

    # Extract from sections if needed
    if len(flashcards) < max_cards:
        for sec in lesson_plan.get("sections", []):
            title = sec.get("title", "")
            key_points = sec.get("key_points", [])
            if title and key_points:
                flashcards.append({
                    "front": f"What are the core principles of {title}?",
                    "back": "; ".join(key_points[:3]),
                    "concept": title
                })
            if len(flashcards) >= max_cards:
                break

    return flashcards
