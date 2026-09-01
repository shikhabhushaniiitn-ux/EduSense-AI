
import os
import json
import re

from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY is not set in .env file."
    )


# ============================================================
# OPENROUTER CLIENT
# ============================================================

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)


# ============================================================
# MODEL
# ============================================================

MODEL_NAME = "google/gemma-4-26b-a4b-it:free"


# ============================================================
# LANGUAGE INSTRUCTIONS
# ============================================================

def get_language_instruction(language):

    language = language.strip().lower()

    if language == "english":

        return """
Write ALL educational content in English.

Do not use Hindi words or Hindi sentences.

Technical terms such as Supervised Learning,
Classification and Regression may remain in English.
"""

    elif language == "hindi":

        return """
Write ALL educational explanations in Hindi.

Use Devanagari script for Hindi sentences.

Technical terms such as Supervised Learning,
Classification and Regression may remain in English
when appropriate.

Do not write the main explanations in English.
"""

    elif language == "hinglish":

        return """
Write the lesson in natural Hinglish.

Use a mixture of simple Hindi and English.

Hindi should generally be written in Roman script,
not Devanagari.

Example style:

"Supervised Learning ek machine learning technique hai
jisme model ko labeled data diya jata hai."

Keep technical terms such as Supervised Learning,
Classification, Regression, input, output and label
in English.

Do NOT use pure Hindi or pure English.
"""

    else:

        return """
Write the educational content in English.
"""


# ============================================================
# BUILD PROMPT
# ============================================================

def build_prompt(
    study_material,
    level,
    language,
    duration
):

    language_instruction = get_language_instruction(
        language
    )

    return f"""
You are EduSense AI, an adaptive AI teacher.

Create a structured lesson plan using ONLY
the provided study material.

Student level:
{level}

Preferred language:
{language}

Available lesson duration:
{duration} minutes

LANGUAGE RULES:
{language_instruction}

IMPORTANT:

1. Stay strictly grounded in the study material.

2. Do not invent unrelated facts.

3. Adapt explanations to the student's level.

4. Beginner:
   Use very simple explanations.

5. Intermediate:
   Give moderate detail and examples.

6. Advanced:
   Give deeper explanations while remaining
   grounded in the material.

7. Create useful learning objectives.

8. Create meaningful lesson sections.

9. Include interactive questions based on
   the actual study material.

10. Create a final multiple-choice quiz.

11. Quiz options must contain one clearly correct
    answer supported by the study material.

12. All textual content must follow the selected
    language.

13. Do NOT mix Hindi into English lessons.

14. Do NOT mix English-only explanations into
    Hindi lessons.

15. For Hinglish, use natural Roman-script Hindi
    mixed with English technical terms.

16. Make the total section duration equal exactly
    {duration} minutes.

RETURN ONLY VALID JSON.

Use exactly this structure:

{{
    "topic": "main topic",

    "level": "{level}",

    "language": "{language}",

    "duration_minutes": {duration},

    "learning_objectives": [
        "objective 1",
        "objective 2",
        "objective 3"
    ],

    "sections": [
        {{
            "title": "section title",
            "duration_minutes": 5,
            "description": "section description",
            "key_points": [
                "key point 1",
                "key point 2"
            ]
        }}
    ],

    "interactive_questions": [
        {{
            "question": "question",
            "expected_concept": "expected concept"
        }},
        {{
            "question": "question",
            "expected_concept": "expected concept"
        }}
    ],

    "final_quiz": [
        {{
            "question": "question",
            "options": [
                "option A",
                "option B",
                "option C",
                "option D"
            ],
            "correct_answer": "correct option"
        }}
    ]
}}

STUDY MATERIAL
==================================================

{study_material[:12000]}

==================================================

Remember:

RETURN ONLY JSON.
"""


# ============================================================
# CLEAN JSON RESPONSE
# ============================================================

def clean_json_response(text):

    if not text:
        return ""

    text = text.strip()

    # Remove ```json
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove ```
    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    return text.strip()


# ============================================================
# FIND TOPIC
# ============================================================

def detect_topic(text):

    lower_text = text.lower()

    if "supervised learning" in lower_text:
        return "Supervised Learning"

    if "classification" in lower_text:
        return "Classification"

    if "regression" in lower_text:
        return "Regression"

    if "gradient descent" in lower_text:
        return "Gradient Descent"

    if "neural network" in lower_text:
        return "Neural Networks"

    if "machine learning" in lower_text:
        return "Machine Learning"

    return "Study Material"


# ============================================================
# DURATION DISTRIBUTION
# ============================================================

def distribute_duration(duration):

    duration = int(duration)

    # Four sections

    intro = max(2, round(duration * 0.20))
    core = max(3, round(duration * 0.40))
    practice = max(2, round(duration * 0.20))

    quiz = duration - intro - core - practice

    # Safety adjustment
    if quiz < 2:

        quiz = 2

        remaining = duration - quiz

        intro = max(2, round(remaining * 0.25))
        core = max(3, round(remaining * 0.50))

        practice = (
            duration
            - intro
            - core
            - quiz
        )

    return intro, core, practice, quiz


# ============================================================
# ENGLISH FALLBACK
# ============================================================

def english_fallback(
    study_material,
    level,
    language,
    duration
):

    topic = detect_topic(study_material)

    intro, core, practice, quiz = (
        distribute_duration(duration)
    )

    return {

        "topic": topic,

        "level": level,

        "language": "English",

        "duration_minutes": duration,

        "learning_objectives": [
            f"Understand the basic concept of {topic}.",
            "Identify the important ideas in the study material.",
            f"Explain {topic} using information from the study material."
        ],

        "sections": [

            {
                "title": "Introduction",
                "duration_minutes": intro,
                "description": (
                    f"Introduce {topic} using simple "
                    f"language suitable for a {level} student."
                ),
                "key_points": [
                    f"What is {topic}?",
                    "Why is the concept important?"
                ]
            },

            {
                "title": "Core Concepts",
                "duration_minutes": core,
                "description": (
                    "Explain the main concepts and "
                    "definitions from the study material."
                ),
                "key_points": extract_key_points(
                    study_material,
                    "English"
                )
            },

            {
                "title": "Examples & Practice",
                "duration_minutes": practice,
                "description": (
                    "Review important ideas and "
                    "check the student's understanding."
                ),
                "key_points": [
                    "Review the important concepts.",
                    "Explain the concept in your own words."
                ]
            },

            {
                "title": "Final Quiz",
                "duration_minutes": quiz,
                "description": (
                    "Test the student's understanding "
                    "of the main concepts."
                ),
                "key_points": [
                    "Review important concepts.",
                    "Answer the multiple-choice question."
                ]
            }
        ],

        "interactive_questions": [

            {
                "question": f"What is {topic}?",
                "expected_concept": (
                    f"Basic definition of {topic}"
                )
            },

            {
                "question": (
                    f"Explain the main idea of {topic} "
                    "in your own words."
                ),
                "expected_concept": (
                    f"Basic understanding of {topic}"
                )
            }
        ],

        "final_quiz": [

            {
                "question": (
                    f"Which statement best describes "
                    f"{topic}?"
                ),

                "options": [
                    f"{topic} is an important concept described in the study material.",
                    "It is unrelated to the study material.",
                    "It is only used for hardware design.",
                    "It does not involve any data."
                ],

                "correct_answer": (
                    f"{topic} is an important concept "
                    "described in the study material."
                )
            }
        ]
    }


# ============================================================
# HINDI FALLBACK
# ============================================================

def hindi_fallback(
    study_material,
    level,
    language,
    duration
):

    topic = detect_topic(study_material)

    intro, core, practice, quiz = (
        distribute_duration(duration)
    )

    return {

        "topic": topic,

        "level": level,

        "language": "Hindi",

        "duration_minutes": duration,

        "learning_objectives": [
            f"{topic} की मूल अवधारणा को समझना।",
            "अध्ययन सामग्री में दिए गए महत्वपूर्ण विचारों को पहचानना।",
            f"अध्ययन सामग्री के आधार पर {topic} को समझाना।"
        ],

        "sections": [

            {
                "title": "परिचय",
                "duration_minutes": intro,
                "description": (
                    f"{topic} का सरल भाषा में परिचय देना, "
                    f"जो {level} स्तर के विद्यार्थी के लिए उपयुक्त हो।"
                ),
                "key_points": [
                    f"{topic} क्या है?",
                    "यह अवधारणा क्यों महत्वपूर्ण है?"
                ]
            },

            {
                "title": "मुख्य अवधारणाएँ",
                "duration_minutes": core,
                "description": (
                    "अध्ययन सामग्री में दी गई मुख्य "
                    "परिभाषाओं और अवधारणाओं को समझाना।"
                ),
                "key_points": extract_key_points(
                    study_material,
                    "Hindi"
                )
            },

            {
                "title": "उदाहरण और अभ्यास",
                "duration_minutes": practice,
                "description": (
                    "मुख्य अवधारणाओं की समीक्षा करना "
                    "और विद्यार्थी की समझ जाँचना।"
                ),
                "key_points": [
                    "महत्वपूर्ण अवधारणाओं की समीक्षा करें।",
                    "अवधारणा को अपने शब्दों में समझाएँ।"
                ]
            },

            {
                "title": "अंतिम क्विज़",
                "duration_minutes": quiz,
                "description": (
                    "विद्यार्थी की मुख्य अवधारणाओं "
                    "की समझ का परीक्षण करना।"
                ),
                "key_points": [
                    "महत्वपूर्ण अवधारणाओं की समीक्षा करें।",
                    "बहुविकल्पीय प्रश्न का उत्तर दें।"
                ]
            }
        ],

        "interactive_questions": [

            {
                "question": f"{topic} क्या है?",
                "expected_concept": (
                    f"{topic} की मूल परिभाषा"
                )
            },

            {
                "question": (
                    f"{topic} की मुख्य अवधारणा "
                    "को अपने शब्दों में समझाइए।"
                ),
                "expected_concept": (
                    f"{topic} की मूल समझ"
                )
            }
        ],

        "final_quiz": [

            {
                "question": (
                    f"{topic} को कौन सा कथन "
                    "सबसे अच्छी तरह समझाता है?"
                ),

                "options": [
                    f"{topic} अध्ययन सामग्री में दी गई एक महत्वपूर्ण अवधारणा है।",
                    "इसका अध्ययन सामग्री से कोई संबंध नहीं है।",
                    "यह केवल hardware design के लिए उपयोग किया जाता है।",
                    "इसमें किसी data का उपयोग नहीं होता।"
                ],

                "correct_answer": (
                    f"{topic} अध्ययन सामग्री में दी गई "
                    "एक महत्वपूर्ण अवधारणा है।"
                )
            }
        ]
    }


# ============================================================
# HINGLISH FALLBACK
# ============================================================

def hinglish_fallback(
    study_material,
    level,
    language,
    duration
):

    topic = detect_topic(study_material)

    intro, core, practice, quiz = (
        distribute_duration(duration)
    )

    return {

        "topic": topic,

        "level": level,

        "language": "Hinglish",

        "duration_minutes": duration,

        "learning_objectives": [
            f"{topic} ka basic concept samajhna.",
            "Study material mein diye gaye important ideas ko identify karna.",
            f"Study material ke basis par {topic} ko explain karna."
        ],

        "sections": [

            {
                "title": "Introduction",
                "duration_minutes": intro,
                "description": (
                    f"{topic} ka simple introduction dena "
                    f"jo {level} student ke liye suitable ho."
                ),
                "key_points": [
                    f"{topic} kya hai?",
                    "Ye concept important kyun hai?"
                ]
            },

            {
                "title": "Core Concepts",
                "duration_minutes": core,
                "description": (
                    "Study material mein diye gaye "
                    "main concepts aur definitions ko samajhna."
                ),
                "key_points": extract_key_points(
                    study_material,
                    "Hinglish"
                )
            },

            {
                "title": "Examples & Practice",
                "duration_minutes": practice,
                "description": (
                    "Important concepts ko review karna "
                    "aur student ki understanding check karna."
                ),
                "key_points": [
                    "Important concepts ko review karo.",
                    "Concept ko apne words mein explain karo."
                ]
            },

            {
                "title": "Final Quiz",
                "duration_minutes": quiz,
                "description": (
                    "Student ki main concepts ke understanding "
                    "ko test karna."
                ),
                "key_points": [
                    "Important concepts ko review karo.",
                    "Multiple-choice question ka answer do."
                ]
            }
        ],

        "interactive_questions": [

            {
                "question": f"{topic} kya hai?",
                "expected_concept": (
                    f"{topic} ka basic concept"
                )
            },

            {
                "question": (
                    f"{topic} ka main idea "
                    "apne words mein explain karo."
                ),
                "expected_concept": (
                    f"{topic} ki basic understanding"
                )
            }
        ],

        "final_quiz": [

            {
                "question": (
                    f"Which statement {topic} ko "
                    "best describe karta hai?"
                ),

                "options": [
                    f"{topic} study material mein explained ek important concept hai.",
                    "Ye study material se unrelated hai.",
                    "Ye sirf hardware design ke liye use hota hai.",
                    "Isme kisi data ka use nahi hota."
                ],

                "correct_answer": (
                    f"{topic} study material mein "
                    "explained ek important concept hai."
                )
            }
        ]
    }


# ============================================================
# EXTRACT KEY POINTS
# ============================================================

def extract_key_points(
    study_material,
    language
):

    text = study_material.strip()

    # Split into sentences
    sentences = re.split(
        r'(?<=[.!?])\s+',
        text
    )

    sentences = [
        s.strip()
        for s in sentences
        if len(s.strip()) > 20
    ]

    # Keep first useful points
    sentences = sentences[:5]

    if language == "English":

        if sentences:
            return sentences

        return [
            "Important definitions",
            "Main concepts",
            "Examples from the material"
        ]

    if language == "Hindi":

        return [
            "अध्ययन सामग्री में दी गई महत्वपूर्ण परिभाषाएँ।",
            "अध्ययन सामग्री में दिए गए मुख्य concepts।",
            "अध्ययन सामग्री में दिए गए उदाहरण।"
        ]

    # Hinglish

    return [
        "Study material mein di gayi important definitions.",
        "Study material ke main concepts.",
        "Material mein diye gaye useful examples."
    ]


# ============================================================
# LOCAL FALLBACK
# ============================================================

def create_fallback_plan(
    study_material,
    level,
    language,
    duration
):

    language_lower = language.strip().lower()

    if language_lower == "hindi":

        return hindi_fallback(
            study_material,
            level,
            language,
            duration
        )

    elif language_lower == "hinglish":

        return hinglish_fallback(
            study_material,
            level,
            language,
            duration
        )

    else:

        return english_fallback(
            study_material,
            level,
            language,
            duration
        )


# ============================================================
# GENERATE LESSON PLAN
# ============================================================

def generate_lesson_plan(
    study_material,
    level="Beginner",
    language="English",
    duration=20
):

    if not study_material or not study_material.strip():

        return None

    # --------------------------------------------------------
    # Validate duration
    # --------------------------------------------------------

    try:

        duration = int(duration)

    except:

        duration = 20

    if duration < 10:

        duration = 10

    # --------------------------------------------------------
    # Build prompt
    # --------------------------------------------------------

    prompt = build_prompt(
        study_material.strip(),
        level,
        language,
        duration
    )

    # --------------------------------------------------------
    # Try OpenRouter
    # --------------------------------------------------------

    print(
        "Generating lesson plan using OpenRouter..."
    )

    try:

        response = client.chat.completions.create(

            model=MODEL_NAME,

            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            max_tokens=2500,

            temperature=0.2
        )

        if not response:

            raise ValueError(
                "Empty response from OpenRouter."
            )

        if not response.choices:

            raise ValueError(
                "OpenRouter returned no choices."
            )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:

            raise ValueError(
                "OpenRouter returned empty content."
            )

        # ----------------------------------------------------
        # Clean JSON
        # ----------------------------------------------------

        content = clean_json_response(
            content
        )

        # ----------------------------------------------------
        # Parse JSON
        # ----------------------------------------------------

        result = json.loads(
            content
        )

        if not isinstance(result, dict):

            raise ValueError(
                "AI returned invalid lesson plan format."
            )

        print(
            "OpenRouter lesson plan generated successfully."
        )

        return result

    except Exception as e:

        print(
            "OpenRouter lesson planner unavailable:",
            e
        )

        print(
            "Using intelligent local lesson planner."
        )

        return create_fallback_plan(
            study_material,
            level,
            language,
            duration
        )