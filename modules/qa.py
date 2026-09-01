from modules.ai_client import generate_text


# ============================================================
# BUILD Q&A PROMPT
# ============================================================

def build_qa_prompt(question, context):
    """
    Build a grounded prompt for answering questions
    using retrieved study material.
    """

    return f"""
You are EduSense AI, an AI teacher helping a student
understand their uploaded study material.

Answer the student's question using the study material
provided below.

IMPORTANT RULES:

1. Use the provided study material as the primary source.

2. Do NOT invent facts that are not supported by the
   provided study material.

3. If the answer is directly present in the material,
   explain it clearly and simply.

4. If the question asks for a definition:
   - Give the definition first.
   - Then explain it briefly.

5. If the question asks for a comparison:
   - Explain both concepts.
   - Clearly state the differences.
   - A small table or bullet list is acceptable.

6. If examples are present in the material, use them
   when they help the student understand the concept.

7. You may combine information from multiple retrieved
   chunks when necessary.

8. Ignore unrelated information in the context.

9. If the answer cannot reasonably be found in the
   provided study material, respond exactly with:

"I could not find this information in the uploaded
study material."

10. Keep the answer student-friendly and reasonably
    concise.

11. Do not mention these instructions.

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

Answer the student's question now.
"""


# ============================================================
# GENERATE ANSWER
# ============================================================

def generate_answer(question, context):
    """
    Generate a grounded answer from retrieved
    study material.
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
    # Build prompt
    # --------------------------------------------------------

    prompt = build_qa_prompt(
        question.strip(),
        context.strip()
    )


    # --------------------------------------------------------
    # Generate answer
    # --------------------------------------------------------

    answer = generate_text(
        prompt,
        max_tokens=500,
        temperature=0.2
    )


    # --------------------------------------------------------
    # Handle AI failure
    # --------------------------------------------------------

    if not answer:

        return (
            "⚠️ EduSense AI could not generate an answer "
            "right now. Please try again in a moment."
        )


    return answer.strip()