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

from modules.lesson_planner import (
    generate_lesson_plan
)

from modules.teacher import (
    generate_teacher_explanation
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

defaults = {

    "document_text": "",

    "cleaned_text": "",

    "chunks": [],

    "page_count": 0,

    "file_name": "",

    "summary": "",

    "answer": "",

    "source_chunks": [],

    "lesson_plan": None,

    "lesson_started": False,

    "current_section": 0,

    "teacher_explanation": "",

    "quiz_answers": {},

    "quiz_submitted": False,

    "quiz_score": 0
}


for key, value in defaults.items():

    if key not in st.session_state:

        st.session_state[key] = value


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
        🎓 Lesson Planner
        🧑‍🏫 AI Teacher
        ❓ Knowledge Check
        📊 Quiz Score
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

    if (
        st.session_state.file_name
        != uploaded_file.name
    ):

        # Reset document information

        st.session_state.document_text = ""
        st.session_state.cleaned_text = ""
        st.session_state.chunks = []
        st.session_state.page_count = 0
        st.session_state.summary = ""
        st.session_state.answer = ""
        st.session_state.source_chunks = []

        st.session_state.lesson_plan = None
        st.session_state.lesson_started = False
        st.session_state.current_section = 0
        st.session_state.teacher_explanation = ""

        st.session_state.quiz_answers = {}
        st.session_state.quiz_submitted = False
        st.session_state.quiz_score = 0

        with st.spinner(
            "📄 Processing your study material..."
        ):

            try:

                page_count = get_pdf_page_count(
                    uploaded_file
                )

                text = extract_text_from_pdf(
                    uploaded_file
                )

                cleaned_text = clean_text(
                    text
                )

                chunks = split_text_into_chunks(
                    cleaned_text,
                    chunk_size=120,
                    overlap=30
                )

                st.session_state.document_text = text

                st.session_state.cleaned_text = (
                    cleaned_text
                )

                st.session_state.chunks = chunks

                st.session_state.page_count = (
                    page_count
                )

                st.session_state.file_name = (
                    uploaded_file.name
                )

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

    words = (
        st.session_state.cleaned_text
        .split()
    )

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

    st.divider()

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

    question = st.text_input(
        "❓ Enter your question",
        placeholder=(
            "Example: What is supervised learning?"
        ),
        key="question_input"
    )


    if st.button(
        "🔍 Ask EduSense AI",
        key="ask_button"
    ):

        if not question.strip():

            st.warning(
                "⚠️ Please enter a question."
            )

        else:

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


            if not relevant_chunks:

                st.warning(
                    "⚠️ I could not find relevant "
                    "information in your study material."
                )

                st.session_state.answer = ""

                st.session_state.source_chunks = []

            else:

                context = "\n\n".join(
                    relevant_chunks
                )

                with st.spinner(
                    "🤖 Generating answer..."
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

                    st.write(chunk)

                    st.divider()


    # ========================================================
    # LESSON PLANNER
    # ========================================================

    st.divider()

    st.header(
        "🎓 Personalized Lesson"
    )

    st.write(
        "Create a lesson based on your study material."
    )


    # --------------------------------------------------------
    # Lesson settings
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)


    with col1:

        student_level = st.selectbox(
            "🎓 Student Level",
            [
                "Beginner",
                "Intermediate",
                "Advanced"
            ],
            key="student_level"
        )


    with col2:

        preferred_language = st.selectbox(
            "🌐 Preferred Language",
            [
                "English",
                "Hindi",
                "Hinglish"
            ],
            key="preferred_language"
        )


    with col3:

        lesson_duration = st.selectbox(
            "⏱️ Lesson Duration",
            [
                15,
                20,
                30,
                45
            ],
            index=1,
            format_func=lambda x: f"{x} minutes",
            key="lesson_duration"
        )


    # --------------------------------------------------------
    # Generate lesson plan
    # --------------------------------------------------------

    if st.button(
        "✨ Generate Lesson Plan",
        key="lesson_plan_button"
    ):

        with st.spinner(
            "🤖 Creating your personalized lesson..."
        ):

            try:

                plan = generate_lesson_plan(

                    st.session_state.cleaned_text,

                    student_level,

                    preferred_language,

                    lesson_duration
                )

                st.session_state.lesson_plan = plan

                st.session_state.lesson_started = False

                st.session_state.current_section = 0

                st.session_state.teacher_explanation = ""

                st.session_state.quiz_answers = {}

                st.session_state.quiz_submitted = False

                st.session_state.quiz_score = 0

            except Exception as e:

                st.error(
                    f"❌ Could not create lesson plan: {e}"
                )


    # ========================================================
    # DISPLAY LESSON PLAN
    # ========================================================

    plan = st.session_state.lesson_plan


    if plan:

        st.divider()

        st.header(
            "📘 Lesson Plan"
        )

        st.markdown(
            f"## 📘 {plan.get('topic', 'Lesson')}"
        )


        # ----------------------------------------------------
        # Lesson information
        # ----------------------------------------------------

        info1, info2, info3 = st.columns(3)


        with info1:

            st.metric(
                "🎓 Level",
                plan.get(
                    "level",
                    student_level
                )
            )


        with info2:

            st.metric(
                "🌐 Language",
                plan.get(
                    "language",
                    preferred_language
                )
            )


        with info3:

            st.metric(
                "⏱️ Duration",
                f"{plan.get('duration_minutes', lesson_duration)} min"
            )


        # ----------------------------------------------------
        # Learning objectives
        # ----------------------------------------------------

        st.subheader(
            "🎯 Learning Objectives"
        )

        objectives = plan.get(
            "learning_objectives",
            []
        )

        for objective in objectives:

            st.write(
                f"✅ {objective}"
            )


        # ----------------------------------------------------
        # Sections
        # ----------------------------------------------------

        st.subheader(
            "📖 Lesson Sections"
        )

        sections = plan.get(
            "sections",
            []
        )

        for i, section in enumerate(
            sections
        ):

            title = section.get(
                "title",
                f"Section {i + 1}"
            )

            section_duration = section.get(
                "duration_minutes",
                0
            )

            description = section.get(
                "description",
                ""
            )

            with st.expander(
                f"📚 {i + 1}. {title} — "
                f"{section_duration} min"
            ):

                st.write(
                    description
                )

                key_points = section.get(
                    "key_points",
                    []
                )

                if key_points:

                    st.markdown(
                        "**Key Points:**"
                    )

                    for point in key_points:

                        st.write(
                            f"• {point}"
                        )


        # ====================================================
        # START LESSON
        # ====================================================

        st.divider()

        if not st.session_state.lesson_started:

            st.subheader(
                "🧑‍🏫 Ready to Learn?"
            )

            st.write(
                "Start the lesson to enter AI Teacher mode."
            )

            if st.button(
                "🚀 Start Lesson",
                key="start_lesson_button"
            ):

                st.session_state.lesson_started = True

                st.session_state.current_section = 0

                st.session_state.teacher_explanation = ""

                st.rerun()


        # ====================================================
        # AI TEACHER
        # ====================================================

        if st.session_state.lesson_started:

            st.divider()

            st.header(
                "🧑‍🏫 AI Teacher"
            )

            if not sections:

                st.warning(
                    "No lesson sections are available."
                )

            else:

                current_index = (
                    st.session_state.current_section
                )

                if current_index >= len(sections):

                    current_index = len(sections) - 1

                    st.session_state.current_section = (
                        current_index
                    )


                current_section = sections[
                    current_index
                ]


                # ------------------------------------------------
                # Progress
                # ------------------------------------------------

                progress = (
                    (current_index + 1)
                    / len(sections)
                )

                st.progress(
                    progress
                )

                st.caption(
                    f"Section {current_index + 1} "
                    f"of {len(sections)}"
                )


                # ------------------------------------------------
                # Current section
                # ------------------------------------------------

                section_title = current_section.get(
                    "title",
                    "Lesson Section"
                )

                st.subheader(
                    f"📚 {section_title}"
                )


                # ------------------------------------------------
                # Teach button
                # ------------------------------------------------

                if st.button(
                    "🧑‍🏫 Teach Me This Section",
                    key=f"teach_{current_index}"
                ):

                    with st.spinner(
                        "🤖 AI Teacher is preparing the lesson..."
                    ):

                        explanation = (
                            generate_teacher_explanation(

                                plan.get(
                                    "topic",
                                    "Study Topic"
                                ),

                                section_title,

                                st.session_state.cleaned_text,

                                plan.get(
                                    "level",
                                    "Beginner"
                                ),

                                plan.get(
                                    "language",
                                    "English"
                                )
                            )
                        )

                        st.session_state.teacher_explanation = (
                            explanation
                        )


                # ------------------------------------------------
                # Show explanation
                # ------------------------------------------------

                if st.session_state.teacher_explanation:

                    st.markdown(
                        "### 👨‍🏫 Explanation"
                    )

                    st.write(
                        st.session_state.teacher_explanation
                    )


                # ------------------------------------------------
                # Navigation
                # ------------------------------------------------

                nav1, nav2 = st.columns(2)


                with nav1:

                    if current_index > 0:

                        if st.button(
                            "⬅️ Previous Section",
                            key=f"previous_{current_index}"
                        ):

                            st.session_state.current_section -= 1

                            st.session_state.teacher_explanation = ""

                            st.rerun()


                with nav2:

                    if current_index < len(sections) - 1:

                        if st.button(
                            "Next Section ➡️",
                            key=f"next_{current_index}"
                        ):

                            st.session_state.current_section += 1

                            st.session_state.teacher_explanation = ""

                            st.rerun()

                    else:

                        st.success(
                            "🎉 You completed all lesson sections!"
                        )


            # ====================================================
            # INTERACTIVE QUESTIONS
            # ====================================================

            st.divider()

            st.header(
                "💡 Interactive Questions"
            )

            interactive_questions = plan.get(
                "interactive_questions",
                []
            )


            if interactive_questions:

                for i, item in enumerate(
                    interactive_questions
                ):

                    st.markdown(
                        f"**Question {i + 1}:** "
                        f"{item.get('question', '')}"
                    )

                    st.info(
                        "💡 Think about your answer before continuing."
                    )


            # ====================================================
            # FINAL QUIZ
            # ====================================================

            st.divider()

            st.header(
                "📝 Final Quiz"
            )

            quiz = plan.get(
                "final_quiz",
                []
            )


            if quiz:

                for i, q in enumerate(quiz):

                    question_text = q.get(
                        "question",
                        ""
                    )

                    options = q.get(
                        "options",
                        []
                    )

                    st.markdown(
                        f"**Question {i + 1}:** "
                        f"{question_text}"
                    )

                    answer = st.radio(
                        "Choose your answer:",
                        options,
                        key=f"quiz_question_{i}",
                        index=None
                    )

                    st.session_state.quiz_answers[i] = (
                        answer
                    )


                if st.button(
                    "✅ Submit Quiz",
                    key="submit_quiz"
                ):

                    score = 0

                    for i, q in enumerate(quiz):

                        selected = (
                            st.session_state
                            .quiz_answers
                            .get(i)
                        )

                        correct = q.get(
                            "correct_answer"
                        )

                        if (
                            selected
                            and correct
                            and selected.strip()
                            == correct.strip()
                        ):

                            score += 1


                    st.session_state.quiz_score = score

                    st.session_state.quiz_submitted = True


                # ------------------------------------------------
                # Quiz result
                # ------------------------------------------------

                if st.session_state.quiz_submitted:

                    total = len(quiz)

                    score = (
                        st.session_state.quiz_score
                    )

                    st.success(
                        f"🎉 Your score: "
                        f"{score}/{total}"
                    )

                    if score == total:

                        st.balloons()

                        st.success(
                            "Excellent! You have "
                            "understood the lesson very well."
                        )

                    elif score >= total / 2:

                        st.info(
                            "Good job! Review the lesson "
                            "once more to strengthen your understanding."
                        )

                    else:

                        st.warning(
                            "Don't worry! Review the lesson "
                            "sections and try the quiz again."
                        )


            # ====================================================
            # LESSON COMPLETE
            # ====================================================

            if (
                sections
                and st.session_state.current_section
                == len(sections) - 1
            ):

                st.divider()

                st.success(
                    "🎓 Lesson completed! "
                    "You can review the sections or "
                    "attempt the final quiz."
                )


# ============================================================
# NO DOCUMENT
# ============================================================

else:

    st.info(
        "👆 Upload a PDF above to begin learning "
        "with EduSense AI."
    )