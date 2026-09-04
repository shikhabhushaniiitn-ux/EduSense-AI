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

def _build_visual_narration_instructions(visual_spec):
    """
    Build the extra prompt block that tells the AI to speak
    ABOUT the visual that will be shown alongside this
    explanation, so the generated text - which is also fed
    straight into text-to-speech - actually narrates the
    visual instead of ignoring it.

    Returns "" if there is no visual (or visual_type is "none"),
    in which case the explanation prompt is unchanged.
    """

    if not visual_spec:
        return ""

    visual_type = visual_spec.get("visual_type", "none")

    if visual_type == "none":
        return ""

    title = visual_spec.get("title", "")

    descriptions = {
        "equation": (
            f'An equation titled "{title}" will be shown with the '
            "explanation. Verbally walk the student through the "
            "equation and its step-by-step solution in your "
            "explanation - describe what each part of the equation "
            "means, as if you were pointing at it while teaching."
        ),
        "graph": (
            f'A graph titled "{title}" will be plotted alongside the '
            "explanation. Describe, in words, what the graph looks "
            "like and what it shows (shape of the curve, where it "
            "rises/falls, key points like intercepts or turning "
            "points) so a student listening to the audio understands "
            "the graph without needing to read it."
        ),
        "process": (
            f'A step-by-step process/flow diagram titled "{title}" '
            "will be shown. Narrate the sequence out loud, step by "
            "step, in the same order as the diagram, so the audio "
            "walks the student through exactly what the diagram "
            "shows."
        ),
        "timeline": (
            f'A timeline diagram titled "{title}" will be shown. '
            "Narrate the events in chronological order, connecting "
            "each event to the next, so the audio matches what the "
            "timeline shows."
        ),
        "code": (
            f'A code snippet titled "{title}" will be shown. Walk '
            "through what the code does line by line in plain "
            "language, and describe what output it produces, so a "
            "student listening to the audio understands the code "
            "without needing to read it."
        ),
        "image": (
            f'A labeled reference image titled "{title}" will be '
            "shown. Describe, in words, the structure/parts shown in "
            "the image and how they relate to each other, so the "
            "audio explanation matches what the image shows."
        ),
        "map": (
            f'A map titled "{title}" will be shown. Describe, in '
            "words, the geography/territory/route it shows, so the "
            "audio explanation matches what the map shows."
        ),
        "simulation": (
            f'An interactive physics simulation titled "{title}" '
            "will be shown, which the student can adjust with "
            "sliders. Explain what the simulation demonstrates, what "
            "happens as the student changes each control, and what "
            "real-world phenomenon it models, so the audio "
            "explanation makes the simulation meaningful even before "
            "the student touches it."
        )
    }

    narration_note = descriptions.get(visual_type)

    if not narration_note:
        return ""

    return f"""

VISUAL BEING SHOWN WITH THIS EXPLANATION:
{narration_note}

Weave this into your explanation naturally (e.g. "look at the graph
below", "as the diagram shows") - do not just describe the visual in
one bolted-on sentence, and do not mention that this instruction was
given to you.
"""


def generate_teacher_explanation(
    section,
    study_material,
    level="Beginner",
    language="English",
    visual_spec=None
):
    """
    Generate a student-friendly explanation
    for the current lesson section.

    If `visual_spec` (the dict from
    modules.subject_visuals.detect_visual) is supplied, the
    explanation is written to also narrate that visual out loud -
    important because this same text is fed to text-to-speech, so
    without this the audio never actually explains the graph /
    diagram / simulation the student is looking at.
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
{_build_visual_narration_instructions(visual_spec)}
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

        # Explanations are naturally long-form (multiple
        # paragraphs, an example, level-appropriate depth) -
        # the default 500-token budget was cutting them off
        # mid-sentence. 1200 covers this comfortably, and the
        # auto-retry in generate_text() is a safety net if a
        # very long Advanced-level explanation still needs more.
        result = generate_text(
            prompt,
            max_tokens=1200
        )

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


def generate_visual_narration(visual_spec, level="Beginner", language="English"):
    """Return short voice-ready narration for the currently visible visual."""

    concept = visual_spec.get("concept_id", visual_spec.get("title", "this concept"))
    visual_type = visual_spec.get("visual_type", "visual")
    details = visual_spec.get("process_steps") or visual_spec.get("steps") or []
    detail_text = "; ".join(details[:3])
    prompt = f"""
Create 2-4 concise, spoken teaching sentences that explain the visual now
visible to a {level} learner. Use {language}. Explain the concept and what
the learner should notice; do not mention implementation.
Concept: {concept}
Visual type: {visual_type}
Visual details: {detail_text}
"""
    try:
        narration = generate_text(prompt, max_tokens=220)
        if narration:
            return clean_response(narration)
    except Exception as error:
        print("Visual narration generation error:", error)

    if detail_text:
        return f"This {visual_type} explains {concept}. Notice: {detail_text}."
    return f"This {visual_type} highlights the key idea behind {concept}."


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

        result = generate_text(
            prompt,
            max_tokens=700
        )

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
# ADAPTIVE FOLLOW-UP QUESTION
# ============================================================

def generate_follow_up_question(
    concept,
    original_question,
    student_answer,
    level="Beginner",
    language="English",
    simplify=False
):
    """Generate a fresh mastery check after a targeted re-teach."""

    difficulty = "very simple and concrete" if simplify else "appropriate"
    prompt = f"""
You are an adaptive teacher. Write ONE new follow-up question that checks
whether a student now understands the concept after re-teaching.

Concept: {concept}
Original question: {original_question}
Student's earlier answer: {student_answer}
Student level: {level}
Preferred language: {language}

The new question must test the same learning goal but use a different
example or framing. Make it {difficulty} for this student. Do not repeat
the original question, give the answer, add feedback, or use Markdown.
Return only the question.
"""

    try:
        question = generate_text(prompt, max_tokens=180)
        if question and question.strip():
            return clean_response(question)
    except Exception as error:
        print("Follow-up question generation error:", error)

    if simplify:
        return f"In one simple sentence, what is the main idea of {concept}?"

    return f"Using a different example, how would you explain {concept}?"


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
10. If the answer is Partially Correct or Needs Improvement,
    identify the SPECIFIC misconception behind it - not just
    "the student is wrong", but the actual incorrect idea they
    seem to hold (e.g. "thinks correlation always implies
    causation", "confuses velocity with acceleration", "believes
    the mitochondria produces sugar instead of energy"). Base
    this only on what their answer actually suggests - never
    invent a misconception that isn't supported by their wording.
    If the answer is Correct, or if it's wrong in a generic
    "didn't study this" way with no specific misconception
    visible, write exactly: None

Use this structure:

Result:
Correct / Partially Correct / Needs Improvement

Feedback:
...

Improvement:
...

Misconception:
...(the specific wrong idea, in one sentence - or "None")

Return only the feedback.
"""

    try:

        result = generate_text(
            prompt,
            max_tokens=700
        )

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
            "और मुख्य अवधारणा को अपने शब्दों में समझाने का प्रयास करें।\n\n"
            "### Misconception\n"
            "None"
        )

    elif language == "Hinglish":

        return (
            "### Result\n"
            "Answer evaluate nahi ho saka.\n\n"
            "### Feedback\n"
            "Study material ko dobara dekhiye aur "
            "main concept ko apne words mein explain kijiye.\n\n"
            "### Misconception\n"
            "None"
        )

    else:

        return (
            "### Result\n"
            "The answer could not be evaluated.\n\n"
            "### Feedback\n"
            "Review the study material and try "
            "explaining the main concept in your own words.\n\n"
            "### Misconception\n"
            "None"
        )
