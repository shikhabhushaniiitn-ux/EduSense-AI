import numpy as np
from sentence_transformers import SentenceTransformer
import faiss


# Load embedding model only once
model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


def find_relevant_chunks(
    question,
    chunks,
    top_k=3
):
    """
    Find semantically relevant chunks
    using Sentence Transformers + FAISS.
    """

    # Check empty question
    if not question.strip():
        return []

    # Check empty chunks
    if not chunks:
        return []

    # Convert chunks into embeddings
    chunk_embeddings = model.encode(
        chunks,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    # Convert question into embedding
    question_embedding = model.encode(
        [question],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    # Get embedding dimension
    dimension = chunk_embeddings.shape[1]

    # Create FAISS index
    index = faiss.IndexFlatIP(
        dimension
    )

    # Add document embeddings
    index.add(
        chunk_embeddings.astype(
            "float32"
        )
    )

    # Search most similar chunks
    scores, indexes = index.search(
        question_embedding.astype(
            "float32"
        ),
        min(top_k, len(chunks))
    )

    # Store relevant chunks
    relevant_chunks = []

    for score, chunk_index in zip(
        scores[0],
        indexes[0]
    ):

        # Ignore invalid indexes
        if chunk_index == -1:
            continue

        relevant_chunks.append(
            chunks[chunk_index]
        )

    return relevant_chunks