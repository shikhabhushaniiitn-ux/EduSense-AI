import streamlit as st
import hashlib

from modules.pdf_processor import (
    extract_text_from_pdf,
    get_pdf_page_count,
    extract_text_from_upload
)

from modules.text_processor import (
    clean_text,
    split_text_into_chunks
)

from modules.topic_generator import (
    generate_study_material_from_topic
)

from modules.summarizer import (
    generate_summary
)

from modules.retriever import (
    build_chunk_index,
    find_relevant_chunks
)

from modules.qa import (
    generate_answer
)

from modules.lesson_planner import (
    generate_lesson_plan,
    generate_weekly_lesson_plan,
    extract_learning_topics
)

from modules.teacher import (
    generate_teacher_explanation,
    generate_follow_up_question,
    generate_visual_narration,
    answer_in_lesson_query
)

from modules.assessment import (
    evaluate_answer
)

from modules.teaching_engine import (
    initialize_lesson,
    get_current_section,
    get_progress,
    move_to_next_section,
    move_to_previous_section,
    save_answer,
    mark_section_completed,
    update_concept_performance,
    record_attempt,
    update_difficulty,
    add_adaptation_event,
    get_learning_summary,
    initialize_weekly_lesson,
    get_current_day,
    get_weekly_progress,
    move_to_next_day,
    move_to_previous_day,
    save_day_answer,
    mark_day_completed,
    is_weekly_complete,
    record_misconception
)

from modules.audio_teacher import (
    generate_speech,
    get_cache_key,
    build_synced_player_html
)

from modules.subject_visuals import (
    detect_visual,
    render_visual,
    plan_concept_visuals
)

from modules.teaching_timeline import (
    attach_audio_metadata,
    build_section_timeline,
    current_event
)

from modules.video_pipeline import (
    build_video_scenes,
    compose_segment,
    refresh_scene_manifest,
)

from modules.avatar_provider import (
    build_avatar_player_html,
    build_classroom_video_html
)

from modules.learner_profile import (
    load_profile,
    save_profile,
    record_session_result,
    get_profile_personalization_context
)

from modules.learning_path import (
    generate_learning_path,
    generate_learning_path_mermaid,
    PRESET_LEARNING_PATHS
)

from modules.study_tools import (
    generate_study_notes,
    generate_flashcards
)

from modules.style_dna import StyleDNA

import streamlit.components.v1 as components


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

    "chunk_index": None,

    "page_count": 0,

    "file_name": "",

    "summary": "",

    "answer": "",

    "source_chunks": [],

    # Lesson planner
    "lesson_plan": None,

    "student_level": "Beginner",

    "preferred_language": "English",

    "lesson_duration": 20,

    "focus_topic": "",

    # Teacher
    "lesson_started": False,

    "teaching_state": None,

    "teacher_explanation": "",

    "answer_evaluation": None,

    "student_answer": "",

    # Misconception-targeted re-teaching for the single-lesson
    # AI Teacher - cached per section index so it's only
    # generated once per wrong answer, not on every rerun.
    "section_remediation": {},

    # Per-checkpoint mastery loop for normal lessons. A checkpoint stays
    # pending until its follow-up answer demonstrates understanding.
    "section_adaptations": {},

    "section_question_progress": {},

    "final_quiz_answers": {},

    "quiz_submitted": False,

    "quiz_score": 0,

    "quiz_breakdown": {},

    # 7-day plan - interactive walkthrough
    "weekly_teaching_state": None,

    "weekly_day_answer": "",

    "weekly_answer_evaluation": None,

    # Cache of the real AI explanation per day, so flipping
    # between days (Prev/Next/Jump) doesn't re-call the AI for
    # a day you've already visited.
    "weekly_day_explanations": {},

    "weekly_plan_id": "",

    # AI Teaching Voice - cache of generated (audio, word_timings)
    # per section, keyed by a hash of its text - so listening to
    # the same section twice doesn't re-call the TTS service.
    "tts_cache": {},

    # Subject-Aware Visuals - cache of the detected visual spec
    # per section, keyed the same way as tts_cache, so the AI
    # isn't re-asked to classify the same section on every rerun.
    "visual_cache": {},
    # Concept-level teaching timeline. These maps survive reruns and let a
    # section reveal its concepts (and their visuals) in teaching order.
    "section_concept_progress": {},
    "concept_explanations": {},
    "visual_narrations": {},
    # Ordered, serializable teaching events keyed by section.  The teaching
    # engine owns the cursor; this cache makes reruns and replay deterministic.
    "teaching_timeline": {},
    "video_scene_cache": {},
    # Teacher persona settings
    "teacher_persona_name": "Dr. Sophia",
    "teacher_gender": "female",
    "teacher_style": "Socratic Mentor",
    "in_lesson_qa_history": {},
    "active_learning_path": None,
    "shortcut_topic": None
}


for key, value in defaults.items():

    if key not in st.session_state:

        st.session_state[key] = value


# ============================================================
# RAG GROUNDING HELPER (ensures FAISS chunks reach LLM)
# ============================================================

def get_grounded_study_material(query, fallback_text="", top_k=5):
    """
    Retrieve grounded chunks from FAISS vector index when available.
    Ensures RAG chunks actually reach the teaching LLM calls!
    """
    if st.session_state.get("chunk_index") and st.session_state.get("chunks"):
        try:
            chunks = find_relevant_chunks(query, st.session_state.chunk_index, top_k=top_k)
            if chunks:
                return "\n\n---\n\n".join(chunks)
        except Exception as e:
            print(f"RAG retrieval note: {e}")
    return fallback_text


# ============================================================
# BROWSER SPEECH-TO-TEXT (STT) COMPONENT
# ============================================================

def render_speech_input_widget(key_suffix=""):
    """
    Browser-native Web Speech API microphone input widget.
    Allows students to speak answers out loud.
    """
    st.components.v1.html(
        f"""
        <div style="display:flex; align-items:center; gap:8px; margin: 4px 0; font-family:-apple-system,BlinkMacSystemFont,sans-serif;">
          <button id="sttBtn_{key_suffix}" onclick="toggleSTT_{key_suffix}()" style="background:#4f46e5; color:#fff; border:none; padding:6px 14px; border-radius:6px; font-size:12px; font-weight:600; cursor:pointer; display:flex; align-items:center; gap:6px;">
            <span id="sttIcon_{key_suffix}">🎤</span> <span id="sttText_{key_suffix}">Speak Answer (Voice Input)</span>
          </button>
          <span id="sttStatus_{key_suffix}" style="font-size:11px; color:#64748b;">Click to speak via microphone</span>
        </div>
        <div id="sttBox_{key_suffix}" style="display:none; margin-top:6px; padding:8px 12px; background:#f1f5f9; border-radius:6px; font-size:12px; color:#1e293b; border:1px solid #cbd5e1; line-height:1.5;">
          <b>Voice Transcribed:</b> <span id="sttTranscript_{key_suffix}" style="color:#0f172a; font-weight:500;"></span>
          <button onclick="copySTT_{key_suffix}()" style="margin-left:10px; padding:3px 8px; font-size:11px; background:#0ea5e9; color:#fff; border:none; border-radius:4px; cursor:pointer; font-weight:600;">📋 Copy to Text Box</button>
        </div>
        <script>
        let rec_{key_suffix} = null;
        let isRec_{key_suffix} = false;
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {{
          const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
          rec_{key_suffix} = new SpeechRec();
          rec_{key_suffix}.continuous = false;
          rec_{key_suffix}.interimResults = true;

          rec_{key_suffix}.onstart = () => {{
            isRec_{key_suffix} = true;
            document.getElementById('sttText_{key_suffix}').innerText = 'Listening... (Speak your answer)';
            document.getElementById('sttBtn_{key_suffix}').style.background = '#ef4444';
            document.getElementById('sttStatus_{key_suffix}').innerText = 'Listening to microphone...';
          }};
          rec_{key_suffix}.onresult = (e) => {{
            let interim = '';
            for (let i = e.resultIndex; i < e.results.length; ++i) {{
              interim += e.results[i][0].transcript;
            }}
            document.getElementById('sttBox_{key_suffix}').style.display = 'block';
            document.getElementById('sttTranscript_{key_suffix}').innerText = interim;
          }};
          rec_{key_suffix}.onerror = (e) => {{
            document.getElementById('sttStatus_{key_suffix}').innerText = 'Mic status: ' + (e.error || 'Ready');
            isRec_{key_suffix} = false;
            document.getElementById('sttText_{key_suffix}').innerText = 'Speak Answer (Voice Input)';
            document.getElementById('sttBtn_{key_suffix}').style.background = '#4f46e5';
          }};
          rec_{key_suffix}.onend = () => {{
            isRec_{key_suffix} = false;
            document.getElementById('sttText_{key_suffix}').innerText = 'Speak Answer (Voice Input)';
            document.getElementById('sttBtn_{key_suffix}').style.background = '#4f46e5';
            document.getElementById('sttStatus_{key_suffix}').innerText = 'Transcription ready! Click Copy, then paste into answer box.';
          }};
        }}

        function toggleSTT_{key_suffix}() {{
          if (!rec_{key_suffix}) {{
            alert('Voice input is supported in Google Chrome, Microsoft Edge, and Safari.');
            return;
          }}
          if (isRec_{key_suffix}) {{
            rec_{key_suffix}.stop();
          }} else {{
            rec_{key_suffix}.start();
          }}
        }}

        function copySTT_{key_suffix}() {{
          const txt = document.getElementById('sttTranscript_{key_suffix}').innerText;
          navigator.clipboard.writeText(txt).then(() => {{
            alert('Copied transcribed answer to clipboard! Now paste it into the answer box below.');
          }}).catch(() => {{
            alert('Select and copy the text: ' + txt);
          }});
        }}
        </script>
        """,
        height=95,
        scrolling=False
    )


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

    st.header("📚 Learning Studio")

    # --------------------------------------------------------
    # 👤 PERSISTENT STUDENT LEARNING PROFILE (Req 14)
    # --------------------------------------------------------
    with st.expander("👤 Student Learning Profile", expanded=False):
        try:
            profile_data = load_profile()
            col_p1, col_p2 = st.columns(2)
            col_p1.metric("Study Time", f"{profile_data.get('total_study_minutes', 0)}m")
            col_p2.metric("Lessons", profile_data.get("total_sessions", 0))

            st.markdown("**Concept Mastery:**")
            mastery_dict = profile_data.get("concept_mastery", {})
            if mastery_dict:
                for c_name, c_score in list(mastery_dict.items())[-5:]:
                    score_val = float(c_score) if isinstance(c_score, (int, float)) else 0.5
                    st.progress(min(1.0, max(0.0, score_val)), text=f"{c_name}: {int(score_val * 100)}%")
            else:
                st.caption("Complete lesson checkpoints to build concept mastery.")

            weak_list = profile_data.get("weak_concepts", [])
            if weak_list:
                st.warning(f"⚠️ Focus Areas: {', '.join(weak_list[:3])}")

            misc_list = profile_data.get("misconceptions", [])
            if misc_list:
                st.caption(f"🧠 Historical Misconceptions Addressed: {len(misc_list)}")

            studied = profile_data.get("topics_studied", [])
            if studied:
                st.markdown("**Recent Topics:**")
                for item in studied[-3:]:
                    st.caption(f"• {item.get('topic', 'Lesson')} (Best: {item.get('best_score', 0)}%)")
        except Exception as err:
            st.caption(f"Profile status: {err}")

    # --------------------------------------------------------
    # 🗺️ AI-GENERATED LEARNING PATHS (Req 15)
    # --------------------------------------------------------
    with st.expander("🗺️ AI Learning Roadmaps", expanded=False):
        st.write("Explore structured curricula with prerequisite progressions:")
        preset_names = list(PRESET_LEARNING_PATHS.keys()) + ["Custom Topic..."]
        chosen_path = st.selectbox("Curriculum Domain:", preset_names, key="sidebar_curriculum_choice")

        custom_topic_query = ""
        if chosen_path == "Custom Topic...":
            custom_topic_query = st.text_input("Enter broad domain:", "Data Science", key="custom_path_input")

        if st.button("🚀 Load Learning Roadmap", key="load_roadmap_btn"):
            path_domain = custom_topic_query if chosen_path == "Custom Topic..." else chosen_path
            with st.spinner(f"Generating roadmap for {path_domain}..."):
                st.session_state.active_learning_path = generate_learning_path(path_domain)
                st.success(f"Roadmap loaded for {path_domain}! See main panel.")

    st.divider()

    st.info(
        """
        **EduSense AI Capabilities**

        📄 Multi-format Ingestion (PDF/DOCX/PPTX/TXT)  
        💡 Topic-based Teaching (Zero upload needed)  
        🧠 Semantic Vector Grounding (FAISS)  
        🎓 16:9 Virtual Classroom Video with Lip-sync  
        🎙️ Neural Edge-TTS Speech with Word Highlighting  
        📹 In-browser WebM Video Lesson Recording  
        🎯 Adaptive Checkpoint & Misconception Engine  
        💬 Live In-Lesson "Ask Teacher" Q&A  
        🎤 Browser Speech-to-Text Voice Answering  
        👤 Persistent Student Mastery Profile  
        🗺️ AI-Generated Learning Roadmaps  
        📚 Flip Flashcards & Revision Notes Export  
        """
    )


# ============================================================
# INPUT MODE: UPLOAD A PDF, OR ENTER A TOPIC
# ============================================================

input_mode = st.radio(
    "How would you like to start?",
    [
        "📄 Upload Study Material",
        "💡 Enter a Topic"
    ],
    horizontal=True,
    key="input_mode"
)


uploaded_file = None

if input_mode == "📄 Upload Study Material":

    uploaded_file = st.file_uploader(
        "📄 Upload your study material",
        type=["pdf", "docx", "pptx", "txt"],
        help="Upload a PDF, Word (.docx), PowerPoint (.pptx), or text (.txt) file containing your study material."
    )


else:

    # --------------------------------------------------------
    # 🗺️ ACTIVE LEARNING PATH DISPLAY (if selected from sidebar)
    # --------------------------------------------------------
    if st.session_state.get("active_learning_path"):
        lp = st.session_state.active_learning_path
        with st.expander(f"🗺️ Active Learning Roadmap: {lp.get('title', 'Curriculum')}", expanded=True):
            st.write(lp.get("description", ""))
            mermaid_code = generate_learning_path_mermaid(lp)
            if mermaid_code:
                st.components.v1.html(
                    f"""
                    {StyleDNA.get_mermaid_init_script()}
                    <div class="mermaid" style="display:flex; justify-content:center;">
                    {mermaid_code}
                    </div>
                    """,
                    height=200,
                    scrolling=True
                )
            st.write("**Jump to a module in this roadmap:**")
            mod_cols = st.columns(min(len(lp.get("modules", [])), 4))
            for m_idx, mod in enumerate(lp.get("modules", [])):
                col_m = mod_cols[m_idx % len(mod_cols)]
                with col_m:
                    if st.button(f"📘 {mod.get('order', m_idx+1)}. {mod.get('title')}", key=f"lp_mod_{m_idx}"):
                        st.session_state.shortcut_topic = f"{lp.get('title', '')}: {mod.get('title')}"
                        st.rerun()

    # --------------------------------------------------------
    # ⚡ POPULAR TOPIC SHORTCUTS (Req 22)
    # --------------------------------------------------------
    st.write("🔥 **Popular Topic Shortcuts:**")
    sc1, sc2, sc3 = st.columns(3)
    if sc1.button("🤖 AI From The Beginning", key="sc_ai"):
        st.session_state.shortcut_topic = "Artificial Intelligence from the beginning"
        st.rerun()
    if sc2.button("🍎 Newton's Laws (Class 8)", key="sc_newton"):
        st.session_state.shortcut_topic = "Newton's Laws for Class 8"
        st.rerun()
    if sc3.button("⚛️ React Technical Interview", key="sc_react"):
        st.session_state.shortcut_topic = "React for a technical interview"
        st.rerun()

    current_default_topic = st.session_state.get("shortcut_topic") or ""

    topic_query = st.text_input(
        "💡 What would you like to learn about?",
        value=current_default_topic,
        placeholder=(
            "e.g. \"Photosynthesis\", \"Newton's Laws of Motion\", "
            "\"Linear Regression\""
        ),
        key="topic_query_input"
    )

    generate_topic_clicked = st.button(
        "✨ Generate Study Material",
        key="generate_topic_material"
    )

    # Auto-trigger if shortcut was clicked
    should_generate = generate_topic_clicked or bool(st.session_state.get("shortcut_topic"))
    if st.session_state.get("shortcut_topic"):
        st.session_state.shortcut_topic = None

    if should_generate:

        if not topic_query or not topic_query.strip():

            st.warning(
                "⚠️ Please enter a topic first."
            )

        else:

            # Reset document-related information - same reset
            # list as the PDF upload path, so switching from a
            # previous PDF (or a previous topic) to a new topic
            # never leaves stale lesson/quiz state behind.

            st.session_state.document_text = ""

            st.session_state.cleaned_text = ""

            st.session_state.chunks = []

            st.session_state.chunk_index = None

            st.session_state.page_count = 0

            st.session_state.summary = ""

            st.session_state.answer = ""

            st.session_state.source_chunks = []

            st.session_state.lesson_plan = None

            st.session_state.lesson_started = False

            st.session_state.teaching_state = None

            st.session_state.teacher_explanation = ""

            st.session_state.answer_evaluation = None

            st.session_state.student_answer = ""

            st.session_state.section_remediation = {}
            st.session_state.section_adaptations = {}

            st.session_state.final_quiz_answers = {}

            st.session_state.quiz_submitted = False

            st.session_state.quiz_score = 0

            st.session_state.quiz_breakdown = {}

            st.session_state.weekly_teaching_state = None

            st.session_state.weekly_day_answer = ""

            st.session_state.weekly_answer_evaluation = None

            st.session_state.weekly_day_explanations = {}
            st.session_state.weekly_plan_id = ""

            with st.spinner(
                f"✨ Building study material on \"{topic_query}\"..."
            ):

                try:

                    # Always generate at Advanced depth here,
                    # regardless of the level the student picks
                    # later for the actual lesson (that choice
                    # happens further down, in the Personalized
                    # Lesson section, after this text already
                    # exists). Generating the deepest version up
                    # front means there's always enough material
                    # for the lesson planner to scale DOWN for a
                    # Beginner lesson or use in full for Advanced -
                    # the same way one uploaded PDF already serves
                    # every level.

                    text = generate_study_material_from_topic(
                        topic_query,
                        level="Advanced"
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

                    st.session_state.cleaned_text = cleaned_text

                    st.session_state.chunks = chunks

                    st.session_state.chunk_index = build_chunk_index(
                        chunks
                    )

                    st.session_state.page_count = "N/A"

                    st.session_state.file_name = (
                        f"Topic: {topic_query.strip()}"
                    )

                except Exception as e:

                    st.error(
                        f"❌ Could not generate study material: {e}"
                    )


# ============================================================
# PROCESS DOCUMENT (upload path only)
# ============================================================

if uploaded_file is not None:

    # Process only when a new file is uploaded

    if st.session_state.file_name != uploaded_file.name:

        # Reset document-related information

        st.session_state.document_text = ""

        st.session_state.cleaned_text = ""

        st.session_state.chunks = []

        st.session_state.chunk_index = None

        st.session_state.page_count = 0

        st.session_state.summary = ""

        st.session_state.answer = ""

        st.session_state.source_chunks = []

        # Reset lesson

        st.session_state.lesson_plan = None

        st.session_state.lesson_started = False

        st.session_state.teaching_state = None

        st.session_state.teacher_explanation = ""

        st.session_state.answer_evaluation = None

        st.session_state.student_answer = ""

        st.session_state.section_remediation = {}
        st.session_state.section_adaptations = {}

        st.session_state.final_quiz_answers = {}

        st.session_state.quiz_submitted = False

        st.session_state.quiz_score = 0

        st.session_state.quiz_breakdown = {}

        st.session_state.weekly_teaching_state = None

        st.session_state.weekly_day_answer = ""

        st.session_state.weekly_answer_evaluation = None

        st.session_state.weekly_day_explanations = {}
        st.session_state.weekly_plan_id = ""

        with st.spinner(
            "📄 Processing your study material..."
        ):

            try:

                # ------------------------------------------------
                # Extract text (+ page count where applicable)
                #
                # extract_text_from_upload() dispatches by file
                # extension - PDF still goes through the exact
                # same extract_text_from_pdf()/get_pdf_page_count()
                # calls as before; DOCX/PPTX/TXT are new and return
                # page_count = "N/A" since those formats don't have
                # a PDF-style page concept.
                # ------------------------------------------------

                text, page_count = extract_text_from_upload(
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

                # Embed the chunks ONCE here, right after upload,
                # instead of re-embedding them on every question.
                st.session_state.chunk_index = build_chunk_index(
                    chunks
                )

                st.session_state.page_count = page_count

                st.session_state.file_name = uploaded_file.name

            except Exception as e:

                st.error(
                    f"❌ Could not process the file: {e}"
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
                            st.session_state.chunk_index,
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
    # PERSONALIZED LESSON
    # ========================================================

    st.divider()

    st.header(
        "🎯 Personalized Lesson"
    )

    st.write(
        "Create a lesson based on your study material."
    )


    # --------------------------------------------------------
    # Lesson settings (Level, Language, Duration, Teacher Persona)
    # --------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        student_level = st.selectbox(
            "🎓 Student Level",
            [
                "Beginner",
                "Intermediate",
                "Advanced"
            ],
            index=[
                "Beginner",
                "Intermediate",
                "Advanced"
            ].index(
                st.session_state.student_level
            )
        )

    with col2:

        lang_choices = [
            "English", "Hindi", "Hinglish",
            "Tamil", "Telugu", "Bengali",
            "Marathi", "Gujarati", "Kannada", "Malayalam",
            "Spanish", "French", "German"
        ]
        curr_lang = st.session_state.preferred_language
        if curr_lang not in lang_choices:
            curr_lang = "English"

        preferred_language = st.selectbox(
            "🌐 Preferred Language",
            lang_choices,
            index=lang_choices.index(curr_lang)
        )

    with col3:

        duration_options = [5, 15, 20, 30, 45, 60, "7 Days"]

        current_duration = st.session_state.lesson_duration

        if current_duration not in duration_options:
            current_duration = 20

        lesson_duration = st.selectbox(
            "⏱️ Lesson Duration",
            duration_options,
            index=duration_options.index(
                current_duration
            ),
            help="5 min: Rapid core concept sprint. 20 min: Comprehensive lesson with visual models."
        )

    with col4:

        persona_options = [
            "Dr. Sophia (Socratic Mentor - Female)",
            "Prof. Marcus (Academic Professor - Male)",
            "Coach Alex (Supportive Coach - Casual)"
        ]
        curr_persona = st.session_state.get("teacher_persona_name", "Dr. Sophia")
        persona_idx = 0
        if "Marcus" in curr_persona:
            persona_idx = 1
        elif "Alex" in curr_persona:
            persona_idx = 2

        chosen_persona = st.selectbox(
            "🧑‍🏫 Teacher Persona",
            persona_options,
            index=persona_idx
        )

        if "Marcus" in chosen_persona:
            st.session_state.teacher_persona_name = "Prof. Marcus"
            st.session_state.teacher_gender = "male"
            st.session_state.teacher_style = "Academic Professor"
        elif "Alex" in chosen_persona:
            st.session_state.teacher_persona_name = "Coach Alex"
            st.session_state.teacher_gender = "female"
            st.session_state.teacher_style = "Supportive Coach"
        else:
            st.session_state.teacher_persona_name = "Dr. Sophia"
            st.session_state.teacher_gender = "female"
            st.session_state.teacher_style = "Socratic Mentor"

    # --------------------------------------------------------
    # Optional source-grounded topic selection. The existing free-text focus
    # behavior is replaced by choices extracted from this material so a
    # selected topic reliably scopes the actual planner input.
    # --------------------------------------------------------

    topic_options = ["Entire Material"] + extract_learning_topics(
        st.session_state.document_text
    )
    selected_topic = st.selectbox(
        "📚 What do you want to learn?",
        topic_options,
        index=(
            topic_options.index(st.session_state.focus_topic)
            if st.session_state.focus_topic in topic_options else 0
        ),
        help="Entire Material keeps the original full-source lesson behavior."
    )

    focus_topic = "" if selected_topic == "Entire Material" else selected_topic

    st.session_state.focus_topic = focus_topic

    # --------------------------------------------------------
    # Save settings
    # --------------------------------------------------------

    st.session_state.student_level = student_level
    st.session_state.preferred_language = preferred_language
    st.session_state.lesson_duration = lesson_duration


    # --------------------------------------------------------
    # Generate lesson
    # --------------------------------------------------------

    if st.button(
        "🎯 Generate Personalized Lesson",
        key="lesson_button"
    ):

        with st.spinner(
            "🤖 Creating your personalized lesson..."
        ):

            try:

                # IMPORTANT: use document_text (the raw extracted
                # text, with line breaks intact), NOT cleaned_text.
                # cleaned_text has already been through
                # text_processor.clean_text(), which collapses every
                # newline into a single space and strips non-ASCII
                # characters. The lesson planner's heading detection
                # works by splitting text into LINES, so handing it
                # already-flattened text silently defeats it and
                # forces it back onto unreliable word-frequency
                # guessing - which is what produced garbled topics/
                # concepts like "Regression Nagpur Indian" even
                # after lesson_planner.py's own internal fix.
                # lesson_planner.py does its own appropriate
                # cleaning internally once headings are detected.

                if lesson_duration == "7 Days":

                    lesson_plan = generate_weekly_lesson_plan(
                        st.session_state.document_text,
                        level=student_level,
                        language=preferred_language,
                        focus_topic=focus_topic
                    )

                else:

                    lesson_plan = generate_lesson_plan(
                        st.session_state.document_text,
                        level=student_level,
                        language=preferred_language,
                        duration=lesson_duration,
                        focus_topic=focus_topic
                    )

                if lesson_plan:

                    st.session_state.lesson_plan = (
                        lesson_plan
                    )

                    # Reset teaching state

                    st.session_state.lesson_started = False

                    st.session_state.teaching_state = None

                    st.session_state.teacher_explanation = ""

                    st.session_state.answer_evaluation = None

                    st.session_state.student_answer = ""

                    st.session_state.section_remediation = {}
                    st.session_state.section_adaptations = {}

                    st.session_state.final_quiz_answers = {}

                    st.session_state.quiz_submitted = False

                    st.session_state.quiz_score = 0

                    st.session_state.quiz_breakdown = {}

                    st.session_state.weekly_teaching_state = None

                    st.session_state.weekly_day_answer = ""

                    st.session_state.weekly_answer_evaluation = None

                    st.session_state.weekly_day_explanations = {}
                    st.session_state.weekly_plan_id = ""

                    st.success(
                        "✅ Personalized lesson created!"
                    )

                    if (
                        focus_topic
                        and focus_topic.strip()
                        and not lesson_plan.get(
                            "focus_topic_found",
                            True
                        )
                    ):

                        st.info(
                            f"ℹ️ Couldn't find \"{focus_topic}\" "
                            "specifically in your material, so this "
                            "lesson covers the whole document instead."
                        )

                else:

                    st.error(
                        "❌ Could not create lesson plan."
                    )

            except Exception as e:

                st.error(
                    f"❌ Lesson planner error: {e}"
                )


    # ========================================================
    # DISPLAY LESSON PLAN
    # ========================================================

    if st.session_state.lesson_plan:

        lesson = st.session_state.lesson_plan

        st.divider()

        st.header(
            "📘 Lesson Plan"
        )


        # ----------------------------------------------------
        # Lesson information
        # ----------------------------------------------------

        st.subheader(
            f"📘 {lesson.get('topic', 'Lesson')}"
        )

        info1, info2, info3 = st.columns(3)

        with info1:

            st.metric(
                "🎓 Level",
                lesson.get(
                    "level",
                    student_level
                )
            )

        with info2:

            st.metric(
                "🌐 Language",
                lesson.get(
                    "language",
                    preferred_language
                )
            )

        with info3:

            is_weekly_plan = bool(
                lesson.get("days")
            )

            st.metric(
                "⏱️ Duration",
                "7 Days"
                if is_weekly_plan
                else f"{lesson.get('duration_minutes', lesson_duration)} min"
            )


        # ----------------------------------------------------
        # Learning objectives
        # ----------------------------------------------------

        objectives = lesson.get(
            "learning_objectives",
            []
        )

        if objectives:

            st.markdown(
                "### 🎯 Learning Objectives"
            )

            for objective in objectives:

                st.write(
                    f"✅ {objective}"
                )


        # ----------------------------------------------------
        # 7-DAY PLAN VIEW - interactive day-by-day walkthrough
        # ----------------------------------------------------

        if is_weekly_plan:

            days = lesson.get(
                "days",
                []
            )

            total_days = len(days)

            if total_days == 0:

                st.warning(
                    "This 7-day plan has no days to show."
                )

                st.stop()

            # ------------------------------------------------
            # Initialize weekly teaching state once per plan.
            # Reuses the SAME adaptive-learning machinery as the
            # single-lesson flow (update_concept_performance,
            # update_difficulty, get_learning_summary) - only the
            # day-navigation helpers are new.
            # ------------------------------------------------

            plan_source = repr(lesson) + "|" + str(
                st.session_state.student_level
            ) + "|" + str(
                st.session_state.preferred_language
            )
            plan_id = hashlib.md5(
                plan_source.encode("utf-8")
            ).hexdigest()[:10]

            if (
                st.session_state.weekly_teaching_state is None
                or st.session_state.weekly_plan_id != plan_id
            ):
                st.session_state.weekly_teaching_state = (
                    initialize_weekly_lesson(lesson)
                )
                st.session_state.weekly_teaching_state.setdefault(
                    "day_remediation", {}
                )
                st.session_state.weekly_teaching_state.setdefault(
                    "weak_concepts_by_day", {}
                )
                st.session_state.weekly_teaching_state.setdefault(
                    "day_results", {}
                )
                st.session_state.weekly_plan_id = plan_id
                st.session_state.weekly_day_answer = ""
                st.session_state.weekly_answer_evaluation = None
                st.session_state.weekly_day_explanations = {}

            weekly_state = st.session_state.weekly_teaching_state

            current_day_index = weekly_state["current_day"]

            current_day = get_current_day(
                lesson,
                current_day_index
            )

            day_number = current_day.get(
                "day_number",
                current_day_index + 1
            )

            day_title = current_day.get(
                "day_title",
                f"Day {day_number}"
            )

            is_last_day = (
                current_day_index == total_days - 1
            )

            completed_days = set(
                weekly_state["completed_days"]
            )

            st.markdown(
                "### 📅 7-Day Plan"
            )

            # ------------------------------------------------
            # Progress bar
            # ------------------------------------------------

            progress_pct = get_weekly_progress(
                current_day_index,
                total_days,
                weekly_state["completed_days"]
            )

            st.progress(
                progress_pct / 100
            )

            st.caption(
                f"Day {current_day_index + 1} of {total_days} · "
                f"{progress_pct}% complete"
            )

            # ------------------------------------------------
            # All days are available. Students can move ahead even
            # when the current question is unanswered.
            # ------------------------------------------------

            unlocked_indexes = list(range(total_days))

            def _day_label(idx):

                label_day = days[idx].get(
                    "day_number",
                    idx + 1
                )

                label_title = days[idx].get(
                    "day_title",
                    f"Day {label_day}"
                )

                done_mark = (
                    "✅ "
                    if label_day in completed_days
                    else ""
                )

                return f"{done_mark}Day {label_day} — {label_title}"

            jump_choice = st.selectbox(
                "Jump to day",
                unlocked_indexes,
                index=unlocked_indexes.index(current_day_index),
                format_func=_day_label,
            )

            if jump_choice != current_day_index:

                weekly_state["current_day"] = jump_choice

                st.session_state.weekly_day_answer = ""

                st.session_state.weekly_answer_evaluation = None

                st.rerun()

            st.markdown(
                f"## 📅 Day {day_number} — {day_title}"
            )

            # ----------------------------------------------------
            # Defined unconditionally (not just inside the
            # "generate lesson" branch below) because it's read
            # later every time this day is rendered — including
            # on reruns where the explanation is already cached
            # and that branch is skipped entirely.
            # ----------------------------------------------------

            day_visual_key = f"day_visual_{day_number}"

            focus = current_day.get(
                "focus",
                ""
            )

            if focus:

                st.write(
                    focus
                )

            key_points = current_day.get(
                "key_points",
                []
            )

            if key_points:

                st.write(
                    "**Key Points:**"
                )

                for point in key_points:

                    st.write(
                        f"• {point}"
                    )

            # ----------------------------------------------------
            # 👨‍🏫 Today's Lesson — the actual explanation, not
            # just focus + bullet fragments. Same function the
            # single-lesson AI Teacher already uses (teacher.py),
            # cached per day_number so it's not re-called on
            # every click/rerun.
            # ----------------------------------------------------

            if day_number not in st.session_state.weekly_day_explanations:

                with st.spinner(
                    "👨‍🏫 Preparing today's lesson..."
                ):

                    try:

                        prior_weak_concepts = []
                        prior_remediation = []

                        for prior_day, concepts in weekly_state.get(
                            "weak_concepts_by_day", {}
                        ).items():
                            try:
                                prior_day_number = int(prior_day)
                            except (TypeError, ValueError):
                                prior_day_number = 0

                            if prior_day_number < day_number:
                                for concept in concepts:
                                    if concept and concept not in prior_weak_concepts:
                                        prior_weak_concepts.append(concept)

                                remediation = weekly_state.get(
                                    "day_remediation", {}
                                ).get(prior_day, "")
                                if remediation:
                                    prior_remediation.append(remediation)

                        adaptive_description = focus

                        if prior_weak_concepts:
                            adaptive_description += (
                                "\n\nPrevious learning signals: The student had difficulty "
                                "with these concepts: "
                                + ", ".join(prior_weak_concepts)
                                + ". Briefly revisit these concepts before "
                                "building today's lesson and connect them to "
                                "today's topic."
                            )

                        if prior_remediation:
                            adaptive_description += (
                                "\n\nPrevious teacher remediation:\n"
                                + "\n".join(prior_remediation[-2:])
                            )

                        day_section = {
                            "title": day_title,
                            "description": adaptive_description,
                            "key_points": key_points
                        }

                        # ------------------------------------------
                        # Detect the visual BEFORE generating the
                        # explanation (not after) so the explanation
                        # - which is also the text fed to
                        # text-to-speech - can be written to
                        # actually narrate that visual out loud.
                        # ------------------------------------------

                        try:

                            day_visual_spec_for_narration = (
                                detect_visual(
                                    day_title,
                                    adaptive_description
                                    + "\n"
                                    + "\n".join(key_points)
                                )
                            )

                        except Exception as visual_error:

                            print(
                                "Day visual detection failed: "
                                f"{visual_error}"
                            )

                            day_visual_spec_for_narration = None

                        st.session_state.visual_cache[
                            day_visual_key
                        ] = day_visual_spec_for_narration

                        explanation = generate_teacher_explanation(
                            day_section,
                            st.session_state.cleaned_text,
                            st.session_state.student_level,
                            st.session_state.preferred_language,
                            visual_spec=day_visual_spec_for_narration
                        )

                        st.session_state.weekly_day_explanations[
                            day_number
                        ] = explanation

                    except Exception as e:

                        st.error(
                            f"❌ Could not generate today's lesson: {e}"
                        )

                        st.session_state.weekly_day_explanations[
                            day_number
                        ] = ""

            day_explanation = (
                st.session_state.weekly_day_explanations.get(
                    day_number,
                    ""
                )
            )

            # ----------------------------------------------------
            # 🎨 Subject-Aware Visual for this day - rendered HERE,
            # right when the day opens, rather than after the
            # lesson text and audio (moved earlier so it's seen
            # right when it's relevant). Already detected above
            # (before the explanation was generated) and cached
            # under day_visual_key, so this just re-renders it.
            # ----------------------------------------------------

            cached_day_visual_spec = (
                st.session_state.visual_cache.get(
                    day_visual_key
                )
            )

            if (
                cached_day_visual_spec
                and cached_day_visual_spec.get(
                    "visual_type",
                    "none"
                ) != "none"
            ):

                with st.expander(
                    "🎨 Visual: "
                    + (
                        cached_day_visual_spec.get("title")
                        or cached_day_visual_spec.get("subject")
                    ),
                    expanded=True
                ):

                    render_visual(cached_day_visual_spec)

            if day_explanation:

                st.markdown(
                    "### 👨‍🏫 Today's Lesson"
                )

                st.markdown(
                    day_explanation
                )

            # ----------------------------------------------------
            # 🔊 AI Teaching Voice for this day (same zero-cost
            # Edge TTS helper as the single-lesson AI Teacher)
            # ----------------------------------------------------

            day_speech_text = day_explanation if day_explanation else focus

            if key_points:

                day_speech_text += ". " + ". ".join(key_points)

            day_cache_key = get_cache_key(
                day_speech_text,
                st.session_state.preferred_language
            )

            if st.button(
                "🔊 Listen to this day",
                key=f"listen_day_{day_number}"
            ):

                if day_cache_key not in st.session_state.tts_cache:

                    with st.spinner(
                        "🎙️ Generating voice..."
                    ):

                        try:

                            audio_bytes, word_timings = (
                                generate_speech(
                                    day_speech_text,
                                    st.session_state
                                    .preferred_language
                                )
                            )

                            st.session_state.tts_cache[
                                day_cache_key
                            ] = (
                                audio_bytes,
                                word_timings
                            )

                        except Exception as tts_error:

                            st.error(
                                "❌ Couldn't generate audio right "
                                f"now: {tts_error}"
                            )

            if day_cache_key in st.session_state.tts_cache:

                cached_audio, cached_timings = (
                    st.session_state.tts_cache[day_cache_key]
                )

                if cached_audio:

                    components.html(
                        build_avatar_player_html(
                            cached_audio,
                            cached_timings
                        ),
                        height=340,
                        scrolling=True
                    )

            # ----------------------------------------------------
            # 🔊 AI Teaching Voice ends here; the visual itself
            # now renders EARLIER (right after the lesson text is
            # ready, before this audio block) so it doesn't sit at
            # the very bottom of the day - see the "🎨 Subject-
            # Aware Visual for this day" block above.
            # ----------------------------------------------------

            day_already_done = (
                day_number in completed_days
            )

            # ==================================================
            # DAYS 1-6: single practice question
            # ==================================================

            if not is_last_day:

                day_questions = current_day.get("questions") or [
                    current_day.get("question", {})
                ]
                day_question_progress = weekly_state.setdefault(
                    "day_question_progress", {}
                )
                day_question_position = day_question_progress.get(
                    str(day_number), 0
                )
                question = (
                    day_questions[day_question_position]
                    if day_question_position < len(day_questions) else {}
                )

                # Some AI responses may return Day 7-style question
                # arrays even for an earlier day - guard against it.
                if isinstance(question, list):

                    question = (
                        question[0]
                        if question
                        else {}
                    )

                question_text = question.get(
                    "question",
                    ""
                )

                expected_concept = question.get(
                    "expected_concept",
                    question.get(
                        "concept",
                        day_title
                    )
                )

                if question_text:

                    st.markdown(
                        f"### 💡 Practice Question {day_question_position + 1} of {len(day_questions)}"
                    )

                    st.write(
                        question_text
                    )

                    options = question.get(
                        "options",
                        []
                    )

                    if options:

                        student_answer = st.radio(
                            "Choose your answer:",
                            options,
                            key=f"weekly_mcq_{plan_id}_{day_number}"
                        )

                    else:

                        student_answer = st.text_area(
                            "✍️ Your Answer",
                            value=st.session_state.weekly_day_answer,
                            placeholder="Write your answer here...",
                            key=f"weekly_answer_{plan_id}_{day_number}"
                        )

                        st.session_state.weekly_day_answer = (
                            student_answer
                        )

                    if st.button(
                        "🧠 Check My Answer",
                        key=f"weekly_check_{plan_id}_{day_number}"
                    ):

                        if options:

                            correct_answer = question.get(
                                "correct_answer",
                                ""
                            )

                            is_correct = (
                                student_answer == correct_answer
                            )

                            evaluation = {
                                "score": 1 if is_correct else 0,
                                "correct": is_correct,
                                "feedback": (
                                    "Correct!"
                                    if is_correct
                                    else (
                                        "Not quite - the correct "
                                        f"answer was: {correct_answer}"
                                    )
                                )
                            }

                        else:

                            evaluation = evaluate_answer(
                                student_answer,
                                expected_concept,
                                question=question_text,
                                study_material=(
                                    st.session_state.cleaned_text
                                ),
                                level=st.session_state.student_level,
                                language=(
                                    st.session_state.preferred_language
                                )
                            )

                        st.session_state.weekly_answer_evaluation = (
                            evaluation
                        )

                        save_day_answer(
                            weekly_state,
                            day_number,
                            question_text,
                            student_answer,
                            evaluation,
                            concept=expected_concept
                        )

                        update_concept_performance(
                            weekly_state,
                            expected_concept,
                            evaluation.get("score", 0)
                        )

                        record_attempt(
                            weekly_state,
                            day_number
                        )

                        update_difficulty(
                            weekly_state,
                            evaluation
                        )

                        weekly_state.setdefault("day_results", {})
                        weekly_state["day_results"][str(day_number)] = evaluation

                        if evaluation.get("correct", False):
                            day_question_progress[str(day_number)] = (
                                day_question_position + 1
                            )
                            weekly_state.setdefault("attempts", {})[day_number] = 0
                            weekly_state.setdefault("weak_concepts_by_day", {})
                            weekly_state["weak_concepts_by_day"].pop(
                                str(day_number), None
                            )
                            weekly_state.setdefault("day_remediation", {})
                            weekly_state["day_remediation"].pop(
                                str(day_number), None
                            )
                        else:
                            weak_concept = str(expected_concept).strip()

                            # -------------------------------------
                            # 🧠 Misconception detection - the AI
                            # evaluator now names the SPECIFIC
                            # wrong idea behind the answer (not
                            # just "incorrect"). Record it, and if
                            # one was found, have the re-teach
                            # explanation correct THAT idea
                            # directly instead of a generic recap
                            # of the weak concept.
                            # -------------------------------------

                            misconception = evaluation.get(
                                "misconception", ""
                            )

                            record_misconception(
                                weekly_state,
                                weak_concept,
                                misconception
                            )

                            if weak_concept:
                                weekly_state.setdefault("weak_concepts_by_day", {})
                                weekly_state["weak_concepts_by_day"][str(day_number)] = [
                                    weak_concept
                                ]

                                if misconception:
                                    remediation_description = (
                                        "The student answered this practice "
                                        "question with a specific misconception. "
                                        "Directly correct this misconception - "
                                        "name what they seem to believe, explain "
                                        "clearly why it's not quite right, and "
                                        "give the correct understanding with a "
                                        "simple example.\n\n"
                                        f"Question: {question_text}\n"
                                        f"Student answer: {student_answer}\n"
                                        f"Misconception to correct: {misconception}"
                                    )
                                    remediation_key_points = [
                                        f"Misconception: {misconception}"
                                    ]
                                else:
                                    remediation_description = (
                                        "The student answered this practice question incorrectly. "
                                        "Re-teach the weak concept clearly and simply.\n\n"
                                        f"Question: {question_text}\n"
                                        f"Student answer: {student_answer}\n"
                                        f"Teacher feedback: {evaluation.get('feedback', '')}"
                                    )
                                    remediation_key_points = [
                                        f"Weak concept: {weak_concept}"
                                    ]

                                remediation_section = {
                                    "title": f"Re-teaching: {weak_concept}",
                                    "description": remediation_description,
                                    "key_points": remediation_key_points
                                }

                                try:
                                    remediation = generate_teacher_explanation(
                                        remediation_section,
                                        st.session_state.cleaned_text,
                                        st.session_state.student_level,
                                        st.session_state.preferred_language
                                    )
                                except Exception:
                                    remediation = (
                                        f"Let's revisit {weak_concept}. "
                                        f"{evaluation.get('feedback', 'Review the concept and try again.')}"
                                    )

                                weekly_state.setdefault("day_remediation", {})
                                weekly_state["day_remediation"][str(day_number)] = remediation

                            retries = weekly_state.get("attempts", {}).get(
                                day_number, 0
                            )
                            if retries > 3:
                                day_question_progress[str(day_number)] = (
                                    day_question_position + 1
                                )
                                weekly_state.setdefault("attempts", {})[day_number] = 0
                                add_adaptation_event(
                                    weekly_state,
                                    day_number,
                                    "weak_after_three_retries",
                                    "Maximum adaptive retries reached"
                                )
                            else:
                                # Replace—not repeat—the failed check with a
                                # simpler alternate framing of the same concept.
                                day_questions[day_question_position]["question"] = (
                                    generate_follow_up_question(
                                        expected_concept,
                                        question_text,
                                        student_answer,
                                        level=("Beginner" if retries > 1 else st.session_state.student_level),
                                        language=st.session_state.preferred_language,
                                        simplify=retries > 1
                                    )
                                )

                        # A day unlocks after all of its checks have been
                        # attempted successfully, or after the bounded
                        # adaptive retry path below releases a weak concept.
                        if day_question_progress.get(str(day_number), 0) >= len(day_questions):
                            mark_day_completed(weekly_state, day_number)

                        if evaluation.get("correct", False):
                            st.rerun()
                        elif day_question_progress.get(str(day_number), 0) > day_question_position:
                            st.rerun()
                        else:
                            st.rerun()

                    evaluation = (
                        st.session_state.weekly_answer_evaluation
                    )

                    if evaluation:

                        if evaluation.get(
                            "correct",
                            False
                        ):

                            st.success(
                                evaluation.get(
                                    "feedback",
                                    "Correct!"
                                )
                            )

                        else:

                            st.warning(
                                evaluation.get(
                                    "feedback",
                                    "Keep trying!"
                                )
                            )

                            remediation = weekly_state.get(
                                "day_remediation", {}
                            ).get(str(day_number), "")

                            if remediation:
                                st.markdown("### 👨‍🏫 Teacher Re-teaching")
                                st.markdown(remediation)

                else:

                    # No question for this day - don't block
                    # progress on something that doesn't exist.
                    mark_day_completed(
                        weekly_state,
                        day_number
                    )

                st.divider()

                nav_col1, nav_col2 = st.columns(2)

                with nav_col1:

                    if current_day_index > 0:

                        if st.button(
                            "⬅️ Previous Day",
                            key="weekly_prev_day"
                        ):

                            weekly_state["current_day"] = (
                                move_to_previous_day(
                                    current_day_index
                                )
                            )
            
                            st.session_state.weekly_day_answer = ""

                            st.session_state.weekly_answer_evaluation = (
                                None
                            )

                            st.rerun()

                with nav_col2:

                    if st.button(
                        "➡️ Next Day",
                        key=f"weekly_next_day_{plan_id}_{day_number}",
                        disabled=(current_day_index >= total_days - 1)
                    ):
                        weekly_state["current_day"] = move_to_next_day(
                            current_day_index,
                            total_days
                        )
                        st.session_state.weekly_day_answer = ""
                        st.session_state.weekly_answer_evaluation = None
                        st.rerun()

            # ==================================================
            # DAY 7: consolidated assessment + Learning Report
            # ==================================================

            else:

                st.divider()

                st.header(
                    "📝 Day 7 Assessment"
                )

                quiz = lesson.get(
                    "final_quiz",
                    []
                )

                if not quiz:

                    st.info(
                        "No assessment questions were generated "
                        "for this week."
                    )

                    mark_day_completed(
                        weekly_state,
                        day_number
                    )

                else:

                    for i, quiz_question in enumerate(quiz):

                        st.markdown(
                            f"### Question {i + 1}"
                        )

                        st.write(
                            quiz_question.get(
                                "question",
                                ""
                            )
                        )

                        options = quiz_question.get(
                            "options",
                            []
                        )

                        if options:

                            answer = st.radio(
                                "Choose your answer:",
                                options,
                                key=f"weekly_quiz_{plan_id}_{i}"
                            )

                            weekly_state["final_quiz_answers"][i] = (
                                answer
                            )

                    if st.button(
                        "🎯 Submit Week's Assessment",
                        key=f"weekly_submit_quiz_{plan_id}"
                    ):

                        score = 0

                        correct_count = 0

                        incorrect_count = 0

                        wrong_concepts = []

                        for i, quiz_question in enumerate(quiz):

                            correct_answer = quiz_question.get(
                                "correct_answer",
                                ""
                            )

                            concept = quiz_question.get(
                                "concept",
                                ""
                            )

                            student_answer = (
                                weekly_state["final_quiz_answers"]
                                .get(i, "")
                            )

                            is_correct = (
                                student_answer == correct_answer
                            )

                            if is_correct:

                                score += 1

                                correct_count += 1

                            else:

                                incorrect_count += 1

                                if (
                                    concept
                                    and concept not in wrong_concepts
                                ):

                                    wrong_concepts.append(concept)

                            if concept:

                                update_concept_performance(
                                    weekly_state,
                                    concept,
                                    1 if is_correct else 0
                                )

                        weekly_state["final_quiz_score"] = score

                        weekly_state["final_quiz_submitted"] = True

                        weekly_state["final_quiz_breakdown"] = {
                            "correct": correct_count,
                            "incorrect": incorrect_count,
                            "wrong_concepts": wrong_concepts
                        }

                        mark_day_completed(
                            weekly_state,
                            day_number
                        )

                    if weekly_state["final_quiz_submitted"]:

                        total_questions = len(quiz)

                        score = weekly_state["final_quiz_score"]

                        breakdown = (
                            weekly_state["final_quiz_breakdown"]
                        )

                        st.success(
                            f"🎉 Your score: "
                            f"{score}/{total_questions}"
                        )

                        st.write(
                            f"✅ Correct: "
                            f"{breakdown.get('correct', 0)}"
                            f"&nbsp;&nbsp;&nbsp;"
                            f"❌ Incorrect: "
                            f"{breakdown.get('incorrect', 0)}",
                            unsafe_allow_html=True
                        )

                        wrong_concepts = breakdown.get(
                            "wrong_concepts",
                            []
                        )

                        if wrong_concepts:

                            st.markdown(
                                "**Topics to review:**"
                            )

                            for concept in wrong_concepts:

                                st.markdown(
                                    f"- {concept}"
                                )

                        if total_questions > 0:

                            percentage = (
                                score / total_questions
                            ) * 100

                            if percentage == 100:

                                st.balloons()

                                st.success(
                                    "Excellent! You've completed "
                                    "the full week with a perfect "
                                    "score."
                                )

                            elif percentage >= 60:

                                st.info(
                                    "Good job finishing the week! "
                                    "Review the topics you found "
                                    "difficult."
                                )

                            else:

                                st.warning(
                                    "Keep practicing! Revisit the "
                                    "days you found difficult and "
                                    "try the assessment again."
                                )

                        # ==========================================
                        # 🎓 WEEKLY LEARNING REPORT
                        #
                        # get_learning_summary() is the SAME
                        # function the single-lesson flow uses -
                        # it just reads generic keys off whatever
                        # state dict it's given.
                        # ==========================================

                        st.divider()

                        st.header(
                            "🎓 Your Weekly Learning Report"
                        )

                        summary = get_learning_summary(
                            weekly_state
                        )

                        report_col1, report_col2 = st.columns(2)

                        with report_col1:

                            st.metric(
                                "Daily Questions Score",
                                f"{summary.get('percentage', 0)}%"
                            )

                        with report_col2:

                            st.metric(
                                "Day 7 Assessment",
                                f"{score}/{total_questions}"
                            )

                        strong_concepts = summary.get(
                            "strong_concepts",
                            []
                        )

                        weak_concepts = summary.get(
                            "weak_concepts",
                            []
                        )

                        st.markdown(
                            "#### Strong Areas"
                        )

                        if strong_concepts:

                            for concept in strong_concepts:

                                st.markdown(
                                    f"✓ {concept}"
                                )

                        else:

                            st.caption(
                                "No strong areas identified yet."
                            )

                        st.markdown(
                            "#### Needs Improvement"
                        )

                        if weak_concepts:

                            for concept in weak_concepts:

                                st.markdown(
                                    f"⚠ {concept}"
                                )

                        else:

                            st.caption(
                                "No weak areas identified - "
                                "nice work!"
                            )

                        if weak_concepts:

                            st.info(
                                "**Teacher Recommendation:** "
                                f"Review {', '.join(weak_concepts)} "
                                "before starting a new topic."
                            )

                        else:

                            st.info(
                                "**Teacher Recommendation:** "
                                "Great week! You're ready for "
                                "the next topic."
                            )

                st.divider()

                if st.button(
                    "⬅️ Back to Day 6",
                    key="weekly_back_to_6"
                ):

                    weekly_state["current_day"] = (
                        move_to_previous_day(
                            current_day_index
                        )
                    )

                    st.rerun()

            st.stop()


        # ----------------------------------------------------
        # Lesson sections
        # ----------------------------------------------------

        st.markdown(
            "### 📖 Lesson Sections"
        )

        sections = lesson.get(
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

            duration = section.get(
                "duration_minutes",
                0
            )

            description = section.get(
                "description",
                ""
            )

            st.markdown(
                f"📚 **{i + 1}. {title} — {duration} min**"
            )

            st.write(
                description
            )

            key_points = section.get(
                "key_points",
                []
            )

            if key_points:

                st.write(
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
                "🧑‍🏫 AI Teacher"
            )

            st.write(
                "Ready to start your personalized lesson?"
            )

            if st.button(
                "▶️ Start Lesson",
                key="start_lesson"
            ):

                state = initialize_lesson(
                    lesson
                )

                st.session_state.teaching_state = state

                st.session_state.lesson_started = True

                st.session_state.teacher_explanation = ""

                st.session_state.answer_evaluation = None

                st.session_state.student_answer = ""

                st.session_state.section_remediation = {}
                st.session_state.section_adaptations = {}
                st.session_state.section_concept_progress = {}
                st.session_state.concept_explanations = {}
                st.session_state.visual_narrations = {}
                st.session_state.teaching_timeline = {}
                st.session_state.video_scene_cache = {}

                st.rerun()


        # ====================================================
        # ACTIVE AI TEACHER
        # ====================================================

        if st.session_state.lesson_started:

            state = st.session_state.teaching_state

            current_index = state.get(
                "current_section",
                0
            )

            total_sections = state.get(
                "total_sections",
                len(sections)
            )


            current_section = get_current_section(
                lesson,
                current_index
            )


            if current_section:

                st.header(
                    "🧑‍🏫 AI Teacher"
                )


                # ------------------------------------------------
                # Progress
                # ------------------------------------------------

                progress = get_progress(
                    current_index,
                    total_sections
                )

                st.write(
                    f"Section {current_index + 1} "
                    f"of {total_sections}"
                )

                st.progress(
                    progress / 100
                )


                # ------------------------------------------------
                # Current section
                # ------------------------------------------------

                st.subheader(
                    f"📚 {current_section.get('title', 'Lesson Section')}"
                )


                # ------------------------------------------------
                # 🎨 Detect the visual FIRST (before the
                # explanation) so the explanation - which is also
                # the exact text fed to text-to-speech below - can
                # be written to actually narrate that visual out
                # loud instead of ignoring it. Keyed by section
                # index/title, not by the explanation text, since
                # the explanation doesn't exist yet at this point.
                # ------------------------------------------------

                section_visual_key = (
                    f"section_visual_{current_index}_"
                    f"{current_section.get('title', '')}"
                )

                if (
                    section_visual_key
                    not in st.session_state.visual_cache
                ):

                    with st.spinner(
                        "🎨 Preparing a visual..."
                    ):

                        try:

                            section_visual_spec = plan_concept_visuals(
                                current_section,
                                st.session_state.student_level,
                                source_material=st.session_state.cleaned_text,
                                concept_performance=state.get("concept_performance", {})
                            )

                        except Exception as visual_error:

                            print(
                                "Section visual detection failed: "
                                f"{visual_error}"
                            )

                            section_visual_spec = None

                        st.session_state.visual_cache[
                            section_visual_key
                        ] = section_visual_spec

                cached_section_visual_plan = (
                    st.session_state.visual_cache.get(
                        section_visual_key
                    )
                )
                concepts = current_section.get("concepts") or current_section.get("key_points") or [current_section.get("title", "Current concept")]
                concept_count = len(concepts)
                section_questions_for_timeline = [
                    question for question in lesson.get("interactive_questions", [])
                    if question.get("section_index") == current_index
                ]
                timeline_key = f"section_timeline_{current_index}_{current_section.get('title', '')}"
                if timeline_key not in st.session_state.teaching_timeline:
                    st.session_state.teaching_timeline[timeline_key] = build_section_timeline(
                        current_index, concepts, {}, cached_section_visual_plan,
                        {}, section_questions_for_timeline
                    )
                section_timeline = st.session_state.teaching_timeline[timeline_key]
                # Task-2 scene manifest mirrors the timeline. It is rebuilt
                # cheaply from cached event data and does not call an avatar
                # service or render a video on Streamlit reruns.
                if timeline_key not in st.session_state.video_scene_cache:
                    st.session_state.video_scene_cache[timeline_key] = compose_segment(
                        build_video_scenes(section_timeline)
                    )
                scene_manifest = st.session_state.video_scene_cache[timeline_key]
                refresh_scene_manifest(scene_manifest, section_timeline)
                event_cursor = state.setdefault("section_timeline_cursors", {}).get(current_index, 0)
                active_event = current_event(section_timeline, event_cursor)
                active_scene = next(
                    (
                        scene for scene in scene_manifest.get("scenes", [])
                        if scene.get("event_id") == (active_event or {}).get("event_id")
                    ),
                    None,
                )
                section_question_count = len(section_questions_for_timeline)
                displayed_question_position = (
                    active_event.get("question_index", 0)
                    if active_event and active_event.get("event_type") == "question"
                    else state.setdefault("section_question_progress", {}).get(current_index, 0)
                )
                concept_position = active_event.get("concept_index", 0) if active_event else 0
                current_visual_spec = active_event.get("visual") if active_event else None
                active_concept = (
                    active_event.get("concept_id") if active_event else concepts[min(concept_position, max(0, concept_count - 1))]
                )
                concept_teaching_section = dict(current_section)
                concept_teaching_section["title"] = str(active_concept)
                concept_teaching_section["description"] = (
                    f"Teach this concept as part of {current_section.get('title', '')}. "
                    f"{current_section.get('description', '')}"
                )
                concept_teaching_section["key_points"] = [str(active_concept)]
                concept_explanation_key = f"{section_visual_key}_concept_{concept_position}"

                # A compact classroom header is driven by the same timeline
                # cursor as the teaching flow, so it cannot drift away from
                # what the student is actually seeing or hearing.
                with st.container(border=True):
                    st.markdown("### AI teacher presentation")
                    status_left, status_middle, status_right = st.columns(3)
                    status_left.metric("Section", f"{current_index + 1} / {total_sections}")
                    status_middle.metric("Concept", f"{concept_position + 1} / {concept_count}")
                    status_right.metric(
                        "Teaching step",
                        (active_event or {}).get("event_type", "complete").replace("_", " ").title()
                    )
                    st.progress(
                        min(1.0, (event_cursor + 1) / max(1, len(section_timeline)))
                    )
                    st.caption(f"Currently teaching: {active_concept}")
                    if section_question_count:
                        st.caption(
                            f"Checkpoint: {min(displayed_question_position + 1, section_question_count)} "
                            f"/ {section_question_count}"
                        )
                    if active_scene:
                        st.caption(
                            f"Presentation scene {event_cursor + 1} / {len(section_timeline)} "
                            f"({scene_manifest.get('renderer', 'local_mock').replace('_', ' ')})"
                        )
                    if current_visual_spec:
                        st.info(
                            "Visual explanation — "
                            + (current_visual_spec.get("title") or str(active_concept))
                        )

                # ------------------------------------------------
                # 🎨 Subject-Aware Visual - rendered HERE, as soon
                # as the section opens, rather than after the
                # explanation and audio (moved earlier so the
                # student sees it right when it's relevant, not
                # buried at the end of the section).
                #
                # AI classifies this section (Mathematics /
                # Physics / Biology / History / Programming /
                # Chemistry / General) and picks a matching visual
                # - equation, graph, process diagram, timeline,
                # code, a physics simulation, or a relevant image.
                # ------------------------------------------------

                if active_event and active_event.get("event_type") in ("visual", "visual_explanation") and current_visual_spec and (
                    current_visual_spec
                    and current_visual_spec.get(
                        "visual_type",
                        "none"
                    ) != "none"
                ):

                    with st.expander(
                        "🎨 Visual: "
                        + (
                            current_visual_spec.get(
                                "title"
                            )
                            or current_visual_spec.get(
                                "subject"
                            )
                        ),
                        expanded=True
                    ):

                        render_visual(
                            current_visual_spec
                        )

                # ------------------------------------------------
                # Generate explanation
                # ------------------------------------------------

                if (
                    active_event
                    and active_event.get("event_type") == "explanation"
                    and concept_explanation_key not in st.session_state.concept_explanations
                ):

                    with st.spinner(
                        "👨‍🏫 Preparing your explanation..."
                    ):

                        try:

                            grounded_material = get_grounded_study_material(
                                f"{concept_teaching_section.get('title', '')} {active_concept}",
                                st.session_state.cleaned_text,
                                top_k=5
                            )

                            explanation = (
                                generate_teacher_explanation(
                                    concept_teaching_section,
                                    grounded_material,
                                    st.session_state.student_level,
                                    st.session_state.preferred_language,
                                    visual_spec=current_visual_spec
                                )
                            )

                            st.session_state.concept_explanations[concept_explanation_key] = explanation
                            active_event["text"] = explanation

                        except Exception as e:

                            st.error(
                                f"❌ Could not generate teacher explanation: {e}"
                            )


                # ------------------------------------------------
                # Explanation
                # ------------------------------------------------

                current_explanation = (
                    st.session_state.concept_explanations.get(concept_explanation_key, "")
                    if active_event and active_event.get("event_type") == "explanation" else ""
                )
                if current_explanation or (active_event and active_event.get("event_type") == "visual_explanation"):

                    st.markdown(
                        "### 👨‍🏫 Explanation"
                    )

                    if current_explanation:
                        st.markdown(current_explanation)

                    # --------------------------------------------
                    # 🔊 AI Teaching Voice (zero-cost, Edge TTS)
                    #
                    # Listen-along audio with word-by-word
                    # highlighting, generated on demand so a
                    # student who just wants to read doesn't pay
                    # the (small) TTS latency cost for nothing.
                    # --------------------------------------------

                    visual_narration = ""
                    if active_event and active_event.get("event_type") == "visual_explanation" and current_visual_spec:
                        narration_key = current_visual_spec["visual_id"] + "_" + st.session_state.preferred_language
                        if narration_key not in st.session_state.visual_narrations:
                            st.session_state.visual_narrations[narration_key] = generate_visual_narration(
                                current_visual_spec,
                                st.session_state.student_level,
                                st.session_state.preferred_language
                            )
                        visual_narration = st.session_state.visual_narrations[narration_key]
                        current_visual_spec["narration"] = visual_narration
                        current_visual_spec["explanation"] = visual_narration
                        active_event["text"] = visual_narration
                        st.markdown("**What to notice in the visual**")
                        st.write(visual_narration)

                    voice_text = (visual_narration or current_explanation).strip()
                    explanation_cache_key = get_cache_key(
                        voice_text,
                        st.session_state.preferred_language
                    )

                    if st.button(
                        "Play or replay narration",
                        key=f"listen_{current_index}_{concept_position}"
                    ):

                        if (
                            explanation_cache_key
                            not in st.session_state.tts_cache
                        ):

                            with st.spinner(
                                "🎙️ Generating voice..."
                            ):

                                try:

                                    audio_bytes, word_timings = (
                                        generate_speech(
                                            voice_text,
                                            st.session_state
                                            .preferred_language,
                                            gender=st.session_state.get("teacher_gender", "female")
                                        )
                                    )

                                    st.session_state.tts_cache[
                                        explanation_cache_key
                                    ] = (
                                        audio_bytes,
                                        word_timings
                                    )
                                    attach_audio_metadata(
                                        active_event,
                                        explanation_cache_key,
                                        word_timings
                                    )

                                except Exception as tts_error:

                                    st.error(
                                        "❌ Couldn't generate audio "
                                        f"right now: {tts_error}"
                                    )

                    if (
                        explanation_cache_key
                        in st.session_state.tts_cache
                    ):

                        cached_audio, cached_timings = (
                            st.session_state.tts_cache[
                                explanation_cache_key
                            ]
                        )

                        if cached_audio:

                            components.html(
                                build_classroom_video_html(
                                    cached_audio,
                                    cached_timings,
                                    section_title=concept_teaching_section.get("title", f"Section {current_index + 1}"),
                                    concept_title=str(active_concept) or "Key Concept",
                                    visual_spec=current_visual_spec,
                                    teacher_name=st.session_state.get("teacher_persona_name", "Dr. Sophia"),
                                    teacher_gender=st.session_state.get("teacher_gender", "female"),
                                    teacher_style=st.session_state.get("teacher_style", "Socratic Mentor")
                                ),
                                height=520,
                                scrolling=True
                            )
                            with st.expander("Captions / transcript"):
                                st.write(voice_text)

                    # --------------------------------------------
                    # 💬 IN-LESSON "ASK TEACHER" Q&A (Task 2 & Req 8)
                    # --------------------------------------------
                    with st.expander("💬 Ask Teacher / Clarify Concept (In-Lesson Q&A)", expanded=False):
                        st.caption(f"Have a doubt about **{active_concept}**? Ask {st.session_state.get('teacher_persona_name', 'your teacher')} without losing lesson state.")
                        qcols = st.columns(3)
                        preset_ask = ""
                        if qcols[0].button("💡 Another Example", key=f"qbtn_ex_{current_index}_{concept_position}"):
                            preset_ask = "Can you give another simple real-world example of this concept?"
                        if qcols[1].button("🇮🇳 Explain in Hindi / Hinglish", key=f"qbtn_hi_{current_index}_{concept_position}"):
                            preset_ask = "Please explain this concept in Hindi / Hinglish."
                        if qcols[2].button("❓ Why does this happen?", key=f"qbtn_why_{current_index}_{concept_position}"):
                            preset_ask = f"Why does this happen in {active_concept}?"

                        ask_text = st.text_input(
                            "Your question to teacher:",
                            value=preset_ask,
                            placeholder="e.g. 'Why does resistance increase heat?' or 'Explain in Hindi'",
                            key=f"ask_input_{current_index}_{concept_position}"
                        )
                        if st.button("🙋 Ask Teacher", key=f"send_ask_{current_index}_{concept_position}"):
                            if ask_text.strip():
                                with st.spinner("🧑‍🏫 Teacher is responding..."):
                                    grounded_qa = get_grounded_study_material(f"{active_concept} {ask_text}", st.session_state.cleaned_text, top_k=4)
                                    reply = answer_in_lesson_query(
                                        ask_text,
                                        str(active_concept),
                                        current_explanation or str(active_concept),
                                        study_material=grounded_qa,
                                        level=st.session_state.student_level,
                                        language=st.session_state.preferred_language,
                                        teacher_persona=st.session_state.get("teacher_persona_name", "Dr. Sophia")
                                    )
                                    st.session_state.setdefault("in_lesson_qa_history", {})[f"{current_index}_{concept_position}"] = reply

                        saved_reply = st.session_state.get("in_lesson_qa_history", {}).get(f"{current_index}_{concept_position}")
                        if saved_reply:
                            st.markdown(f"**🧑‍🏫 {st.session_state.get('teacher_persona_name', 'Teacher')} replied:**")
                            st.info(saved_reply)


                # ------------------------------------------------
                # Interactive question
                # ------------------------------------------------

                # Advance only non-interactive events. Question events pause
                # here until the existing assessment/adaptation flow releases
                # them, preserving the lesson's interactive nature.
                if active_event and active_event.get("event_type") != "question":
                    if st.button(
                        "Continue",
                        key=f"next_event_{current_index}_{event_cursor}",
                        icon=":material/arrow_forward:"
                    ):
                        state.setdefault("section_timeline_cursors", {})[current_index] = event_cursor + 1
                        st.rerun()
                    st.caption(
                        f"Concept {concept_position + 1} of {concept_count} · "
                        f"{active_event.get('event_type', 'teaching').replace('_', ' ')}"
                    )

                interactive_questions = lesson.get(
                    "interactive_questions",
                    []
                )


                section_questions = [
                    question for question in interactive_questions
                    if question.get("section_index") == current_index
                ]
                question_position = (
                    active_event.get("question_index", 0)
                    if active_event and active_event.get("event_type") == "question"
                    else state.setdefault("section_question_progress", {}).get(current_index, 0)
                )
                interactive_question = (
                    section_questions[question_position]
                    if active_event and active_event.get("event_type") == "question"
                    and question_position < len(section_questions)
                    else None
                )


                if interactive_question:

                    question_text = (
                        interactive_question.get(
                            "question",
                            "What did you learn from this section?"
                        )
                    )

                    expected_concept = (
                        interactive_question.get(
                            "expected_concept",
                            current_section.get(
                                "title",
                                ""
                            )
                        )
                    )


                    st.markdown(
                        f"### 💡 Checkpoint {question_position + 1} of {len(section_questions)}"
                    )

                    st.write(
                        question_text
                    )


                    # ------------------------------------------------
                    # Student answer
                    # ------------------------------------------------

                    question_options = interactive_question.get(
                        "options", []
                    )

                    if question_options:
                        student_answer = st.radio(
                            "Choose your answer:",
                            question_options,
                            key=f"student_mcq_{current_index}_{question_position}"
                        )

                    else:
                        render_speech_input_widget(key_suffix=f"{current_index}_{question_position}")
                        student_answer = st.text_area(
                            "✍️ Your Answer",
                            value=st.session_state.student_answer,
                            placeholder="Type your answer here, or click Speak Answer above...",
                            key=f"student_answer_{current_index}_{question_position}"
                        )


                    st.session_state.student_answer = student_answer


                    # ------------------------------------------------
                    # Check answer
                    # ------------------------------------------------

                    if st.button(
                        "🧠 Check My Answer",
                        key=f"check_answer_{current_index}"
                    ):

                        if question_options:
                            is_correct = student_answer == interactive_question.get(
                                "correct_answer", ""
                            )
                            evaluation = {
                                "score": 1 if is_correct else 0,
                                "correct": is_correct,
                                "feedback": (
                                    "Correct!" if is_correct else
                                    "Not quite. Let's revisit this idea."
                                )
                            }
                        else:
                            grounded_eval_mat = get_grounded_study_material(
                                f"{expected_concept} {question_text}",
                                st.session_state.cleaned_text,
                                top_k=4
                            )
                            evaluation = evaluate_answer(
                                student_answer,
                                expected_concept,
                                question=question_text,
                                study_material=grounded_eval_mat,
                                level=st.session_state.student_level,
                                language=st.session_state.preferred_language
                            )

                        st.session_state.answer_evaluation = (
                            evaluation
                        )

                        save_answer(
                            state,
                            question_text,
                            student_answer,
                            evaluation
                        )

                        # ------------------------------------------------
                        # Adaptive engine - this data already existed in
                        # teaching_engine.py, it just wasn't being called.
                        # Now every answer actually updates the student's
                        # concept performance and teaching difficulty.
                        # ------------------------------------------------

                        update_concept_performance(
                            state,
                            expected_concept,
                            evaluation.get("score", 0)
                        )

                        record_attempt(
                            state,
                            current_index
                        )

                        update_difficulty(
                            state,
                            evaluation
                        )

                        if evaluation.get(
                            "correct",
                            False
                        ):

                            next_question_position = question_position + 1
                            state["section_question_progress"][
                                current_index
                            ] = next_question_position
                            state.setdefault("section_timeline_cursors", {})[current_index] = event_cursor + 1
                            st.session_state.answer_evaluation = None
                            st.session_state.student_answer = ""
                            if next_question_position >= len(section_questions):
                                mark_section_completed(state, current_index)

                            # A correct retry clears any earlier
                            # re-teaching card for this section so
                            # it doesn't linger once resolved.
                            st.session_state.section_remediation.pop(
                                current_index,
                                None
                            )
                            st.session_state.section_adaptations.pop(
                                current_index,
                                None
                            )
                            st.rerun()

                        else:

                            # ------------------------------------
                            # 🧠 Misconception detection +
                            # targeted re-teaching. The AI
                            # evaluator (modules/teacher.py) now
                            # names the SPECIFIC wrong idea behind
                            # an incorrect/partial answer (not just
                            # "wrong") - record it, and if one was
                            # found, generate a re-explanation that
                            # directly corrects that misconception
                            # instead of a generic recap.
                            # ------------------------------------

                            misconception = evaluation.get(
                                "misconception",
                                ""
                            )

                            record_misconception(
                                state,
                                expected_concept,
                                misconception
                            )

                            # Every incorrect answer gets a re-teach. A named
                            # misconception makes it more targeted; otherwise
                            # the evaluator's feedback describes the gap.
                            learning_gap = (
                                misconception
                                or evaluation.get("feedback", "")
                                or "The core idea still needs review."
                            )

                            if learning_gap:

                                remediation_section = {
                                    "title": (
                                        f"Re-teaching: "
                                        f"{expected_concept}"
                                    ),
                                    "description": (
                                        "The student answered the practice "
                                        "question incorrectly. Explain why "
                                        "their reasoning is incomplete or "
                                        "incorrect, then give a different "
                                        "explanation or analogy and a simple "
                                        "example.\n\n"
                                        f"Question: {question_text}\n"
                                        f"Student answer: "
                                        f"{student_answer}\n"
                                        f"Learning gap to correct: "
                                        f"{learning_gap}"
                                    ),
                                    "key_points": [
                                        f"Learning gap: "
                                        f"{learning_gap}"
                                    ]
                                }

                                try:

                                    grounded_remed_mat = get_grounded_study_material(
                                        f"{expected_concept} {learning_gap}",
                                        st.session_state.cleaned_text,
                                        top_k=4
                                    )

                                    remediation_text = (
                                        generate_teacher_explanation(
                                            remediation_section,
                                            grounded_remed_mat,
                                            st.session_state
                                            .student_level,
                                            st.session_state
                                            .preferred_language
                                        )
                                    )

                                except Exception:

                                    remediation_text = (
                                        f"It looks like there's a "
                                        f"mix-up here: {misconception}"
                                        f". Let's revisit "
                                        f"{expected_concept}."
                                    )

                                st.session_state.section_remediation[
                                    current_index
                                ] = remediation_text

                                simplify = state.get(
                                    "attempts", {}
                                ).get(current_index, 0) > 1

                                follow_up_question = (
                                    generate_follow_up_question(
                                        expected_concept,
                                        question_text,
                                        student_answer,
                                        level=st.session_state.student_level,
                                        language=st.session_state.preferred_language,
                                        simplify=simplify
                                    )
                                )

                                st.session_state.section_adaptations[
                                    current_index
                                ] = {
                                    "follow_up_question": follow_up_question,
                                    "follow_up_evaluation": None,
                                    "simplified": simplify,
                                    "retry_count": 1,
                                    "question_position": question_position
                                }

                                add_adaptation_event(
                                    state,
                                    current_index,
                                    "re_explain_and_follow_up",
                                    learning_gap
                                )


                    # ------------------------------------------------
                    # Display feedback
                    # ------------------------------------------------

                    evaluation = (
                        st.session_state.answer_evaluation
                    )


                    if evaluation:

                        if evaluation.get(
                            "correct",
                            False
                        ):

                            st.success(
                                f"🎉 {evaluation.get('feedback', '')}"
                            )

                        else:

                            st.warning(
                                f"💡 {evaluation.get('feedback', '')}"
                            )


                        st.write(
                            f"Score: {evaluation.get('score', 0)} / 1"
                        )

                        # --------------------------------------------
                        # 🧠 Targeted re-teaching card - only shown
                        # when a specific misconception was detected
                        # for THIS section, so it doesn't linger
                        # after a correct retry or for a generic
                        # "didn't know it" wrong answer.
                        # --------------------------------------------

                        section_remediation_text = (
                            st.session_state.section_remediation.get(
                                current_index
                            )
                        )

                        if (
                            not evaluation.get("correct", False)
                            and section_remediation_text
                        ):

                            with st.expander(
                                "🧠 Let's clear up that mix-up",
                                expanded=True
                            ):

                                st.markdown(
                                    section_remediation_text
                                )

                                alternative_key = f"remedial_visual_{current_index}_{expected_concept}"
                                if alternative_key not in st.session_state.visual_cache:
                                    alternative_section = {
                                        "title": f"Simpler view: {expected_concept}",
                                        "description": "Use one concrete, beginner-friendly representation.",
                                        "concepts": [expected_concept]
                                    }
                                    st.session_state.visual_cache[alternative_key] = plan_concept_visuals(
                                        alternative_section, "Beginner", max_visuals=1,
                                        source_material=st.session_state.cleaned_text,
                                        concept_performance={expected_concept: 0}
                                    )
                                remedial_plan = st.session_state.visual_cache.get(alternative_key, [])
                                if remedial_plan:
                                    st.caption("A simpler visual framing")
                                    render_visual(remedial_plan[0])

                        adaptation = st.session_state.section_adaptations.get(
                            current_index
                        )

                        if adaptation:
                            st.markdown("### 🔁 Quick follow-up check")
                            st.write(adaptation["follow_up_question"])

                            render_speech_input_widget(key_suffix=f"followup_{current_index}")
                            follow_up_answer = st.text_area(
                                "Your follow-up answer",
                                placeholder="Try the new question in your own words...",
                                key=f"follow_up_answer_{current_index}"
                            )

                            if st.button(
                                "✅ Check follow-up answer",
                                key=f"check_follow_up_{current_index}"
                            ):
                                grounded_followup_mat = get_grounded_study_material(
                                    f"{expected_concept} {adaptation['follow_up_question']}",
                                    st.session_state.cleaned_text,
                                    top_k=4
                                )
                                follow_up_evaluation = evaluate_answer(
                                    follow_up_answer,
                                    expected_concept,
                                    question=adaptation["follow_up_question"],
                                    study_material=grounded_followup_mat,
                                    level=st.session_state.student_level,
                                    language=st.session_state.preferred_language
                                )

                                adaptation["follow_up_evaluation"] = (
                                    follow_up_evaluation
                                )
                                save_answer(
                                    state,
                                    adaptation["follow_up_question"],
                                    follow_up_answer,
                                    follow_up_evaluation,
                                    concept=expected_concept,
                                    section_index=current_index
                                )
                                update_concept_performance(
                                    state,
                                    expected_concept,
                                    follow_up_evaluation.get("score", 0)
                                )
                                record_attempt(state, current_index)
                                update_difficulty(state, follow_up_evaluation)

                                if follow_up_evaluation.get("correct", False):
                                    next_question_position = question_position + 1
                                    state["section_question_progress"][
                                        current_index
                                    ] = next_question_position
                                    state.setdefault("section_timeline_cursors", {})[current_index] = event_cursor + 1
                                    st.session_state.answer_evaluation = None
                                    st.session_state.student_answer = ""
                                    if next_question_position >= len(section_questions):
                                        mark_section_completed(state, current_index)
                                    st.session_state.section_remediation.pop(
                                        current_index, None
                                    )
                                    st.session_state.section_adaptations.pop(
                                        current_index, None
                                    )
                                    add_adaptation_event(
                                        state,
                                        current_index,
                                        "mastered_after_follow_up",
                                        "Student answered the follow-up correctly"
                                    )
                                    st.rerun()
                                else:
                                    # Three remedial checks is the ceiling:
                                    # record the weakness, then let the lesson
                                    # move forward rather than trapping a student.
                                    if adaptation.get("retry_count", 1) >= 3:
                                        state["section_question_progress"][
                                            current_index
                                        ] = question_position + 1
                                        state.setdefault("section_timeline_cursors", {})[current_index] = event_cursor + 1
                                        st.session_state.answer_evaluation = None
                                        st.session_state.student_answer = ""
                                        if question_position + 1 >= len(section_questions):
                                            mark_section_completed(state, current_index)
                                        add_adaptation_event(
                                            state,
                                            current_index,
                                            "weak_after_three_retries",
                                            "Maximum adaptive retries reached"
                                        )
                                        st.session_state.section_adaptations.pop(
                                            current_index, None
                                        )
                                        st.warning(
                                            "We'll revisit this weak concept later. You can continue."
                                        )
                                        st.rerun()

                                    # Keep the mastery loop active but lower
                                    # the next question's difficulty.
                                    retry_section = {
                                        "title": f"Simpler re-teaching: {expected_concept}",
                                        "description": (
                                            "The student is still struggling. "
                                            "Use a very simple, concrete analogy and a "
                                            "small worked example before asking again.\n\n"
                                            f"Question: {adaptation['follow_up_question']}\n"
                                            f"Student answer: {follow_up_answer}"
                                        ),
                                        "key_points": [f"Core idea: {expected_concept}"]
                                    }
                                    try:
                                        st.session_state.section_remediation[
                                            current_index
                                        ] = generate_teacher_explanation(
                                            retry_section,
                                            st.session_state.cleaned_text,
                                            "Beginner",
                                            st.session_state.preferred_language
                                        )
                                    except Exception:
                                        pass

                                    adaptation["follow_up_question"] = (
                                        generate_follow_up_question(
                                            expected_concept,
                                            adaptation["follow_up_question"],
                                            follow_up_answer,
                                            level="Beginner",
                                            language=st.session_state.preferred_language,
                                            simplify=True
                                        )
                                    )
                                    adaptation["follow_up_evaluation"] = None
                                    adaptation["simplified"] = True
                                    adaptation["retry_count"] = (
                                        adaptation.get("retry_count", 1) + 1
                                    )
                                    add_adaptation_event(
                                        state,
                                        current_index,
                                        "simplify_and_retry",
                                        "Follow-up answer was still insufficient"
                                    )

                            follow_up_evaluation = adaptation.get(
                                "follow_up_evaluation"
                            )
                            if follow_up_evaluation:
                                if follow_up_evaluation.get("correct", False):
                                    st.success("Great — you can continue to the next section.")
                                else:
                                    st.warning(
                                        follow_up_evaluation.get(
                                            "feedback",
                                            "Let's try one simpler check."
                                        )
                                    )


                # =================================================
                # NAVIGATION
                # =================================================

                st.divider()

                checkpoint_pending = (
                    interactive_question is not None
                    and current_index not in state.get(
                        "completed_sections", []
                    )
                )
                timeline_pending = (
                    active_event is not None
                    and active_event.get("event_type") != "question"
                )

                nav1, nav2, nav3 = st.columns(
                    [1, 1, 1]
                )


                with nav1:

                    if st.button(
                        "⬅️ Previous",
                        key=f"previous_{current_index}",
                        disabled=(current_index == 0)
                    ):

                        new_index = (
                            move_to_previous_section(
                                current_index
                            )
                        )

                        state["current_section"] = (
                            new_index
                        )

                        st.session_state.teacher_explanation = ""

                        st.session_state.answer_evaluation = None

                        st.session_state.student_answer = ""

                        st.session_state.section_remediation = {}
                        st.session_state.section_adaptations = {}

                        st.rerun()


                with nav2:

                    if st.button(
                        "🔄 Restart Lesson",
                        key="restart_lesson"
                    ):

                        st.session_state.teaching_state = (
                            initialize_lesson(
                                lesson
                            )
                        )

                        st.session_state.teacher_explanation = ""

                        st.session_state.answer_evaluation = None

                        st.session_state.student_answer = ""

                        st.rerun()


                with nav3:

                    if st.button(
                        "Next ➡️",
                        key=f"next_{current_index}",
                        disabled=(
                            current_index
                            >= total_sections - 1
                            or checkpoint_pending
                            or timeline_pending
                        )
                    ):

                        new_index = (
                            move_to_next_section(
                                current_index,
                                total_sections
                            )
                        )

                        state["current_section"] = (
                            new_index
                        )

                        st.session_state.teacher_explanation = ""

                        st.session_state.answer_evaluation = None

                        st.session_state.student_answer = ""

                        st.rerun()


            # ====================================================
            # FINAL QUIZ
            # ====================================================

            if (
                total_sections > 0
                and current_index == total_sections - 1
            ):

                st.divider()

                st.header(
                    "📝 Final Quiz"
                )

                quiz = lesson.get(
                    "final_quiz",
                    []
                )


                if not quiz:

                    st.info(
                        "No final quiz questions were generated."
                    )

                else:

                    for i, quiz_question in enumerate(
                        quiz
                    ):

                        st.markdown(
                            f"### Question {i + 1}"
                        )

                        st.write(
                            quiz_question.get(
                                "question",
                                ""
                            )
                        )

                        options = quiz_question.get(
                            "options",
                            []
                        )

                        if options:

                            answer = st.radio(
                                "Choose your answer:",
                                options,
                                key=f"quiz_{i}"
                            )

                            st.session_state.final_quiz_answers[
                                i
                            ] = answer


                    if st.button(
                        "🎯 Submit Quiz",
                        key="submit_quiz"
                    ):

                        score = 0

                        correct_count = 0

                        incorrect_count = 0

                        wrong_concepts = []

                        for i, quiz_question in enumerate(
                            quiz
                        ):

                            correct_answer = (
                                quiz_question.get(
                                    "correct_answer",
                                    ""
                                )
                            )

                            concept = quiz_question.get(
                                "concept",
                                ""
                            )

                            student_answer = (
                                st.session_state.final_quiz_answers.get(
                                    i,
                                    ""
                                )
                            )

                            is_correct = (
                                student_answer == correct_answer
                            )

                            if is_correct:

                                score += 1

                                correct_count += 1

                            else:

                                incorrect_count += 1

                                if concept and concept not in wrong_concepts:

                                    wrong_concepts.append(concept)

                            # --------------------------------------------
                            # Feed the final quiz into the SAME adaptive
                            # engine the section questions use, so weak
                            # concepts reflect the whole lesson, not just
                            # the "Think About It" questions.
                            # --------------------------------------------

                            if concept:

                                update_concept_performance(
                                    state,
                                    concept,
                                    1 if is_correct else 0
                                )

                        st.session_state.quiz_score = score

                        st.session_state.quiz_submitted = True

                        st.session_state.quiz_breakdown = {
                            "correct": correct_count,
                            "incorrect": incorrect_count,
                            "wrong_concepts": wrong_concepts
                        }


                    # ------------------------------------------------
                    # Quiz result
                    # ------------------------------------------------

                    if st.session_state.quiz_submitted:

                        total_questions = len(
                            quiz
                        )

                        score = (
                            st.session_state.quiz_score
                        )

                        breakdown = (
                            st.session_state.quiz_breakdown
                        )


                        st.success(
                            f"🎉 Your score: "
                            f"{score}/{total_questions}"
                        )

                        st.write(
                            f"✅ Correct: {breakdown.get('correct', 0)}"
                            f"&nbsp;&nbsp;&nbsp;"
                            f"❌ Incorrect: {breakdown.get('incorrect', 0)}",
                            unsafe_allow_html=True
                        )

                        wrong_concepts = breakdown.get(
                            "wrong_concepts",
                            []
                        )

                        if wrong_concepts:

                            st.markdown(
                                "**Topics to review:**"
                            )

                            for concept in wrong_concepts:

                                st.markdown(
                                    f"- {concept}"
                                )


                        if total_questions > 0:

                            percentage = (
                                score
                                / total_questions
                            ) * 100

                            if percentage == 100:

                                st.balloons()

                                st.success(
                                    "Excellent! You have understood the lesson very well."
                                )

                            elif percentage >= 60:

                                st.info(
                                    "Good job! Review the topics you found difficult."
                                )

                            else:

                                st.warning(
                                    "Keep practicing! Review the lesson sections and try again."
                                )


                        # ==================================================
                        # 🎓 LEARNING REPORT
                        # ==================================================

                        st.divider()

                        st.header(
                            "🎓 Your Learning Report"
                        )

                        summary = get_learning_summary(
                            state
                        )

                        report_col1, report_col2 = st.columns(2)

                        with report_col1:

                            st.metric(
                                "Section Questions Score",
                                f"{summary.get('percentage', 0)}%"
                            )

                        with report_col2:

                            st.metric(
                                "Final Quiz Score",
                                f"{score}/{total_questions}"
                            )

                        strong_concepts = summary.get(
                            "strong_concepts",
                            []
                        )

                        weak_concepts = summary.get(
                            "weak_concepts",
                            []
                        )

                        st.markdown(
                            "#### Strong Areas"
                        )

                        if strong_concepts:

                            for concept in strong_concepts:

                                st.markdown(
                                    f"✓ {concept}"
                                )

                        else:

                            st.caption(
                                "No strong areas identified yet."
                            )

                        st.markdown(
                            "#### Needs Improvement"
                        )

                        if weak_concepts:

                            for concept in weak_concepts:

                                st.markdown(
                                    f"⚠ {concept}"
                                )

                        else:

                            st.caption(
                                "No weak areas identified - nice work!"
                            )

                        misconceptions = summary.get(
                            "misconceptions",
                            []
                        )

                        if misconceptions:

                            st.markdown(
                                "#### Detected Misconceptions"
                            )

                            for item in misconceptions:

                                st.markdown(
                                    f"- {item.get('misconception', '')}"
                                )

                        if weak_concepts:

                            st.info(
                                "**Teacher Recommendation:** "
                                f"Review {', '.join(weak_concepts)} "
                                "and try a few extra practice questions "
                                "on these topics before moving on."
                            )

                        else:

                            st.info(
                                "**Teacher Recommendation:** "
                                "You're ready to move on to the next topic!"
                            )

                        # ------------------------------------------------
                        # 👤 PERSIST TO LEARNER PROFILE (Req 14)
                        # ------------------------------------------------
                        try:
                            record_session_result(
                                topic=lesson.get("topic", "Lesson"),
                                level=st.session_state.student_level,
                                language=st.session_state.preferred_language,
                                duration_minutes=st.session_state.lesson_duration,
                                learning_summary=summary,
                                final_score=score,
                                total_quiz_questions=total_questions
                            )
                            st.caption("✅ Session progress and concept mastery saved to your Student Profile.")
                        except Exception as prof_err:
                            print(f"Profile update note: {prof_err}")

                        # ------------------------------------------------
                        # 📚 REVISION FLASHCARDS & STUDY NOTES (Req 18)
                        # ------------------------------------------------
                        st.divider()
                        st.header("📚 Revision Flashcards & Study Tools")
                        st.write("Reinforce your understanding with active recall and downloadable study notes:")

                        tools_tab1, tools_tab2 = st.tabs(["🗂️ Interactive Flashcards", "📝 Comprehensive Study Notes"])

                        with tools_tab1:
                            flashcards = generate_flashcards(lesson, max_cards=6)
                            if flashcards:
                                fc_cols = st.columns(min(len(flashcards), 3))
                                for f_idx, card in enumerate(flashcards):
                                    col_fc = fc_cols[f_idx % len(fc_cols)]
                                    with col_fc:
                                        with st.container(border=True):
                                            st.markdown(f"**Card {f_idx + 1}: {card.get('concept', 'Key Idea')}**")
                                            st.write(f"❓ {card.get('front', '')}")
                                            with st.expander("💡 Reveal Concept Answer"):
                                                st.success(card.get("back", ""))
                            else:
                                st.caption("Flashcards generated from lesson checkpoints.")

                        with tools_tab2:
                            study_notes_md = generate_study_notes(lesson, language=st.session_state.preferred_language)
                            st.download_button(
                                "📥 Download Revision Notes (.md)",
                                data=study_notes_md,
                                file_name=f"EduSense_Revision_{lesson.get('topic', 'Lesson').replace(' ', '_')}.md",
                                mime="text/markdown",
                                key="download_study_notes_btn"
                            )
                            with st.expander("📖 Preview Revision Notes", expanded=True):
                                st.markdown(study_notes_md)



# ============================================================
# NO DOCUMENT
# ============================================================

else:

    st.info(
        "👆 Upload study material or enter a topic above to begin learning with EduSense AI."
    )
