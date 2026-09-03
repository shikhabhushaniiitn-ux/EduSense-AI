import os

from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")


# ============================================================
# CHECK API KEY
# ============================================================

if not API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY is not set in .env"
    )


# ============================================================
# OPENROUTER CLIENT
# ============================================================

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY
)


# ============================================================
# MODEL CONFIGURATION
# ============================================================

PRIMARY_MODEL = "google/gemma-4-26b-a4b-it:free"

FALLBACK_MODELS = [
    "google/gemma-4-31b-it:free",
    "minimax/minimax-m3:free",
    "z-ai/glm-5.2:free"
]


# ============================================================
# GENERATE TEXT
# ============================================================

def generate_text(
    prompt,
    max_tokens=500,
    temperature=0.2,
    _is_retry=False
):
    """
    Generate text using OpenRouter.

    This function is used by:
        - qa.py
        - summarizer.py
        - teacher.py
        - other modules

    The function keeps the original interface so
    existing files do not need to be changed.
    """

    # --------------------------------------------------------
    # Validate prompt
    # --------------------------------------------------------

    if not prompt or not prompt.strip():
        return None

    try:

        # ----------------------------------------------------
        # Send request to OpenRouter
        # ----------------------------------------------------

        response = client.chat.completions.create(
            model=PRIMARY_MODEL,

            extra_body={
                "models": FALLBACK_MODELS
            },

            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            max_tokens=max_tokens,
            temperature=temperature
        )

        # ----------------------------------------------------
        # Validate response
        # ----------------------------------------------------

        if not response:
            return None

        if not response.choices:
            return None

        choice = response.choices[0]

        message = choice.message

        if not message:
            return None

        content = message.content

        finish_reason = getattr(
            choice,
            "finish_reason",
            None
        )

        # ----------------------------------------------------
        # TRUNCATION FIX
        #
        # If the model ran out of tokens mid-sentence
        # (finish_reason == "length"), the response looks
        # like a cut-off fragment - e.g. "Regression is a
        # technique that" with nothing after it. Instead of
        # returning that broken text, retry ONCE with double
        # the token budget (capped, and only once, so a
        # genuinely broken prompt can't loop forever).
        # ----------------------------------------------------

        if (
            content
            and finish_reason == "length"
            and not _is_retry
            and max_tokens < 4000
        ):

            print(
                f"Response was cut off at max_tokens={max_tokens}, "
                "retrying with a larger budget..."
            )

            return generate_text(
                prompt,
                max_tokens=min(max_tokens * 2, 4000),
                temperature=temperature,
                _is_retry=True
            )

        if content:
            return content.strip()

        return None

    except Exception as e:

        print(
            f"OpenRouter generation error: {e}"
        )

        return None


# ============================================================
# GENERATE AI RESPONSE
# ============================================================

def generate_ai_response(
    prompt,
    max_tokens=1500,
    temperature=0.3
):
    """
    Generate a larger AI response.

    This function is used by lesson_planner.py.

    It internally uses generate_text(), so both old
    and new modules use the same OpenRouter client.
    """

    return generate_text(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature
    )