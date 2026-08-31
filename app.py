import streamlit as st

from modules.pdf_processor import (
    extract_text_from_pdf,
    get_pdf_page_count
)

from modules.text_processor import (
    clean_text,
    split_text_into_chunks
)


# Page configuration
st.set_page_config(
    page_title="EduSense AI",
    page_icon="🎓",
    layout="wide"
)


# Header
st.title("🎓 EduSense AI")

st.subheader("AI-Powered Learning Assistant")

st.write(
    "Upload your study material and explore its content."
)


# Sidebar
with st.sidebar:
    st.header("📚 Learning Tools")
    st.write("Upload a PDF to get started.")


# PDF uploader
uploaded_file = st.file_uploader(
    "📄 Upload your study material",
    type=["pdf"]
)


# Process uploaded PDF
if uploaded_file is not None:

    st.success(
        f"Uploaded: {uploaded_file.name}"
    )

    # Get page count
    page_count = get_pdf_page_count(
        uploaded_file
    )

    st.info(
        f"📑 Total pages: {page_count}"
    )

    # Extract text
    text = extract_text_from_pdf(
        uploaded_file
    )

    # Clean extracted text
    cleaned_text = clean_text(
        text
    )

    # Split text into chunks
    chunks = split_text_into_chunks(
        cleaned_text,
        chunk_size=1000
    )

    # Check whether text was extracted
    if cleaned_text:

        # Display extracted content
        st.subheader("📖 Extracted Content")

        st.text_area(
            "Study Material",
            cleaned_text,
            height=500
        )

        # Document statistics
        words = cleaned_text.split()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "📄 Pages",
                page_count
            )

        with col2:
            st.metric(
                "📝 Words",
                len(words)
            )

        with col3:
            st.metric(
                "🔤 Characters",
                len(cleaned_text)
            )

        # Display text chunks
        st.subheader("✂️ Text Chunks")

        st.write(
            f"Document divided into {len(chunks)} chunks."
        )

        # Show first 5 chunks
        for i, chunk in enumerate(chunks[:5]):

            with st.expander(
                f"Chunk {i + 1}"
            ):
                st.write(chunk)

    else:

        st.warning(
            "⚠️ No text could be extracted from this PDF."
        )