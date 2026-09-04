import json
import re
from collections import Counter

from modules.ai_client import generate_ai_response


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_topic_text(text):
    """
    Clean extracted document text.
    """

    if not text:
        return ""

    text = str(text)

    # Remove repeated whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# STRIP REPEATED BOILERPLATE (headers/footers)
# ============================================================

def strip_repeated_boilerplate_lines(text, min_repeats=2):
    """
    Remove lines that repeat verbatim many times across the
    document - the classic signature of a page header/footer
    (institute name, course code, page numbers, watermark text,
    etc. printed on every page of the source PDF).

    Without this, those lines end up dominating word-frequency
    based topic/concept detection simply because they appear
    once per page - e.g. an institute name like "Bharat Academix
    Institute of Information Technology" showing up as lesson
    concepts ("Nagpur", "Indian", "Institute", "Information",
    "Technology") even though it has nothing to do with the
    actual subject being taught.

    This is content-agnostic - it doesn't blacklist any specific
    words, it only removes lines that are suspiciously repetitive,
    so it works the same way regardless of what subject the PDF
    is about.

    NOTE (bugfix): min_repeats used to default to 3, so a footer
    that only appeared on 2 pages (a short document) was never
    caught. A short administrative-looking line (see the length
    cap below) repeating even twice, verbatim, is already a
    strong boilerplate signal - real prose essentially never
    repeats a full line word-for-word - so the default was
    lowered to 2.
    """

    if not text:
        return text

    lines = text.splitlines()

    if len(lines) < 10:
        # Too short a document for repetition-based detection
        # to be meaningful - leave it alone.
        return text

    normalized_counts = Counter()

    for line in lines:

        normalized = line.strip().lower()

        # Only short lines are realistic headers/footers -
        # a long repeated paragraph is very unlikely to be
        # boilerplate and more likely a genuinely important
        # repeated definition, so we leave those alone.
        if normalized and len(normalized) <= 80:
            normalized_counts[normalized] += 1

    boilerplate = {
        line
        for line, count in normalized_counts.items()
        if count >= min_repeats
    }

    if not boilerplate:
        return text

    cleaned_lines = [
        line
        for line in lines
        if line.strip().lower() not in boilerplate
    ]

    return "\n".join(cleaned_lines)


# ============================================================
# ADMINISTRATIVE METADATA FILTER
#
# Catches presenter/author credit, credentials, and institute
# affiliation lines - the kind of line a title slide or a
# footer carries on ANY academic PDF, regardless of subject
# ("Presented by: Dr. Amol P. Bhopale", "Assistant Professor",
# "Department of Computer Science and Engineering"). This is
# deliberately about universal ACADEMIC-DOCUMENT structure, not
# about subject content, so it stays generic across any topic.
#
# It complements strip_repeated_boilerplate_lines(): that
# function only catches a line if it repeats verbatim; this one
# catches metadata-shaped lines even if they appear only ONCE
# (e.g. a title-slide credit line that's never repeated).
# ============================================================

ADMINISTRATIVE_METADATA_PHRASES = (
    "presented by",
    "submitted by",
    "prepared by",
    "compiled by",
    "created by",
    "guided by",
    "under the guidance of",
    "assistant professor",
    "associate professor",
    "professor",
    "lecturer",
    "department of",
    "faculty of",
    "school of",
    "institute of",
    "university of",
    "college of",
    "roll no",
    "roll number",
    "reg no",
    "registration no",
    "student id",
    "enrollment no",
    "course code",
    "subject code",
    "academic year"
)

TITLE_PREFIXES = (
    "dr.", "prof.", "mr.", "ms.", "mrs.", "er."
)


def is_administrative_metadata_line(line):
    """
    True if `line` looks like document metadata (presenter/
    author credit, academic title, department/institute
    affiliation, roll/course number) rather than actual
    teachable content.
    """

    if not line:
        return False

    stripped = line.strip()

    if not stripped:
        return False

    normalized = normalize_text(stripped)

    if normalized:

        for phrase in ADMINISTRATIVE_METADATA_PHRASES:

            if phrase in normalized:
                return True

    stripped_lower = stripped.lower()

    for prefix in TITLE_PREFIXES:

        if stripped_lower.startswith(prefix):
            return True

    return False


def remove_administrative_metadata_lines(text):
    """
    Remove lines that are document metadata BEFORE any topic/
    concept/heading detection, so this metadata can never leak
    into extract_headings(), extract_important_words(), or
    extract_generic_concepts() - regardless of how many times it
    repeats in the document. Run this AFTER
    strip_repeated_boilerplate_lines() (that one catches broad
    verbatim repeats; this one catches metadata-shaped lines even
    when they show up only once, like a title-slide credit line).
    """

    if not text:
        return text

    lines = text.splitlines()

    cleaned_lines = [
        line
        for line in lines
        if not is_administrative_metadata_line(line)
    ]

    return "\n".join(cleaned_lines)


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):
    """
    Normalize text for comparisons.
    """

    if not text:
        return ""

    text = str(text).lower()

    # Keep letters, numbers and spaces
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Remove repeated spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# STOP WORDS
# ============================================================

STOP_WORDS = {
    "the", "and", "for", "that", "with", "this",
    "from", "are", "was", "were", "have", "has",
    "had", "will", "would", "should", "could",
    "into", "about", "than", "then", "them",
    "they", "their", "there", "which", "when",
    "where", "what", "while", "also", "such",
    "using", "used", "use", "can", "may",
    "not", "but", "all", "any", "our",
    "your", "its", "these", "those", "each",
    "between", "within", "through", "during",
    "after", "before", "under", "over",
    "input", "output", "data", "into",
    "more", "most", "other", "some",
    "these", "those", "being", "been",
    "does", "doing", "such", "very"
}


# ============================================================
# EXTRACT SENTENCES
# ============================================================

def extract_sentences(text):
    """
    Extract useful sentences from document text.
    """

    if not text:
        return []

    text = str(text)

    sentences = re.split(
        r"(?<=[.!?])\s+|\n+",
        text
    )

    cleaned_sentences = []

    for sentence in sentences:

        sentence = clean_topic_text(sentence)

        # Ignore tiny fragments
        if len(sentence) < 20:
            continue

        # Prevent extremely long content
        if len(sentence) > 500:
            sentence = sentence[:500].strip()

        cleaned_sentences.append(sentence)

    return cleaned_sentences


# ============================================================
# EXTRACT POSSIBLE HEADINGS
# ============================================================

def extract_headings(text, max_headings=12):
    """
    Try to detect headings from extracted document text.

    Works with PDFs where headings are available
    on separate lines.
    """

    if not text:
        return []

    lines = str(text).splitlines()

    headings = []

    for line in lines:

        original_line = line.strip()

        if not original_line:
            continue

        # Defense-in-depth: even if this line slipped past
        # remove_administrative_metadata_lines() (e.g. it wasn't
        # cleaned before this particular call site), never let a
        # presenter/credential/department line become a heading.
        if is_administrative_metadata_line(original_line):
            continue

        line = clean_topic_text(original_line)

        # Ignore very long lines
        if len(line) > 120:
            continue

        words = line.split()

        # Headings generally have a reasonable number of words
        if len(words) < 1 or len(words) > 15:
            continue

        # Avoid normal sentences
        if line.endswith("."):
            continue

        score = 0

        # ALL CAPS heading
        if original_line.isupper():
            score += 3

        # Numbered heading
        if re.match(
            r"^\d+(\.\d+)*[\)\.\-:]?\s+",
            line
        ):
            score += 3

        # Short line
        if len(words) <= 8:
            score += 1

        # Title-style text
        title_words = [
            word
            for word in words
            if word[:1].isupper()
        ]

        if len(title_words) >= max(1, len(words) // 2):
            score += 1

        if score >= 2:

            cleaned_heading = re.sub(
                r"^\d+(\.\d+)*[\)\.\-:]?\s*",
                "",
                line
            ).strip()

            if (
                len(cleaned_heading) >= 3
                and cleaned_heading not in headings
            ):
                headings.append(cleaned_heading)

        if len(headings) >= max_headings:
            break

    return headings


# ============================================================
# EXTRACT IMPORTANT WORDS
# ============================================================

def extract_important_words(text, max_words=20):
    """
    Extract meaningful frequently occurring words.

    This is generic and does not depend on the
    subject of the PDF.

    IMPORTANT: words are returned in the order they FIRST
    appear in the document, not by raw frequency. A word
    mentioned in passing near the end of the document (e.g.
    a place name inside one example) should never jump ahead
    of concepts that are introduced earlier - lesson sections
    and the detected topic should follow the same sequence as
    the source material, not word-count popularity.
    """

    if not text:
        return []

    words = re.findall(
        r"\b[a-zA-Z]{4,}\b",
        text.lower()
    )

    filtered_words = []

    for word in words:

        if word not in STOP_WORDS:
            filtered_words.append(word)

    frequency = Counter(filtered_words)

    # Words that occur often enough to count as "important",
    # picked the same way as before...
    qualifying_words = [
        word
        for word, count in frequency.most_common(max_words)
        if count >= 2
    ]

    # ...but then re-ordered by where they FIRST appear in
    # the document, so downstream concept/topic ordering
    # follows the document's own sequence.
    qualifying_words.sort(
        key=lambda word: words.index(word)
    )

    return qualifying_words


# ============================================================
# EXTRACT CONCEPTS
# ============================================================

def extract_generic_concepts(
    document_text,
    max_concepts=8
):
    """
    Extract concepts dynamically from ANY study material.

    Priority:
    1. Headings
    2. Frequently occurring meaningful words
    """

    concepts = []

    # --------------------------------------------------------
    # HEADINGS
    # --------------------------------------------------------

    headings = extract_headings(
        document_text,
        max_headings=max_concepts
    )

    for heading in headings:

        if heading not in concepts:

            concepts.append(heading)

        if len(concepts) >= max_concepts:
            return concepts[:max_concepts]

    # --------------------------------------------------------
    # IMPORTANT WORDS
    # --------------------------------------------------------

    important_words = extract_important_words(
        document_text,
        max_words=max_concepts * 3
    )

    for word in important_words:

        concept = word.capitalize()

        # Avoid very similar duplicates
        if not is_duplicate_text(
            concept,
            concepts
        ):
            concepts.append(concept)

        if len(concepts) >= max_concepts:
            break

    return concepts[:max_concepts]


# ============================================================
# TEXT DUPLICATE CHECK
# ============================================================

def is_duplicate_text(
    text,
    existing_texts,
    similarity_threshold=0.75
):
    """
    Simple local similarity detection.

    Prevents repeated concepts or repeated questions.
    """

    normalized = normalize_text(text)

    if not normalized:
        return False

    words = set(normalized.split())

    if not words:
        return False

    for existing in existing_texts:

        existing_normalized = normalize_text(existing)

        existing_words = set(
            existing_normalized.split()
        )

        if not existing_words:
            continue

        intersection = len(
            words & existing_words
        )

        union = len(
            words | existing_words
        )

        similarity = (
            intersection / union
            if union
            else 0
        )

        if similarity >= similarity_threshold:
            return True

    return False


# ============================================================
# DETECT MAIN TOPIC
# ============================================================

def detect_main_topic(document_text):
    """
    Detect the broad topic without relying on
    hardcoded subject names.

    Priority:
    1. First meaningful heading
    2. Combination of important words
    3. Generic fallback
    """

    if not document_text:
        return "Study Material"

    headings = extract_headings(
        document_text,
        max_headings=10
    )

    generic_headings = {
        "introduction",
        "overview",
        "contents",
        "summary",
        "references",
        "conclusion",
        "index"
    }

    for heading in headings:

        if (
            heading.lower()
            not in generic_headings
        ):
            return heading

    important_words = extract_important_words(
        document_text,
        max_words=6
    )

    if important_words:

        return " ".join(
            word.capitalize()
            for word in important_words[:3]
        )

    return "Study Material"


# ============================================================
# QUIZ QUESTION COUNT
# ============================================================

def get_quiz_question_count(duration_minutes):
    """
    Decide quiz size based on lesson duration.
    """

    try:
        duration_minutes = int(duration_minutes)

    except (
        TypeError,
        ValueError
    ):
        duration_minutes = 20

    if duration_minutes <= 5:
        return 3

    if duration_minutes <= 8:
        return 5

    if duration_minutes <= 10:
        return 6

    if duration_minutes <= 15:
        return 8

    if duration_minutes <= 20:
        return 10

    return 12


# ============================================================
# IN-LESSON CHECKPOINTS
# ============================================================

def get_checkpoint_count(duration_minutes):
    """Return a practical number of understanding checks for a lesson."""

    try:
        duration_minutes = int(duration_minutes)
    except (TypeError, ValueError):
        duration_minutes = 20

    if duration_minutes <= 15:
        return 2
    if duration_minutes <= 30:
        return 3
    if duration_minutes <= 45:
        return 4
    return 5


def extract_learning_topics(document_text, max_topics=15):
    """Return a small, source-grounded list for the optional topic picker."""

    if not document_text or not document_text.strip():
        return []

    topics = []
    for candidate in extract_headings(document_text, max_headings=max_topics * 2):
        candidate = " ".join(str(candidate).split()).strip()
        if 3 <= len(candidate) <= 100 and candidate not in topics:
            topics.append(candidate)
        if len(topics) >= max_topics:
            return topics

    for candidate in extract_generic_concepts(document_text, max_concepts=max_topics):
        candidate = " ".join(str(candidate).split()).strip()
        if 3 <= len(candidate) <= 80 and candidate not in topics:
            topics.append(candidate)
        if len(topics) >= max_topics:
            break

    return topics


# ============================================================
# LANGUAGE CONTENT
# ============================================================

def get_language_content(language):
    """
    Return structural labels based on language.

    AI generation will generate actual content
    in the selected language.
    """

    language = str(
        language
    ).lower().strip()

    # --------------------------------------------------------
    # HINDI
    # --------------------------------------------------------

    if language == "hindi":

        return {

            "introduction": "परिचय",
            "foundation": "मूल अवधारणाएँ",
            "core_concepts": "मुख्य अवधारणाएँ",
            "relationships": "अवधारणाओं के संबंध",
            "advanced": "उन्नत अवधारणाएँ",
            "application": "उदाहरण और अनुप्रयोग",
            "practice": "अभ्यास और पुनरावृत्ति",
            "quiz": "अंतिम क्विज़",

            "introduction_description":
                "विषय का परिचय दें और उसके महत्व को समझाएँ।",

            "foundation_description":
                "विषय की मूल अवधारणाओं को सरल तरीके से समझाएँ।",

            "core_concepts_description":
                "अध्ययन सामग्री की महत्वपूर्ण अवधारणाओं को समझाएँ।",

            "relationships_description":
                "महत्वपूर्ण अवधारणाओं के बीच संबंध समझाएँ।",

            "advanced_description":
                "अध्ययन सामग्री में उपलब्ध गहरी अवधारणाओं का अध्ययन करें।",

            "application_description":
                "उदाहरणों और व्यावहारिक उपयोगों के माध्यम से समझें।",

            "practice_description":
                "महत्वपूर्ण अवधारणाओं की पुनरावृत्ति और अभ्यास करें।",

            "quiz_description":
                "पूरे lesson में पढ़ाए गए concepts का परीक्षण करें।"
        }

    # --------------------------------------------------------
    # HINGLISH
    # --------------------------------------------------------

    if language == "hinglish":

        return {

            "introduction": "Introduction",
            "foundation": "Basic Concepts",
            "core_concepts": "Important Concepts",
            "relationships": "Concept Connections",
            "advanced": "Advanced Concepts",
            "application": "Examples aur Applications",
            "practice": "Practice aur Revision",
            "quiz": "Final Quiz",

            "introduction_description":
                "Topic ka introduction do aur batao ki yeh important kyun hai.",

            "foundation_description":
                "Basic concepts ko simple language mein samjhao.",

            "core_concepts_description":
                "Study material ke important concepts explain karo.",

            "relationships_description":
                "Important concepts ke beech relationship samjhao.",

            "advanced_description":
                "Study material ke deeper concepts explore karo.",

            "application_description":
                "Examples aur practical applications ke through samjhao.",

            "practice_description":
                "Important concepts revise karo aur practice karo.",

            "quiz_description":
                "Pure lesson mein cover kiye gaye concepts ko test karo."
        }

    # --------------------------------------------------------
    # ENGLISH
    # --------------------------------------------------------

    return {

        "introduction": "Introduction",
        "foundation": "Foundations",
        "core_concepts": "Core Concepts",
        "relationships": "Concept Relationships",
        "advanced": "Advanced Concepts",
        "application": "Examples and Applications",
        "practice": "Practice and Revision",
        "quiz": "Final Quiz",

        "introduction_description":
            "Introduce the topic and explain why it is important.",

        "foundation_description":
            "Explain the fundamental concepts in simple terms.",

        "core_concepts_description":
            "Explain the important concepts available in the study material.",

        "relationships_description":
            "Explain relationships between important concepts.",

        "advanced_description":
            "Explore deeper concepts supported by the study material.",

        "application_description":
            "Use examples and practical applications to understand the concepts.",

        "practice_description":
            "Review important concepts and apply them through practice.",

        "quiz_description":
            "Assess the concepts covered throughout the lesson."
    }


# ============================================================
# BUILD PROGRESSIVE CONCEPT SECTIONS
# ============================================================

def build_progressive_sections(
    concepts,
    level,
    language_text
):
    """
    Build sections dynamically.

    No subject-specific logic exists here.
    The same logic works for:
    - Machine Learning
    - Computer Networks
    - Operating Systems
    - Biology
    - History
    - Mathematics
    - Any other text-based study material
    """

    sections = []

    if not concepts:

        concepts = [
            "Fundamental Concepts"
        ]

    # --------------------------------------------------------
    # BEGINNER
    # --------------------------------------------------------

    if level == "Beginner":

        for concept in concepts[:4]:

            sections.append({

                "title":
                    concept,

                "description":
                    f"Understand the basic idea and importance of {concept}.",

                "key_points": [

                    f"What is {concept}?",

                    f"Why is {concept} important?",

                    f"Understand the basic principles of {concept}."
                ],
                # A section can be taught as a sequence of concepts.  Keep
                # this separate from the prose key points so downstream
                # teaching tools can anchor explanations and visuals.
                "concepts": [concept]
            })

    # --------------------------------------------------------
    # INTERMEDIATE
    # --------------------------------------------------------

    elif level == "Intermediate":

        # Foundations

        if concepts:

            sections.append({

                "title":
                    language_text["foundation"],

                "description":
                    language_text["foundation_description"],

                "key_points": [

                    f"Understand the foundations of {concepts[0]}.",

                    (
                        f"Understand the role of "
                        f"{concepts[1]}"
                        if len(concepts) > 1
                        else "Understand the fundamental principles."
                    )
                ]
            })

        # Core concepts

        core_points = []

        for concept in concepts[1:5]:

            core_points.append(
                f"Understand the meaning and role of {concept}."
            )

        if core_points:

            sections.append({

                "title":
                    language_text["core_concepts"],

                "description":
                    language_text["core_concepts_description"],

                "key_points": core_points,
                "concepts": concepts[1:5]
            })

        # Relationships

        if len(concepts) >= 2:

            sections.append({

                "title":
                    language_text["relationships"],

                "description":
                    language_text["relationships_description"],

                "key_points": [

                    (
                        f"Understand how {concepts[0]} "
                        f"relates to {concepts[1]}."
                    ),

                    (
                        "Identify relationships between "
                        "important concepts."
                    ),

                    (
                        "Understand how concepts work "
                        "together."
                    )
                ]
            })

    # --------------------------------------------------------
    # ADVANCED
    # --------------------------------------------------------

    else:

        # Foundations

        sections.append({

            "title":
                language_text["foundation"],

            "description":
                language_text["foundation_description"],

            "key_points": [

                f"Review the foundations of {concepts[0]}.",

                (
                    f"Connect {concepts[0]} "
                    f"with related concepts."
                )
            ]
        })

        # Core concepts

        core_points = []

        for concept in concepts[:5]:

            core_points.append(
                f"Analyze the role of {concept}."
            )

        sections.append({

            "title":
                language_text["core_concepts"],

            "description":
                language_text["core_concepts_description"],

            "key_points":
                core_points
        })

        # Relationships

        if len(concepts) >= 2:

            sections.append({

                "title":
                    language_text["relationships"],

                "description":
                    language_text["relationships_description"],

                "key_points": [

                    (
                        f"Analyze the relationship between "
                        f"{concepts[0]} and {concepts[1]}."
                    ),

                    (
                        "Compare related concepts and "
                        "approaches."
                    )
                ]
            })

        # Advanced concepts

        advanced_points = []

        for concept in concepts[5:8]:

            advanced_points.append(
                f"Explore deeper aspects of {concept}."
            )

        if advanced_points:

            sections.append({

                "title":
                    language_text["advanced"],

                "description":
                    language_text["advanced_description"],

                "key_points":
                    advanced_points
            })

    return sections


# ============================================================
# DISTRIBUTE TIME
# ============================================================

def distribute_time(
    total_duration,
    number_of_sections
):
    """
    Distribute total duration exactly among sections.
    """

    if number_of_sections <= 0:
        return []

    try:

        total_duration = int(
            total_duration
        )

    except (
        TypeError,
        ValueError
    ):

        total_duration = 0

    if total_duration < 0:

        total_duration = 0

    base_time = (
        total_duration
        // number_of_sections
    )

    remainder = (
        total_duration
        % number_of_sections
    )

    times = []

    for index in range(
        number_of_sections
    ):

        if index < remainder:

            times.append(
                base_time + 1
            )

        else:

            times.append(
                base_time
            )

    return times


# ============================================================
# BUILD SECTION-SPECIFIC QUESTION
# ============================================================

def build_section_question(
    section,
    index=0
):
    """
    Create a Think About It question directly
    from the CURRENT section.

    This prevents questions from being unrelated
    to the section being taught.
    """

    title = section.get(
        "title",
        "this concept"
    )

    key_points = section.get(
        "key_points",
        []
    )

    description = section.get(
        "description",
        ""
    )

    if not key_points:

        key_points = [
            f"Understand the main idea of {title}."
        ]

    question_templates = [

        {
            "question":
                f"Think About It: How would you explain {title} in your own words?",

            "expected_concept":
                description or key_points[0],

            "question_type":
                "short_answer"
        },

        {
            "question":
                (
                    f"Think About It: Why is "
                    f"{title} important in this topic?"
                ),

            "expected_concept":
                key_points[0],

            "question_type":
                "conceptual"
        },

        {
            "question":
                (
                    f"Think About It: How could you apply "
                    f"{title} to a practical situation?"
                ),

            "expected_concept":
                (
                    "The answer should connect the concept "
                    "with an appropriate practical example."
                ),

            "question_type":
                "conceptual"
        }
    ]

    selected = question_templates[
        index % len(question_templates)
    ]

    return {

        "question":
            selected["question"],

        "question_type":
            selected["question_type"],

        "expected_concept":
            selected["expected_concept"],

        "concept":
            title
    }


# ============================================================
# ATTACH QUESTIONS TO SECTIONS
# ============================================================

def attach_section_questions(sections):
    """
    Attach one Think About It question directly
    inside each teaching section.

    Introduction, practice and quiz can still
    exist without a Think About It question.
    """

    existing_questions = []

    for index, section in enumerate(sections):

        title = normalize_text(
            section.get("title", "")
        )

        # Skip practice and quiz sections
        skip_titles = {
            "practice and revision",
            "practice aur revision",
            "अभ्यास और पुनरावृत्ति",
            "final quiz",
            "अंतिम क्विज़"
        }

        if title in {
            normalize_text(item)
            for item in skip_titles
        }:
            continue

        question_data = build_section_question(
            section,
            index
        )

        question_text = question_data[
            "question"
        ]

        if not is_duplicate_text(
            question_text,
            existing_questions
        ):

            section[
                "think_about_it"
            ] = question_data

            existing_questions.append(
                question_text
            )

    return sections


def ensure_section_concepts(sections):
    """Give every legacy/AI lesson section a stable concept sequence.

    Older plans contain only ``key_points``.  This compatibility layer keeps
    those plans usable without forcing a wholesale lesson-plan migration.
    """
    for section in sections or []:
        concepts = section.get("concepts")
        if not isinstance(concepts, list) or not concepts:
            concepts = section.get("key_points") or [section.get("title", "")]
        cleaned = []
        seen = set()
        for concept in concepts:
            concept = str(concept).strip()
            key = normalize_text(concept)
            if concept and key and key not in seen:
                seen.add(key)
                cleaned.append(concept)
        section["concepts"] = cleaned or [str(section.get("title", "Current concept"))]
    return sections


def distribute_interactive_checkpoints(sections, interactive_questions, duration_minutes):
    """Place duration-appropriate checks after taught sections.

    Plans from the AI and the local fallback have slightly different
    question shapes.  This normalizes both into questions explicitly tied
    to a section index, so the teacher never displays a question before its
    material or accidentally reuses the last question for later sections.
    """

    candidates = []
    for index, section in enumerate(sections):
        title = normalize_text(section.get("title", ""))
        if "practice" not in title and "quiz" not in title:
            candidates.append(index)

    if not candidates:
        return []

    # Every substantive teaching section gets a queue. Longer lessons and
    # larger sections receive more checks, so this is not a fixed "three per
    # section" rule. Questions remain sequential in the UI.
    total_teaching_minutes = max(
        1, sum(sections[index].get("duration_minutes", 0) for index in candidates)
    )
    positions = []
    for section_index in candidates:
        section_minutes = sections[section_index].get("duration_minutes", 0)
        question_count = 1
        if duration_minutes >= 30 and section_minutes * 2 >= total_teaching_minutes / len(candidates):
            question_count = 2
        if duration_minutes >= 45 and section_minutes * 3 >= total_teaching_minutes / len(candidates):
            question_count = 3
        positions.extend([section_index] * min(question_count, 3))

    source_questions = list(interactive_questions or [])
    normalized = []
    used_text = []

    per_section_number = {}
    for question_number, section_index in enumerate(positions):
        section = sections[section_index]
        within_section = per_section_number.get(section_index, 0)
        per_section_number[section_index] = within_section + 1
        question = section.get("think_about_it") if within_section == 0 else None

        if not question:
            section_title = section.get("title", "")
            question = next(
                (
                    item for item in source_questions
                    if item.get("section_title") == section_title
                ),
                None
            )

        if not question and question_number < len(source_questions):
            question = source_questions[question_number]

        if not question:
            question = build_section_question(section, section_index)

        question_copy = question.copy()
        question_text = question_copy.get("question", "")
        if not question_text or is_duplicate_text(question_text, used_text):
            question_copy = build_section_question(section, section_index + within_section + 1)
            question_text = question_copy["question"]

        question_copy["section_index"] = section_index
        question_copy["section_title"] = section.get("title", "")
        question_copy["question_id"] = f"section-{section_index}-question-{within_section + 1}"
        question_copy["concept_id"] = question_copy.get("concept", question_copy.get("expected_concept", section.get("title", "")))
        question_copy["difficulty"] = "advanced" if within_section >= 2 else ("application" if within_section else "foundation")
        question_copy["purpose"] = "check_understanding"
        normalized.append(question_copy)
        used_text.append(question_text)

    return normalized


# ============================================================
# BUILD GENERIC QUIZ POOL
# ============================================================

def build_generic_quiz_pool(
    topic,
    concepts
):
    """
    Build generic MCQ questions dynamically.

    Questions are based on concepts extracted from
    the document and contain no subject-specific
    hardcoded knowledge.
    """

    quiz_pool = []

    # Topic question

    quiz_pool.append({

        "question":
            f"What is the main goal of studying {topic}?",

        "question_type":
            "mcq",

        "concept":
            topic,

        "options": [

            "Understand and apply the important concepts",

            "Ignore the study material",

            "Memorize unrelated information",

            "Avoid learning the topic"
        ],

        "correct_answer":
            "Understand and apply the important concepts"
    })

    # Concept questions

    for concept in concepts:

        quiz_pool.append({

            "question":
                f"Why is understanding {concept} important?",

            "question_type":
                "mcq",

            "concept":
                concept,

            "options": [

                f"It helps build understanding of {topic}",

                "It is unrelated to the topic",

                "It removes the need for learning",

                "It has no connection with the study material"
            ],

            "correct_answer":
                f"It helps build understanding of {topic}"
        })

        quiz_pool.append({

            "question":
                (
                    f"Which statement best describes "
                    f"the role of {concept}?"
                ),

            "question_type":
                "mcq",

            "concept":
                concept,

            "options": [

                (
                    f"It is an important concept "
                    f"for understanding {topic}"
                ),

                "It is completely unrelated",

                "It removes all other concepts",

                "It prevents learning"
            ],

            "correct_answer":
                (
                    f"It is an important concept "
                    f"for understanding {topic}"
                )
        })

    return quiz_pool


# ============================================================
# SELECT UNIQUE QUIZ QUESTIONS
# ============================================================

def select_unique_quiz_questions(
    quiz_pool,
    question_count
):
    """
    Select unique quiz questions.

    Never intentionally repeats questions.
    """

    final_quiz = []

    used_questions = []

    for question in quiz_pool:

        question_text = question.get(
            "question",
            ""
        )

        if is_duplicate_text(
            question_text,
            used_questions
        ):
            continue

        final_quiz.append(
            question.copy()
        )

        used_questions.append(
            question_text
        )

        if len(final_quiz) >= question_count:
            break

    return final_quiz


# ============================================================
# SCOPE DOCUMENT TO A SPECIFIC TOPIC/SECTION
# ============================================================

def scope_document_to_topic(document_text, focus_topic):
    """
    Narrow the study material down to just the part relevant
    to a specific topic/section the student asked for, so the
    LOCAL planner only builds sections from that part instead
    of the whole document.

    The local planner has no real language understanding, so
    it needs a deterministic heading-based slice. (The AI
    planner instead gets the full document plus an explicit
    instruction - see focus_topic_instruction in
    generate_ai_lesson_plan - since the AI can understand
    semantic scope directly.)

    Returns (scoped_text, matched_label, found):
        scoped_text   - the narrowed text to use (or the
                         original document_text if nothing
                         matched, so callers can safely fall
                         back to a full-document lesson)
        matched_label - the heading/phrase that matched, or
                         None
        found         - False only when focus_topic was given
                         but nothing in the document matched it
    """

    if not focus_topic or not focus_topic.strip():
        return document_text, None, True

    focus_topic_lower = focus_topic.strip().lower()

    headings = extract_headings(
        document_text,
        max_headings=40
    )

    matched_heading = None

    for heading in headings:

        heading_lower = heading.lower()

        if (
            focus_topic_lower in heading_lower
            or heading_lower in focus_topic_lower
        ):
            matched_heading = heading
            break

    # ----------------------------------------------------
    # Slice between the matched heading and the NEXT heading
    # ----------------------------------------------------

    if matched_heading:

        lines = document_text.splitlines()

        heading_lines_lower = [
            h.lower() for h in headings
        ]

        start_index = None
        end_index = len(lines)
        found_start = False

        for i, line in enumerate(lines):

            cleaned_line = clean_topic_text(
                line.strip()
            )

            if not cleaned_line:
                continue

            if not found_start:

                if matched_heading.lower() in cleaned_line.lower():
                    start_index = i
                    found_start = True

                continue

            if (
                cleaned_line.lower() in heading_lines_lower
                and cleaned_line.lower() != matched_heading.lower()
            ):
                end_index = i
                break

        if start_index is not None:

            scoped_text = "\n".join(
                lines[start_index:end_index]
            ).strip()

            # Sanity check - make sure we actually captured
            # enough content to build a lesson from.
            if len(scoped_text) > 200:
                return scoped_text, matched_heading, True

    # ----------------------------------------------------
    # Fallback: the focus_topic text appears literally
    # somewhere in the document - take a window around it
    # ----------------------------------------------------

    text_lower = document_text.lower()

    position = text_lower.find(focus_topic_lower)

    if position != -1:

        window_start = max(0, position - 1500)
        window_end = min(len(document_text), position + 4000)

        scoped_text = document_text[window_start:window_end]

        return scoped_text, focus_topic, True

    # ----------------------------------------------------
    # Nothing matched at all
    # ----------------------------------------------------

    return document_text, None, False


# ============================================================
# GENERATE LOCAL LESSON PLAN
# ============================================================

def generate_local_lesson_plan(
    document_text,
    level,
    language,
    duration_minutes,
    focus_topic=None
):
    """
    Generic local fallback.

    IMPORTANT:
    This does NOT depend on PDF subject type.

    It dynamically extracts:
    - topic
    - headings
    - concepts
    - important words
    """

    # --------------------------------------------------------
    # SCOPE TO A SPECIFIC TOPIC/SECTION (if requested)
    #
    # Done BEFORE any cleaning, so heading matching can still
    # see the document's original line breaks.
    # --------------------------------------------------------

    scoped_text, matched_focus_label, focus_found = (
        scope_document_to_topic(
            document_text,
            focus_topic
        )
    )

    # --------------------------------------------------------
    # Strip repeated headers/footers (institute name, page
    # numbers, watermark text, etc.) BEFORE any topic/concept
    # detection - see strip_repeated_boilerplate_lines() for
    # why this matters.
    # --------------------------------------------------------

    scoped_text = strip_repeated_boilerplate_lines(
        scoped_text
    )

    scoped_text = remove_administrative_metadata_lines(
        scoped_text
    )

    # --------------------------------------------------------
    # BUG FIX: detect_main_topic()/extract_generic_concepts()
    # rely on extract_headings(), which finds headings by
    # splitting the text into LINES. clean_topic_text()
    # collapses ALL whitespace - including newlines - into
    # single spaces, so calling it BEFORE heading detection
    # silently destroyed every line break and made real
    # headings undetectable. That forced the local planner to
    # almost always fall back to raw word-frequency guessing
    # for the topic/concepts instead of the document's actual
    # headings, which is what produced garbled topics like
    # "Regression Linear Nagpur" out of a document that had
    # perfectly good headings.
    #
    # Fix: run heading-based detection on the RAW text first,
    # and only clean_topic_text() afterwards for anything that
    # doesn't need line structure.
    # --------------------------------------------------------

    topic = detect_main_topic(
        scoped_text
    )

    concepts = extract_generic_concepts(
        scoped_text,
        max_concepts=8
    )

    document_text = clean_topic_text(
        scoped_text
    )

    language_text = get_language_content(
        language
    )

    # --------------------------------------------------------
    # BUILD CONCEPT SECTIONS
    # --------------------------------------------------------

    concept_sections = build_progressive_sections(

        concepts,

        level,

        language_text
    )

    if not concept_sections:

        concept_sections = [{

            "title":
                language_text["foundation"],

            "description":
                language_text[
                    "foundation_description"
                ],

            "key_points": [

                (
                    "Understand the fundamental concepts "
                    "introduced in the study material."
                )
            ]
        }]

    # --------------------------------------------------------
    # TOTAL SECTIONS
    # --------------------------------------------------------

    total_sections = (

        1

        + len(concept_sections)

        + 2
    )

    section_times = distribute_time(

        duration_minutes,

        total_sections
    )

    time_index = 0

    sections = []

    # --------------------------------------------------------
    # INTRODUCTION
    # --------------------------------------------------------

    sections.append({

        "title":
            language_text[
                "introduction"
            ],

        "duration_minutes":
            section_times[time_index],

        "description":
            language_text[
                "introduction_description"
            ],

        "key_points": [

            f"What is {topic}?",

            f"Why is {topic} important?"
        ]
    })

    time_index += 1

    # --------------------------------------------------------
    # CONCEPT SECTIONS
    # --------------------------------------------------------

    for section in concept_sections:

        section_copy = section.copy()

        section_copy[
            "duration_minutes"
        ] = section_times[time_index]

        sections.append(
            section_copy
        )

        time_index += 1

    # --------------------------------------------------------
    # APPLICATION
    # --------------------------------------------------------

    if level in [
        "Intermediate",
        "Advanced"
    ]:

        # Add application by reusing part of practice
        sections.append({

            "title":
                language_text[
                    "application"
                ],

            "duration_minutes":
                0,

            "description":
                language_text[
                    "application_description"
                ],

            "key_points": [

                (
                    "Connect the concepts with "
                    "practical examples."
                ),

                (
                    "Identify situations where "
                    "the concepts can be applied."
                ),

                (
                    "Analyze how different concepts "
                    "work together."
                )
            ]
        })

    # --------------------------------------------------------
    # PRACTICE
    # --------------------------------------------------------

    sections.append({

        "title":
            language_text[
                "practice"
            ],

        "duration_minutes":
            0,

        "description":
            language_text[
                "practice_description"
            ],

        "key_points": [

            "Review the important concepts.",

            "Apply the concepts to examples.",

            "Answer conceptual questions."
        ]
    })

    # --------------------------------------------------------
    # QUIZ
    # --------------------------------------------------------

    sections.append({

        "title":
            language_text[
                "quiz"
            ],

        "duration_minutes":
            0,

        "description":
            language_text[
                "quiz_description"
            ],

        "key_points": [

            "Review important concepts.",

            "Answer multiple-choice questions.",

            "Apply concepts to practical situations."
        ]
    })

    # --------------------------------------------------------
    # REDISTRIBUTE TIME
    # --------------------------------------------------------

    final_times = distribute_time(

        duration_minutes,

        len(sections)
    )

    for index, section in enumerate(sections):

        section[
            "duration_minutes"
        ] = final_times[index]

    # --------------------------------------------------------
    # SECTION-SPECIFIC QUESTIONS
    # --------------------------------------------------------

    sections = attach_section_questions(
        sections
    )

    # --------------------------------------------------------
    # LEARNING OBJECTIVES
    # --------------------------------------------------------

    learning_objectives = [

        (
            f"Understand the fundamental concepts "
            f"of {topic}."
        ),

        (
            "Explain important concepts using "
            "appropriate examples."
        ),

        (
            "Apply concepts from the study "
            "material."
        )
    ]

    if level == "Intermediate":

        learning_objectives.extend([

            (
                "Connect related concepts "
                "together."
            ),

            (
                "Apply concepts to practical "
                "situations."
            )
        ])

    elif level == "Advanced":

        learning_objectives.extend([

            (
                "Analyze relationships between "
                "concepts."
            ),

            (
                "Compare related concepts "
                "when supported."
            ),

            (
                "Apply theoretical concepts "
                "to complex problems."
            ),

            (
                "Evaluate concepts critically."
            )
        ])

    # --------------------------------------------------------
    # INTERACTIVE QUESTIONS
    #
    # Also preserve the top-level field for
    # compatibility with your current app.
    # --------------------------------------------------------

    interactive_questions = distribute_interactive_checkpoints(
        sections,
        [],
        duration_minutes
    )

    # --------------------------------------------------------
    # FINAL QUIZ
    # --------------------------------------------------------

    quiz_question_count = (
        get_quiz_question_count(
            duration_minutes
        )
    )

    quiz_pool = build_generic_quiz_pool(

        topic,

        concepts
    )

    final_quiz = select_unique_quiz_questions(

        quiz_pool,

        quiz_question_count
    )

    # --------------------------------------------------------
    # FINAL PLAN
    # --------------------------------------------------------

    lesson_plan = {

        "topic":
            topic,

        "level":
            level,

        "language":
            language,

        "duration_minutes":
            duration_minutes,

        "learning_objectives":
            learning_objectives,

        "sections":
            sections,

        "interactive_questions":
            interactive_questions,

        "final_quiz":
            final_quiz,

        "focus_topic_requested":
            focus_topic,

        "focus_topic_found":
            focus_found
    }

    ensure_section_concepts(lesson_plan["sections"])

    return lesson_plan


# ============================================================
# CLEAN AI JSON RESPONSE
# ============================================================

def clean_ai_json_response(response):
    """
    Remove markdown fences and extract JSON.
    """

    if not response:

        raise ValueError(
            "AI returned an empty response."
        )

    response = response.strip()

    # Remove Markdown fences

    response = re.sub(

        r"^```(?:json)?\s*",

        "",

        response,

        flags=re.IGNORECASE
    )

    response = re.sub(

        r"\s*```$",

        "",

        response
    )

    response = response.strip()

    # Extract JSON object

    start = response.find("{")

    end = response.rfind("}")

    if (

        start != -1

        and end != -1

        and end > start

    ):

        response = response[
            start:end + 1
        ]

    return response


# ============================================================
# VALIDATE QUESTION
# ============================================================

def validate_question(question):
    """
    Validate standardized question structure.
    """

    if not isinstance(
        question,
        dict
    ):

        raise ValueError(
            "Question must be an object."
        )

    if "question" not in question:

        raise ValueError(
            "Question text is missing."
        )

    question_type = question.get(
        "question_type",
        "short_answer"
    )

    valid_question_types = [

        "mcq",

        "short_answer",

        "conceptual"
    ]

    if question_type not in valid_question_types:

        raise ValueError(
            "Invalid question_type."
        )

    # --------------------------------------------------------
    # MCQ
    # --------------------------------------------------------

    if question_type == "mcq":

        if not isinstance(
            question.get("options"),
            list
        ):

            raise ValueError(
                "MCQ options must be a list."
            )

        if len(
            question["options"]
        ) < 2:

            raise ValueError(
                "MCQ must have at least two options."
            )

        if (
            question.get("correct_answer")
            not in question["options"]
        ):

            raise ValueError(
                "MCQ correct_answer must match an option."
            )

    # --------------------------------------------------------
    # SHORT / CONCEPTUAL
    # --------------------------------------------------------

    else:

        if not question.get(
            "expected_concept"
        ):

            raise ValueError(
                "Expected concept is missing."
            )

    return question


# ============================================================
# VALIDATE AI LESSON PLAN
# ============================================================

def validate_ai_lesson_plan(
    lesson_plan,
    level,
    language,
    duration_minutes
):
    """
    Validate AI-generated lesson plan.
    """

    if not isinstance(
        lesson_plan,
        dict
    ):

        raise ValueError(
            "AI lesson plan is not a JSON object."
        )

    required_fields = [

        "topic",

        "level",

        "language",

        "duration_minutes",

        "learning_objectives",

        "sections",

        "interactive_questions",

        "final_quiz"
    ]

    for field in required_fields:

        if field not in lesson_plan:

            raise ValueError(
                f"AI lesson plan is missing '{field}'."
            )

    # Force selected settings

    lesson_plan[
        "level"
    ] = level

    lesson_plan[
        "language"
    ] = language

    lesson_plan[
        "duration_minutes"
    ] = duration_minutes

    # --------------------------------------------------------
    # LIST VALIDATION
    # --------------------------------------------------------

    list_fields = [

        "learning_objectives",

        "sections",

        "interactive_questions",

        "final_quiz"
    ]

    for field in list_fields:

        if not isinstance(
            lesson_plan[field],
            list
        ):

            raise ValueError(
                f"AI {field} must be a list."
            )

    # --------------------------------------------------------
    # SECTION VALIDATION
    # --------------------------------------------------------

    total_section_time = 0

    section_questions = []

    for section in lesson_plan[
        "sections"
    ]:

        if not isinstance(
            section,
            dict
        ):

            raise ValueError(
                "Each section must be an object."
            )

        required_section_fields = [

            "title",

            "duration_minutes",

            "description",

            "key_points"
        ]

        for field in required_section_fields:

            if field not in section:

                raise ValueError(
                    f"Lesson section is missing '{field}'."
                )

        section_time = int(
            section[
                "duration_minutes"
            ]
        )

        if section_time < 0:

            raise ValueError(
                "Section duration cannot be negative."
            )

        section[
            "duration_minutes"
        ] = section_time

        total_section_time += (
            section_time
        )

        # Validate section-specific question

        if section.get(
            "think_about_it"
        ):

            validate_question(
                section[
                    "think_about_it"
                ]
            )

            section_questions.append(

                section[
                    "think_about_it"
                ].copy()
            )

    if total_section_time != duration_minutes:

        raise ValueError(
            "AI section durations do not add up "
            "to the requested duration."
        )

    # --------------------------------------------------------
    # INTERACTIVE QUESTIONS
    # --------------------------------------------------------

    validated_interactive = []

    existing_questions = []

    for question in lesson_plan[
        "interactive_questions"
    ]:

        validate_question(
            question
        )

        question_text = question[
            "question"
        ]

        if is_duplicate_text(
            question_text,
            existing_questions
        ):
            continue

        existing_questions.append(
            question_text
        )

        validated_interactive.append(
            question
        )

    lesson_plan[
        "interactive_questions"
    ] = distribute_interactive_checkpoints(
        lesson_plan["sections"],
        validated_interactive,
        duration_minutes
    )

    # --------------------------------------------------------
    # FINAL QUIZ
    # --------------------------------------------------------

    validated_quiz = []

    existing_quiz_questions = []

    for question in lesson_plan[
        "final_quiz"
    ]:

        validate_question(
            question
        )

        question_text = question[
            "question"
        ]

        if is_duplicate_text(
            question_text,
            existing_quiz_questions
        ):
            continue

        existing_quiz_questions.append(
            question_text
        )

        validated_quiz.append(
            question
        )

    lesson_plan[
        "final_quiz"
    ] = validated_quiz

    ensure_section_concepts(lesson_plan["sections"])

    return lesson_plan


# ============================================================
# GENERATE AI LESSON PLAN
# ============================================================

def generate_ai_lesson_plan(
    document_text,
    level,
    language,
    duration_minutes,
    focus_topic=None
):
    """
    Generate lesson plan using OpenRouter AI.

    focus_topic (optional): when the student asks to be taught
    only a specific topic/chapter/section instead of the whole
    document, pass that text here. The AI still receives the
    full study material for context, but is explicitly told to
    build the lesson only around that part.
    """

    if (

        not document_text

        or not document_text.strip()

    ):

        raise ValueError(
            "Study material is empty."
        )

    document_text = (
        document_text.strip()
    )

    # Strip repeated headers/footers before sampling/sending
    # to the AI too - keeps boilerplate out of its context.
    document_text = strip_repeated_boilerplate_lines(
        document_text
    )

    document_text = remove_administrative_metadata_lines(
        document_text
    )

    # --------------------------------------------------------
    # SAMPLE VERY LARGE DOCUMENTS
    # --------------------------------------------------------

    text_length = len(
        document_text
    )

    if text_length > 30000:

        step = (
            text_length // 6
        )

        sampled_text = "\n\n".join([

            document_text[
                0:5000
            ],

            document_text[
                step:step + 5000
            ],

            document_text[
                step * 2:step * 2 + 5000
            ],

            document_text[
                step * 3:step * 3 + 5000
            ],

            document_text[
                step * 4:step * 4 + 5000
            ],

            document_text[
                -5000:
            ]
        ])

    else:

        sampled_text = document_text

    # --------------------------------------------------------
    # FOCUS TOPIC INSTRUCTION
    # --------------------------------------------------------

    if focus_topic and focus_topic.strip():

        focus_topic_instruction = f"""
The student has specifically asked to be taught ONLY the
following topic/section, not the whole document:

"{focus_topic.strip()}"

Build the entire lesson plan around this part of the material
only, even if it appears in the middle or near the end of the
document. Still follow rule 3a (natural document order) WITHIN
that topic/section. If this exact topic cannot be clearly
matched in the study material, choose the closest matching
part of the material and mention that in the "topic" field.
"""

    else:

        focus_topic_instruction = (
            "The student has NOT asked for a specific topic - "
            "build the lesson around the whole document, "
            "following its natural sequence (see rule 3a)."
        )

    # --------------------------------------------------------
    # AI PROMPT
    # --------------------------------------------------------

    prompt = f"""
You are an expert educational lesson planner.

Create a progressive lesson plan using ONLY concepts
clearly supported by the provided study material.

The study material may belong to ANY academic subject.
Do not assume that it belongs to Machine Learning,
Computer Science, Regression, or any predefined subject.

You must first understand:

- the broad main topic
- important concepts
- subtopics
- relationships between concepts
- methods or processes when present

Student level:
{level}

Preferred language:
{language}

Total lesson duration:
{duration_minutes} minutes

{focus_topic_instruction}

IMPORTANT RULES

1. Use ONLY concepts supported by the study material.

2. Do NOT invent subject-specific concepts.

3. The lesson must progress logically from
   foundations to deeper understanding.

3a. SEQUENCE: Unless the student asked for a specific
    topic/section (see instruction above, if present),
    cover concepts in the SAME order they naturally appear
    in the study material. Do not start from a concept that
    appears in the middle or end of the material while
    skipping concepts that appear before it, unless that
    earlier concept is genuinely unrelated to this subject.

3b. DEPTH SCALES WITH LEVEL AND DURATION: as student level
    and/or duration increase, add MORE concepts and GO
    DEEPER into each one - but every deeper/advanced concept
    you introduce must logically build on a simpler one
    already covered earlier in this same lesson. Never
    introduce an advanced concept (e.g. a formula, metric,
    or technique) before its prerequisite basic concept has
    been explained. A longer, more advanced lesson should
    read like a smooth staircase of difficulty, not a list
    of disconnected advanced terms.

4. Respect the student level.

BEGINNER:
- Focus on basic concepts.
- Use simple explanations.
- Avoid unnecessary complexity.
- Include simple examples.

INTERMEDIATE:
- Cover foundations and important concepts.
- Explain relationships.
- Include methods and practical applications
  when supported.

ADVANCED:
- Start with foundations.
- Move toward deeper concepts.
- Include analysis and comparison when supported.
- Do not invent advanced concepts.

5. Do not repeatedly teach the same concept.

6. The topic must represent the broad main subject
   of the study material.

7. Every section must contain:

- title
- duration_minutes
- description
- key_points

8. The sum of all section durations must equal
   exactly {duration_minutes} minutes.

9. Include:

- Introduction
- Teaching sections
- Practice
- Final Quiz

10. Each teaching section should contain a
    section-specific Think About It question.

11. The Think About It question MUST test ONLY
    concepts covered in that same section.

12. Use question_type:

- "short_answer"
- "conceptual"
- "mcq"

13. For short_answer and conceptual questions:

- expected_concept is required.

14. For mcq questions:

- options are required.
- correct_answer is required.
- correct_answer must exactly match one option.

15. Avoid duplicate questions.

16. Do not ask the same concept repeatedly
    using different wording.

17. The final quiz should contain multiple
    unique MCQ questions.

18. Use the selected language for lesson content.

19. Return ONLY valid JSON.

20. Do NOT use Markdown.

STUDY MATERIAL:

{sampled_text}


Use this exact JSON structure:

{{
    "topic": "...",

    "level": "{level}",

    "language": "{language}",

    "duration_minutes": {duration_minutes},

    "learning_objectives": [
        "..."
    ],

    "sections": [
        {{
            "title": "...",

            "duration_minutes": 5,

            "description": "...",

            "key_points": [
                "..."
            ],

            "think_about_it": {{
                "question": "...",

                "question_type": "short_answer",

                "expected_concept": "...",

                "concept": "..."
            }}
        }}
    ],

    "interactive_questions": [
        {{
            "question": "...",

            "question_type": "short_answer",

            "expected_concept": "...",

            "concept": "...",

            "section_title": "..."
        }}
    ],

    "final_quiz": [
        {{
            "question": "...",

            "question_type": "mcq",

            "concept": "...",

            "options": [
                "...",
                "...",
                "...",
                "..."
            ],

            "correct_answer": "..."
        }}
    ]
}}
"""

    # --------------------------------------------------------
    # GENERATE RESPONSE
    # --------------------------------------------------------

    response = generate_ai_response(

        prompt,

        max_tokens=3500,

        temperature=0.2
    )

    response = clean_ai_json_response(
        response
    )

    try:

        lesson_plan = json.loads(
            response
        )

    except json.JSONDecodeError as error:

        raise ValueError(
            f"AI returned invalid JSON: {error}"
        )

    validated_plan = validate_ai_lesson_plan(

        lesson_plan,

        level,

        language,

        duration_minutes
    )

    # The AI was explicitly instructed (see focus_topic_instruction
    # above) to build around the requested topic when one was given,
    # so we record that it was honored, for consistency with the
    # same fields the local planner returns.
    validated_plan["focus_topic_requested"] = focus_topic
    validated_plan["focus_topic_found"] = True

    return validated_plan


# ============================================================
# EVALUATE INTERACTIVE ANSWER
# ============================================================

def evaluate_interactive_answer(
    user_answer,
    expected_concept
):
    """
    Basic local evaluation for a short or conceptual answer.

    Returns a score from 0 to 100.
    """

    if not user_answer:

        return {

            "score": 0,

            "feedback":
                "No answer was provided."
        }

    user_text = normalize_text(
        user_answer
    )

    expected_text = normalize_text(
        expected_concept
    )

    user_words = set(
        user_text.split()
    )

    expected_words = set(
        expected_text.split()
    )

    important_expected_words = {

        word

        for word in expected_words

        if (

            len(word) > 3

            and word not in STOP_WORDS
        )
    }

    if not important_expected_words:

        return {

            "score": 50,

            "feedback":
                (
                    "Your answer was recorded. "
                    "Try explaining the concept "
                    "with more detail."
                )
        }

    matched_words = (

        user_words

        & important_expected_words
    )

    match_ratio = (

        len(matched_words)

        / len(
            important_expected_words
        )
    )

    score = int(

        min(

            100,

            match_ratio * 100
        )
    )

    if score >= 70:

        feedback = (

            "Good answer! Your explanation covers "
            "important parts of the concept."
        )

    elif score >= 40:

        feedback = (

            "Partially correct. Try including more "
            "important ideas from the concept."
        )

    else:

        feedback = (

            "Your answer needs more detail. "
            "Review the concept and try again."
        )

    return {

        "score":
            score,

        "feedback":
            feedback
    }


# ============================================================
# CALCULATE THINK ABOUT IT SCORE
# ============================================================

def calculate_interactive_score(
    results
):
    """
    Calculate average Think About It score.
    """

    if not results:

        return {

            "total_questions": 0,

            "average_score": 0,

            "message":
                "No interactive questions were answered."
        }

    scores = []

    for result in results:

        try:

            score = float(

                result.get(

                    "score",

                    0
                )
            )

            score = max(

                0,

                min(

                    100,

                    score
                )
            )

            scores.append(
                score
            )

        except (

            TypeError,

            ValueError
        ):

            scores.append(
                0
            )

    average_score = round(

        sum(scores)

        / len(scores),

        2
    )

    return {

        "total_questions":
            len(scores),

        "average_score":
            average_score,

        "message":
            (
                f"Your Think About It score "
                f"is {average_score}%."
            )
    }


# ============================================================
# MAIN FUNCTION
# ============================================================

# ============================================================
# TRANSLATE LOCAL LESSON PLAN
# ============================================================

def translate_lesson_plan(lesson_plan, language):
    """
    Translate a locally-generated lesson plan's text content
    into the requested language using a single AI call.

    Only does anything when:
      - the local (non-AI) planner was used, AND
      - the selected language is Hindi or Hinglish

    generate_local_lesson_plan() only translates the fixed
    structural labels (section titles like "Introduction" /
    "Quiz") via get_language_content(). The key points,
    descriptions, learning objectives, and quiz questions it
    builds are always plain English f-strings. This function
    translates exactly those remaining fields in one pass.

    Structure, section order, and quiz options stay identical -
    only the text itself changes. If the AI call fails for any
    reason, the original English plan is returned unchanged.
    This is a safe fallback: it never crashes and never leaves
    a half-translated plan, it just stays in English.
    """

    if not lesson_plan:
        return lesson_plan

    target = str(language).strip().lower()

    if target not in ("hindi", "hinglish"):
        return lesson_plan

    texts = []
    setters = []

    def register(value, setter):
        texts.append(value or "")
        setters.append(setter)

    # ----------------------------------------------------
    # Learning objectives
    # ----------------------------------------------------

    objectives = lesson_plan.get(
        "learning_objectives",
        []
    )

    for i in range(len(objectives)):
        register(
            objectives[i],
            (lambda i: lambda v: objectives.__setitem__(i, v))(i)
        )

    # ----------------------------------------------------
    # Section descriptions + key points
    # ----------------------------------------------------

    sections = lesson_plan.get(
        "sections",
        []
    )

    for section in sections:

        register(
            section.get("description", ""),
            (lambda s: lambda v: s.__setitem__("description", v))(section)
        )

        key_points = section.get(
            "key_points",
            []
        )

        for i in range(len(key_points)):
            register(
                key_points[i],
                (lambda kp, i: lambda v: kp.__setitem__(i, v))(key_points, i)
            )

    # ----------------------------------------------------
    # Final quiz - questions + options
    #
    # correct_answer must exactly match one of the translated
    # options afterwards, so instead of translating it as its
    # own string, we remember WHICH option index is correct and
    # copy the already-translated option text back into it once
    # translation is done.
    # ----------------------------------------------------

    quiz = lesson_plan.get(
        "final_quiz",
        []
    )

    correct_answer_links = []

    for question in quiz:

        register(
            question.get("question", ""),
            (lambda q: lambda v: q.__setitem__("question", v))(question)
        )

        options = question.get(
            "options",
            []
        )

        correct_answer = question.get(
            "correct_answer",
            ""
        )

        correct_index = (
            options.index(correct_answer)
            if correct_answer in options
            else None
        )

        for i in range(len(options)):
            register(
                options[i],
                (lambda opt, i: lambda v: opt.__setitem__(i, v))(options, i)
            )

        if correct_index is not None:
            correct_answer_links.append(
                (question, options, correct_index)
            )

    if not texts:
        return lesson_plan

    # ----------------------------------------------------
    # Single translation call
    # ----------------------------------------------------

    try:

        language_name = (
            "Hindi"
            if target == "hindi"
            else "Hinglish (Hindi-English mix, written in Roman/English script)"
        )

        prompt = f"""
Translate each string in this JSON array into {language_name}.

Keep technical terms and proper nouns recognizable - you may
keep them in English if that is standard usage, for example
"Regression", "Machine Learning", "API".

Keep the SAME number of items, in the SAME order. Do not add,
remove, merge, or explain anything.

Return ONLY valid JSON in this exact shape, nothing else:
{{"translations": ["...", "...", ...]}}

Input array:
{json.dumps(texts, ensure_ascii=False)}
"""

        response = generate_ai_response(
            prompt,
            max_tokens=3000,
            temperature=0.2
        )

        cleaned = clean_ai_json_response(response)

        parsed = json.loads(cleaned)

        translations = parsed.get(
            "translations",
            []
        )

        if len(translations) != len(texts):

            print(
                "Lesson plan translation count mismatch, "
                "keeping English content."
            )

            return lesson_plan

        for setter, translated_text in zip(setters, translations):
            setter(translated_text)

        for question, options, correct_index in correct_answer_links:
            question["correct_answer"] = options[correct_index]

        lesson_plan["_translated"] = True

        return lesson_plan

    except Exception as error:

        print(
            "Lesson plan translation failed, "
            "keeping English content:",
            error
        )

        return lesson_plan


# ============================================================
# MAIN LESSON PLANNER
# ============================================================

def generate_lesson_plan(

    document_text,

    level="Beginner",

    language="English",

    duration_minutes=20,

    duration=None,

    focus_topic=None
):
    """
    Main lesson planner.

    focus_topic (optional): if the student wants a lesson on
    just one topic/chapter/section of the material instead of
    the whole document, pass that here (e.g. "Gradient Descent",
    "Chapter 3"). Leave it as None (the default) for a lesson
    covering the whole document, which is the original behavior.

    Supports both:

        duration_minutes=20

    and:

        duration=20
    """

    # --------------------------------------------------------
    # DURATION COMPATIBILITY
    # --------------------------------------------------------

    if duration is not None:

        duration_minutes = duration

    # --------------------------------------------------------
    # NORMALIZE DURATION
    # --------------------------------------------------------

    try:

        duration_minutes = int(
            duration_minutes
        )

    except (

        TypeError,

        ValueError
    ):

        duration_minutes = 20

    if duration_minutes < 5:

        duration_minutes = 5

    if duration_minutes > 120:

        duration_minutes = 120

    # --------------------------------------------------------
    # NORMALIZE LEVEL
    # --------------------------------------------------------

    valid_levels = [

        "Beginner",

        "Intermediate",

        "Advanced"
    ]

    if level not in valid_levels:

        level = "Beginner"

    # --------------------------------------------------------
    # NORMALIZE LANGUAGE
    # --------------------------------------------------------

    valid_languages = [

        "English",

        "Hindi",

        "Hinglish"
    ]

    if language not in valid_languages:

        language = "English"

    # --------------------------------------------------------
    # VALIDATE STUDY MATERIAL
    # --------------------------------------------------------

    if (

        not document_text

        or not document_text.strip()

    ):

        return {

            "error":
                "Study material is empty."
        }

    # --------------------------------------------------------
    # TRY AI GENERATION
    # --------------------------------------------------------

    try:

        print(
            "Generating lesson plan using OpenRouter..."
        )

        lesson_plan = generate_ai_lesson_plan(

            document_text,

            level,

            language,

            duration_minutes,

            focus_topic=focus_topic
        )

        print(
            "Lesson plan generated using AI."
        )

        return lesson_plan

    except Exception as error:

        print(

            "OpenRouter lesson planner unavailable "
            "(attempt 1):",

            error
        )

        # ------------------------------------------------
        # RETRY ONCE
        #
        # Most of these failures (invalid JSON, durations
        # not adding up, malformed MCQ options) are a
        # one-off slip by the model, not a real outage - a
        # second attempt succeeds far more often than not,
        # and it means we reach the local fallback (which
        # is lower quality) much less often.
        # ------------------------------------------------

        try:

            print(
                "Retrying AI lesson plan generation..."
            )

            lesson_plan = generate_ai_lesson_plan(

                document_text,

                level,

                language,

                duration_minutes,

                focus_topic=focus_topic
            )

            print(
                "Lesson plan generated using AI (on retry)."
            )

            return lesson_plan

        except Exception as retry_error:

            print(

                "OpenRouter lesson planner unavailable "
                "after retry:",

                retry_error
            )

            print(

                "Using intelligent generic local lesson planner."
            )

            # ----------------------------------------------------
            # GENERIC LOCAL FALLBACK
            # ----------------------------------------------------

            local_plan = generate_local_lesson_plan(

                document_text,

                level,

                language,

                duration_minutes,

                focus_topic=focus_topic
            )

            # ----------------------------------------------------
            # The local planner only translates structural labels
            # (section titles). Translate the actual content too
            # when Hindi/Hinglish was requested, so the fallback
            # is no longer stuck in English.
            # ----------------------------------------------------

            local_plan = translate_lesson_plan(
                local_plan,
                language
            )

            return local_plan



# ============================================================
# GENERATE 7-DAY LESSON PLAN
# ============================================================
#
# Matches the requirement doc's "Available Time" option:
#
#   5 minutes / 20 minutes / 60 minutes / 7 days
#
#   Day 1 -> Fundamentals
#   Day 2 -> Concepts
#   Day 3 -> Practice
#   Day 4 -> Advanced concepts
#   Day 5 -> Application
#   Day 6 -> Deeper / connecting concepts
#   Day 7 -> Revision + assessment
#
# NOTE: this function only builds the PLAN data. Walking a
# student through it day-by-day in the UI (day selector, saving
# progress per day) needs its own changes to app.py and
# teaching_engine.py - that is the next step, not part of this
# function. This gives you a tested, ready-to-call generator to
# build that UI on top of.
# ============================================================

def _weekly_day_titles(language):
    """
    Structural day titles/labels, same idea as
    get_language_content() but for the 7-day plan.
    """

    language = str(language).lower().strip()

    if language == "hindi":

        return [
            "मूल बातें",
            "मुख्य अवधारणाएँ",
            "अभ्यास",
            "उन्नत अवधारणाएँ",
            "अनुप्रयोग",
            "गहन समझ",
            "पुनरावृत्ति और मूल्यांकन"
        ]

    if language == "hinglish":

        return [
            "Fundamentals",
            "Concepts",
            "Practice",
            "Advanced Concepts",
            "Application",
            "Deeper Understanding",
            "Revision aur Assessment"
        ]

    return [
        "Fundamentals",
        "Concepts",
        "Practice",
        "Advanced Concepts",
        "Application",
        "Deeper Understanding",
        "Revision and Assessment"
    ]


def _generate_ai_weekly_plan(
    document_text,
    level,
    language,
    focus_topic
):
    """
    Ask the AI for a 7-day plan directly. Kept as a SIMPLER
    schema than the single-lesson planner (one focus + a few
    key points + one practice question per day, instead of a
    full nested "sections" structure repeated 7 times) - a
    smaller schema is far less likely to come back malformed,
    which matters even more here since a failure means
    regenerating a much bigger response.
    """

    if not document_text or not document_text.strip():
        raise ValueError("Study material is empty.")

    document_text = strip_repeated_boilerplate_lines(
        document_text
    )

    document_text = remove_administrative_metadata_lines(
        document_text
    )

    text_length = len(document_text)

    if text_length > 20000:
        sampled_text = (
            document_text[:8000]
            + "\n\n"
            + document_text[-8000:]
        )
    else:
        sampled_text = document_text

    if focus_topic and focus_topic.strip():

        focus_instruction = (
            "The student has specifically asked to be taught "
            f"ONLY the following topic/section: \"{focus_topic.strip()}\". "
            "Build all 7 days around this part of the material only."
        )

    else:

        focus_instruction = (
            "The student has NOT asked for a specific topic - "
            "cover the whole document across the 7 days, following "
            "the SAME order the concepts appear in the material."
        )

    prompt = f"""
You are an expert educational lesson planner building a 7-DAY
learning plan (not a single lesson).

Student level:
{level}

Preferred language:
{language}

{focus_instruction}

RULES

1. Use ONLY concepts supported by the study material.
2. Do NOT invent subject-specific concepts.
3. Follow this exact day structure and increase depth as the
   days progress - later days must build on concepts already
   taught in earlier days, never introduce an advanced concept
   before its prerequisite:

   Day 1 -> Fundamentals (basic definitions, why the topic matters)
   Day 2 -> Concepts (the core ideas)
   Day 3 -> Practice (applying Day 1-2 concepts)
   Day 4 -> Advanced Concepts (deeper material, only if supported)
   Day 5 -> Application (real examples/use cases)
   Day 6 -> Deeper Understanding (connections between concepts)
   Day 7 -> Revision and Assessment (recap + a short quiz)

4. Unless a specific topic was requested above, cover the
   material in the SAME order it appears in the document.
5. Each day needs: day_number, day_title, focus (1-2 sentences),
   key_points (3-5 short bullet strings), and ONE practice
   question (question_type "short_answer" or "conceptual" needs
   expected_concept; "mcq" needs options + correct_answer that
   exactly matches one option).
6. Day 7's question(s) should be a short multi-question quiz
   (an array of 3-5 mcq questions) instead of a single question,
   to actually assess the whole week.
7. Use the selected language for all text content.
8. Return ONLY valid JSON, no Markdown.

STUDY MATERIAL:

{sampled_text}

Use this exact JSON structure:

{{
    "topic": "...",
    "level": "{level}",
    "language": "{language}",
    "duration_days": 7,
    "days": [
        {{
            "day_number": 1,
            "day_title": "...",
            "focus": "...",
            "key_points": ["...", "..."],
            "question": {{
                "question": "...",
                "question_type": "short_answer",
                "expected_concept": "...",
                "concept": "..."
            }}
        }}
    ],
    "final_quiz": [
        {{
            "question": "...",
            "question_type": "mcq",
            "concept": "...",
            "options": ["...", "...", "...", "..."],
            "correct_answer": "..."
        }}
    ]
}}
"""

    response = generate_ai_response(
        prompt,
        max_tokens=4000,
        temperature=0.2
    )

    response = clean_ai_json_response(response)

    try:
        plan = json.loads(response)
    except json.JSONDecodeError as error:
        raise ValueError(f"AI returned invalid JSON: {error}")

    if not isinstance(plan, dict):
        raise ValueError("AI weekly plan is not a JSON object.")

    days = plan.get("days", [])

    if not isinstance(days, list) or len(days) == 0:
        raise ValueError("AI weekly plan has no days.")

    if len(days) != 7:
        raise ValueError(
            f"AI weekly plan returned {len(days)} days, expected 7."
        )

    for day in days:

        if not isinstance(day, dict):
            raise ValueError("A day entry is not a JSON object.")

        for field in ("day_number", "day_title", "key_points"):
            if field not in day:
                raise ValueError(f"Day is missing '{field}'.")

    plan.setdefault("topic", "Study Material")
    plan.setdefault("level", level)
    plan.setdefault("language", language)
    plan.setdefault("duration_days", 7)
    plan.setdefault("final_quiz", [])

    return plan


def _generate_local_weekly_plan(
    document_text,
    level,
    language
):
    """
    Deterministic 7-day fallback - no AI required. Builds day
    buckets from the same concept-extraction the single-lesson
    local planner uses, so it inherits the same document-order
    fix (concepts are already ordered by first appearance in
    the document, not by frequency).
    """

    document_text = strip_repeated_boilerplate_lines(
        document_text
    )

    document_text = remove_administrative_metadata_lines(
        document_text
    )

    topic = detect_main_topic(document_text)

    concepts = extract_generic_concepts(
        document_text,
        max_concepts=12
    )

    if not concepts:
        concepts = [topic]

    day_titles = _weekly_day_titles(language)

    # Spread the (document-ordered) concepts across the first
    # 6 days, day 7 is always revision - no new concepts.
    concepts_per_day = max(1, -(-len(concepts) // 6))  # ceil division

    days = []

    for day_number in range(1, 8):

        if day_number == 7:

            day_concepts = concepts[-3:] if concepts else []

            days.append({
                "day_number": 7,
                "day_title": day_titles[6],
                "focus": (
                    "Review the concepts covered this week and "
                    "check your understanding."
                ),
                "key_points": [
                    f"Review: {c}" for c in day_concepts
                ] or ["Review the concepts covered this week."]
            })

            continue

        start = (day_number - 1) * concepts_per_day
        end = start + concepts_per_day
        day_concepts = concepts[start:end]

        if not day_concepts:
            day_concepts = [topic]

        days.append({
            "day_number": day_number,
            "day_title": day_titles[day_number - 1],
            "focus": (
                f"Understand {', '.join(day_concepts)}."
            ),
            "key_points": [
                f"What is {c}?" for c in day_concepts
            ]
        })

    quiz_pool = build_generic_quiz_pool(topic, concepts)

    final_quiz = select_unique_quiz_questions(quiz_pool, 5)

    return {
        "topic": topic,
        "level": level,
        "language": language,
        "duration_days": 7,
        "days": days,
        "final_quiz": final_quiz
    }


def add_weekly_question_queues(plan):
    """Give each teaching day a small, concept-linked question queue."""

    for day in plan.get("days", []):
        if day.get("day_number") == 7:
            continue
        existing = day.get("questions") or []
        if not existing and day.get("question"):
            existing = [day["question"]]
        pseudo_section = {
            "title": day.get("day_title", "Today's concept"),
            "key_points": day.get("key_points", []),
            "description": day.get("focus", "")
        }
        # Two checks are a practical baseline for a multi-concept day; use
        # distinct templates and preserve any planner-generated first check.
        while len(existing) < 2:
            existing.append(build_section_question(pseudo_section, len(existing) + 1))
        normalized = []
        for index, question in enumerate(existing[:3]):
            item = question.copy()
            item["question_id"] = f"day-{day.get('day_number')}-question-{index + 1}"
            item["concept_id"] = item.get("concept", item.get("expected_concept", day.get("day_title", "")))
            item["difficulty"] = "application" if index else "foundation"
            item["purpose"] = "check_understanding"
            normalized.append(item)
        day["questions"] = normalized
        # Retain legacy field for compatibility with saved/generated plans.
        day["question"] = normalized[0]
    return plan


def generate_weekly_lesson_plan(
    document_text,
    level="Beginner",
    language="English",
    focus_topic=None
):
    """
    Main entry point for a 7-day lesson plan. Same
    try-AI-twice-then-fall-back-locally pattern as
    generate_lesson_plan().
    """

    if not document_text or not document_text.strip():
        return {"error": "Study material is empty."}

    if level not in ("Beginner", "Intermediate", "Advanced"):
        level = "Beginner"

    if language not in ("English", "Hindi", "Hinglish"):
        language = "English"

    scoped_text, matched_focus_label, focus_found = (
        scope_document_to_topic(document_text, focus_topic)
    )

    try:

        print("Generating 7-day lesson plan using OpenRouter...")

        plan = _generate_ai_weekly_plan(
            scoped_text, level, language, focus_topic
        )

        print("7-day lesson plan generated using AI.")

        plan["focus_topic_requested"] = focus_topic
        plan["focus_topic_found"] = True

        return add_weekly_question_queues(plan)

    except Exception as error:

        print("OpenRouter weekly planner unavailable (attempt 1):", error)

        try:

            print("Retrying 7-day lesson plan generation...")

            plan = _generate_ai_weekly_plan(
                scoped_text, level, language, focus_topic
            )

            print("7-day lesson plan generated using AI (on retry).")

            plan["focus_topic_requested"] = focus_topic
            plan["focus_topic_found"] = True

            return add_weekly_question_queues(plan)

        except Exception as retry_error:

            print(
                "OpenRouter weekly planner unavailable after retry:",
                retry_error
            )

            print("Using local 7-day lesson planner.")

            # NOTE: unlike the single-lesson local planner, this
            # local weekly fallback does not yet call
            # translate_lesson_plan() for Hindi/Hinglish - the
            # AI path (tried twice above) already handles
            # language correctly, and reaching this local path
            # for a 7-day plan should be rare. Flagging this as
            # a known gap rather than silently leaving it broken.

            plan = _generate_local_weekly_plan(
                scoped_text, level, language
            )

            plan["focus_topic_requested"] = focus_topic
            plan["focus_topic_found"] = focus_found

            return add_weekly_question_queues(plan)
