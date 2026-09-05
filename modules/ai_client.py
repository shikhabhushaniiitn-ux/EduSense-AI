import os
from dotenv import load_dotenv

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

GEMINI_KEY_1 = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
GEMINI_KEY_2 = os.getenv("GEMINI_API_KEY_2")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")

# ============================================================
# CLIENT INITIALIZATIONS
# ============================================================

gemini_client_1 = None
gemini_client_2 = None
openrouter_client = None
groq_client = None

try:
    from google import genai
    if GEMINI_KEY_1:
        gemini_client_1 = genai.Client(api_key=GEMINI_KEY_1)
    if GEMINI_KEY_2:
        gemini_client_2 = genai.Client(api_key=GEMINI_KEY_2)
except Exception as e:
    print(f"Gemini client init note: {e}")

try:
    from openai import OpenAI
    if OPENROUTER_KEY:
        openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_KEY
        )
    if GROQ_KEY:
        groq_client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_KEY
        )
except Exception as e:
    print(f"OpenAI client init note: {e}")

PRIMARY_OPENROUTER_MODEL = "google/gemma-4-26b-a4b-it:free"
FALLBACK_OPENROUTER_MODELS = [
    "google/gemma-4-31b-it:free",
    "minimax/minimax-m3:free",
    "z-ai/glm-5.2:free"
]


# ============================================================
# INTERNAL GENERATION HELPERS
# ============================================================

def _generate_with_gemini(client, prompt, max_tokens, temperature):
    """Generate using Google GenAI SDK."""
    if not client:
        return None
    try:
        from google.genai import types
        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature
        )
        # Try gemini-3.6-flash first, then gemini-2.5-flash
        for model_name in ["gemini-3.6-flash", "gemini-2.5-flash"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as model_err:
                if "404" in str(model_err) or "not found" in str(model_err).lower():
                    continue
                raise model_err
    except Exception as e:
        print(f"Gemini generation error: {e}")
    return None


def _generate_with_openrouter(prompt, max_tokens, temperature):
    """Generate using OpenRouter."""
    if not openrouter_client:
        return None
    try:
        response = openrouter_client.chat.completions.create(
            model=PRIMARY_OPENROUTER_MODEL,
            extra_body={"models": FALLBACK_OPENROUTER_MODELS},
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        if response and response.choices and response.choices[0].message:
            content = response.choices[0].message.content
            if content:
                return content.strip()
    except Exception as e:
        print(f"OpenRouter generation error: {e}")
    return None


def _generate_with_groq(prompt, max_tokens, temperature):
    """Generate using Groq."""
    if not groq_client:
        return None
    for model_name in ["llama-3.1-8b-instant", "llama3-70b-8192", "mixtral-8x7b-32768"]:
        try:
            response = groq_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            if response and response.choices and response.choices[0].message:
                content = response.choices[0].message.content
                if content:
                    return content.strip()
        except Exception:
            continue
    return None


# ============================================================
# GENERATE TEXT (PUBLIC API)
# ============================================================

def generate_text(
    prompt,
    max_tokens=500,
    temperature=0.2,
    _is_retry=False
):
    """
    Generate text using Gemini (primary) with fallback to
    OpenRouter and Groq. Preserves the exact signature used
    by qa.py, summarizer.py, teacher.py, lesson_planner.py, etc.
    """
    if not prompt or not prompt.strip():
        return None

    # 1. Primary: Gemini Key 1
    if gemini_client_1:
        text = _generate_with_gemini(gemini_client_1, prompt, max_tokens, temperature)
        if text:
            return text

    # 2. Secondary: Gemini Key 2
    if gemini_client_2:
        text = _generate_with_gemini(gemini_client_2, prompt, max_tokens, temperature)
        if text:
            return text

    # 3. Tertiary: OpenRouter
    if openrouter_client:
        text = _generate_with_openrouter(prompt, max_tokens, temperature)
        if text:
            return text

    # 4. Quaternary: Groq
    if groq_client:
        text = _generate_with_groq(prompt, max_tokens, temperature)
        if text:
            return text

    return None


# ============================================================
# GENERATE AI RESPONSE (PUBLIC API)
# ============================================================

def generate_ai_response(
    prompt,
    max_tokens=1500,
    temperature=0.3
):
    """Generate a larger AI response for lesson planning / structuring."""
    return generate_text(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature
    )