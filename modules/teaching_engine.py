# ============================================================
# EDU SENSE AI - ADAPTIVE TEACHING ENGINE
# ============================================================


def initialize_lesson(lesson_plan):
    """
    Initialize the teaching state for a lesson.

    This state stores both normal lesson progress and
    adaptive learning information.
    """

    if not lesson_plan:
        return None

    sections = lesson_plan.get(
        "sections",
        []
    )

    return {
        # ----------------------------------------------------
        # Basic lesson progress
        # ----------------------------------------------------
        "current_section": 0,

        "total_sections": len(sections),

        "completed_sections": [],

        # Position of the active question within each section's question
        # queue. Kept in lesson state so Streamlit reruns cannot leak a
        # question from one section into another.
        "section_question_progress": {},

        "answers": [],

        "score": 0,

        # ----------------------------------------------------
        # Adaptive learning information
        # ----------------------------------------------------
        "concept_performance": {},

        "strong_concepts": [],

        "weak_concepts": [],

        "misconceptions": [],

        "attempts": {},

        "adaptation_history": [],

        # Current teaching difficulty
        "current_difficulty": "normal"
    }


# ============================================================
# CURRENT SECTION
# ============================================================

def get_current_section(
    lesson_plan,
    current_section
):
    """
    Return the current lesson section.
    """

    sections = lesson_plan.get(
        "sections",
        []
    )

    if not sections:
        return None

    if current_section < 0:
        current_section = 0

    if current_section >= len(sections):
        current_section = len(sections) - 1

    return sections[current_section]


# ============================================================
# PROGRESS
# ============================================================

def get_progress(
    current_section,
    total_sections,
    completed_sections=None
):
    """
    Calculate lesson progress percentage.

    If completed_sections are provided, progress is based
    on completed sections.

    Otherwise, progress is based on the current section.
    """

    if total_sections <= 0:
        return 0

    # --------------------------------------------------------
    # More accurate progress when completed sections exist
    # --------------------------------------------------------

    if completed_sections is not None:

        completed_count = len(
            set(completed_sections)
        )

        progress = (
            completed_count / total_sections
        ) * 100

        return min(
            100,
            int(progress)
        )

    # --------------------------------------------------------
    # Backward-compatible progress calculation
    # --------------------------------------------------------

    progress = (
        current_section / total_sections
    ) * 100

    return min(
        100,
        int(progress)
    )


# ============================================================
# NAVIGATION
# ============================================================

def move_to_next_section(
    current_section,
    total_sections
):
    """
    Move to the next lesson section.
    """

    if current_section < total_sections - 1:

        return current_section + 1

    return current_section


def move_to_previous_section(
    current_section
):
    """
    Move to the previous lesson section.
    """

    if current_section > 0:

        return current_section - 1

    return 0


# ============================================================
# ANSWER SAVING
# ============================================================

def save_answer(
    state,
    question,
    student_answer,
    evaluation,
    concept=None,
    section_index=None
):
    """
    Save a student's answer and its evaluation.

    Also stores information required for adaptive teaching.
    """

    if state is None:
        return

    score = evaluation.get(
        "score",
        0
    )

    correct = evaluation.get(
        "correct",
        False
    )

    answer_data = {

        "question": question,

        "student_answer": student_answer,

        "score": score,

        "correct": correct,

        "concept": concept,

        "section_index": section_index,

        "feedback": evaluation.get(
            "feedback",
            ""
        )
    }

    state["answers"].append(
        answer_data
    )

    state["score"] += score


# ============================================================
# SECTION COMPLETION
# ============================================================

def mark_section_completed(
    state,
    section_index
):
    """
    Mark a lesson section as completed.
    """

    if state is None:
        return

    if section_index not in state[
        "completed_sections"
    ]:

        state[
            "completed_sections"
        ].append(section_index)


# ============================================================
# CONCEPT PERFORMANCE
# ============================================================

def update_concept_performance(
    state,
    concept,
    score
):
    """
    Update the student's performance for a concept.

    Example:

    Regression -> [1, 0.5, 1]

    The stored value becomes the average score.
    """

    if state is None:
        return

    if not concept:
        return

    concept = str(concept).strip()

    if not concept:
        return

    if "concept_scores" not in state:

        state["concept_scores"] = {}

    if concept not in state[
        "concept_scores"
    ]:

        state[
            "concept_scores"
        ][concept] = []

    state[
        "concept_scores"
    ][concept].append(
        score
    )

    scores = state[
        "concept_scores"
    ][concept]

    average_score = (
        sum(scores) / len(scores)
    )

    state[
        "concept_performance"
    ][concept] = round(
        average_score,
        2
    )

    # --------------------------------------------------------
    # Strong concept
    # --------------------------------------------------------

    if average_score >= 0.75:

        if concept not in state[
            "strong_concepts"
        ]:

            state[
                "strong_concepts"
            ].append(concept)

        if concept in state[
            "weak_concepts"
        ]:

            state[
                "weak_concepts"
            ].remove(concept)

    # --------------------------------------------------------
    # Weak concept
    # --------------------------------------------------------

    elif average_score < 0.5:

        if concept not in state[
            "weak_concepts"
        ]:

            state[
                "weak_concepts"
            ].append(concept)

        if concept in state[
            "strong_concepts"
        ]:

            state[
                "strong_concepts"
            ].remove(concept)


# ============================================================
# ATTEMPT TRACKING
# ============================================================

def record_attempt(
    state,
    section_index
):
    """
    Record how many times a student has attempted
    a section/question.
    """

    if state is None:
        return

    attempts = state.get(
        "attempts",
        {}
    )

    current_attempts = attempts.get(
        section_index,
        0
    )

    attempts[
        section_index
    ] = current_attempts + 1

    state[
        "attempts"
    ] = attempts


# ============================================================
# MISCONCEPTION TRACKING
# ============================================================

def record_misconception(
    state,
    concept,
    misconception
):
    """
    Save a detected misconception.

    Duplicate misconceptions are avoided.
    """

    if state is None:
        return

    if not misconception:
        return

    misconception_data = {

        "concept": concept,

        "misconception": misconception
    }

    existing = state.get(
        "misconceptions",
        []
    )

    if misconception_data not in existing:

        existing.append(
            misconception_data
        )

    state[
        "misconceptions"
    ] = existing


# ============================================================
# ADAPTIVE TEACHING LEVEL
# ============================================================

def update_difficulty(
    state,
    evaluation
):
    """
    Decide whether teaching should be simplified,
    kept normal, or made more challenging.

    Expected evaluation score:

    1   -> correct
    0.5 -> partially correct
    0   -> incorrect
    """

    if state is None:
        return "normal"

    score = evaluation.get(
        "score",
        0
    )

    # --------------------------------------------------------
    # Student understands well
    # --------------------------------------------------------

    if score >= 1:

        state[
            "current_difficulty"
        ] = "advanced"

    # --------------------------------------------------------
    # Student partially understands
    # --------------------------------------------------------

    elif score >= 0.5:

        state[
            "current_difficulty"
        ] = "normal"

    # --------------------------------------------------------
    # Student is struggling
    # --------------------------------------------------------

    else:

        state[
            "current_difficulty"
        ] = "simplified"

    return state[
        "current_difficulty"
    ]


# ============================================================
# ADAPTATION HISTORY
# ============================================================

def add_adaptation_event(
    state,
    section_index,
    action,
    reason
):
    """
    Record an adaptive teaching decision.

    Example:

    action = "re_explain"
    reason = "Student confused regression and classification"
    """

    if state is None:
        return

    event = {

        "section_index": section_index,

        "action": action,

        "reason": reason
    }

    state[
        "adaptation_history"
    ].append(event)


# ============================================================
# GET ADAPTIVE STATUS
# ============================================================

def get_adaptive_status(
    state,
    concept=None
):
    """
    Return the current adaptive learning status.

    This will later be used by app.py to decide
    whether to continue or re-teach.
    """

    if state is None:

        return {
            "needs_reteaching": False,
            "difficulty": "normal",
            "attempts": 0
        }

    difficulty = state.get(
        "current_difficulty",
        "normal"
    )

    attempts = 0

    current_section = state.get(
        "current_section",
        0
    )

    attempts = state.get(
        "attempts",
        {}
    ).get(
        current_section,
        0
    )

    needs_reteaching = False

    if concept:

        performance = state.get(
            "concept_performance",
            {}
        ).get(
            concept,
            None
        )

        if performance is not None:

            needs_reteaching = (
                performance < 0.5
            )

    return {

        "needs_reteaching": needs_reteaching,

        "difficulty": difficulty,

        "attempts": attempts
    }


# ============================================================
# LESSON COMPLETION
# ============================================================

def is_lesson_complete(state):
    """
    Check whether all sections are completed.
    """

    if state is None:
        return False

    total_sections = state.get(
        "total_sections",
        0
    )

    completed_sections = state.get(
        "completed_sections",
        []
    )

    return (
        len(
            set(completed_sections)
        )
        >= total_sections
    )


# ============================================================
# LEARNING SUMMARY
# ============================================================

def get_learning_summary(state):
    """
    Return a structured summary of student performance.

    This will later be used for the final
    Learning Report.
    """

    if state is None:

        return {
            "total_score": 0,
            "strong_concepts": [],
            "weak_concepts": [],
            "misconceptions": [],
            "concept_performance": {}
        }

    answers = state.get(
        "answers",
        []
    )

    total_questions = len(
        answers
    )

    total_score = state.get(
        "score",
        0
    )

    if total_questions > 0:

        percentage = (
            total_score /
            total_questions
        ) * 100

    else:

        percentage = 0

    return {

        "total_questions": total_questions,

        "total_score": round(
            total_score,
            2
        ),

        "percentage": round(
            percentage,
            2
        ),

        "strong_concepts": state.get(
            "strong_concepts",
            []
        ),

        "weak_concepts": state.get(
            "weak_concepts",
            []
        ),

        "misconceptions": state.get(
            "misconceptions",
            []
        ),

        "concept_performance": state.get(
            "concept_performance",
            {}
        ),

        "adaptation_history": state.get(
            "adaptation_history",
            []
        )
    }

# ============================================================
# WEEKLY (7-DAY) PLAN NAVIGATION
#
# A 7-day plan is structured as a flat list of "days" (each with
# a focus, key_points and ONE practice question) rather than the
# nested "sections" a single lesson uses - so it gets its own
# small set of navigation helpers instead of reusing
# initialize_lesson()/get_current_section()/move_to_next_section().
#
# Everything ELSE (update_concept_performance, record_attempt,
# update_difficulty, get_learning_summary, record_misconception)
# is intentionally reused as-is below - those functions only read
# generic keys like "concept_performance", "attempts", and
# "weak_concepts", so the same state shape works for both a
# single lesson and a weekly plan without any changes to those
# functions.
# ============================================================

def initialize_weekly_lesson(weekly_plan):
    """
    Initialize teaching state for a 7-day plan.

    Same adaptive-learning keys as initialize_lesson() (so
    update_concept_performance / update_difficulty /
    get_learning_summary work unmodified), plus day-based
    progress tracking and its own final-quiz state so it never
    collides with a single lesson's quiz state.
    """

    if not weekly_plan:
        return None

    days = weekly_plan.get(
        "days",
        []
    )

    return {
        # ----------------------------------------------------
        # Day-based progress (instead of section-based)
        # ----------------------------------------------------
        "current_day": 0,

        "total_days": len(days),

        "completed_days": [],

        "answers": [],

        "score": 0,

        # ----------------------------------------------------
        # Adaptive learning information - same shape as
        # initialize_lesson(), reused by the same functions.
        # ----------------------------------------------------
        "concept_performance": {},

        "strong_concepts": [],

        "weak_concepts": [],

        "misconceptions": [],

        "attempts": {},

        "adaptation_history": [],

        "current_difficulty": "normal",

        # ----------------------------------------------------
        # Day 7 final assessment (separate from any single
        # lesson's final_quiz_* session state)
        # ----------------------------------------------------
        "final_quiz_answers": {},

        "final_quiz_submitted": False,

        "final_quiz_score": 0,

        "final_quiz_breakdown": {}
    }


# ============================================================
# CURRENT DAY
# ============================================================

def get_current_day(
    weekly_plan,
    current_day_index
):
    """
    Return the current day's dict from a 7-day plan.
    """

    days = weekly_plan.get(
        "days",
        []
    )

    if not days:
        return None

    if current_day_index < 0:
        current_day_index = 0

    if current_day_index >= len(days):
        current_day_index = len(days) - 1

    return days[current_day_index]


# ============================================================
# WEEKLY PROGRESS
# ============================================================

def get_weekly_progress(
    current_day,
    total_days,
    completed_days=None
):
    """
    Same shape/behavior as get_progress(), for the 7-day view.
    """

    if total_days <= 0:
        return 0

    if completed_days is not None:

        completed_count = len(
            set(completed_days)
        )

        progress = (
            completed_count / total_days
        ) * 100

        return min(
            100,
            int(progress)
        )

    progress = (
        current_day / total_days
    ) * 100

    return min(
        100,
        int(progress)
    )


# ============================================================
# DAY NAVIGATION
# ============================================================

def move_to_next_day(
    current_day,
    total_days
):
    """
    Move to the next day. Unlike lesson sections, a day is only
    meant to be reached after the previous one is completed - the
    UI (app.py) is responsible for deciding whether to allow this
    call; this function just does the bounds-safe increment.
    """

    if current_day < total_days - 1:

        return current_day + 1

    return current_day


def move_to_previous_day(
    current_day
):
    """
    Move to the previous day (always allowed - reviewing an
    already-completed day doesn't need to be gated).
    """

    if current_day > 0:

        return current_day - 1

    return 0


# ============================================================
# DAY ANSWER SAVING
# ============================================================

def save_day_answer(
    state,
    day_number,
    question,
    student_answer,
    evaluation,
    concept=None
):
    """
    Save a student's answer to a day's practice question.

    Same shape as save_answer(), keyed by day_number instead of
    section_index, so get_learning_summary() works unmodified.
    """

    if state is None:
        return

    score = evaluation.get(
        "score",
        0
    )

    correct = evaluation.get(
        "correct",
        False
    )

    answer_data = {

        "day_number": day_number,

        "question": question,

        "student_answer": student_answer,

        "score": score,

        "correct": correct,

        "concept": concept,

        "feedback": evaluation.get(
            "feedback",
            ""
        )
    }

    state["answers"].append(
        answer_data
    )

    state["score"] += score


# ============================================================
# DAY COMPLETION
# ============================================================

def mark_day_completed(
    state,
    day_number
):
    """
    Mark a day as completed.
    """

    if state is None:
        return

    if day_number not in state[
        "completed_days"
    ]:

        state[
            "completed_days"
        ].append(day_number)


def is_weekly_complete(state):
    """
    True once every day (1 through total_days) has been marked
    completed - used to decide whether to unlock the final report.
    """

    if not state:
        return False

    return len(
        set(state["completed_days"])
    ) >= state["total_days"]
