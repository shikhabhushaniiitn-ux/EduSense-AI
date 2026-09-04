"""
Subject-Aware Visual Dispatch.

Given a lesson section's text, this module:

  1. Asks the AI to classify WHICH subject the section belongs to
     (Mathematics / Physics / Biology / History / Programming /
     Chemistry / General) and WHAT KIND of visual best supports
     it (equation, graph, process diagram, timeline, code, image,
     or none).

  2. Renders that visual with Streamlit:
       - equation  -> LaTeX + step-by-step text
       - graph     -> SymPy (parse) + NumPy (sample) +
                       Matplotlib (plot)
       - process   -> Mermaid.js flowchart (top-down), loaded
                       from a CDN - no extra Python package
       - timeline  -> Mermaid.js flowchart (left-right)
       - code      -> st.code() with the AI's stated expected
                       output shown separately - the code is
                       NEVER executed
       - image     -> a free, keyless Wikimedia Commons image
                       search

Every renderer fails gracefully (catches its own errors and
simply shows nothing / a plain fallback) so a bad AI response or
a flaky network call never breaks the lesson page around it.

Requires: numpy, sympy, matplotlib, requests (matplotlib is the
only one of these not already in a typical Streamlit project -
add "matplotlib" to requirements.txt).
"""

import json
import re

import numpy as np
import requests
import streamlit as st
import streamlit.components.v1 as components
import sympy

from modules.ai_client import generate_ai_response
from modules.lesson_planner import clean_ai_json_response


# ============================================================
# AI CLASSIFICATION
# ============================================================

VALID_SUBJECTS = {
    "Mathematics", "Physics", "Biology", "History",
    "Programming", "Chemistry", "General"
}

VALID_VISUAL_TYPES = {
    "equation", "graph", "process", "timeline",
    "code", "image", "map", "none"
}


def _build_classification_prompt(section_title, section_content):

    trimmed_content = (section_content or "")[:1500]

    return f"""
You are deciding what VISUAL best supports one lesson section.
Respond with ONLY a JSON object, no markdown, no explanation.

Section title: {section_title}
Section content: {trimmed_content}

Respond in exactly this shape:

{{
  "subject": "Mathematics | Physics | Biology | History | Programming | Chemistry | General",
  "visual_type": "equation | graph | process | timeline | code | image | map | none",
  "title": "short title for the visual",
  "equation": "a plain-text equation, ONLY if visual_type is equation or graph, else empty string",
  "graph_expression": "a Python/SymPy-style expression in terms of x ONLY, ONLY if visual_type is graph, e.g. x**2 - 3*x + 2, else empty string",
  "steps": ["step 1", "step 2"],
  "process_steps": ["Step A", "Step B", "Step C"],
  "code": "a short code snippet, ONLY if visual_type is code, else empty string",
  "expected_output": "what that code would print when run, ONLY if visual_type is code, else empty string",
  "image_query": "a short, specific search phrase for a real educational image, ONLY if visual_type is image, else empty string",
  "map_query": "a short, specific search phrase for a real historical/geographic map image, ONLY if visual_type is map, else empty string"
}}

RULES:
1. Pick visual_type "none" if the section is abstract/definitional
   and no visual would genuinely help - don't force one.
2. "graph" is ONLY for a single-variable function of x that can
   actually be plotted (e.g. y = x**2, y = sin(x)). If the concept
   doesn't reduce to a plottable function of x, use "equation" or
   "process" instead.
3. "process_steps" is for a short causal/sequential chain (a
   Physics cause-effect chain, a Biology process, a History
   timeline) - 3 to 6 short steps, each just a few words.
4. Return ONLY the JSON object above, nothing else - no markdown
   fences, no commentary before or after it.
5. Do NOT default to "process" just because it feels like a safe,
   general-purpose choice. A generic step-by-step flowchart is
   frequently the WRONG answer - only use "process" when the
   content is genuinely a sequence of causally-connected steps or
   events, not for a static structure or a formula.
6. If the section names a specific equation or formula (contains
   an "=" sign with algebraic terms), you MUST use "equation" or
   "graph", never "process".
7. If the section describes anatomy, a labeled structure, parts
   of an organ, or "what something looks like", prefer "image"
   over "process" - a real picture teaches a structure far better
   than a flowchart of its parts.
8. If the section is History content that centers on WHERE
   something happened (a place, a region, a route, a battle
   location, territory/borders), use "map" instead of "timeline" -
   give a real, specific map_query (e.g. "Roman Empire 117 AD
   extent map"). Only use "map" for genuinely geographic content;
   never invent coordinates - map_query must describe a REAL map
   to search for, not data to plot.
9. If the section is Programming content describing how SYSTEM
   COMPONENTS connect (e.g. "the frontend calls the backend API,
   which reads from the database"), use "process" with
   process_steps listing each component in order - this renders
   as a component/architecture diagram, not a plain step list.

EXAMPLES (follow this pattern):

Section: "Quadratic Equations - A quadratic equation has the form
y = ax^2 + bx + c. For example, y = x^2 - 3x + 2."
Correct answer: {{"subject": "Mathematics", "visual_type": "graph", "title": "y = x^2 - 3x + 2", "equation": "y = x^2 - 3x + 2", "graph_expression": "x**2 - 3*x + 2", "steps": ["Identify a=1, b=-3, c=2", "Plot the parabola"], "process_steps": [], "code": "", "expected_output": "", "image_query": "", "map_query": ""}}

Section: "The Pericardium - The heart is wrapped in a protective
sac called the pericardium, which has a fibrous outer layer and
a serous inner layer with two sub-layers (parietal and visceral)."
Correct answer: {{"subject": "Biology", "visual_type": "image", "title": "Layers of the Pericardium", "equation": "", "graph_expression": "", "steps": [], "process_steps": [], "code": "", "expected_output": "", "image_query": "pericardium layers labeled diagram heart", "map_query": ""}}

Section: "Ohm's Law - If resistance increases while voltage stays
constant, current decreases, since I = V/R."
Correct answer: {{"subject": "Physics", "visual_type": "process", "title": "Ohm's Law: Resistance Up, Current Down", "equation": "I = V/R", "graph_expression": "", "steps": [], "process_steps": ["Voltage stays constant", "Resistance increases", "Current decreases (I = V/R)"], "code": "", "expected_output": "", "image_query": "", "map_query": ""}}

Section: "The Roman Empire reached its greatest territorial extent
under Trajan in 117 AD, stretching from Britain to Mesopotamia."
Correct answer: {{"subject": "History", "visual_type": "map", "title": "Roman Empire at Its Greatest Extent (117 AD)", "equation": "", "graph_expression": "", "steps": [], "process_steps": [], "code": "", "expected_output": "", "image_query": "", "map_query": "Roman Empire 117 AD extent map Trajan"}}

Section: "In a typical web app, the frontend sends a request to
the backend API, which queries the database and returns the
result to the frontend."
Correct answer: {{"subject": "Programming", "visual_type": "process", "title": "Web App Architecture", "equation": "", "graph_expression": "", "steps": [], "process_steps": ["Frontend", "Backend API", "Database"], "code": "", "expected_output": "", "image_query": "", "map_query": ""}}
"""


def _normalize_visual_spec(raw_spec):
    """
    Defensively fill in a complete, safe spec even if the AI
    response is partial, missing keys, or slightly malformed -
    callers never need to guard against missing keys themselves.
    """

    spec = {
        "subject": "General",
        "visual_type": "none",
        "title": "",
        "equation": "",
        "graph_expression": "",
        "steps": [],
        "process_steps": [],
        "code": "",
        "expected_output": "",
        "image_query": "",
        "map_query": ""
    }

    if not isinstance(raw_spec, dict):
        return spec

    for key in spec:

        value = raw_spec.get(key)

        if value is None:
            continue

        if key in ("steps", "process_steps"):

            if isinstance(value, list):

                spec[key] = [
                    str(item).strip()
                    for item in value
                    if str(item).strip()
                ]

        else:

            spec[key] = str(value).strip()

    if spec["subject"] not in VALID_SUBJECTS:
        spec["subject"] = "General"

    if spec["visual_type"] not in VALID_VISUAL_TYPES:
        spec["visual_type"] = "none"

    return spec


# ============================================================
# HEURISTIC SAFETY NET
#
# Free/small AI models have a well-known bias toward defaulting
# to a generic "process" flowchart even when the content clearly
# calls for something more specific - it's the lowest-risk answer
# for a model unsure of itself. Rather than trusting the AI's
# CATEGORY choice blindly, cross-check it against simple,
# content-agnostic signals and correct the obvious mismatches.
# The AI still supplies all the actual content (equations, image
# queries, process steps) - this only fixes the category.
# ============================================================

EQUATION_PATTERN = re.compile(
    r"\b[A-Za-z]\w{0,3}\s*=\s*[-+]?[\w\^\*/\.\(\)\s\+\-]{1,60}"
)

STRUCTURE_KEYWORDS = (
    "layer", "layers", "structure", "anatomy", "labeled diagram",
    "cross-section", "cross section", "organ", "membrane",
    "parts of the", "components of the", "sac", "wall of"
)

PROCESS_KEYWORDS = (
    "process of", "cycle", "pathway", "converts to", "sequence of",
    "mechanism", "chain reaction", "step-by-step process",
    "step by step process"
)

GEOGRAPHIC_KEYWORDS = (
    "empire", "territory", "border", "region", "kingdom",
    "route", "invasion", "conquest", "colony", "colonies",
    "map of", "extent", "province", "trade route"
)

CODE_PATTERN = re.compile(
    r"(def |class \w|import |print\(|for\s*\(|function |"
    r"#include|public static|=\s*\d+\s*;)"
)


def _has_plottable_equation(text):
    """
    True if `text` contains something SHAPED like a mathematical
    equation (e.g. "y = x^2 - 3x + 2", "F = ma") - a short token,
    an "=" sign, then algebra-looking characters. Deliberately
    loose - a heuristic, not a parser - only used to catch cases
    where the AI skipped an equation it should have used.
    """

    return bool(EQUATION_PATTERN.search(text or ""))


def _looks_structural(text):

    lowered = (text or "").lower()

    return any(
        keyword in lowered
        for keyword in STRUCTURE_KEYWORDS
    )


def _looks_like_process(text):

    lowered = (text or "").lower()

    return any(
        keyword in lowered
        for keyword in PROCESS_KEYWORDS
    )


def _looks_like_code(text):

    return bool(CODE_PATTERN.search(text or ""))


def _looks_geographic(text):

    lowered = (text or "").lower()

    return any(
        keyword in lowered
        for keyword in GEOGRAPHIC_KEYWORDS
    )


def _try_build_graph_expression(equation_text):
    """
    Given a short equation (e.g. "y = x^2 - 3x + 2"), ask the AI
    ONE narrow, single-purpose question: convert it to a plain
    SymPy-style expression in terms of x only.

    This is a much easier task for a small/free model than the
    full multi-option visual classification, so it succeeds far
    more reliably - and the result is validated with SymPy before
    being trusted, so a bad answer just means "no graph", never a
    crash.

    Returns the expression string, or "" if the equation isn't a
    genuine single-variable function of x (e.g. it has two
    unknowns like "V = IR"), or if anything fails.
    """

    if not equation_text:
        return ""

    prompt = f"""
Convert this equation into a plain Python/SymPy expression in
terms of x ONLY (no other variables), suitable for plotting.

Equation: {equation_text}

If it genuinely cannot be written as a function of a single
variable x (e.g. it has two unknowns, or isn't a plottable
function), respond with exactly: NONE

Otherwise respond with ONLY the expression, nothing else - no
"y =", no explanation, no markdown. Example: for "y = x^2 - 3x + 2"
respond with exactly: x**2 - 3*x + 2
"""

    try:

        response = generate_ai_response(
            prompt,
            max_tokens=60,
            temperature=0.1
        )

        if not response:
            return ""

        candidate = response.strip().strip("`").strip()

        if not candidate or candidate.upper() == "NONE":
            return ""

        # Validate it actually parses as a function of x only -
        # never trust the AI's text as safe to plot without
        # checking it first.
        x = sympy.symbols("x")

        expr = sympy.sympify(
            candidate,
            locals={"x": x}
        )

        free_symbols = expr.free_symbols

        if free_symbols and free_symbols != {x}:
            return ""

        return candidate

    except Exception as error:

        print(f"Graph expression conversion failed: {error}")

        return ""


def _apply_heuristic_overrides(spec, section_content):
    """
    Correct obvious subject/visual_type mismatches after the AI's
    classification - see module docstring above for why this is
    needed. Only touches visual_type (and fills in missing
    equation/image_query/graph_expression when it changes the
    type) - everything else the AI produced is left as-is.
    """

    visual_type = spec.get("visual_type", "none")
    subject = spec.get("subject", "General")

    # ----------------------------------------------------------
    # Math/Physics/Chemistry content with an obvious equation the
    # AI didn't route to "equation"/"graph".
    # ----------------------------------------------------------

    if (
        subject in ("Mathematics", "Physics", "Chemistry")
        and visual_type not in ("graph", "equation")
        and _has_plottable_equation(section_content)
    ):

        match = EQUATION_PATTERN.search(section_content)

        equation_text = (
            spec.get("equation")
            or (match.group(0).strip() if match else "")
        )

        spec["equation"] = equation_text
        spec["visual_type"] = "equation"

    # For ANY math/physics/chemistry section that ended up as
    # "equation" (whether the AI chose it directly or we just
    # overrode into it above), try upgrading to a real "graph" -
    # a plotted curve teaches more than static text when the
    # equation genuinely is a plottable function of x.
    if (
        subject in ("Mathematics", "Physics", "Chemistry")
        and spec.get("visual_type") == "equation"
        and spec.get("equation")
        and not spec.get("graph_expression")
    ):

        graph_expression = _try_build_graph_expression(
            spec["equation"]
        )

        if graph_expression:

            spec["graph_expression"] = graph_expression
            spec["visual_type"] = "graph"

    # ----------------------------------------------------------
    # Biology/anatomy content that's clearly about a STATIC
    # STRUCTURE, not a process - a labeled image serves this far
    # better than a generic flowchart.
    # ----------------------------------------------------------

    if (
        subject == "Biology"
        and visual_type == "process"
        and _looks_structural(section_content)
        and not _looks_like_process(section_content)
    ):

        spec["visual_type"] = "image"

        if not spec.get("image_query"):

            spec["image_query"] = (
                f"{spec.get('title') or 'anatomy'} "
                "labeled diagram"
            )

    # ----------------------------------------------------------
    # Programming content the AI didn't recognize as code.
    # ----------------------------------------------------------

    if (
        subject == "Programming"
        and visual_type not in ("code",)
        and _looks_like_code(section_content)
    ):

        spec["visual_type"] = "code"

    # ----------------------------------------------------------
    # History content that's really about WHERE something
    # happened - a map teaches this better than a chronological
    # timeline.
    # ----------------------------------------------------------

    if (
        subject == "History"
        and visual_type == "timeline"
        and _looks_geographic(section_content)
    ):

        spec["visual_type"] = "map"

        if not spec.get("map_query"):

            spec["map_query"] = (
                f"{spec.get('title') or 'historical'} map"
            )

    return spec


def detect_visual(section_title, section_content):
    """
    Ask the AI to classify a section and decide what visual (if
    any) best supports it.

    Never raises - on any failure (AI error, bad JSON, network
    issue) it returns a "none" spec, so a visual-detection glitch
    never breaks lesson rendering; it just means no visual is
    shown for that section.
    """

    if not section_content or not section_content.strip():
        return _normalize_visual_spec(None)

    prompt = _build_classification_prompt(
        section_title,
        section_content
    )

    try:

        response = generate_ai_response(
            prompt,
            max_tokens=500,
            temperature=0.2
        )

        if not response:
            return _normalize_visual_spec(None)

        json_text = clean_ai_json_response(response)

        raw_spec = json.loads(json_text)

        spec = _normalize_visual_spec(raw_spec)

    except Exception as error:

        print(f"Visual detection failed: {error}")

        spec = _normalize_visual_spec(None)

    return _apply_heuristic_overrides(spec, section_content)


# ============================================================
# RENDER: EQUATION
# ============================================================

def _to_latex_friendly(equation_text):
    """
    Light touch-up so common plain-text equation notation renders
    reasonably as LaTeX via st.latex() - not a full parser, just
    handles the common cases (^ for powers, * for multiplication,
    which LaTeX otherwise drops silently).
    """

    if not equation_text:
        return ""

    latex = equation_text

    latex = latex.replace("*", r" \cdot ")
    latex = re.sub(r"\^(\w+)", r"^{\1}", latex)

    return latex


def render_equation(spec):

    if spec.get("title"):
        st.markdown(f"**{spec['title']}**")

    equation = spec.get("equation", "")

    if equation:

        try:
            st.latex(_to_latex_friendly(equation))
        except Exception:
            st.code(equation)

    steps = spec.get("steps", [])

    if steps:

        st.markdown("**Step-by-step:**")

        for i, step in enumerate(steps, start=1):
            st.markdown(f"{i}. {step}")


# ============================================================
# RENDER: GRAPH
# ============================================================

def render_graph(spec):

    expression_text = spec.get("graph_expression", "")

    if not expression_text:
        # Nothing plottable - fall back to just the equation/steps.
        render_equation(spec)
        return

    try:

        x = sympy.symbols("x")

        expr = sympy.sympify(
            expression_text,
            locals={"x": x}
        )

        func = sympy.lambdify(x, expr, "numpy")

        x_values = np.linspace(-10, 10, 400)

        with np.errstate(all="ignore"):
            y_values = func(x_values)

        y_values = np.asarray(y_values, dtype=float)

        if y_values.shape == ():
            # A constant expression (e.g. "5") - broadcast it.
            y_values = np.full_like(x_values, float(y_values))

        # Keep the plot readable even if the function blows up
        # (e.g. 1/x near 0) by clipping extreme values instead of
        # letting the y-axis stretch to +/- infinity.
        finite_y = y_values[np.isfinite(y_values)]

        if finite_y.size > 0:

            y_min, y_max = np.percentile(finite_y, [2, 98])

            padding = max(
                (y_max - y_min) * 0.1,
                1
            )

            y_values = np.clip(
                y_values,
                y_min - padding,
                y_max + padding
            )

        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 4))

        ax.plot(x_values, y_values, color="#4C6FFF", linewidth=2)

        ax.axhline(0, color="#999999", linewidth=0.8)
        ax.axvline(0, color="#999999", linewidth=0.8)

        ax.set_title(spec.get("title") or f"y = {expression_text}")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.grid(True, alpha=0.3)

        st.pyplot(fig)

        plt.close(fig)

        if spec.get("equation"):
            st.latex(_to_latex_friendly(spec["equation"]))

        steps = spec.get("steps", [])

        if steps:

            st.markdown("**Step-by-step:**")

            for i, step in enumerate(steps, start=1):
                st.markdown(f"{i}. {step}")

    except Exception as error:

        print(f"Graph rendering failed: {error}")

        # Never let a bad AI expression crash the lesson - fall
        # back to just showing the equation as text.
        render_equation(spec)


# ============================================================
# RENDER: PROCESS DIAGRAM / TIMELINE (Mermaid.js via CDN)
# ============================================================

def _escape_mermaid_label(text):

    return text.replace('"', "'")


def _render_mermaid(mermaid_code, height):

    html = f"""
    <div class="mermaid">
    {mermaid_code}
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.0/mermaid.min.js"></script>
    <script>
      mermaid.initialize({{ startOnLoad: true, theme: "neutral" }});
    </script>
    """

    components.html(html, height=height, scrolling=True)


def render_process(spec):
    """
    Top-down flowchart for a causal/sequential chain
    (e.g. Physics: Force -> Acceleration -> Motion).
    """

    steps = spec.get("process_steps") or spec.get("steps")

    if not steps:
        return

    if spec.get("title"):
        st.markdown(f"**{spec['title']}**")

    lines = ["graph TD"]

    for i, step in enumerate(steps):

        node_id = f"n{i}"
        label = _escape_mermaid_label(step)

        lines.append(f'    {node_id}["{label}"]')

        if i > 0:
            lines.append(f"    n{i - 1} --> {node_id}")

    mermaid_code = "\n".join(lines)

    _render_mermaid(
        mermaid_code,
        height=90 * len(steps) + 60
    )


def render_timeline(spec):
    """
    Left-right flowchart for a chronological sequence
    (e.g. History events in order).
    """

    steps = spec.get("process_steps") or spec.get("steps")

    if not steps:
        return

    if spec.get("title"):
        st.markdown(f"**{spec['title']}**")

    lines = ["graph LR"]

    for i, step in enumerate(steps):

        node_id = f"n{i}"
        label = _escape_mermaid_label(step)

        lines.append(f'    {node_id}["{label}"]')

        if i > 0:
            lines.append(f"    n{i - 1} --> {node_id}")

    mermaid_code = "\n".join(lines)

    _render_mermaid(mermaid_code, height=200)


# ============================================================
# RENDER: CODE
#
# The code is only ever DISPLAYED (st.code), never executed -
# "expected_output" is text the AI states the code would print,
# shown as a separate read-only block. We never eval()/exec()
# AI-generated code in a student-facing app.
# ============================================================

def render_code(spec):

    if spec.get("title"):
        st.markdown(f"**{spec['title']}**")

    code = spec.get("code", "")

    if code:
        st.code(code, language="python")

    expected_output = spec.get("expected_output", "")

    if expected_output:

        st.markdown("**Output:**")
        st.code(expected_output, language="text")

    steps = spec.get("steps", [])

    if steps:

        st.markdown("**Execution flow:**")

        process_spec = dict(spec)
        process_spec["process_steps"] = steps
        process_spec["title"] = ""

        render_process(process_spec)


# ============================================================
# RENDER: IMAGE (free, keyless Wikimedia Commons search)
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def _search_wikimedia_image(query):
    """
    Search Wikimedia Commons for a freely-licensed image matching
    `query`. Returns an image URL, or None if nothing suitable
    was found (or the request failed) - no API key required.
    Cached for an hour so the same query doesn't hit the network
    again on every rerun.
    """

    try:

        response = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": f"filetype:bitmap {query}",
                "gsrnamespace": 6,
                "gsrlimit": 1,
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": 600
            },
            headers={
                "User-Agent": "EduSense-AI/1.0 (student project)"
            },
            timeout=6
        )

        response.raise_for_status()

        data = response.json()

        pages = data.get("query", {}).get("pages", {})

        for page in pages.values():

            imageinfo = page.get("imageinfo")

            if imageinfo:

                return imageinfo[0].get(
                    "thumburl",
                    imageinfo[0].get("url")
                )

    except Exception as error:

        print(f"Wikimedia image lookup failed: {error}")

    return None


def render_image(spec):

    query = spec.get("image_query", "")

    if not query:
        return

    if spec.get("title"):
        st.markdown(f"**{spec['title']}**")

    image_url = _search_wikimedia_image(query)

    if image_url:

        st.image(
            image_url,
            caption=query,
            use_container_width=True
        )

    else:

        st.caption(
            f'🖼️ (No matching image found for "{query}")'
        )


# ============================================================
# RENDER: MAP
#
# Deliberately reuses the SAME free Wikimedia Commons search as
# render_image() rather than plotting AI-supplied coordinates -
# an AI asked to invent latitude/longitude for a historical
# border or trade route would very likely hallucinate them. A
# real, searched-for map image is factually safer than a
# fabricated one, at the cost of not being a custom-drawn map.
# ============================================================

def render_map(spec):

    query = spec.get("map_query", "") or spec.get("image_query", "")

    if not query:
        return

    if spec.get("title"):
        st.markdown(f"**{spec['title']}**")

    map_url = _search_wikimedia_image(query)

    if map_url:

        st.image(
            map_url,
            caption=query,
            use_container_width=True
        )

    else:

        st.caption(
            f'🗺️ (No matching map found for "{query}")'
        )


# ============================================================
# MAIN DISPATCH
# ============================================================

RENDERERS = {
    "equation": render_equation,
    "graph": render_graph,
    "process": render_process,
    "timeline": render_timeline,
    "code": render_code,
    "image": render_image,
    "map": render_map
}


def render_visual(spec):
    """
    Render whatever visual `spec` describes. Safe to call with a
    "none" spec (does nothing) or any spec from detect_visual() -
    every renderer catches its own errors, so an odd AI response
    never crashes the lesson page around it.
    """

    if not spec:
        return

    visual_type = spec.get("visual_type", "none")

    renderer = RENDERERS.get(visual_type)

    if not renderer:
        return

    try:
        renderer(spec)
    except Exception as error:
        print(f"Visual rendering failed ({visual_type}): {error}")


def show_subject_visual(section_title, section_content):
    """
    Convenience one-call entry point: detect + render in one
    step, inside an expander so it doesn't dominate the page.
    Returns the spec so the caller can cache it (avoids re-asking
    the AI for the same section on every Streamlit rerun).
    """

    spec = detect_visual(section_title, section_content)

    if spec.get("visual_type", "none") != "none":

        with st.expander(
            f"🎨 Visual: {spec.get('title') or spec.get('subject')}",
            expanded=True
        ):

            render_visual(spec)

    return spec