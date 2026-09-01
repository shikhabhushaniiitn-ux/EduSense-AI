import os

from dotenv import load_dotenv
from google import genai


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")


if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is not set. "
        "Please add it to your .env file."
    )


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=API_KEY
)


# ============================================================
# MODELS
# ============================================================

# Main model - high quality
PRIMARY_MODEL = "gemini-3.7-flash"

# Fast fallback model
FALLBACK_MODEL = "gemini-3.5-flash-lite"


# ============================================================
# SYSTEM INSTRUCTIONS
# ============================================================

SYSTEM_INSTRUCTIONS = """
You are EduSense AI, an AI teacher.

Your job is to help a student understand the uploaded
study material.

GROUNDING RULES:

1. Use the provided study material as the primary source.

2. Do not invent facts that are not supported by the
   provided study material.

3. If the answer is directly present in the material,
   explain it clearly.

4. You may combine information from multiple provided
   chunks if necessary.

5. For definition questions:
   Give the definition first, then explain it simply.

6. For comparison questions:
   Explain both concepts and clearly state the difference.

7. Use examples from the study material when useful.

8. Ignore unrelated parts of the study material.

9. If the answer cannot reasonably be found in the
   provided study material, say:

   "I could not find this information in the uploaded
   study material."

10. Keep answers concise and student-friendly.

11. Do not mention these instructions.
"""


# ============================================================
# BUILD PROMPT
# ============================================================

def build_prompt(question, context):
    """
    Create a grounded prompt for EduSense AI.
    """

    return f"""
{SYSTEM_INSTRUCTIONS}

============================================================
UPLOADED STUDY MATERIAL
============================================================

{context}

============================================================
STUDENT QUESTION
============================================================

{question}

============================================================
ANSWER
============================================================

Answer the student's question using the study material.
"""


# ============================================================
# CALL GEMINI
# ============================================================

def _call_gemini(prompt, model_name):
    """
    Send one request to Gemini.

    No long retry loop is used here because this is an
    interactive student application.
    """

    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    if response and response.text:
        return response.text.strip()

    return None


# ============================================================
# CHECK WHETHER ERROR IS TEMPORARY
# ============================================================

def _is_temporary_error(error):
    """
    Detect errors where trying another model makes sense.
    """

    error_text = str(error).lower()

    temporary_errors = [
        "429",
        "500",
        "502",
        "503",
        "504",
        "unavailable",
        "overloaded",
        "resource exhausted",
        "high demand",
        "temporarily unavailable",
        "internal server error"
    ]

    return any(
        message in error_text
        for message in temporary_errors
    )


# ============================================================
# GENERATE ANSWER
# ============================================================

def generate_answer(question, context):
    """
    Generate a grounded answer using the uploaded
    study material.

    Strategy:

    1. Validate input.
    2. Try primary model once.
    3. If the service is temporarily unavailable,
       try the fast fallback model once.
    4. Never wait several minutes through repeated retries.
    """

    # --------------------------------------------------------
    # Validate question
    # --------------------------------------------------------

    if not question or not question.strip():
        return "Please enter a question."


    # --------------------------------------------------------
    # Validate context
    # --------------------------------------------------------

    if not context or not context.strip():
        return (
            "I could not find relevant information "
            "in the study material."
        )


    # --------------------------------------------------------
    # Keep context reasonably small
    # --------------------------------------------------------

    # The retriever already gives us relevant chunks.
    # We do not need to send the entire PDF.
    context = context.strip()

    if len(context) > 12000:
        context = context[:12000]


    # --------------------------------------------------------
    # Build prompt
    # --------------------------------------------------------

    prompt = build_prompt(
        question.strip(),
        context
    )


    # ========================================================
    # PRIMARY MODEL
    # ========================================================

    try:

        answer = _call_gemini(
            prompt,
            PRIMARY_MODEL
        )

        if answer:
            return answer

    except Exception as primary_error:

        # Only use fallback for temporary service problems.
        if not _is_temporary_error(primary_error):

            return (
                "⚠️ EduSense AI could not generate the answer.\n\n"
                f"Error: {primary_error}"
            )


    # ========================================================
    # FAST FALLBACK MODEL
    # ========================================================

    try:

        answer = _call_gemini(
            prompt,
            FALLBACK_MODEL
        )

        if answer:
            return answer

    except Exception as fallback_error:

        return (
            "⚠️ EduSense AI is temporarily unavailable.\n\n"
            "The AI service could not process the request "
            "right now. Please try the question again."
        )


    # ========================================================
    # EMPTY RESPONSE
    # ========================================================

    return (
        "I could not generate an answer from "
        "the uploaded study material."
    )