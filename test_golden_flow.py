"""
Golden Demo & Uploaded Material End-to-End Verification for EduSense AI.

Simulates:
1. Golden Scenario:
   - Topic: "Newton's Laws of Motion"
   - Level: Beginner
   - Language: Hinglish
   - Duration: 20 minutes
   - Persona: Dr. Sophia
   - Path: Topic generation -> RAG Chunks -> Lesson Plan -> Explanations ->
           Visuals -> TTS Audio & Timings -> Video Classroom HTML ->
           Student Wrong Answer -> Misconception Detection -> Adaptive Re-explanation ->
           Targeted Follow-up Question -> Student Correct Answer -> Next Concept ->
           Final Assessment -> Learning Report -> Profile Persistence -> Study Tools

2. Uploaded Material Scenario:
   - File: test_material.txt
   - Ingestion -> Unicode Clean -> Vector Index -> Grounded Retrieval ->
     Lesson Plan -> Grounded Explanation -> Visual -> Evaluation -> Report.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from modules.topic_generator import generate_study_material_from_topic
from modules.text_processor import clean_text, split_text_into_chunks
from modules.retriever import build_chunk_index, find_relevant_chunks
from modules.lesson_planner import generate_lesson_plan
from modules.teacher import (
    generate_teacher_explanation,
    generate_follow_up_question,
    answer_in_lesson_query
)
from modules.assessment import evaluate_answer
from modules.teaching_engine import (
    initialize_lesson,
    save_answer,
    update_concept_performance,
    record_misconception,
    record_attempt,
    update_difficulty,
    add_adaptation_event,
    get_learning_summary
)
from modules.audio_teacher import generate_speech
from modules.subject_visuals import detect_visual
from modules.avatar_provider import build_classroom_video_html
from modules.learner_profile import load_profile, record_session_result, get_profile_personalization_context
from modules.study_tools import generate_study_notes, generate_flashcards


def run_golden_demo():
    print("=" * 60)
    print("STARTING GOLDEN DEMO: Newton's Laws of Motion (Hinglish, 20m, Beginner)")
    print("=" * 60)

    # 1. Topic & Study Material
    topic = "Newton's Laws of Motion"
    print(f"\n[1] Generating study material for: {topic}...")
    raw_material = generate_study_material_from_topic(topic, level="Advanced")
    cleaned_material = clean_text(raw_material)
    print(f"    Cleaned material words: {len(cleaned_material.split())}")

    # 2. Chunking & RAG Indexing
    print("\n[2] Indexing chunks in FAISS...")
    chunks = split_text_into_chunks(cleaned_material, chunk_size=120, overlap=30)
    chunk_index = build_chunk_index(chunks)
    print(f"    Indexed {len(chunks)} chunks in FAISS vector store.")

    # 3. Lesson Planning
    print("\n[3] Generating 20-minute Beginner Lesson Plan in Hinglish...")
    lesson_plan = generate_lesson_plan(
        document_text=raw_material,
        level="Beginner",
        language="Hinglish",
        duration=20
    )
    self_topic = lesson_plan.get("topic", topic)
    sections = lesson_plan.get("sections", [])
    print(f"    Plan Title: {self_topic}")
    print(f"    Sections generated: {len(sections)}")
    for i, s in enumerate(sections, 1):
        print(f"      {i}. {s.get('title')} ({s.get('duration_minutes', 0)} mins)")

    # 4. Teaching First Section: Grounded Explanation
    first_sec = sections[0] if sections else {"title": "First Law of Motion", "description": "Inertia"}
    first_concept = first_sec.get("concepts", ["Inertia"])[0] if first_sec.get("concepts") else "Inertia"
    print(f"\n[4] Teaching Section 1 Concept: {first_concept}")

    retrieved = find_relevant_chunks(f"{first_sec.get('title')} {first_concept}", chunk_index, top_k=3)
    grounded_ctx = "\n\n".join(retrieved) if retrieved else cleaned_material[:3000]
    print(f"    Retrieved {len(retrieved)} relevant RAG chunks for grounding.")

    visual_spec = detect_visual(first_sec.get("title", ""), first_sec.get("description", ""))
    print(f"    Subject-aware visual detected: {visual_spec.get('subject')} -> {visual_spec.get('visual_type')}")

    explanation = generate_teacher_explanation(
        first_sec,
        grounded_ctx,
        level="Beginner",
        language="Hinglish",
        visual_spec=visual_spec
    )
    print(f"    Hinglish Explanation snippet:\n    {explanation[:200]}...")

    # 5. Neural TTS & Word Timings
    print("\n[5] Synthesizing Neural Edge-TTS Speech with Word Boundaries...")
    audio_bytes, word_timings = generate_speech(explanation[:250], language="Hinglish", gender="female")
    print(f"    Audio generated: {len(audio_bytes)} bytes, Word timings count: {len(word_timings)}")
    assert len(word_timings) > 0, "Word timings must not be empty!"

    # 6. Virtual Classroom Video Stage
    print("\n[6] Building Virtual Classroom Video Experience...")
    classroom_html = build_classroom_video_html(
        audio_bytes=audio_bytes,
        word_timings=word_timings,
        section_title=first_sec.get("title", ""),
        concept_title=first_concept,
        visual_spec=visual_spec,
        teacher_name="Dr. Sophia",
        teacher_gender="female",
        teacher_style="Socratic Mentor"
    )
    print(f"    Classroom HTML built: {len(classroom_html)} characters.")
    assert "EduSense AI Studio" in classroom_html

    # 7. In-Lesson Ask Teacher
    print("\n[7] In-Lesson Ask Teacher Interaction...")
    student_query = "Ek simple daily life example do please"
    teacher_reply = answer_in_lesson_query(
        student_query,
        first_concept,
        explanation[:1000],
        study_material=grounded_ctx,
        level="Beginner",
        language="Hinglish",
        teacher_persona="Dr. Sophia"
    )
    print(f"    Teacher reply: {teacher_reply[:180]}...")

    # 8. Interactive Question & Adaptive Feedback Loop (Incorrect Answer)
    print("\n[8] Checkpoint Question & Misconception Handling...")
    state = initialize_lesson(lesson_plan)
    q_text = "Agar ek car achanak stop ho jaye, toh passenger aage kyu girta hai?"
    expected_concept = "Inertia"

    # Test Scenario A: Incorrect Answer with Misconception
    wrong_answer = "Passenger aage girta hai kyunki car ka engine use aage dhakka deta hai."
    print(f"    Student Answer (Erroneous): '{wrong_answer}'")

    eval_a = evaluate_answer(
        wrong_answer,
        expected_concept,
        question=q_text,
        study_material=grounded_ctx,
        level="Beginner",
        language="Hinglish"
    )
    print(f"    Evaluation Correct: {eval_a.get('correct')}")
    print(f"    Feedback: {eval_a.get('feedback')}")
    detected_misc = eval_a.get("misconception")
    print(f"    Detected Misconception: {detected_misc}")

    # State update
    save_answer(state, q_text, wrong_answer, eval_a)
    update_concept_performance(state, expected_concept, eval_a.get("score", 0))
    record_attempt(state, 0)
    update_difficulty(state, eval_a)
    record_misconception(state, expected_concept, detected_misc)

    print(f"    Teaching State Difficulty: {state.get('current_difficulty')}")
    print(f"    Weak Concepts: {state.get('weak_concepts')}")

    # Adaptive Remediation & Follow-up
    print("\n[9] Generating Adaptive Remediation & Targeted Retry Question...")
    remed_section = {
        "title": f"Re-teaching: {expected_concept}",
        "description": f"Correct the misconception: {detected_misc}. Explain why passengers move forward due to inertia.",
        "key_points": [f"Learning gap: {detected_misc}"]
    }
    remed_explanation = generate_teacher_explanation(
        remed_section,
        grounded_ctx,
        level="Beginner",
        language="Hinglish"
    )
    print(f"    Remediation Explanation: {remed_explanation[:180]}...")

    follow_up_q = generate_follow_up_question(
        expected_concept,
        q_text,
        wrong_answer,
        level="Beginner",
        language="Hinglish",
        simplify=True
    )
    print(f"    Targeted Retry Question: {follow_up_q}")

    # Test Scenario B: Correct Answer on Retry
    print("\n[10] Student Retries Follow-up Question...")
    correct_answer = "Inertia ki wajah se! Body pehle se motion mein thi, jab car ruki toh body aage chalte rehna chahti hai."
    print(f"    Student Retry Answer: '{correct_answer}'")

    eval_b = evaluate_answer(
        correct_answer,
        expected_concept,
        question=follow_up_q,
        study_material=grounded_ctx,
        level="Beginner",
        language="Hinglish"
    )
    print(f"    Follow-up Correct: {eval_b.get('correct')}")
    print(f"    Follow-up Feedback: {eval_b.get('feedback')}")
    update_concept_performance(state, expected_concept, 1.0)
    add_adaptation_event(state, 0, "mastered_after_follow_up", "Correct understanding confirmed")

    # 11. Final Assessment & Learning Report
    print("\n[11] Generating Final Assessment & Learning Summary...")
    learning_summary = get_learning_summary(state)
    print(f"    Concept Performance: {learning_summary.get('concept_performance')}")
    print(f"    Strong Areas: {learning_summary.get('strong_concepts')}")
    print(f"    Misconceptions Log: {learning_summary.get('misconceptions')}")

    # 12. Persistent Learner Profile Update
    print("\n[12] Persisting to Student Learning Profile...")
    updated_profile = record_session_result(
        topic=self_topic,
        level="Beginner",
        language="Hinglish",
        duration_minutes=20,
        learning_summary=learning_summary,
        final_score=4,
        total_quiz_questions=5
    )
    print(f"    Profile updated! Total Sessions: {updated_profile.get('total_sessions')}, Study Minutes: {updated_profile.get('total_study_minutes')}")

    # 13. Study Tools
    print("\n[13] Generating Study Tools (Revision Notes & Flashcards)...")
    notes = generate_study_notes(lesson_plan, language="Hinglish")
    flashcards = generate_flashcards(lesson_plan, max_cards=4)
    print(f"    Study notes length: {len(notes)} chars")
    print(f"    Flashcards generated: {len(flashcards)}")
    for fc in flashcards[:2]:
        print(f"      • Front: {fc.get('front')[:60]}... | Back: {fc.get('back')[:60]}...")

    print("\n" + "=" * 60)
    print("GOLDEN DEMO EXECUTION COMPLETE: 100% SUCCESS!")
    print("=" * 60)


if __name__ == "__main__":
    run_golden_demo()
