
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


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="EduSense AI",
    page_icon="🎓",
    layout="wide"
)


# ============================================================
# SESSION STATE
# ============================================================

if "document_text" not in st.session_state:
    st.session_state.document_text = ""

if "cleaned_text" not in st.session_state:
    st.session_state.cleaned_text = ""

if "chunks" not in st.session_state:
    st.session_state.chunks = []

if "page_count" not in st.session_state:
    st.session_state.page_count = 0

if "file_name" not in st.session_state:
    st.session_state.file_name = ""

if "summary" not in st.session_state:
    st.session_state.summary = ""

if "answer" not in st.session_state:
    st.session_state.answer = ""

if "source_chunks" not in st.session_state:
    st.session_state.source_chunks = []


# ============================================================
# HEADER
# ============================================================

st.title("🎓 EduSense AI")

st.subheader(
    "AI-Powered Adaptive Learning Assistant"
)

st.write(
    "Upload your study material and let EduSense AI "
    "help you understand, revise and learn it."
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("📚 Learning Tools")

    st.write(
        "Upload a study document to get started."
    )

    st.divider()

    st.info(
        """
        **Current Features**

        📄 PDF Processing  
        🧠 Semantic Search  
        🔍 Document Q&A  
        📝 AI Summary  
        📚 Source-based Answers

        **Coming Next**

        🎯 Personalized Learning  
        🧑‍🏫 AI Teaching  
        ❓ Adaptive Quiz  
        📊 Learning Report
        """
    )


# ============================================================
# DOCUMENT UPLOAD
# ============================================================

uploaded_file = st.file_uploader(
    "📄 Upload your study material",
    type=["pdf"],
    help="Upload a PDF containing your study material."
)


# ============================================================
# PROCESS DOCUMENT
# ============================================================

if uploaded_file is not None:

    # --------------------------------------------------------
    # Process only when a new file is uploaded
    # --------------------------------------------------------

    if st.session_state.file_name != uploaded_file.name:

        # Reset previous document information
        st.session_state.document_text = ""
        st.session_state.cleaned_text = ""
        st.session_state.chunks = []
        st.session_state.page_count = 0
        st.session_state.summary = ""
        st.session_state.answer = ""
        st.session_state.source_chunks = ""

        with st.spinner(
            "📄 Processing your study material..."
        ):

            try:

                # ------------------------------------------------
                # Page count
                # ------------------------------------------------

                page_count = get_pdf_page_count(
                    uploaded_file
                )

                # ------------------------------------------------
                # Extract text
                # ------------------------------------------------

                text = extract_text_from_pdf(
                    uploaded_file
                )

                # ------------------------------------------------
                # Clean text
                # ------------------------------------------------

                cleaned_text = clean_text(
                    text
                )

                # ------------------------------------------------
                # Create chunks
                # ------------------------------------------------

                chunks = split_text_into_chunks(
                    cleaned_text,
                    chunk_size=120,
                    overlap=30
                )

                # ------------------------------------------------
                # Save document information
                # ------------------------------------------------

                st.session_state.document_text = text
                st.session_state.cleaned_text = cleaned_text
                st.session_state.chunks = chunks
                st.session_state.page_count = page_count
                st.session_state.file_name = uploaded_file.name

            except Exception as e:

                st.error(
                    f"❌ Could not process the PDF: {e}"
                )


# ============================================================
# DOCUMENT READY
# ============================================================

if st.session_state.cleaned_text:

    st.success(
        f"✅ Ready: {st.session_state.file_name}"
    )


    # ========================================================
    # DOCUMENT STATISTICS
    # ========================================================

    words = st.session_state.cleaned_text.split()

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "📄 Pages",
            st.session_state.page_count
        )

    with col2:

        st.metric(
            "📝 Words",
            len(words)
        )

    with col3:

        st.metric(
            "✂️ Chunks",
            len(st.session_state.chunks)
        )


    # ========================================================
    # DOCUMENT CONTENT
    # ========================================================

    with st.expander(
        "📖 View extracted study material"
    ):

        st.text_area(
            "Extracted Content",
            st.session_state.cleaned_text,
            height=400
        )


    # ========================================================
    # CHUNKS
    # ========================================================

    with st.expander(
        "✂️ View document chunks"
    ):

        st.write(
            f"Document divided into "
            f"{len(st.session_state.chunks)} chunks."
        )

        for i, chunk in enumerate(
            st.session_state.chunks[:5]
        ):

            st.markdown(
                f"### Chunk {i + 1}"
            )

            st.write(chunk)

            st.divider()


    # ========================================================
    # AI SUMMARY
    # ========================================================

    st.subheader(
        "📝 AI Summary"
    )

    if st.button(
        "✨ Generate Summary",
        key="summary_button"
    ):

        with st.spinner(
            "🤖 Generating summary..."
        ):

            try:

                summary = generate_summary(
                    st.session_state.cleaned_text
                )

                st.session_state.summary = summary

            except Exception as e:

                st.error(
                    f"❌ Could not generate summary: {e}"
                )


    # --------------------------------------------------------
    # Display saved summary
    # --------------------------------------------------------

    if st.session_state.summary:

        st.markdown(
            "### 📌 Summary"
        )

        st.write(
            st.session_state.summary
        )


    # ========================================================
    # QUESTION ANSWERING
    # ========================================================

    st.divider()

    st.subheader(
        "📚 Ask Your Study Material"
    )

    st.write(
        "Ask any question about the uploaded study material."
    )


    # --------------------------------------------------------
    # Question input
    # --------------------------------------------------------

    question = st.text_input(
        "❓ Enter your question",
        placeholder=(
            "Example: What is supervised learning?"
        ),
        key="question_input"
    )


    # --------------------------------------------------------
    # Ask button
    # --------------------------------------------------------

    if st.button(
        "🔍 Ask EduSense AI",
        key="ask_button"
    ):

        if not question.strip():

            st.warning(
                "⚠️ Please enter a question."
            )

        else:

            # ------------------------------------------------
            # Retrieve relevant chunks
            # ------------------------------------------------

            with st.spinner(
                "🔎 Searching your study material..."
            ):

                try:

                    relevant_chunks = (
                        find_relevant_chunks(
                            question,
                            st.session_state.chunks,
                            top_k=3
                        )
                    )

                except Exception as e:

                    relevant_chunks = []

                    st.error(
                        f"❌ Search error: {e}"
                    )


            # ------------------------------------------------
            # Check retrieval
            # ------------------------------------------------

            if not relevant_chunks:

                st.warning(
                    "⚠️ I could not find relevant "
                    "information in your study material."
                )

                st.session_state.answer = ""
                st.session_state.source_chunks = []


            else:

                # ------------------------------------------------
                # Combine retrieved chunks
                # ------------------------------------------------

                context = "\n\n".join(
                    relevant_chunks
                )


                # ------------------------------------------------
                # Generate grounded answer
                # ------------------------------------------------

                with st.spinner(
                    "🤖 Generating answer from your study material..."
                ):

                    try:

                        answer = generate_answer(
                            question,
                            context
                        )

                        st.session_state.answer = answer
                        st.session_state.source_chunks = (
                            relevant_chunks
                        )

                    except Exception as e:

                        st.session_state.answer = ""

                        st.error(
                            f"❌ Could not generate answer: {e}"
                        )


    # ========================================================
    # DISPLAY ANSWER
    # ========================================================

    if st.session_state.answer:

        st.markdown(
            "### 🤖 Answer"
        )

        st.write(
            st.session_state.answer
        )


        # ----------------------------------------------------
        # Source material
        # ----------------------------------------------------

        if st.session_state.source_chunks:

            with st.expander(
                "📚 View source material"
            ):

                for i, chunk in enumerate(
                    st.session_state.source_chunks
                ):

                    st.markdown(
                        f"**Relevant Chunk {i + 1}**"
                    )

                    st.write(
                        chunk
                    )

                    st.divider()


    # ========================================================
    # FUTURE AI TEACHER SECTION
    # ========================================================

    st.divider()

    st.subheader(
        "🧑‍🏫 AI Teacher"
    )

    st.info(
        "🚧 Adaptive teaching mode will be added here next."
    )


    # ========================================================
    # FUTURE QUIZ SECTION
    # ========================================================

    st.subheader(
        "❓ Knowledge Check"
    )

    st.info(
        "🚧 Adaptive quiz and answer evaluation will be added next."
    )


    # ========================================================
    # FUTURE LEARNING REPORT
    # ========================================================

    st.subheader(
        "📊 Learning Report"
    )

    st.info(
        "🚧 Personalized learning report will be generated after the teaching and quiz modules are added."
    )


# ============================================================
# NO DOCUMENT
# ============================================================

else:

    st.info(
        "👆 Upload a PDF above to begin learning with EduSense AI."
    )

