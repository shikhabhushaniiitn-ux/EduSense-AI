import re


def clean_text(text):
    """Clean extracted PDF text."""

    # Replace multiple spaces/newlines
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    # Remove unusual control characters
    text = re.sub(
        r"[^\x00-\x7F]+",
        " ",
        text
    )

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