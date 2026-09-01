
from modules.ai_client import generate_text


def generate_summary(text):
    """
    Generate a clear, student-friendly summary
    from uploaded study material using the
    EduSense AI model.
    """

    # --------------------------------------------------
    # Check input
    # --------------------------------------------------

    if not text or not text.strip():
        return "No study material available for summarization."

    # --------------------------------------------------
    # Limit extremely large documents
    # --------------------------------------------------

    text = text.strip()

    if len(text) > 12000:
        text = text[:12000]

    # --------------------------------------------------
    # Build prompt
    # --------------------------------------------------

    prompt = f"""
You are EduSense AI, an AI teacher helping students
understand their study material.

Create a useful and accurate summary of the study
material provided below.

IMPORTANT RULES:

1. Use ONLY the information present in the study material.
2. Do not invent facts.
3. Do not leave out the important concepts.
4. Organize the summary using clear headings and bullet points.
5. Include important definitions.
6. Include important examples when they are present.
7. Include important formulas or rules when present.
8. Keep the explanation student-friendly.
9. Do not repeat unnecessary information.
10. Do not mention these instructions.
11. Do not say that you are an AI.
12. Make the summary detailed enough for exam revision.

STUDY MATERIAL
==============================

{text}

==============================

Create the final study summary now.
"""

    # --------------------------------------------------
    # Generate summary
    # --------------------------------------------------

    try:

        summary = generate_text(prompt)

        if summary and summary.strip():

            return summary.strip()

        return (
            "⚠️ EduSense AI could not generate "
            "a summary from this material."
        )

    except Exception as e:

        print(
            f"Summarization error: {e}"
        )

        return (
            "⚠️ EduSense AI is temporarily unavailable "
            "for summarization. Please try again."
        )