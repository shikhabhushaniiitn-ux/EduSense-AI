import streamlit as st

from modules.pdf_processor import (
    extract_text_from_pdf,
    get_pdf_page_count
)

from modules.text_processor import (
    clean_text,
    split_text_into_chunks
)

from modules.summarizer import (
    generate_summary
)

from modules.retriever import (
    find_relevant_chunks
)

from modules.qa import (
    generate_answer
)


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="EduSense AI",
    page_icon="🎓",
    layout="wide"
)


# --------------------------------------------------
# Header
# --------------------------------------------------

st.title("🎓 EduSense AI")

st.subheader("AI-Powered Learning Assistant")

st.write(
    "Upload your study material and use AI "
    "to understand it."
)


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:
    st.header("📚 Learning Tools")

    st.write(
        "Upload a PDF to get started."
    )


# --------------------------------------------------
# PDF Upload
# --------------------------------------------------

uploaded_file = st.file_uploader(
    "📄 Upload your study material",
    type=["pdf"]
)


# --------------------------------------------------
# Process PDF
# --------------------------------------------------

if uploaded_file is not None:

    st.success(
        f"Uploaded: {uploaded_file.name}"
    )

    # --------------------------------------------------
    # Get page count
    # --------------------------------------------------

    page_count = get_pdf_page_count(
        uploaded_file
    )

    st.info(
        f"📑 Total pages: {page_count}"
    )


    # --------------------------------------------------
    # Extract text
    # --------------------------------------------------

    text = extract_text_from_pdf(
        uploaded_file
    )


    # --------------------------------------------------
    # Clean text
    # --------------------------------------------------

    cleaned_text = clean_text(
        text
    )


    # --------------------------------------------------
    # Split text into chunks
    # --------------------------------------------------

    chunks = split_text_into_chunks(
        cleaned_text,
        chunk_size=120,
        overlap=30
    )


    # --------------------------------------------------
    # Check extracted text
    # --------------------------------------------------

    if cleaned_text:

        # --------------------------------------------------
        # Extracted Content
        # --------------------------------------------------

        st.subheader(
            "📖 Extracted Content"
        )

        st.text_area(
            "Study Material",
            cleaned_text,
            height=400
        )


        # --------------------------------------------------
        # Document Statistics
        # --------------------------------------------------

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
                "✂️ Chunks",
                len(chunks)
            )


        # --------------------------------------------------
        # Text Chunks
        # --------------------------------------------------

        st.subheader(
            "✂️ Text Chunks"
        )

        st.write(
            f"Document divided into "
            f"{len(chunks)} chunks."
        )


        # Show first 5 chunks
        for i, chunk in enumerate(
            chunks[:5]
        ):

            with st.expander(
                f"Chunk {i + 1}"
            ):

                st.write(
                    chunk
                )


        # --------------------------------------------------
        # AI Summary
        # --------------------------------------------------

        st.subheader(
            "📝 AI Summary"
        )

        if st.button(
            "✨ Generate Summary"
        ):

            with st.spinner(
                "🤖 AI is generating "
                "your summary..."
            ):

                try:

                    summary = generate_summary(
                        cleaned_text
                    )


                    if summary:

                        st.success(
                            "Summary generated!"
                        )

                        st.markdown(
                            "### 📌 Summary"
                        )

                        st.write(
                            summary
                        )

                    else:

                        st.warning(
                            "The AI returned "
                            "an empty summary."
                        )


                except Exception as e:

                    st.error(
                        f"❌ Could not generate "
                        f"summary: {e}"
                    )


        # --------------------------------------------------
        # Question Answering
        # --------------------------------------------------

        st.subheader(
            "📚 Ask Your Study Material"
        )

        st.write(
            "Ask a question about the "
            "uploaded PDF."
        )


        # Question input
        question = st.text_input(
            "❓ Enter your question",
            placeholder=(
                "Example: What is supervised learning?"
            )
        )


        # Ask button
        if st.button(
            "🔍 Ask EduSense AI"
        ):

            # Check question
            if not question.strip():

                st.warning(
                    "⚠️ Please enter a question."
                )


            else:

                # --------------------------------------------------
                # Retrieve relevant chunks
                # --------------------------------------------------

                with st.spinner(
                    "🔎 Searching your study material..."
                ):

                    relevant_chunks = (
                        find_relevant_chunks(
                            question,
                            chunks,
                            top_k=3
                        )
                    )


                # --------------------------------------------------
                # Check retrieval result
                # --------------------------------------------------

                if not relevant_chunks:

                    st.warning(
                        "⚠️ I could not find "
                        "relevant information "
                        "in your document."
                    )


                else:

                    # --------------------------------------------------
                    # Combine relevant chunks
                    # --------------------------------------------------

                    context = "\n\n".join(
                        relevant_chunks
                    )


                    # --------------------------------------------------
                    # Generate Answer
                    # --------------------------------------------------

                    with st.spinner(
                        "🤖 Generating answer..."
                    ):

                        try:

                            answer = generate_answer(
                                question,
                                context
                            )


                            # --------------------------------------------------
                            # Display Answer
                            # --------------------------------------------------

                            st.markdown(
                                "### 🤖 Answer"
                            )

                            st.write(
                                answer
                            )


                            # --------------------------------------------------
                            # Source Material
                            # --------------------------------------------------

                            with st.expander(
                                "📚 View source material"
                            ):

                                for i, chunk in enumerate(
                                    relevant_chunks
                                ):

                                    st.markdown(
                                        f"**Relevant "
                                        f"Chunk {i + 1}**"
                                    )

                                    st.write(
                                        chunk
                                    )


                        except Exception as e:

                            st.error(
                                f"❌ Could not "
                                f"generate answer: {e}"
                            )


    # --------------------------------------------------
    # No extracted text
    # --------------------------------------------------

    else:

        st.warning(
            "⚠️ No text could be extracted "
            "from this PDF."
        )