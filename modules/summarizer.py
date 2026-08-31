from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


MODEL_NAME = "sshleifer/distilbart-cnn-12-6"


# Load the tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)


def generate_summary(text):
    """Generate a summary from study material."""

    if not text or not text.strip():
        return "No text available for summarization."

    # Use a reasonable amount of text
    text = text[:5000]

    # Convert text into tokens
    inputs = tokenizer(
        text,
        return_tensors="pt",
        max_length=1024,
        truncation=True
    )

    # Generate summary
    summary_ids = model.generate(
        inputs["input_ids"],
        max_length=150,
        min_length=30,
        num_beams=4,
        early_stopping=True
    )

    # Convert generated tokens into readable text
    summary = tokenizer.decode(
        summary_ids[0],
        skip_special_tokens=True
    )

    return summary.strip()


