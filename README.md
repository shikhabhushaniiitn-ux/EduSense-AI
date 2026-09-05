# 🎓 EduSense AI: The Human-Like Adaptive AI Educator

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/frontend-Streamlit-red.svg)](https://streamlit.io/)
[![Edge-TTS](https://img.shields.io/badge/speech-Neural%20Edge--TTS-green.svg)](https://github.com/rany2/edge-tts)
[![FAISS](https://img.shields.io/badge/vector%20search-FAISS-orange.svg)](https://github.com/facebookresearch/faiss)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**EduSense AI** is a competition-ready, multimodal, adaptive AI educator platform that transforms static study materials and open topics into interactive virtual classroom lectures. It features a pedagogical feedback loop with misconception detection, high-fidelity neural speech with synchronized lip-sync and subtitles, a 16:9 chalkboard video stage with recording export, grounded FAISS retrieval, and a persistent student cognitive profile.

---

## ✨ Key Capabilities

- **🎙️ Human-Like Virtual Classroom**: 16:9 canvas stage featuring customizable teacher personas (Dr. Sophia, Prof. Marcus, Alex Rivers), real-time animated lip-sync, dynamic blackboard concept rendering, and synchronized subtitles.
- **🧠 12-Step Adaptive Teaching Loop**: Formative checkpoints evaluate student answers, isolate specific conceptual misconceptions (e.g. confusing inertia with active force), deploy adaptive remediation, and issue targeted follow-up retries.
- **📚 Grounded RAG Ingestion**: Upload PDFs, Word documents, or plain text, or enter any syllabus topic. Content is parsed with PyMuPDF, unicode-sanitized, chunked, and embedded into FAISS vector space to ground all explanations and assessments.
- **🛡️ Multi-Tier AI Client Failover**: Cascading failover (`Gemini 3.6 Flash (Key 1)` ➔ `Gemini 3.6 Flash (Key 2)` ➔ `OpenRouter (DeepSeek/Gemini)` ➔ `Groq (Llama 3.1)`) guarantees zero downtime and immune resilience to rate limits.
- **🗣️ Neural Multilingual TTS**: Edge-TTS with character-weighted millisecond word timing interpolation for Hindi, Hinglish, English, and 10 other languages.
- **🎤 Web Speech Browser Voice Input**: Speech-to-Text integration enabling students to answer questions naturally using their microphone.
- **❓ In-Lesson "Ask Teacher" Drawer**: Real-time student doubt-clearing during active lessons without losing state or resetting timeline progress.
- **📈 Persistent Student Profile**: `data/learner_profile.json` tracks total sessions, study duration, concept mastery percentages, weak concepts, and recurring misconceptions.
- **🛠️ AI Study Tools & Visual Roadmaps**: One-click flashcard flip-deck, downloadable markdown revision notes, and interactive Mermaid prerequisite flowcharts.
- **🎥 WebM Video Recording**: Client-side recording combining canvas visuals and neural audio into downloadable `.webm` lecture videos.

---

## 🏗️ System Architecture

```text
Student Interaction (Voice / Text)
       │
       ▼
 ┌────────────────────────────────────────────────────────┐
 │                   Streamlit UI (app.py)                │
 │  - Lesson Configuration & Persona Selector             │
 │  - 16:9 Virtual Classroom Stage & Video Canvas         │
 │  - Checkpoint Questions & Speech-to-Text               │
 │  - In-Lesson Ask Teacher Drawer                        │
 └─────────────────────────┬──────────────────────────────┘
                           │
       ┌───────────────────┴──────────────────┐
       ▼                                      ▼
┌─────────────────────────┐        ┌─────────────────────────┐
│  RAG Knowledge Pipeline │        │ Multi-Tier AI Client    │
│  - PyMuPDF / docx Parser│        │  1. Gemini Key 1        │
│  - Unicode Normalizer   │        │  2. Gemini Key 2        │
│  - 120-Word Chunking    │        │  3. OpenRouter          │
│  - FAISS Vector Store   │        │  4. Groq (Llama 3.1)    │
└──────────────┬──────────┘        └──────────┬──────────────┘
               │                              │
               └──────────────┬───────────────┘
                              ▼
        ┌───────────────────────────────────────────┐
        │        Pedagogical State Machine          │
        │   (modules/teaching_timeline.py & engine) │
        │  1. Lesson Plan (5m - 7 Days)             │
        │  2. Grounded Explanation & Analogies      │
        │  3. Formative Checkpoint Question         │
        │  4. Misconception Evaluator               │
        │  5. Remediation & Follow-Up Retry         │
        │  6. Profile & Study Tools Generation      │
        └─────────────────────┬─────────────────────┘
                              │
       ┌──────────────────────┴──────────────────────┐
       ▼                                             ▼
┌─────────────────────────┐               ┌─────────────────────────┐
│ Multimodal Presentation │               │ Cognitive Memory        │
│ - Subject Visuals       │               │ - Learner Profile JSON  │
│ - Edge-TTS Neural Audio │               │ - Mermaid Roadmaps      │
│ - Canvas Lip-Sync Engine│               │ - Flashcard Flip Deck   │
│ - WebM Video Downloader │               │ - Markdown Notes Export │
└─────────────────────────┘               └─────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/shikhabhushaniiitn-ux/EduSense-AI.git
cd EduSense-AI

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows
# or source venv/bin/activate on Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)
Create a `.env` file in the root directory:
```ini
GEMINI_API_KEY_1=your_primary_gemini_key
GEMINI_API_KEY_2=your_secondary_gemini_key
OPENROUTER_API_KEY=your_openrouter_key
GROQ_API_KEY=your_groq_key
```

### 3. Run the Application
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

---

## 🧪 Verification & Testing

EduSense AI comes with comprehensive automated test suites:

### Modular Integration Tests
```bash
python test_modules.py
```
*Validates 10 core systems: text cleaning, LLM failover, TTS timing interpolation, visual generator, profile persistence, roadmap generator, study tools, doubt resolution, misconception detection, and FAISS RAG.*

### Golden Flow End-to-End Simulation
```bash
python test_golden_flow.py
```
*Simulates a full 20-minute Hinglish lesson on Newton's Laws with Dr. Sophia: from lesson planning and RAG retrieval to misconception detection, adaptive remediation, mastery confirmation, profile persistence, and flashcard generation.*

---

## 📁 Repository Structure

```text
EduSense-AI/
├── app.py                     # Main Streamlit application & interactive UI
├── requirements.txt           # Python dependencies
├── README.md                  # Project overview & documentation
├── test_modules.py            # 10-point unit & integration test suite
├── test_golden_flow.py        # End-to-end golden flow simulation
├── data/
│   └── learner_profile.json   # Persistent student cognitive memory & mastery log
├── docs/
│   └── TECHNICAL_DOCUMENTATION.md  # Detailed architectural documentation
└── modules/
    ├── ai_client.py           # Multi-tier LLM client with cascading failover
    ├── assessment.py          # Formative evaluation & misconception detector
    ├── audio_teacher.py       # Edge-TTS synthesizer with word timing interpolation
    ├── avatar_provider.py     # 16:9 Canvas virtual classroom & lip-sync renderer
    ├── learner_profile.py     # Student cognitive profile manager
    ├── learning_path.py       # AI prerequisite roadmap generator (Mermaid)
    ├── lesson_planner.py      # Adaptive curriculum planner (5m to 7 days)
    ├── pdf_processor.py       # Multi-format document parser (PDF, DOCX, TXT)
    ├── qa.py                  # In-lesson conversational doubt solver
    ├── retriever.py           # FAISS vector database & semantic search
    ├── study_tools.py         # Flashcard & revision note generator
    ├── style_dna.py           # Centralized visual design system
    ├── subject_visuals.py     # Physics, Math, Chemistry, CS visual generator
    ├── teacher.py             # Grounded explanation & retry question generator
    ├── teaching_engine.py     # Pedagogical state manager & difficulty tracker
    ├── teaching_timeline.py   # Teaching loop state machine
    ├── text_processor.py      # Unicode normalizer & text chunker
    └── topic_generator.py     # Syllabus & topic content generator
```

---

## 🏆 Round 2 Technical Assessment Compliance

| Assessment Requirement | Implementation Status | Implementation Details |
|---|---|---|
| **Real Adaptive Teaching Loop** | ✅ Verified (100%) | `teaching_timeline.py` & `teaching_engine.py` manage 12 pedagogical steps: Plan -> Explain -> Checkpoint -> Misconception Detect -> Remediation -> Retry. |
| **Multimodal Classroom Video** | ✅ Verified (100%) | 16:9 canvas stage with teacher personas, animated blackboard, dynamic LaTeX equations, procedural lip-sync, and WebM recording export. |
| **Neural Speech & Lip-Sync** | ✅ Verified (100%) | `edge-tts` with word boundary timing interpolation matching syllable length for sub-second subtitle and mouth sync. |
| **Document Ingestion & RAG** | ✅ Verified (100%) | PyMuPDF parser + Unicode cleaner + 120-word overlapping chunker + FAISS vector search actively grounded into explanations. |
| **LLM Resilience & Failover** | ✅ Verified (100%) | 4-tier cascade (`Gemini 1` -> `Gemini 2` -> `OpenRouter` -> `Groq`) guaranteeing zero downtime. |
| **Cognitive Memory & Profile** | ✅ Verified (100%) | Persistent JSON profiling tracking weak concepts, mastery scores, study duration, and misconception logs across sessions. |
| **Student Agency & Interaction**| ✅ Verified (100%) | In-lesson Ask Teacher drawer, Web Speech API browser STT voice input, and topic shortcut templates. |
| **Study Tools** | ✅ Verified (100%) | Interactive 3D flip flashcards, downloadable Markdown revision summaries, and Mermaid learning path roadmaps. |

---

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.