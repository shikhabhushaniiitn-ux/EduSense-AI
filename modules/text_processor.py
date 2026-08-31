import re


def clean_text(text):
    """Clean extracted PDF text."""

    # Replace multiple spaces with one space
    text = re.sub(r"\s+", " ", text)

    # Remove leading and trailing spaces
    text = text.strip()

    return text


def split_text_into_chunks(text, chunk_size=1000):
    """Split text into smaller chunks."""

    words = text.split()

    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)

    return chunks