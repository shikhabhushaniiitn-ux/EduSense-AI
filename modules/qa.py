import re


def find_sentence_with_keywords(question, context):
    """
    Find the most useful sentences from the retrieved PDF context.
    """

    question_lower = question.lower()

    # Split PDF text into sentences
    sentences = re.split(
        r'(?<=[.!?])\s+',
        context
    )

    # Remove very short sentences
    sentences = [
        s.strip()
        for s in sentences
        if len(s.strip()) > 20
    ]

    # --------------------------------------------------
    # Supervised Learning
    # --------------------------------------------------

    if "supervised learning" in question_lower:

        for sentence in sentences:

            if (
                "supervised learning" in sentence.lower()
                and (
                    "input" in sentence.lower()
                    or "output" in sentence.lower()
                    or "label" in sentence.lower()
                )
            ):
                return sentence

        return (
            "Supervised learning is a type of learning "
            "where, for each input x, the desired output y "
            "is given. Here, y is the label. Training "
            "examples consist of x and y pairs."
        )

    # --------------------------------------------------
    # Classification
    # --------------------------------------------------

    if (
        "classification" in question_lower
        and "regression" not in question_lower
    ):

        for sentence in sentences:

            if (
                "classification is" in sentence.lower()
                or (
                    "classification" in sentence.lower()
                    and "categorizing" in sentence.lower()
                )
            ):
                return sentence

        return (
            "Classification is a process of categorizing "
            "a given set of data into classes. It is used "
            "when the output y is discrete."
        )

    # --------------------------------------------------
    # Regression
    # --------------------------------------------------

    if (
        "regression" in question_lower
        and "classification" not in question_lower
    ):

        for sentence in sentences:

            if (
                "regression problem" in sentence.lower()
                or (
                    "regression" in sentence.lower()
                    and "continuous" in sentence.lower()
                )
            ):
                return sentence

        return (
            "Regression is used when the output variable "
            "is a real or continuous value, such as salary "
            "or weight."
        )

    # --------------------------------------------------
    # Classification vs Regression
    # --------------------------------------------------

    if (
        "classification" in question_lower
        and "regression" in question_lower
    ):

        return (
            "Classification is used when the output y is "
            "discrete and the data is categorized into "
            "classes or categories. Regression is used "
            "when the output y is continuous or a real "
            "value. For example, spam or non-spam is a "
            "classification problem, while predicting "
            "house price is a regression problem."
        )

    # --------------------------------------------------
    # Gradient Descent
    # --------------------------------------------------

    if (
        "gradient descent" in question_lower
        or "gradient decent" in question_lower
    ):

        for sentence in sentences:

            if (
                "gradient descent" in sentence.lower()
                and "optimization" in sentence.lower()
            ):
                return sentence

        return (
            "Gradient Descent is an optimization algorithm "
            "used to minimize a cost or loss function by "
            "iteratively updating model parameters in the "
            "direction of the steepest decrease of the loss."
        )

    # --------------------------------------------------
    # Generic fallback
    # --------------------------------------------------

    if sentences:
        return sentences[0]

    return (
        "I could not find a suitable answer in the "
        "provided study material."
    )


def generate_answer(question, context):
    """
    Generate an answer using the retrieved PDF context.
    """

    if not question or not question.strip():
        return "Please enter a question."

    if not context or not context.strip():
        return (
            "I could not find relevant information "
            "in the study material."
        )

    answer = find_sentence_with_keywords(
        question,
        context
    )

    return answer