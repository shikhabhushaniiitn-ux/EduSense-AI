"""
Comprehensive Automated Test Suite for EduSense AI.

Verifies:
1. Gemini AI Client generation
2. Multilingual text cleaning & Unicode preservation
3. Neural Edge-TTS with word-level timing interpolation
4. Subject-aware visual detection (Math, Physics, Bio, Code, etc.)
5. Student Learning Profile persistence & context injection
6. AI Learning Paths curriculum & Mermaid roadmap generation
7. Study tools (flashcards & revision notes)
8. In-lesson conversational Q&A
9. Adaptive teaching response & misconception detection
10. Semantic RAG index construction & grounded retrieval
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestEduSenseAI(unittest.TestCase):

    def test_01_unicode_text_cleaning(self):
        """Test Unicode-safe text cleaning preserves Hindi, Tamil, and math."""
        from modules.text_processor import clean_text
        raw = "नमस्ते दुनिया! F = ma \u03c0 \u2211 \u222b \u0ba4\u0bae\u0bbf\u0bb4\u0bcd \x00\x08 control"
        cleaned = clean_text(raw)
        self.assertIn("नमस्ते", cleaned)
        self.assertIn("F = ma", cleaned)
        self.assertIn("\u03c0", cleaned)
        self.assertIn("\u0ba4\u0bae\u0bbf\u0bb4\u0bcd", cleaned)
        self.assertNotIn("\x00", cleaned)
        self.assertNotIn("\x08", cleaned)

    def test_02_ai_client_generation(self):
        """Test Gemini AI client generates responses."""
        from modules.ai_client import generate_text
        resp = generate_text("Reply with exactly: 'EduSense Verification'", max_tokens=20)
        self.assertIsNotNone(resp)
        self.assertTrue(len(resp) > 0)

    def test_03_neural_edge_tts_timings(self):
        """Test Edge-TTS audio generation produces valid bytes and word timings."""
        from modules.audio_teacher import generate_speech
        audio_bytes, word_timings = generate_speech("Welcome to EduSense AI.")
        self.assertIsNotNone(audio_bytes)
        self.assertGreater(len(audio_bytes), 1000)
        self.assertGreater(len(word_timings), 0)
        for wt in word_timings:
            self.assertIn("text", wt)
            self.assertIn("start_ms", wt)
            self.assertIn("end_ms", wt)
            self.assertGreaterEqual(wt["end_ms"], wt["start_ms"])

    def test_04_subject_visual_detection(self):
        """Test subject-aware visual dispatch classifies physics and math concepts."""
        from modules.subject_visuals import detect_visual
        spec = detect_visual(
            "Newton's Second Law of Motion",
            "Force equals mass times acceleration. F = ma. A heavier mass requires more force."
        )
        self.assertIsNotNone(spec)
        self.assertIn(spec.get("subject"), ["Physics", "Mathematics", "General"])
        self.assertIn(spec.get("visual_type"), ["equation", "graph", "simulation", "process", "image"])

    def test_05_learner_profile_persistence(self):
        """Test Student Learning Profile records sessions and persists to disk."""
        from modules.learner_profile import load_profile, record_session_result, get_profile_personalization_context
        summary = {
            "percentage": 85,
            "concept_performance": {"First Law": 1.0, "F=ma": 0.3},
            "strong_concepts": ["First Law"],
            "weak_concepts": ["F=ma"],
            "misconceptions": [{"concept": "F=ma", "misconception": "Confuses mass with velocity"}]
        }
        profile = record_session_result(
            topic="Test Physics Unit",
            level="Beginner",
            language="English",
            duration_minutes=20,
            learning_summary=summary,
            final_score=4,
            total_quiz_questions=5
        )
        self.assertIsNotNone(profile)
        self.assertGreater(profile.get("total_sessions", 0), 0)
        context = get_profile_personalization_context()
        self.assertTrue(len(context) > 0)
        self.assertIn("F=ma", context)

    def test_06_learning_paths_generation(self):
        """Test broad domain curriculum generation and Mermaid roadmaps."""
        from modules.learning_path import generate_learning_path, generate_learning_path_mermaid
        path = generate_learning_path("Machine Learning")
        self.assertIn("modules", path)
        self.assertGreaterEqual(len(path["modules"]), 3)
        mermaid = generate_learning_path_mermaid(path)
        self.assertIn("graph LR", mermaid)
        self.assertIn("m1", mermaid)

    def test_07_study_tools(self):
        """Test flashcards and revision notes generator."""
        from modules.study_tools import generate_study_notes, generate_flashcards
        lesson = {
            "topic": "Newton's Laws of Motion",
            "level": "Beginner",
            "learning_objectives": ["Understand inertia", "Apply F=ma"],
            "sections": [
                {
                    "title": "First Law",
                    "description": "An object at rest stays at rest.",
                    "key_points": ["Inertia is the tendency to resist change."]
                }
            ],
            "interactive_questions": [
                {
                    "question": "What is inertia?",
                    "expected_concept": "Inertia",
                    "correct_answer": "Tendency to resist changes in state of motion."
                }
            ]
        }
        notes = generate_study_notes(lesson, language="English")
        self.assertIn("Comprehensive Revision Notes", notes)
        self.assertIn("First Law", notes)
        cards = generate_flashcards(lesson)
        self.assertGreaterEqual(len(cards), 1)
        self.assertIn("Inertia", cards[0].get("concept", ""))

    def test_08_in_lesson_query(self):
        """Test spontaneous in-lesson Ask Teacher Q&A."""
        from modules.teacher import answer_in_lesson_query
        reply = answer_in_lesson_query(
            student_query="Why does a heavier object need more force?",
            current_section_title="Newton's Second Law",
            current_section_content="F = ma. Acceleration is inversely proportional to mass.",
            level="Beginner",
            language="English",
            teacher_persona="Dr. Sophia"
        )
        self.assertIsNotNone(reply)
        self.assertTrue(len(reply) > 20)

    def test_09_adaptive_teaching_misconception(self):
        """Test evaluation detects misconceptions and generates targeted feedback."""
        from modules.assessment import evaluate_answer
        eval_res = evaluate_answer(
            student_answer="Heavier objects always fall faster because they have more gravity.",
            expected_concept="Free Fall Acceleration",
            question="Do heavy and light objects fall at different rates in a vacuum?",
            study_material="In a vacuum, all objects fall with the same gravitational acceleration regardless of mass."
        )
        self.assertIsNotNone(eval_res)
        self.assertIn("feedback", eval_res)
        self.assertIn("misconception", eval_res)
        self.assertFalse(eval_res.get("correct", True))

    def test_10_rag_indexing_and_retrieval(self):
        """Test FAISS vector indexing and grounded semantic retrieval."""
        from modules.retriever import build_chunk_index, find_relevant_chunks
        chunks = [
            "Newton's first law states that an object at rest remains at rest unless acted on by a net external force.",
            "Photosynthesis occurs in chloroplasts where chlorophyll absorbs sunlight to convert water and carbon dioxide into glucose.",
            "Linear regression finds the best fitting straight line between independent and dependent variables."
        ]
        index = build_chunk_index(chunks)
        self.assertIsNotNone(index)
        results = find_relevant_chunks("Tell me about inertia and forces", index, top_k=1)
        self.assertEqual(len(results), 1)
        self.assertIn("Newton's first law", results[0])


if __name__ == "__main__":
    unittest.main()
