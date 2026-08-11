"""
DJ AI OS — Pro DJ Design System (Rekordbox / Serato Style)

Professional dark theme for club environments.
Clean lines, high contrast, no glow — just signal.
"""

# ============================================================
# BASE SURFACES
# ============================================================
BG = "#0C0C14"                  # deep black background
SURFACE = "#14141E"             # card / panel surface
SURFACE_RAISED = "#1C1C28"      # elevated elements (hover, dropdown)
SURFACE_HOVER = "#22222E"       # interactive hover
BORDER = "#2A2A3A"              # subtle dividers / borders
BORDER_LIGHT = "#383848"        # focused / active borders

# ============================================================
# TEXT
# ============================================================
TEXT_PRIMARY = "#F0F0F5"        # main text (near-white)
TEXT_SECONDARY = "#8888A0"      # muted labels
TEXT_DIM = "#555570"            # hints / disabled / placeholders

# ============================================================
# ACCENT COLORS
# ============================================================
RED = "#E63946"                 # primary accent (Serato red)
RED_HOVER = "#FF5A68"           # red hover / active
RED_DIM = "#8B2530"             # red inactive / background

BLUE = "#457B9D"               # secondary accent
BLUE_BRIGHT = "#5DADE2"         # info highlights / active links

GREEN = "#2ECC71"              # success / playing / good health
GREEN_DIM = "#1A7A42"           # green inactive

AMBER = "#F5A623"              # warning / energy bars / caution
AMBER_DIM = "#A06B15"           # amber muted

# ============================================================
# STATUS COLORS
# ============================================================
DANGER = RED
SUCCESS = GREEN
WARNING = AMBER
INFO = BLUE_BRIGHT

# ============================================================
# BACKWARD COMPATIBILITY (old tokens → new)
# ============================================================
# Keep these so existing imports don't break
BACKGROUND = BG
PANEL = SURFACE
CARD = SURFACE
ACCENT = RED
ACCENT_SOFT = RED_HOVER
ACCENT_DARK = RED_DIM
NEON_PURPLE = BLUE
NEON_MAGENTA = RED_HOVER
NEON_BLUE = BLUE_BRIGHT
NEON_PURPLE_DARK = "#1A2A3A"
MUTED = TEXT_SECONDARY
SUBTLE = TEXT_DIM
HOVER = SURFACE_HOVER
SELECTED = "#1E1520"            # selected row tint
GRID = BG
SHADOW = "#050508"
GLOW = "#E63946"
PURPLE_GLOW = "#457B9D"
TEXT = TEXT_PRIMARY
GLASS_BG = SURFACE
GLASS_BG_HOVER = SURFACE_HOVER
GLASS_BORDER = BORDER
GLASS_HIGHLIGHT = BORDER_LIGHT
GLOW_ACCENT = "#E63946"
GLOW_PURPLE = "#457B9D"
GLOW_BLUE = "#5DADE2"
GLOW_MAGENTA = "#FF5A68"

# ============================================================
# SCALE
# ============================================================
SP1 = 4
SP2 = 8
SP3 = 12
SP4 = 16
SP5 = 24
SP6 = 32

R_SMALL = 6
R_MED = 8
R_LG = 12
R_SM = 6
R_MD = 8

# ============================================================
# TYPOGRAPHY
# ============================================================
_FONT_FAMILY = "Inter"
_MONO_FONT = "Consolas"         # fallback: Consolas always available

F_H1 = (_FONT_FAMILY, 28, "bold")
F_H2 = (_FONT_FAMILY, 20, "bold")
F_H3 = (_FONT_FAMILY, 15, "bold")
F_H4 = (_FONT_FAMILY, 13, "bold")
F_BODY = (_FONT_FAMILY, 13)
F_BODY_BOLD = (_FONT_FAMILY, 13, "bold")
F_META = (_FONT_FAMILY, 11)
F_SMALL = (_FONT_FAMILY, 10)
F_TINY = (_FONT_FAMILY, 9)
F_MONO = (_MONO_FONT, 12)
F_LARGE = (_FONT_FAMILY, 36, "bold")

# ============================================================
# SEMANTIC NAMES
# ============================================================
# Surface colors
COL_BG = BG
COL_CARD = SURFACE
COL_CARD_HOVER = SURFACE_HOVER
COL_ELEVATED = SURFACE_RAISED

# Border
COL_BORDER = BORDER
COL_BORDER_ACTIVE = RED

# Text
COL_TEXT = TEXT_PRIMARY
COL_TEXT_MUTE = TEXT_SECONDARY
COL_TEXT_DIM = TEXT_DIM

# Accents
COL_ACCENT = RED
COL_ACCENT_HOVER = RED_HOVER
COL_ACCENT_ALT = BLUE_BRIGHT
COL_SUCCESS = GREEN
COL_WARNING = AMBER
COL_DANGER = RED

# ============================================================
# WIDGET DEFAULTS
# ============================================================
# Button defaults
BTN_PRIMARY_FG = RED
BTN_PRIMARY_HOVER = RED_HOVER
BTN_PRIMARY_TEXT = "#FFFFFF"
BTN_SECONDARY_FG = SURFACE_RAISED
BTN_SECONDARY_HOVER = SURFACE_HOVER
BTN_SECONDARY_TEXT = TEXT_PRIMARY
BTN_BORDER_RADIUS = R_SM

# Card defaults
CARD_FG = SURFACE
CARD_BORDER = BORDER
CARD_BORDER_WIDTH = 1
CARD_BORDER_RADIUS = R_MD
CARD_PADDING = 16

# Input defaults
INPUT_FG = BG
INPUT_BORDER = BORDER
INPUT_BORDER_FOCUS = RED
INPUT_TEXT = TEXT_PRIMARY
INPUT_PLACEHOLDER = TEXT_DIM

# Table defaults
TABLE_HEADER_BG = SURFACE_RAISED
TABLE_HEADER_TEXT = TEXT_SECONDARY
TABLE_ROW_BG = BG
TABLE_ROW_ALT = SURFACE
TABLE_ROW_HOVER = SURFACE_HOVER
TABLE_ROW_SELECTED = "#1E1520"
TABLE_ROW_HEIGHT = 34
TABLE_BORDER = BORDER

# Scrollbar defaults
SCROLLBAR_BG = SURFACE
SCROLLBAR_FG = SURFACE_RAISED
SCROLLBAR_HOVER = BORDER_LIGHT
