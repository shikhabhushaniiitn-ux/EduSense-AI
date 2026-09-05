import re


def clean_text(text):
    """
    Clean extracted document text.
    Preserves multilingual scripts (Devanagari, Hindi, Tamil, etc.)
    and mathematical symbols while removing unprintable control codes.
    """
    if not text:
        return ""

    # Replace multiple spaces/newlines with single space
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    # Remove unprintable control characters (except newline, carriage return, tab)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)

    return text.strip()


def split_text_into_chunks(
    text,
    chunk_size=250,
    overlap=50
):
    """
    Split text into smaller word-based chunks.

    chunk_size = number of words
    overlap = number of words shared
    between consecutive chunks
    """

    # Split into words
    words = text.split()

    chunks = []

    # Move through the document
    start = 0

    while start < len(words):

        end = start + chunk_size

        # Create chunk
        chunk = " ".join(
            words[start:end]
        )

        chunks.append(
            chunk
        )

        # Stop when document ends
        if end >= len(words):
            break

        # Move forward with overlap
        start = end - overlap

    return chunks