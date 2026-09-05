"""
Centralized Visual Style DNA for EduSense AI.

Controls:
- Color palette (accents, backgrounds, text, semantic states)
- Typography (prose, display, monospace)
- Matplotlib plot theme
- Mermaid diagram theme
- Virtual classroom blackboard & card styling
"""

class StyleDNA:
    # Color Palette
    PRIMARY = "#4F46E5"        # Indigo-600 (Main educational brand)
    PRIMARY_LIGHT = "#818CF8"  # Indigo-400
    SECONDARY = "#0EA5E9"      # Sky-500
    ACCENT_FEMALE = "#EC4899"  # Pink-500 (Dr. Sophia avatar)
    ACCENT_MALE = "#3B82F6"    # Blue-500 (Prof. Marcus avatar)
    ACCENT_COACH = "#10B981"   # Emerald-500 (Coach Alex avatar)

    # Backgrounds & Cards
    BG_DARK = "#0F172A"        # Slate-900 (Classroom blackboard background)
    BG_CARD_DARK = "#1E293B"   # Slate-800 (Cards inside classroom)
    BG_LIGHT = "#F8FAFC"       # Slate-50
    BG_CARD_LIGHT = "#FFFFFF"

    # Typography & Text
    TEXT_DARK = "#0F172A"
    TEXT_LIGHT = "#F8FAFC"
    TEXT_MUTED = "#94A3B8"     # Slate-400
    TEXT_CHALK = "#E2E8F0"     # Blackboard chalk text

    # Borders & Dividers
    BORDER_LIGHT = "#E2E8F0"
    BORDER_DARK = "#334155"

    # Semantic Status
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    ERROR = "#EF4444"
    INFO = "#3B82F6"

    # Typography Stack
    FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    FONT_MONO = "'Fira Code', 'Cascadia Code', 'Consolas', monospace"

    @classmethod
    def apply_matplotlib_theme(cls, fig, ax, dark_mode=False):
        """Apply consistent StyleDNA to a Matplotlib plot."""
        if dark_mode:
            bg_color = cls.BG_CARD_DARK
            text_color = cls.TEXT_LIGHT
            grid_color = "#334155"
            line_color = cls.PRIMARY_LIGHT
        else:
            bg_color = "#FFFFFF"
            text_color = cls.TEXT_DARK
            grid_color = "#E2E8F0"
            line_color = cls.PRIMARY

        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)

        for spine in ax.spines.values():
            spine.set_color(grid_color)
            spine.set_linewidth(1.0)

        ax.tick_params(colors=text_color, labelsize=9)
        ax.xaxis.label.set_color(text_color)
        ax.yaxis.label.set_color(text_color)
        ax.title.set_color(text_color)
        ax.title.set_fontsize(11)
        ax.title.set_fontweight("bold")
        ax.grid(True, linestyle="--", alpha=0.5, color=grid_color)
        return line_color

    @classmethod
    def get_mermaid_init_script(cls):
        """Consistent Mermaid initialization script."""
        return f"""
        <script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.0/mermaid.min.js"></script>
        <script>
          mermaid.initialize({{
            startOnLoad: true,
            theme: "base",
            themeVariables: {{
              primaryColor: "#EEF2FF",
              primaryTextColor: "{cls.TEXT_DARK}",
              primaryBorderColor: "{cls.PRIMARY}",
              lineColor: "{cls.PRIMARY}",
              secondaryColor: "#F0FDF4",
              tertiaryColor: "#F8FAFC",
              fontFamily: "{cls.FONT_FAMILY}",
              fontSize: "14px"
            }}
          }});
        </script>
        """
