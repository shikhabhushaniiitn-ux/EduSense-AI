import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# Load embedding model only once (unchanged)
model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


# ============================================================
# BUILD INDEX (call this ONCE per uploaded document)
# ============================================================

def build_chunk_index(chunks):
    """
    Embed all chunks and build a FAISS index ONCE.

    Returns a small dict that app.py stores in
    st.session_state (e.g. st.session_state.chunk_index).
    Re-run this only when the chunks change (new upload).
    """

    if not chunks:
        return None

    chunk_embeddings = model.encode(
        chunks,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    dimension = chunk_embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)
    index.add(chunk_embeddings.astype("float32"))

    return {
        "index": index,
        "chunks": chunks,
    }


# ============================================================
# FIND RELEVANT CHUNKS (call this on EVERY question)
# ============================================================

def find_relevant_chunks(question, chunk_index, top_k=3):
    """
    Find semantically relevant chunks using a pre-built
    FAISS index. Only the question gets embedded here -
    the document chunks were already embedded once in
    build_chunk_index().

    `chunk_index` is the dict returned by build_chunk_index().
    """

    if not question or not question.strip():
        return []

    if not chunk_index or not chunk_index.get("chunks"):
        return []

    index = chunk_index["index"]
    chunks = chunk_index["chunks"]

    # Only the question gets embedded now - the expensive
    # part (embedding every chunk) already happened once.
    question_embedding = model.encode(
        [question],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    scores, indexes = index.search(
        question_embedding.astype("float32"),
        min(top_k, len(chunks))
    )

    relevant_chunks = []

    for score, chunk_index_pos in zip(scores[0], indexes[0]):
        if chunk_index_pos == -1:
            continue
        relevant_chunks.append(chunks[chunk_index_pos])

    return relevant_chunks