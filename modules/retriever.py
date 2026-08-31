from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def find_relevant_chunks(
    question,
    chunks,
    top_k=3
):
    """Find the most relevant chunks for a question."""

    if not question.strip():
        return []

    if not chunks:
        return []

    # Create TF-IDF representation
    vectorizer = TfidfVectorizer(
        stop_words="english"
    )

    documents = chunks + [question]

    tfidf_matrix = vectorizer.fit_transform(
        documents
    )

    # Compare question with chunks
    similarities = cosine_similarity(
        tfidf_matrix[-1],
        tfidf_matrix[:-1]
    ).flatten()

    # Get indexes of most relevant chunks
    ranked_indexes = similarities.argsort()[::-1]

    relevant_chunks = []

    for index in ranked_indexes[:top_k]:

        if similarities[index] > 0:

            relevant_chunks.append(
                chunks[index]
            )

    return relevant_chunks