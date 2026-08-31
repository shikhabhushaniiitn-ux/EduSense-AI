from transformers import AutoTokenizer, AutoModelForQuestionAnswering


MODEL_NAME = "distilbert-base-cased-distilled-squad"


# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)

# Load question-answering model
model = AutoModelForQuestionAnswering.from_pretrained(
    MODEL_NAME
)


def generate_answer(question, context):
    """Generate an answer using the provided context."""

    if not question.strip():
        return "Please enter a question."

    if not context.strip():
        return "No relevant information was found."

    # Tokenize question and context
    inputs = tokenizer(
        question,
        context,
        return_tensors="pt",
        max_length=512,
        truncation=True
    )

    # Generate model output
    outputs = model(
        **inputs
    )

    # Find answer start and end positions
    start_index = outputs.start_logits.argmax()
    end_index = outputs.end_logits.argmax()

    # Make sure the answer positions are valid
    if end_index < start_index:
        return "I could not find an answer in the provided material."

    # Extract answer tokens
    answer_tokens = inputs["input_ids"][
        0,
        start_index:end_index + 1
    ]

    # Convert tokens into text
    answer = tokenizer.decode(
        answer_tokens,
        skip_special_tokens=True
    )

    if not answer.strip():
        return "I could not find an answer in the provided material."

    return answer.strip()