"""
Zero-cost AI Teaching Voice.

Uses Microsoft Edge's free, keyless text-to-speech service (via the
open-source `edge-tts` package) to read lesson content aloud, with
word-level timing so the on-screen transcript can highlight in sync
with the voice - a "listen along" experience without needing any
paid TTS or avatar/video API.

No API key, no signup, no per-character cost, no rate limit tied to
your account (it's the same free service Microsoft Edge's built-in
"Read Aloud" feature uses).

Install: pip install edge-tts
"""

import asyncio
import base64
import hashlib
import re

import edge_tts


# ============================================================
# VOICE SELECTION
#
# One representative, clear voice per language your app already
# supports - kept to a short curated list rather than exposing
# all 300+ Edge voices, since a student picking a lesson doesn't
# need a voice picker to get a working feature.
# ============================================================

LANGUAGE_VOICES = {
    "English": "en-US-AriaNeural",
    "Hindi": "hi-IN-SwaraNeural",

    # Edge TTS has no dedicated "Hinglish" voice - the Hindi
    # voice reads mixed Hindi/English text reasonably naturally,
    # so it's the closest available match.
    "Hinglish": "hi-IN-SwaraNeural"
}

DEFAULT_VOICE = "en-US-AriaNeural"


def get_voice_for_language(language):
    """
    Map your app's existing language selector value to an Edge
    TTS voice name. Unknown/missing language falls back to
    English rather than erroring.
    """

    return LANGUAGE_VOICES.get(
        language,
        DEFAULT_VOICE
    )


# ============================================================
# TEXT CLEANUP FOR SPEECH
# ============================================================

def prepare_text_for_speech(text):
    """
    Lesson content has markdown-ish formatting meant for reading
    on screen, not out loud (bullet symbols, markdown emphasis
    characters, etc.) - strip those so the voice doesn't try to
    pronounce punctuation literally.
    """

    if not text:
        return ""

    cleaned = str(text)

    # Bullet markers
    cleaned = cleaned.replace("•", " ")
    cleaned = re.sub(r"^\s*[-*]\s+", " ", cleaned, flags=re.MULTILINE)

    # Markdown emphasis / heading / code characters
    cleaned = re.sub(r"[*_#`>]", " ", cleaned)

    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned


# ============================================================
# CORE SYNTHESIS (async - edge-tts is an async library)
# ============================================================

async def _synthesize(text, voice):
    """
    Stream audio + WordBoundary timing events from Edge TTS.

    Returns (audio_bytes, word_timings), where word_timings is a
    list of {"text": str, "start_ms": float, "end_ms": float},
    one entry per spoken word, in order.
    """

    communicate = edge_tts.Communicate(text, voice)

    audio_chunks = []
    word_timings = []

    async for chunk in communicate.stream():

        if chunk["type"] == "audio":

            audio_chunks.append(chunk["data"])

        elif chunk["type"] == "WordBoundary":

            # edge-tts reports offset/duration in 100-nanosecond
            # units (the same convention as .NET TimeSpan ticks).
            # Dividing by 10,000 converts ticks -> milliseconds.
            start_ms = chunk["offset"] / 10000
            duration_ms = chunk["duration"] / 10000

            word_timings.append({
                "text": chunk["text"],
                "start_ms": start_ms,
                "end_ms": start_ms + duration_ms
            })

    audio_bytes = b"".join(audio_chunks)

    return audio_bytes, word_timings


def generate_speech(text, language="English"):
    """
    Synchronous wrapper around the async Edge TTS call, since
    Streamlit scripts run in a plain synchronous context.

    Returns (audio_bytes, word_timings). Returns (None, []) if
    there's no text to speak, and re-raises any real failure
    (e.g. no internet access) so the caller can show a friendly
    error instead of silently doing nothing.
    """

    cleaned_text = prepare_text_for_speech(text)

    if not cleaned_text:
        return None, []

    voice = get_voice_for_language(language)

    audio_bytes, word_timings = asyncio.run(
        _synthesize(cleaned_text, voice)
    )

    return audio_bytes, word_timings


# ============================================================
# CACHE KEY
# ============================================================

def get_cache_key(text, language):
    """
    A short, stable key for caching generated audio in
    st.session_state, keyed by (text, language) - so re-rendering
    the same section (e.g. after a rerun triggered by an unrelated
    button elsewhere on the page) doesn't call the TTS service
    again for content that hasn't changed.
    """

    raw = f"{language}::{text or ''}"

    return hashlib.md5(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# HTML PLAYER WITH WORD-LEVEL HIGHLIGHTING
# ============================================================

def build_synced_player_html(audio_bytes, word_timings):
    """
    Build a single self-contained HTML block: an <audio> player
    plus the transcript text, where each word is wrapped in its
    own <span> that gets highlighted as playback reaches it -
    driven entirely by the browser's native audio.currentTime via
    a "timeupdate" listener, no external JS libraries needed.

    Meant to be rendered with st.components.v1.html(...).
    """

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    spans = []

    for i, word in enumerate(word_timings):

        safe_text = (
            word["text"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        spans.append(
            f'<span id="w{i}" class="tts-word" '
            f'data-start="{word["start_ms"]}" '
            f'data-end="{word["end_ms"]}">{safe_text}</span>'
        )

    transcript_html = " ".join(spans)

    html = f"""
    <div style="font-family: -apple-system, Segoe UI, sans-serif;">
      <audio id="ttsAudio" controls style="width: 100%;">
        <source src="data:audio/mpeg;base64,{audio_b64}"
                type="audio/mpeg">
      </audio>
      <div id="ttsTranscript"
           style="margin-top: 12px; line-height: 1.9; font-size: 16px;
                  max-height: 160px; overflow-y: auto; padding: 8px;
                  border: 1px solid rgba(0,0,0,0.08); border-radius: 8px;">
        {transcript_html}
      </div>
    </div>
    <style>
      .tts-word {{
        padding: 1px 2px;
        border-radius: 3px;
        transition: background-color 0.1s ease;
      }}
      .tts-word.active {{
        background-color: #ffe08a;
        font-weight: 600;
      }}
    </style>
    <script>
      (function() {{
        const audio = document.getElementById("ttsAudio");
        const words = document.querySelectorAll(".tts-word");
        let lastActive = null;

        audio.addEventListener("timeupdate", function () {{
          const nowMs = audio.currentTime * 1000;
          let current = null;

          for (const w of words) {{
            const start = parseFloat(w.dataset.start);
            const end = parseFloat(w.dataset.end);
            if (nowMs >= start && nowMs < end) {{
              current = w;
              break;
            }}
          }}

          if (current !== lastActive) {{
            if (lastActive) {{
              lastActive.classList.remove("active");
            }}
            if (current) {{
              current.classList.add("active");
              current.scrollIntoView({{
                block: "nearest",
                behavior: "smooth"
              }});
            }}
            lastActive = current;
          }}
        }});
      }})();
    </script>
    """

    return html