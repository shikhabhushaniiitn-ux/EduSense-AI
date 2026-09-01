import json
import re

from modules.ai_client import generate_text


# ============================================================
# CLEAN AI RESPONSE
# ============================================================

def clean_response(text):
    """
    Remove unnecessary markdown formatting
    from the AI response.
    """

    if not text:
        return ""

    text = text.strip()

    # Remove code fences if AI adds them
    text = re.sub(
        r"^```(?:text|markdown)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    return text.strip()


# ============================================================
# GENERATE TEACHER EXPLANATION
# ============================================================

def generate_teacher_explanation(
    section,
    study_material,
    level="Beginner",
    language="English"
):
    """
    Generate a student-friendly explanation
    for the current lesson section.
    """

    if not section:
        return "No lesson section was provided."

    if not study_material:
        return "No study material was provided."

    title = section.get(
        "title",
        "Current Topic"
    )

    description = section.get(
        "description",
        ""
    )

    key_points = section.get(
        "key_points",
        []
    )

    key_points_text = "\n".join(
        f"- {point}"
        for point in key_points
    )

    prompt = f"""
You are EduSense AI, an intelligent personal teacher.

Teach the student the CURRENT LESSON SECTION.

Student level:
{level}

Preferred language:
{language}

Current section:
{title}

Section description:
{description}

Important points:
{key_points_text}

Study material:
{study_material[:10000]}

IMPORTANT LANGUAGE RULE:

If the preferred language is English:
- Write the entire explanation in English.
- Do not use Hindi.

If the preferred language is Hindi:
- Write the explanation in Hindi.
- Technical terms such as Machine Learning,
  Supervised Learning, Classification and Regression
  may remain in English when natural.

If the preferred language is Hinglish:
- Explain naturally using a mixture of Hindi and English.
- Keep technical terms in English.

TEACHING RULES:

1. Teach the actual current section.
2. Do not give a generic introduction.
3. Use only information supported by the study material.
4. Explain difficult concepts in simple language.
5. Give a simple example when possible.
6. Adapt the explanation to the student's level.
7. Beginner:
   Use very simple explanations and examples.
8. Intermediate:
   Give more detail and explain relationships between concepts.
9. Advanced:
   Give deeper conceptual explanations.
10. Keep the explanation focused on the current section.
11. Do not mention that you are an AI.
12. Do not discuss programming or implementation.
13. Do not make up information.

Return only the teaching explanation.
"""

    try:

        result = generate_text(prompt)

        if result:

            result = clean_response(result)

            if result:
                return result

    except Exception as e:

        print(
            "Teacher explanation error:",
            e
        )

    # --------------------------------------------------------
    # Local fallback
    # --------------------------------------------------------

    return create_fallback_explanation(
        section,
        level,
        language
    )


# ============================================================
# FALLBACK EXPLANATION
# ============================================================

def create_fallback_explanation(
    section,
    level,
    language
):
    """
    Local explanation used when OpenRouter
    is temporarily unavailable.
    """

    title = section.get(
        "title",
        "Current Topic"
    )

    description = section.get(
        "description",
        ""
    )

    key_points = section.get(
        "key_points",
        []
    )

    if language == "Hindi":

        explanation = (
            f"### {title}\n\n"
            f"{description}\n\n"
            "इस भाग में हम निम्नलिखित महत्वपूर्ण "
            "बिंदुओं को समझेंगे:\n\n"
        )

        for point in key_points:
            explanation += f"- {point}\n"

        return explanation

    elif language == "Hinglish":

        explanation = (
            f"### {title}\n\n"
            f"{description}\n\n"
            "Is section mein hum ye important "
            "points samjhenge:\n\n"
        )

        for point in key_points:
            explanation += f"- {point}\n"

        return explanation

    else:

        explanation = (
            f"### {title}\n\n"
            f"{description}\n\n"
            "In this section, we will focus on "
            "these important points:\n\n"
        )

        for point in key_points:
            explanation += f"- {point}\n"

        return explanation


# ============================================================
# GENERATE SECTION QUESTION
# ============================================================

def generate_section_question(
    section,
    study_material,
    level="Beginner",
    language="English"
):
    """
    Generate an interactive question based
    on the current lesson section.
    """

    title = section.get(
        "title",
        "Current Topic"
    )

    key_points = section.get(
        "key_points",
        []
    )

    key_points_text = "\n".join(
        f"- {point}"
        for point in key_points
    )

    prompt = f"""
You are EduSense AI.

Generate ONE short interactive question
to check whether the student understood
the current lesson section.

Student level:
{level}

Preferred language:
{language}

Section:
{title}

Key points:
{key_points_text}

Study material:
{study_material[:6000]}

Language rules:

English:
Return the question completely in English.

Hindi:
Return the question in Hindi.
Technical terms can remain in English.

Hinglish:
Return the question naturally in Hinglish.

Rules:

- Ask about the current section only.
- Do not ask something unrelated.
- Keep it appropriate for the student's level.
- The question should test understanding, not memorization.
- Return ONLY the question.
"""

    try:

        result = generate_text(prompt)

        if result:

            return clean_response(result)

    except Exception as e:

        print(
            "Question generation error:",
            e
        )

    # Local fallback

    if language == "Hindi":

        return (
            f"{title} में आपने क्या समझा? "
            "अपने शब्दों में समझाइए।"
        )

    elif language == "Hinglish":

        return (
            f"{title} ke baare mein aapne "
            "kya samjha? Apne words mein explain kijiye."
        )

    else:

        return (
            f"What did you understand about {title}? "
            "Explain it in your own words."
        )


# ============================================================
# EVALUATE STUDENT ANSWER
# ============================================================

def evaluate_student_answer(
    question,
    student_answer,
    study_material,
    level="Beginner",
    language="English"
):
    """
    Evaluate a student's answer and provide
    useful learning feedback.
    """

    if not student_answer.strip():

        if language == "Hindi":
            return "कृपया अपना उत्तर लिखें।"

        elif language == "Hinglish":
            return "Please apna answer likhiye."

        return "Please enter your answer."

    prompt = f"""
You are EduSense AI, a supportive teacher.

Evaluate the student's answer.

Question:
{question}

Student answer:
{student_answer}

Study material:
{study_material[:8000]}

Student level:
{level}

Preferred language:
{language}

Language rules:

English:
Give feedback completely in English.

Hindi:
Give feedback in Hindi.
Technical terms may remain in English.

Hinglish:
Give feedback naturally in Hinglish.

Evaluation rules:

1. Check whether the student's answer demonstrates
   understanding of the concept.
2. Do not require exact wording.
3. Give credit for a conceptually correct answer.
4. If partially correct, explain what is missing.
5. If incorrect, explain the correct concept simply.
6. Be encouraging.
7. Do not shame the student.
8. Keep feedback concise.
9. Give one useful improvement suggestion.

Use this structure:

Result:
Correct / Partially Correct / Needs Improvement

Feedback:
...

Improvement:
...

Return only the feedback.
"""

    try:

        result = generate_text(prompt)

        if result:

            return clean_response(result)

    except Exception as e:

        print(
            "Answer evaluation error:",
            e
        )

    # Fallback

    if language == "Hindi":

        return (
            "### Result\n"
            "उत्तर की जाँच पूरी नहीं हो सकी।\n\n"
            "### Feedback\n"
            "कृपया अध्ययन सामग्री को दोबारा देखें "
            "और मुख्य अवधारणा को अपने शब्दों में समझाने का प्रयास करें।"
        )

    elif language == "Hinglish":

        return (
            "### Result\n"
            "Answer evaluate nahi ho saka.\n\n"
            "### Feedback\n"
            "Study material ko dobara dekhiye aur "
            "main concept ko apne words mein explain kijiye."
        )

    else:

        return (
            "### Result\n"
            "The answer could not be evaluated.\n\n"
            "### Feedback\n"
            "Review the study material and try "
            "explaining the main concept in your own words."
        )
