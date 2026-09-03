import re

from modules.teacher import evaluate_student_answer


def normalize_text(text):
    """
    Normalize text before comparing answers.
    """

    if not text:
        return ""

    text = text.lower()

    # Remove punctuation
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Remove extra spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# KEYWORD FALLBACK (kept - used only if the AI evaluator fails)
# ============================================================

def evaluate_answer_keyword(student_answer, expected_concept):
    """
    Evaluate a student's answer using simple
    concept-based keyword matching.

    This is now only a FALLBACK for when the AI evaluator
    (evaluate_answer) is unavailable - see below.
    """

    if not student_answer or not student_answer.strip():

        return {
            "score": 0,
            "correct": False,
            "feedback": (
                "Please try answering the question "
                "before continuing."
            )
        }

    answer = normalize_text(student_answer)
    concept = normalize_text(expected_concept)

    concept_words = [
        word
        for word in concept.split()
        if len(word) > 2
    ]

    if not concept_words:

        return {
            "score": 0,
            "correct": False,
            "feedback": (
                "I could not determine the expected concept."
            )
        }

    matched_words = [
        word
        for word in concept_words
        if word in answer
    ]

    match_ratio = (
        len(matched_words) / len(concept_words)
    )

    if match_ratio >= 0.60:

        return {
            "score": 1,
            "correct": True,
            "feedback": (
                "Excellent! Your answer contains "
                "the important concept."
            )
        }

    elif match_ratio >= 0.30:

        return {
            "score": 0.5,
            "correct": False,
            "feedback": (
                "Good attempt! You have part of the "
                "idea, but your answer could be more complete."
            )
        }

    else:

        return {
            "score": 0,
            "correct": False,
            "feedback": (
                "Good try! Review the explanation and "
                "try to include the main concept in your answer."
            )
        }


# ============================================================
# PARSE THE AI EVALUATOR'S OUTPUT INTO THE SAME DICT SHAPE
# ============================================================

def _parse_ai_evaluation(raw_text):
    """
    teacher.evaluate_student_answer() returns free text shaped like:

        Result:
        Correct / Partially Correct / Needs Improvement

        Feedback:
        ...

        Improvement:
        ...

    Convert that into the {score, correct, feedback} dict that
    the rest of the app (mark_section_completed, update_difficulty,
    etc.) already expects, so nothing downstream has to change.
    """

    if not raw_text:
        return None

    text = raw_text.strip()
    lower = text.lower()

    # Pull out the "Result" line to classify the answer
    result_match = re.search(
        r"result[:\s]*\n?\s*(correct|partially correct|needs improvement)",
        lower
    )

    if result_match:
        verdict = result_match.group(1)
    elif "partially correct" in lower:
        verdict = "partially correct"
    elif re.search(r"\bcorrect\b", lower) and "incorrect" not in lower and "needs improvement" not in lower:
        verdict = "correct"
    else:
        verdict = "needs improvement"

    if verdict == "correct":
        score, correct = 1, True
    elif verdict == "partially correct":
        score, correct = 0.5, False
    else:
        score, correct = 0, False

    return {
        "score": score,
        "correct": correct,
        # Show the full structured feedback to the student,
        # not just the verdict line.
        "feedback": text
    }


# ============================================================
# MAIN ENTRY POINT - use this from app.py
# ============================================================

def evaluate_answer(
    student_answer,
    expected_concept,
    question="",
    study_material="",
    level="Beginner",
    language="English"
):
    """
    Evaluate a student's answer using the AI evaluator from
    teacher.py (conceptually aware, not just keyword matching).
    Falls back to keyword matching only if the AI call fails
    or no study_material/question context is available.

    Returns the same {score, correct, feedback} shape the app
    already relies on, so app.py's existing logic
    (mark_section_completed, update_difficulty, save_answer)
    needs no other changes.
    """

    if not student_answer or not student_answer.strip():

        return {
            "score": 0,
            "correct": False,
            "feedback": (
                "Please try answering the question "
                "before continuing."
            )
        }

    # Without a question + study material we can't call the AI
    # evaluator meaningfully - fall back to keyword matching.
    if not question or not study_material:
        return evaluate_answer_keyword(student_answer, expected_concept)

    try:
        raw = evaluate_student_answer(
            question=question,
            student_answer=student_answer,
            study_material=study_material,
            level=level,
            language=language
        )

        parsed = _parse_ai_evaluation(raw)

        if parsed:
            return parsed

    except Exception as e:
        print("AI answer evaluation failed, falling back:", e)

    return evaluate_answer_keyword(student_answer, expected_concept)