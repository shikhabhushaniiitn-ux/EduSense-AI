from modules.ai_client import generate_ai_response


# ============================================================
# GENERATE STUDY MATERIAL FROM A TOPIC
# ============================================================
#
# This is the "second input mode" the requirement doc asks for -
# a student can type a topic ("Photosynthesis", "Newton's Laws
# of Motion") instead of uploading a PDF.
#
# Rather than building a second, parallel pipeline for topic-only
# study, this generates a textbook-style passage of text and
# plugs it into app.py's EXISTING document_text / cleaned_text
# flow. Everything downstream - chunking, semantic search, the
# lesson planner (including heading detection, sequencing, and
# depth scaling), the AI teacher, and the quiz - already works
# on "text extracted from a document", so it works identically
# here without any of those modules needing to know the
# difference.
# ============================================================

def generate_study_material_from_topic(
    topic,
    level="Beginner"
):
    """
    Generate a well-structured study material passage for a
    topic the student wants to learn, with no PDF required.

    Returns the generated text (str). Raises ValueError with a
    student-facing message if generation fails, so app.py can
    show it directly with st.error().
    """

    if not topic or not topic.strip():
        raise ValueError(
            "Please enter a topic to learn about."
        )

    topic = topic.strip()

    if level not in ("Beginner", "Intermediate", "Advanced"):
        level = "Beginner"

    depth_hint = {

        "Beginner": (
            "Keep it accessible - simple language, basic "
            "definitions, everyday examples."
        ),

        "Intermediate": (
            "Include moderate depth - clear definitions, how "
            "concepts relate to each other, and a few worked "
            "examples."
        ),

        "Advanced": (
            "Include real depth - precise definitions, "
            "important edge cases, relevant formulas/technical "
            "detail, and how each concept builds on the ones "
            "before it."
        )

    }[level]

    prompt = f"""
You are writing a study material chapter for a student who wants
to learn about:

"{topic}"

Student level: {level}
{depth_hint}

Write a well-structured, textbook-style chapter covering this
topic from fundamentals to more advanced related ideas, IN A
LOGICAL ORDER - foundational concepts first, anything more
advanced only after its prerequisite has been introduced.

FORMAT RULES (important - this text will be parsed
automatically by other software, follow them exactly):

- Use clear section headings, each on its OWN line, written
  exactly like this: "1. <Heading>", "2. <Heading>", and so on.
  Do not use markdown symbols like # or **.
- Each heading is followed by 2-4 plain paragraphs of
  explanation (no markdown formatting inside paragraphs either).
- Include at least 5 and at most 9 sections.
- Do not include a title page, table of contents, or references
  section.
- Do not mention that you are an AI or that this text was
  generated.
- Only write real, accurate information about the topic.

If "{topic}" is too vague, nonsensical, or not something with
real educational content to teach (for example: gibberish, or
something with no factual subject matter), instead write ONLY
one section:
"1. Topic Not Recognized" followed by one paragraph explaining
that this topic could not be understood, and suggesting the
student try being more specific.

Begin directly with section "1." - no introduction before it.
"""

    result = generate_ai_response(
        prompt,
        max_tokens=3500,
        temperature=0.3
    )

    if not result or not result.strip():

        # One retry - a single generation call failing outright
        # (as opposed to a malformed multi-step JSON response) is
        # usually transient.
        result = generate_ai_response(
            prompt,
            max_tokens=3500,
            temperature=0.3
        )

    if not result or not result.strip():

        raise ValueError(
            "Could not generate study material for this topic "
            "right now. Please try again, or try a more specific "
            "topic."
        )

    result = result.strip()

    if "Topic Not Recognized" in result[:200]:

        raise ValueError(
            f"\"{topic}\" wasn't specific enough to build a "
            "lesson from. Try being more precise, e.g. "
            "\"Photosynthesis\" instead of \"biology stuff\"."
        )

    return result