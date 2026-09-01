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
# MODEL FALLBACK CHAIN
# ============================================================

PRIMARY_MODEL = (
    "google/gemma-4-26b-a4b-it:free"
)

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
    temperature=0.2
):
    """
    Generate text using OpenRouter.

    The primary model is tried first.
    If it is unavailable or rate-limited,
    OpenRouter automatically tries the
    fallback models.
    """

    if not prompt or not prompt.strip():
        return None

    try:

        response = client.chat.completions.create(

            # Primary model
            model=PRIMARY_MODEL,

            # OpenRouter model fallback chain
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
        # Check response
        # ----------------------------------------------------

        if not response:
            return None

        if not response.choices:
            return None

        message = response.choices[0].message

        if not message:
            return None

        content = message.content

        if content:
            return content.strip()

        return None

    except Exception as e:

        print(
            f"OpenRouter generation error: {e}"
        )

        return None