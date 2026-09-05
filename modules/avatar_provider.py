"""Provider-neutral avatar interface with an offline development fallback."""

from __future__ import annotations

import base64
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class AvatarSegment:
    scene_id: str
    status: str
    provider: str
    playback_url: str | None = None
    message: str = ""


class AvatarProvider(ABC):
    """A vendor adapter must implement this small, stable contract."""

    @abstractmethod
    def generate_segment(self, scene: dict[str, Any]) -> AvatarSegment:
        raise NotImplementedError

    @abstractmethod
    def get_status(self, scene_id: str) -> AvatarSegment:
        raise NotImplementedError


class MockAvatarProvider(AvatarProvider):
    """Local fallback: preserves scene flow without claiming to make a video."""

    def generate_segment(self, scene: dict[str, Any]) -> AvatarSegment:
        return AvatarSegment(
            scene_id=scene["scene_id"],
            status="mock_ready",
            provider="mock",
            message="No avatar provider is configured; using local teacher presentation."
        )

    def get_status(self, scene_id: str) -> AvatarSegment:
        return AvatarSegment(scene_id=scene_id, status="mock_ready", provider="mock")


def get_avatar_provider() -> AvatarProvider:
    """Return the safe fallback until a concrete credentialed adapter is added."""
    return MockAvatarProvider()


# ============================================================
# REAL, ZERO-COST TALKING AVATAR (HTML5 Canvas)
#
# This does NOT replace the AvatarProvider/AvatarSegment contract
# above - video_pipeline.compose_segment() still uses those exactly
# as before. This is a separate, additive rendering helper for the
# actual on-screen "AI Teacher" experience: a browser-drawn avatar
# whose mouth/eyes animate in sync with the SAME audio bytes +
# word_timings that modules.audio_teacher.generate_speech() already
# produces - no new AI/TTS call, no paid avatar API, no GPU render.
#
# IMPORTANT: the avatar canvas and the transcript panel share ONE
# <audio> element inside ONE components.html() call. Streamlit
# components render each call in its own sandboxed iframe, so two
# separate components.html() calls could never share one <audio>
# tag - that's why this returns a single combined widget instead of
# a standalone avatar fragment.
# ============================================================

def build_avatar_player_html(
    audio_bytes: bytes,
    word_timings: list[dict[str, Any]] | None,
    avatar_gender: str = "female",
) -> str:
    """
    Build one self-contained HTML block: an animated talking-head
    canvas (left) + the audio player and word-highlighted transcript
    (right), all driven by a single shared <audio> element.

    audio_bytes: raw audio from audio_teacher.generate_speech()
    word_timings: the same [{"text", "start_ms", "end_ms"}, ...]
        list generate_speech() already returns.

    Meant to be rendered with streamlit.components.v1.html(...).
    """

    audio_b64 = base64.b64encode(audio_bytes or b"").decode("utf-8")
    accent = "#3b82f6" if avatar_gender == "male" else "#ec4899"

    timings = word_timings or []
    boundaries_json = json.dumps(timings)

    spans = []
    for i, word in enumerate(timings):
        safe_text = (
            str(word.get("text", ""))
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        spans.append(
            f'<span id="avw{i}" class="avatar-word" '
            f'data-start="{word.get("start_ms", 0)}" '
            f'data-end="{word.get("end_ms", 0)}">{safe_text}</span>'
        )
    transcript_html = " ".join(spans)

    return f"""
    <div style="display:flex; gap:16px; flex-wrap:wrap; font-family:-apple-system,Segoe UI,sans-serif;">

      <div style="flex:0 0 220px; background:#0f172a; border-radius:16px; padding:14px; text-align:center; color:#fff;">
        <div style="position:relative; width:190px; height:190px; margin:0 auto;">
          <canvas id="avCanvas" width="190" height="190"
            style="background:radial-gradient(circle,#1e293b 0%,#0f172a 100%);
                   border-radius:50%; border:3px solid {accent};"></canvas>
          <div id="avStatus" style="position:absolute; bottom:4px; right:8px;
              background:rgba(0,0,0,0.7); padding:2px 8px; border-radius:10px;
              font-size:10px; color:{accent}; border:1px solid {accent};">● Ready</div>
        </div>
        <div style="font-size:12px; color:#94a3b8; margin-top:8px;">AI Teacher</div>
      </div>

      <div style="flex:1 1 260px; min-width:220px;">
        <audio id="avAudio" controls style="width:100%;">
          <source src="data:audio/mpeg;base64,{audio_b64}" type="audio/mpeg">
        </audio>
        <div id="avTranscript"
             style="margin-top:10px; line-height:1.9; font-size:15px;
                    max-height:180px; overflow-y:auto; padding:8px;
                    border:1px solid rgba(0,0,0,0.08); border-radius:8px;">
          {transcript_html}
        </div>
      </div>
    </div>

    <style>
      .avatar-word {{ padding:1px 2px; border-radius:3px; transition:background-color .1s ease; }}
      .avatar-word.active {{ background-color:#ffe08a; font-weight:600; }}
    </style>

    <script>
    (function() {{
      const audio = document.getElementById("avAudio");
      const canvas = document.getElementById("avCanvas");
      const ctx = canvas.getContext("2d");
      const status = document.getElementById("avStatus");
      const words = document.querySelectorAll(".avatar-word");
      const boundaries = {boundaries_json};

      let isSpeaking = false;
      let mouthOpenness = 2;
      let blinkState = 0;
      let lastActiveWord = null;

      setInterval(() => {{
        if (Math.random() > 0.6) {{
          blinkState = 1;
          setTimeout(() => {{ blinkState = 0; }}, 150);
        }}
      }}, 3000);

      audio.addEventListener("play", () => {{
        isSpeaking = true;
        status.innerHTML = "● Teaching...";
        status.style.color = "#4ade80"; status.style.borderColor = "#4ade80";
      }});
      audio.addEventListener("pause", () => {{
        isSpeaking = false; mouthOpenness = 2;
        status.innerHTML = "● Paused";
        status.style.color = "#facc15"; status.style.borderColor = "#facc15";
      }});
      audio.addEventListener("ended", () => {{
        isSpeaking = false; mouthOpenness = 2;
        status.innerHTML = "● Finished";
        status.style.color = "{accent}"; status.style.borderColor = "{accent}";
      }});

      // Single shared timeupdate listener: drives BOTH the
      // transcript highlight and the avatar's current word/mouth
      // state, so they can never drift apart.
      audio.addEventListener("timeupdate", () => {{
        const nowMs = audio.currentTime * 1000;
        let current = null;
        for (const w of words) {{
          const start = parseFloat(w.dataset.start);
          const end = parseFloat(w.dataset.end);
          if (nowMs >= start && nowMs < end) {{ current = w; break; }}
        }}
        if (current !== lastActiveWord) {{
          if (lastActiveWord) lastActiveWord.classList.remove("active");
          if (current) {{
            current.classList.add("active");
            current.scrollIntoView({{ block: "nearest", behavior: "smooth" }});
          }}
          lastActiveWord = current;
        }}
        mouthOpenness = (isSpeaking && current)
          ? 10 + Math.sin(Date.now() * 0.02) * 7
          : (isSpeaking ? 4 + Math.sin(Date.now() * 0.01) * 3 : 2);
      }});

      function draw() {{
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const t = Date.now() * 0.003;
        const bob = isSpeaking ? Math.sin(t * 4) * 2 : Math.sin(t * 1.5) * 1;
        const cx = 95, cy = 95 + bob;

        ctx.fillStyle = "{accent}";
        ctx.beginPath(); ctx.ellipse(cx, cy + 88, 58, 40, 0, 0, Math.PI * 2); ctx.fill();

        ctx.fillStyle = "#f87171";
        ctx.fillRect(cx - 14, cy + 18, 28, 24);

        ctx.fillStyle = "#fca5a5";
        ctx.beginPath(); ctx.arc(cx, cy - 8, 44, 0, Math.PI * 2); ctx.fill();

        ctx.fillStyle = "#1e1b4b";
        ctx.beginPath(); ctx.arc(cx, cy - 18, 46, Math.PI, 0); ctx.fill();

        ctx.fillStyle = "#0f172a";
        if (blinkState === 1) {{
          ctx.fillRect(cx - 20, cy - 14, 14, 2);
          ctx.fillRect(cx + 6, cy - 14, 14, 2);
        }} else {{
          ctx.beginPath();
          ctx.arc(cx - 13, cy - 14, 5, 0, Math.PI * 2);
          ctx.arc(cx + 13, cy - 14, 5, 0, Math.PI * 2);
          ctx.fill();
        }}

        if (mouthOpenness > 6) {{
          ctx.fillStyle = "#881337";
          ctx.beginPath();
          ctx.ellipse(cx, cy + 16, 11, Math.max(2, mouthOpenness), 0, 0, Math.PI * 2);
          ctx.fill();
        }} else {{
          ctx.strokeStyle = "#881337"; ctx.lineWidth = 2;
          ctx.beginPath(); ctx.moveTo(cx - 8, cy + 16); ctx.lineTo(cx + 8, cy + 16); ctx.stroke();
        }}

        requestAnimationFrame(draw);
      }}
      draw();
    }})();
    </script>
    """
