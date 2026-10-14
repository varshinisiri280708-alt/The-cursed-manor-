"""
Cryptic Escape: The Cursed Manor (Streamlit edition)

Run with:
    streamlit run app.py

This is a point and click take on the Pygame game in main.py. It keeps the
same three chapters, Caesar seals, Witness dialogue, side stories, mini games,
seasonal themes and the same savegame.json / settings.json files, so a save
made here can be continued in the Pygame version and the other way round.
"""

import base64
import html
import io
import json
import os
import random

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from game_data import (CLOAK_NAMES, CLOAKS, DIALOGUES, DIFFICULTY, ENDING_COMPLETE,
                       ENDING_PARTIAL, HEROES, LEVELS, QUESTS, SEASON_THEMES, STORIES)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "assets")
SAVE_FILE = os.path.join(BASE_DIR, "savegame.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "master_volume": 0.65, "music_volume": 0.35, "sfx_volume": 0.8,
    "sensitivity": 0.0022, "dark_mode": True, "character_color": 2,
    "character_type": 0, "difficulty": "Normal", "minimap": True,
    "head_bob": True, "active_theme": "Haunted",
}
DEFAULT_SAVE = {"level": 0, "health": 100, "clues": [], "won": False,
                "difficulty": "Normal", "quest_flags": []}

st.set_page_config(page_title="Cryptic Escape: The Cursed Manor", page_icon="🕯️",
                   layout="wide", initial_sidebar_state="collapsed")


# ----------------------------------------------------------------------------
# Files and assets
# ----------------------------------------------------------------------------
def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {**default, **data}
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return dict(default)


def write_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


@st.cache_data(show_spinner=False)
def img_b64(name, max_w=1100):
    """Return a compressed base64 data URI for an asset (cached)."""
    path = os.path.join(ASSET_DIR, name)
    try:
        im = Image.open(path).convert("RGB")
    except OSError:
        im = Image.new("RGB", (640, 360), (30, 18, 34))
    if im.width > max_w:
        im = im.resize((max_w, int(im.height * max_w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


@st.cache_data(show_spinner=False)
def audio_b64(name):
    """Return an audio data URI so sound assets work inside the embedded game iframe."""
    path = os.path.join(ASSET_DIR, "sounds", name)
    try:
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        return "data:audio/mpeg;base64," + encoded
    except OSError:
        return ""


# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
S = st.session_state


def init_state():
    if "ready" in S:
        return
    S.settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    if S.settings.get("active_theme") not in SEASON_THEMES:
        S.settings["active_theme"] = "Haunted"
    if S.settings.get("difficulty") not in DIFFICULTY:
        S.settings["difficulty"] = "Normal"
    save = load_json(SAVE_FILE, DEFAULT_SAVE)
    S.has_save = os.path.exists(SAVE_FILE) and not save.get("won") and (save.get("level", 0) > 0 or save.get("clues"))
    S.quest_flags = set(save.get("quest_flags", []))
    S.screen = "title"
    S.return_to = "title"
    S.minigame = {}
    S.story_idx = 0
    S.story_page = 0
    S.flash = False
    reset_run(0)
    S.ready = True


def reset_run(level=0, clues=None, health=100):
    S.level = level
    S.clues = set(clues or [])
    S.health = health
    S.oil = 100
    S.hollow = 15
    S.log = [LEVELS[level]["intro"]]
    S.searched = set()
    S.hint_shown = False
    S.feedback = ""
    S.dialogue = None
    S.won = False


def persist_save(won=False):
    write_json(SAVE_FILE, {
        "level": S.level, "health": S.health, "clues": sorted(S.clues), "won": won,
        "difficulty": S.settings["difficulty"], "quest_flags": sorted(S.quest_flags),
    })


def persist_settings():
    write_json(SETTINGS_FILE, S.settings)


HUB_FAMILY = ("hub", "minigame", "quests", "stories", "story", "themes")


def go(screen, remember=False):
    if remember and S.screen not in HUB_FAMILY:
        if screen == "hub":
            S.hub_return = S.screen
        else:
            S.return_to = S.screen
    elif remember and screen != "hub":
        S.return_to = "hub"
    S.screen = screen


def say(msg):
    if not S.log or S.log[0] != msg:
        S.log = ([msg] + S.log)[:5]


init_state()
THEME = SEASON_THEMES[S.settings["active_theme"]]
ACCENT = THEME["accent"]


# ----------------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------------
def inject_css():
    dark = S.settings.get("dark_mode", True)
    bg, ink, muted, panel = (("#120A16", "#EDE1CB", "#B9A9B8", "rgba(28,16,32,.82)") if dark
                             else ("#E7DCCB", "#2A1A2C", "#6A5868", "rgba(250,244,234,.86)"))
    css = f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700;900&family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:{bg}; --ink:{ink}; --muted:{muted}; --panel:{panel};
  --brass:#B8935A; --brass-dim:rgba(184,147,90,.38); --cyan:#6BE1FF;
  --ember:#E8A050; --rose:#C2465F; --accent:{ACCENT};
}}
html, body, .stApp {{ background: var(--bg); color: var(--ink); }}
.stApp {{
  background:
    radial-gradient(ellipse 80% 60% at 70% -10%, color-mix(in srgb, var(--accent) 16%, transparent), transparent 70%),
    radial-gradient(ellipse 60% 50% at 0% 100%, rgba(120,40,60,.18), transparent 70%),
    var(--bg);
  font-family: 'Cormorant Garamond', Georgia, serif;
}}
[data-testid="stHeader"], [data-testid="stToolbar"], footer, #MainMenu,
[data-testid="stSidebar"], [data-testid="stDecoration"] {{ display:none !important; }}
.block-container {{ padding: 1.4rem 2.2rem 3rem; max-width: 1280px; }}
p, li, label, .stMarkdown, [data-testid="stMarkdownContainer"] {{
  font-family:'Cormorant Garamond', Georgia, serif; color:var(--ink); font-size:1.12rem; line-height:1.6;
}}
h1,h2,h3,h4 {{ font-family:'Cinzel', Georgia, serif !important; color:var(--ink) !important; letter-spacing:.04em; }}

/* Buttons */
.stButton button, [data-testid="stFormSubmitButton"] button, [data-testid^="stBaseButton"] {{
  font-family:'Cinzel', Georgia, serif !important; font-weight:600; letter-spacing:.06em;
  background: linear-gradient(180deg, rgba(60,34,58,.92), rgba(30,17,32,.95));
  color: var(--ink) !important; border:1px solid var(--brass-dim) !important; border-radius:3px !important;
  padding:.62rem 1.1rem; transition: border-color .2s, box-shadow .2s, transform .1s;
}}
.stFormSubmitButton button p, .stButton > button p {{ font-family:'Cinzel', Georgia, serif !important; font-size:.92rem; }}
.stButton button:hover, [data-testid="stFormSubmitButton"] button:hover {{ border-color: var(--brass) !important; box-shadow: 0 0 18px -4px var(--accent); color:#fff !important; }}
.stButton button:active {{ transform: translateY(1px); }}
.stButton button:focus-visible, [data-testid="stFormSubmitButton"] button:focus-visible {{ outline:2px solid var(--cyan) !important; outline-offset:2px; }}
.stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"], [data-testid="stBaseButton-primaryFormSubmit"], [data-testid="stBaseButton-primary"] {{
  background: linear-gradient(180deg, color-mix(in srgb, var(--accent) 55%, #2a1530), color-mix(in srgb, var(--accent) 30%, #1a0d1e)) !important;
  border-color: var(--brass) !important;
}}
.stButton button:disabled {{ opacity:.38; box-shadow:none; }}
.stButton button p, [data-testid="stFormSubmitButton"] button p {{ font-family:'Cinzel', Georgia, serif !important; font-size:.92rem !important; }}

/* Inputs */
[data-testid="stTextInput"] input {{
  background: rgba(10,5,14,.85) !important; color:#F4ECFF !important; border:1px solid var(--brass-dim) !important;
  font-family:'Cinzel', Georgia, serif !important; font-size:1.15rem !important; letter-spacing:.12em; padding:.8rem 1rem !important;
}}
[data-testid="stTextInput"] input:focus {{ border-color: var(--cyan) !important; box-shadow:0 0 0 1px var(--cyan) !important; }}
[data-testid="stExpander"] {{ background: var(--panel); border:1px solid var(--brass-dim) !important; border-radius:3px; }}
[data-testid="stExpander"] summary p {{ font-family:'Cinzel', Georgia, serif; font-size:.95rem; }}
[data-testid="stSlider"] [role="slider"] {{ background: var(--accent) !important; }}
[data-testid="stRadio"] label p, [data-testid="stToggle"] label p {{ font-size:1.05rem; }}

/* Shared pieces */
.frame {{ position:relative; border:1px solid var(--brass); padding:6px; background:rgba(0,0,0,.45);
  box-shadow: 0 30px 60px -20px rgba(0,0,0,.8), inset 0 0 0 1px rgba(0,0,0,.6); }}
.frame::after {{ content:""; position:absolute; inset:12px; border:1px solid rgba(184,147,90,.25); pointer-events:none; }}
.frame img {{ display:block; width:100% !important; max-width:none !important; height:auto; aspect-ratio:16/10; object-fit:cover; }}
.frame.tall img {{ aspect-ratio:4/3; }}
.panel {{ background:var(--panel); border:1px solid var(--brass-dim); padding:1.3rem 1.5rem; border-radius:3px; }}
.kicker {{ font-family:'Cinzel', serif; color:var(--brass); font-size:.86rem; letter-spacing:.14em; margin:0 0 .3rem; }}
.title-xl {{ font-family:'Cinzel', serif; font-weight:900; font-size:clamp(2.6rem,5.6vw,4.6rem); line-height:1.02; margin:0;
  color:#F4E6D2; text-shadow:0 2px 0 #3d1a3f, 0 0 40px color-mix(in srgb, var(--accent) 45%, transparent); }}
.title-md {{ font-family:'Cinzel', serif; font-weight:700; font-size:clamp(1.6rem,3vw,2.3rem); margin:.1rem 0 .6rem; color:var(--ink); }}
.lede {{ font-size:1.25rem; color:var(--muted); font-style:italic; max-width:38ch; }}
.muted {{ color:var(--muted); }}
.rule {{ height:1px; background:linear-gradient(90deg, transparent, var(--brass), transparent); margin:1.1rem 0; border:0; }}

/* HUD bars */
.meter {{ margin:.25rem 0 .8rem; }}
.meter .lbl {{ display:flex; justify-content:space-between; font-family:'Cinzel',serif; font-size:.8rem; letter-spacing:.08em; color:var(--muted); }}
.meter .track {{ height:8px; background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.08); margin-top:4px; }}
.meter .fill {{ height:100%; transition: width .5s ease; }}

/* Room scene */
.scene {{ position:relative; overflow:hidden; }}
.scene .vign {{ position:absolute; inset:6px; pointer-events:none;
  background: radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,.75) 100%); }}
.scene .threat {{ position:absolute; inset:6px; pointer-events:none; mix-blend-mode:multiply; transition:opacity .6s; }}
.scene .eyes {{ position:absolute; right:12%; top:38%; display:flex; gap:14px; pointer-events:none; }}
.scene .eyes i {{ width:10px; height:6px; border-radius:50%; background:#ff3049; box-shadow:0 0 14px 4px #ff2040; animation: blink 4s infinite; }}
.scene .cap {{ position:absolute; left:18px; bottom:16px; right:18px; font-family:'Cinzel',serif; color:#F4E6D2;
  text-shadow:0 2px 8px #000; font-size:1.05rem; letter-spacing:.06em; }}
.scene .flash {{ position:absolute; inset:0; background:#fffbe8; animation: flash .9s ease-out forwards; pointer-events:none; }}
@keyframes flash {{ from {{opacity:.95}} to {{opacity:0}} }}
@keyframes blink {{ 0%,92%,100% {{transform:scaleY(1)}} 95% {{transform:scaleY(.1)}} }}

/* Dialogue */
.dlg {{ display:flex; gap:1.2rem; align-items:flex-start; }}
.dlg .orb {{ flex:0 0 74px; height:74px; border-radius:50%; border:1px solid var(--cyan);
  background: radial-gradient(circle at 50% 40%, #A5F1FF 0, #3BA7C4 28%, #10304A 62%, #070F18 100%);
  box-shadow: 0 0 28px -4px var(--cyan); animation: hover 5s ease-in-out infinite; }}
.dlg.hollow .orb {{ border-color:var(--rose); background: radial-gradient(circle at 50% 40%, #FF9AAA 0, #A2283F 30%, #2A0812 70%, #080206 100%); box-shadow:0 0 28px -4px var(--rose); }}
.dlg .who {{ font-family:'Cinzel',serif; color:var(--cyan); letter-spacing:.1em; font-size:.92rem; margin-bottom:.35rem; }}
.dlg.hollow .who {{ color:#FF8A9C; }}
.dlg .line {{ font-size:1.32rem; line-height:1.55; }}
.dlg .line span {{ opacity:0; animation: word .35s ease forwards; }}
@keyframes word {{ to {{ opacity:1 }} }}
@keyframes hover {{ 0%,100% {{ transform:translateY(0) }} 50% {{ transform:translateY(-5px) }} }}

/* Cipher tiles */
.cipher {{ display:flex; flex-wrap:wrap; gap:.6rem 1.4rem; justify-content:center; margin:1rem 0 1.2rem; }}
.cipher .word {{ display:flex; gap:5px; }}
.cipher .ch {{ width:2.4rem; height:3rem; display:grid; place-items:center; font-family:'Cinzel',serif; font-weight:700; font-size:1.5rem;
  color:var(--cyan); border:1px solid rgba(107,225,255,.35); background:rgba(8,28,40,.55);
  text-shadow:0 0 12px rgba(107,225,255,.9); box-shadow: inset 0 0 12px rgba(107,225,255,.12); }}
.cipher.solved .ch {{ color:#9DF5BF; border-color:rgba(157,245,191,.4); text-shadow:0 0 12px rgba(157,245,191,.8); background:rgba(10,36,24,.55); }}
.wheel {{ display:flex; flex-wrap:wrap; gap:4px; font-family:'Cinzel',serif; }}
.wheel div {{ display:flex; flex-direction:column; width:1.75rem; text-align:center; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.06); }}
.wheel b {{ font-weight:600; padding:.12rem 0; font-size:.88rem; }}
.wheel .enc {{ color:#F2A9A9; border-bottom:1px solid rgba(255,255,255,.08); }} .wheel .dec {{ color:#A6F5BC; }}
.cipher.sm {{ gap:.4rem 1rem; justify-content:flex-start; margin:.8rem 0 .2rem; }}
.cipher.sm .ch {{ width:1.7rem; height:2.1rem; font-size:1.05rem; }}

/* Cards */
.card {{ border:1px solid var(--brass-dim); background:var(--panel); padding:0; overflow:hidden; height:100%; }}
.card img {{ width:100%; height:150px; object-fit:cover; display:block; filter:saturate(.85) brightness(.8); }}
.card .body {{ padding:.85rem 1rem 1rem; }}
.card h4 {{ margin:0 0 .25rem; font-size:1.05rem; }}
.card p {{ margin:0; color:var(--muted); font-size:1.02rem; line-height:1.4; }}
.done {{ color:#9DF5BF; }}
.badge {{ display:inline-block; font-family:'Cinzel',serif; font-size:.72rem; letter-spacing:.1em; padding:.15rem .5rem; border:1px solid; margin-left:.4rem; vertical-align:middle; }}

/* Mini games */
.sigils {{ display:flex; gap:.8rem; justify-content:center; margin:1rem 0; min-height:96px; }}
.sigils div {{ width:86px; height:86px; display:grid; place-items:center; font-family:'Cinzel',serif; font-weight:700;
  border:1px solid rgba(255,255,255,.2); opacity:0; animation: sig .62s ease forwards; }}
@keyframes sig {{ 0% {{opacity:0; transform:scale(.8)}} 25% {{opacity:1; transform:scale(1.06)}} 70% {{opacity:1}} 100% {{opacity:.12; transform:scale(1)}} }}
.candles {{ display:flex; justify-content:space-around; align-items:flex-end; height:150px; margin:.5rem 0 0; }}
.candle {{ width:34px; position:relative; background:linear-gradient(90deg,#d9cdb5,#f3ead8,#cbbd9f); border-radius:3px 3px 0 0; }}
.candle .fl {{ position:absolute; left:50%; top:-30px; width:16px; height:26px; margin-left:-8px; border-radius:50% 50% 50% 50%/60% 60% 40% 40%;
  background:radial-gradient(circle at 50% 70%, #fff6c8, #ffb547 50%, rgba(255,90,20,0) 72%); filter:blur(.4px);
  box-shadow:0 0 30px 10px rgba(255,170,60,.35); animation: flick 1.6s infinite alternate; }}
@keyframes flick {{ from {{ transform:scale(1) rotate(-2deg) }} to {{ transform:scale(1.08,.94) rotate(2deg) }} }}

/* Particles */
.fx {{ position:fixed; inset:0; pointer-events:none; z-index:0; overflow:hidden; }}
.fx span {{ position:absolute; top:-10px; border-radius:50%; background:var(--p); opacity:.0; animation: fall linear infinite; }}
.fx.wisp span {{ top:auto; bottom:-10px; animation-name: rise; box-shadow:0 0 10px 2px var(--p); }}
.fx.ember span {{ top:auto; bottom:-10px; animation-name: rise; border-radius:1px; }}
@keyframes fall {{ 0% {{ transform:translate(0,0); opacity:0 }} 10% {{opacity:.8}} 100% {{ transform:translate(40px,105vh); opacity:.2 }} }}
@keyframes rise {{ 0% {{ transform:translate(0,0); opacity:0 }} 15% {{opacity:.75}} 100% {{ transform:translate(-30px,-105vh); opacity:0 }} }}
.block-container > div {{ position:relative; z-index:1; }}

.st-key-flowers .stButton button {{ min-height:108px; font-size:1.1rem; background:
  radial-gradient(circle at 50% 40%, rgba(184,147,90,.18), transparent 60%), linear-gradient(180deg, rgba(60,34,58,.92), rgba(30,17,32,.95)); }}
.st-key-flowers .stButton button p {{ font-size:1.05rem !important; }}
.st-key-flowers .stButton button[kind="primary"] {{ background: linear-gradient(180deg, rgba(194,70,120,.55), rgba(70,20,50,.9)) !important; opacity:1; }}
.st-key-sigils .stButton button {{ min-height:96px; }}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation-duration:.01ms !important; animation-iteration-count:1 !important; transition:none !important; }}
  .dlg .line span, .sigils div {{ opacity:1 !important; }}
  .fx {{ display:none; }}
}}
@media (max-width: 760px) {{
  .block-container {{ padding: 1rem .9rem 2rem; }}
  .cipher .ch {{ width:1.7rem; height:2.3rem; font-size:1.1rem; }}
}}
</style>
"""
    # blank lines would end the HTML block in markdown, so drop them
    st.markdown("\n".join(l for l in css.splitlines() if l.strip()), unsafe_allow_html=True)


def particles():
    rnd = random.Random(7)
    spans = []
    for _ in range(38):
        size = rnd.randint(2, 5)
        spans.append(f'<span style="left:{rnd.random()*100:.1f}%;width:{size}px;height:{size}px;'
                     f'animation-duration:{rnd.uniform(11, 26):.1f}s;animation-delay:-{rnd.uniform(0, 24):.1f}s"></span>')
    st.markdown(f'<div class="fx {THEME["fx"]}" style="--p:{THEME["particle"]}">{"".join(spans)}</div>',
                unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Small render helpers
# ----------------------------------------------------------------------------
def md(markup):
    st.markdown(markup, unsafe_allow_html=True)


def esc(t):
    return html.escape(str(t))


def meter(label, value, color, right=None):
    value = max(0, min(100, int(value)))
    return (f'<div class="meter"><div class="lbl"><span>{label}</span><span>{right or value}</span></div>'
       f'<div class="track"><div class="fill" style="width:{value}%;background:{color}"></div></div></div>')


def cipher_tiles(textval, solved=False, small=False):
    words = "".join(
        '<div class="word">' + "".join(f'<div class="ch">{esc(c)}</div>' for c in w) + "</div>"
        for w in textval.split())
    return f'<div class="cipher{" solved" if solved else ""}{" sm" if small else ""}">{words}</div>'


def cipher_wheel():
    tiles = "".join(
        f'<div><b class="enc">{chr(65 + (i + 2) % 26)}</b><b class="dec">{chr(65 + i)}</b></div>' for i in range(26))
    md('<p class="muted" style="margin:0 0 .5rem;font-size:1rem">Top row is the letter carved on the seal, '
       'bottom row is what it really says.</p>'
       f'<div class="wheel">{tiles}</div>')


def typed(textval):
    words = esc(textval).split(" ")
    spans = " ".join(f'<span style="animation-delay:{i*0.045:.2f}s">{w}</span>' for i, w in enumerate(words))
    return f'<div class="line">{spans}</div>'


def hero_svg(kind, cloak, size=220):
    k = kind % 4
    if k == 0:
        body = f'<polygon points="32,195 52,105 75,90 125,90 148,105 168,195" fill="{cloak}"/>' \
               '<ellipse cx="100" cy="69" rx="25" ry="31" fill="#D6AA8B"/>' \
               '<path d="M72 70 Q72 30 100 30 Q128 30 128 70" fill="none" stroke="#1E1223" stroke-width="10"/>'
    elif k == 1:
        body = f'<polygon points="25,195 60,92 140,92 175,195" fill="{cloak}"/>' \
               '<ellipse cx="100" cy="70" rx="22" ry="27" fill="#D6B8A6"/>' \
               '<polygon points="58,55 100,-8 142,55" fill="#28193E"/>'
    elif k == 2:
        body = f'<polygon points="35,195 45,96 155,96 165,195" fill="{cloak}"/>' \
               '<rect x="69" y="35" width="62" height="64" rx="9" fill="#96A0B4"/>' \
               '<rect x="78" y="55" width="44" height="9" rx="3" fill="#374155"/>' \
               '<polygon points="70,35 80,12 100,28 120,12 130,35" fill="#BEC3D2"/>'
    else:
        body = f'<polygon points="25,195 45,75 70,50 130,50 155,75 175,195 135,175 100,198 65,175" fill="{cloak}"/>' \
               '<ellipse cx="100" cy="62" rx="28" ry="34" fill="#C3DCEB"/>' \
               '<ellipse cx="86" cy="58" rx="6" ry="4" fill="#191E37"/><ellipse cx="114" cy="58" rx="6" ry="4" fill="#191E37"/>'
    return (f'<svg viewBox="0 -10 200 220" width="{size}" height="{size}" role="img" aria-label="{HEROES[k]}">'
            '<defs><radialGradient id="g" cx="50%" cy="45%"><stop offset="0" stop-color="#6BE1FF" stop-opacity=".22"/>'
            '<stop offset="1" stop-color="#6BE1FF" stop-opacity="0"/></radialGradient></defs>'
            '<circle cx="100" cy="110" r="100" fill="url(#g)"/>'
            '<ellipse cx="100" cy="200" rx="80" ry="10" fill="#000" opacity=".55"/>' + body + "</svg>")


def back_button(label="Back", target=None, key=None):
    st.button(label, key=key or f"back_{S.screen}", on_click=go, args=(target or S.return_to,))


# ----------------------------------------------------------------------------
# Game actions (callbacks)
# ----------------------------------------------------------------------------
def diff():
    return DIFFICULTY[S.settings["difficulty"]]


def advance_hollow(extra=0):
    S.hollow = min(100, S.hollow + diff()["step"] + extra)
    S.oil = min(100, S.oil + 6)
    if S.hollow >= 100:
        S.health = max(0, S.health - diff()["hit"])
        S.hollow = 40
        if S.health <= 0:
            persist_save()
            go("failure")
            return
        say("The Hollow's cold hands close around you, then let go. It wants you to keep looking. For now.")
    persist_save()


def new_game():
    reset_run(0)
    persist_save()
    start_dialogue("intro")
    go("play")


def continue_game():
    save = load_json(SAVE_FILE, DEFAULT_SAVE)
    lvl = max(0, min(int(save.get("level", 0)), len(LEVELS) - 1))
    clues = {int(c) for c in save.get("clues", []) if str(c).isdigit()}
    reset_run(lvl, clues, max(1, min(100, int(save.get("health", 100)))))
    S.quest_flags = set(save.get("quest_flags", [])) | S.quest_flags
    say(f"You return to {LEVELS[lvl]['name']}. Nothing has moved. Everything has changed.")
    go("play")


def start_dialogue(kind):
    lev = LEVELS[S.level]
    if kind == "intro":
        S.dialogue = {"who": lev["speaker"], "lines": [lev["intro"]] + lev["opening"],
                      "choices": lev["choices"], "i": 0}
    else:
        who, lines, choices = DIALOGUES[kind]
        S.dialogue = {"who": who, "lines": lines, "choices": choices, "i": 0}


def talk():
    start_dialogue("flower_story" if "flower_memory" in S.quest_flags and S.level == 0 else "intro")
    advance_hollow(-4)


def dialogue_next():
    S.dialogue["i"] = min(S.dialogue["i"] + 1, len(S.dialogue["lines"]) - 1)


def dialogue_choose(action):
    if action == "close":
        S.dialogue = None
        say("The words linger in the cold air.")
    else:
        start_dialogue(action)


def search_room():
    lev = LEVELS[S.level]
    remaining = [i for i in range(len(lev["search"])) if i not in S.searched]
    if not remaining:
        say("You have searched every corner. The manor has nothing more to show you here.")
    else:
        i = remaining[0]
        S.searched.add(i)
        say(lev["search"][i])
    advance_hollow()


def lantern_flash():
    if S.oil < 30:
        say("The lantern sputters. Not enough oil for a flash yet.")
        return
    S.oil -= 35
    S.hollow = max(0, S.hollow - 45)
    S.flash = True
    say("White light floods the room. Somewhere in the dark, the Hollow shrieks and retreats.")
    persist_save()


def open_seal():
    S.feedback = ""
    S.hint_shown = False
    S["answer_box"] = ""
    go("puzzle")


def submit_answer():
    raw = S.get("answer_box", "")
    guess = "".join(c for c in raw.upper() if c.isalpha())
    expected = "".join(c for c in LEVELS[S.level]["answer"] if c.isalpha())
    if not guess:
        S.feedback = "Type the decoded sentence first."
        return
    if guess == expected:
        S.clues.add(S.level)
        S.feedback = ""
        persist_save()
        if len(S.clues) == len(LEVELS) and S.level == len(LEVELS) - 1:
            win()
        else:
            go("level_complete")
        return
    d = diff()
    if S.settings["difficulty"] == "Nightmare":
        reset_run(0)
        persist_save()
        say("A wrong answer. The manor folds in on itself and you wake again in the foyer.")
        go("play")
        return
    S.health = max(0, S.health - d["wrong"])
    S.hollow = min(100, S.hollow + 15)
    persist_save()
    if S.health <= 0:
        go("failure")
        return
    S.feedback = f"The seal rejects you. You lose {d['wrong']} health and hear something move closer."


def moon_door():
    if S.level not in S.clues:
        say("The Moon Door will not open. Its seal is still unbroken.")
        advance_hollow()
        return
    if S.level < len(LEVELS) - 1:
        next_chapter()
    else:
        win()


def next_chapter():
    lvl = S.level + 1
    clues = S.clues
    reset_run(lvl, clues, 100)
    persist_save()
    start_dialogue("intro")
    go("play")


def win():
    S.won = True
    persist_save(won=True)
    go("victory")


def set_setting(key, value):
    S.settings[key] = value
    persist_settings()


# Mini games -------------------------------------------------------------------
def start_minigame(name):
    mg = {"name": name, "feedback": ""}
    if name == "Flower Memory":
        deck = ["Rose", "Lily", "Iris", "Violet", "Daisy", "Lotus"] * 2
        random.shuffle(deck)
        mg.update(cards=deck, revealed=[], matched=set(), moves=0)
    elif name == "Ghost Signal":
        mg.update(sequence=[random.randrange(4)], player=[], phase="show", round=0)
    elif name == "Candle Order":
        mg.update(lit=[])
    S.minigame = mg
    go("minigame")


def flower_click(i):
    mg = S.minigame
    if i in mg["matched"] or i in mg["revealed"]:
        return
    if len(mg["revealed"]) == 2:
        mg["revealed"] = []
    mg["revealed"].append(i)
    if len(mg["revealed"]) == 2:
        mg["moves"] += 1
        a, b = mg["revealed"]
        if mg["cards"][a] == mg["cards"][b]:
            mg["matched"].update((a, b))
            mg["revealed"] = []
            mg["feedback"] = f"A {mg['cards'][a].lower()} blooms. One memory returns."
            if len(mg["matched"]) == 12:
                S.quest_flags.add("flower_memory")
                persist_save()
                mg["feedback"] = "Memory restored. The Witness remembers the garden."
        else:
            mg["feedback"] = "Not a pair. Keep their positions in mind."


def signal_ready():
    S.minigame["phase"] = "input"
    S.minigame["player"] = []


def signal_click(i):
    mg = S.minigame
    mg["player"].append(i)
    pos = len(mg["player"]) - 1
    if mg["player"][pos] != mg["sequence"][pos]:
        mg["feedback"] = "The signal broke. Watch the sequence again."
        mg["player"], mg["phase"] = [], "show"
        mg["round"] += 1
    elif len(mg["player"]) == len(mg["sequence"]):
        if len(mg["sequence"]) >= 5:
            mg["feedback"] = "Signal restored. A hidden melody returns."
            mg["phase"] = "done"
            S.quest_flags.add("ghost_signal")
            persist_save()
        else:
            mg["sequence"].append(random.randrange(4))
            mg["feedback"] = "Correct. The ghost adds another note."
            mg["phase"] = "show"
            mg["round"] += 1


def candle_click(i):
    mg = S.minigame
    if i == len(mg["lit"]):
        mg["lit"].append(i)
        mg["feedback"] = ""
        if len(mg["lit"]) == 5:
            mg["feedback"] = "The passage opens. The candle task is complete."
            S.quest_flags.add("candle_order")
            persist_save()
    else:
        mg["lit"] = []
        mg["feedback"] = "A candle gutters out. Read the rhyme and try again."


def read_story(i):
    S.story_idx, S.story_page = i, 0
    go("story")


def set_theme(name):
    set_setting("active_theme", name)


# ----------------------------------------------------------------------------
# Screens
# ----------------------------------------------------------------------------
def top_bar(in_game=True):
    items = []
    if in_game:
        items.append(("Journal", "nav_j", ("journal", True)))
    if S.screen != "hub":
        items.append(("Side stories", "nav_h", ("hub", S.screen not in HUB_FAMILY)))
    items.append(("Settings", "nav_s", ("settings", True)))
    if S.screen != "explore":
        items.append(("3D mode", "nav_3d", ("explore", True)))
    items.append(("Main menu", "nav_m", ("title",)))
    c = st.columns([2.6] + [1] * 5, vertical_alignment="center")
    with c[0]:
        md('<div style="font-family:Cinzel,serif;font-weight:700;letter-spacing:.12em;font-size:1.05rem;color:var(--brass)">'
           'Cryptic Escape <span class="muted" style="font-weight:500">· The Cursed Manor</span></div>')
    for col, (label, key, args) in zip(c[6 - len(items):], items):
        col.button(label, key=key, width="stretch", on_click=go, args=args)
    md('<hr class="rule" style="margin-top:.6rem">')


def screen_title():
    left, right = st.columns([1, 1.25], gap="large", vertical_alignment="center")
    with left:
        md('<div style="height:2vh"></div>')
        md('<p class="kicker">A gothic cipher mystery in three chapters</p>')
        md('<h1 class="title-xl">Cryptic<br>Escape</h1>')
        md('<p class="title-md" style="color:#D9AACA;font-weight:500;margin-top:.4rem">The Cursed Manor</p>')
        md(f'<p class="lede">{esc(THEME["subtitle"])} Break three seals, hear the dead out, and decide what this house is allowed to forget.</p>')
        md('<div style="height:.6rem"></div>')
        b1, b2 = st.columns(2)
        b1.button("New game", type="primary", width="stretch", on_click=new_game)
        b2.button("Continue", width="stretch", disabled=not S.has_save, on_click=continue_game,
                  help=None if S.has_save else "No saved journey yet")
        b3, b4 = st.columns(2)
        b3.button("Side stories", width="stretch", on_click=go, args=("hub", True))
        b4.button("Choose hero", width="stretch", on_click=go, args=("character", True))
        b5, b6 = st.columns(2)
        b5.button("Settings", width="stretch", on_click=go, args=("settings", True))
        b6.button("How to play", width="stretch", on_click=go, args=("howto", True))
        st.button("Explore the manor in 3D", type="primary", width="stretch", on_click=go, args=("explore", True))
    with right:
        md(f'<div class="frame scene"><img src="{img_b64("candle.png")}" alt="A candlelit dining hall laid for guests who never arrived">'
           '<div class="vign"></div><div class="cap">The banquet hall, laid for a family that died in 1897</div></div>')
        d = S.settings["difficulty"]
        md(f'<p class="muted" style="text-align:right;margin-top:.7rem;font-size:1rem">'
           f'Playing as {esc(HEROES[S.settings["character_type"] % 4])} on {esc(d)} · {esc(S.settings["active_theme"])} theme</p>')


def render_dialogue():
    dlg = S.dialogue
    i = dlg["i"]
    hollow = "hollow" if dlg["who"] == "The Hollow" else ""
    with st.container(border=False):
        md(f'<div class="panel" style="border-color:{"rgba(194,70,95,.5)" if hollow else "rgba(107,225,255,.35)"}">'
           f'<div class="dlg {hollow}"><div class="orb"></div><div><div class="who">{esc(dlg["who"])}'
           f'<span class="muted" style="font-size:.78rem;margin-left:.6rem">{i+1} of {len(dlg["lines"])}</span></div>'
           f'{typed(dlg["lines"][i])}</div></div></div>')
        md('<div style="height:.5rem"></div>')
        if i < len(dlg["lines"]) - 1:
            a, b = st.columns([1, 1])
            a.button("Continue", key=f"dlg_next_{i}", type="primary", width="stretch", on_click=dialogue_next)
            b.button("Skip to choices", key=f"dlg_skip_{i}", width="stretch",
                     on_click=lambda: S.dialogue.update(i=len(S.dialogue["lines"]) - 1))
        else:
            for label, action in dlg["choices"]:
                st.button(label, key=f"dlg_{action}_{label}", width="stretch", on_click=dialogue_choose, args=(action,))


def screen_play():
    top_bar()
    lev = LEVELS[S.level]
    solved = S.level in S.clues
    scene, side = st.columns([1.7, 1], gap="large")
    with scene:
        md(f'<p class="kicker">Chapter {S.level + 1} of {len(LEVELS)}</p><h2 class="title-md" style="margin-top:0">{esc(lev["name"])}</h2>')
        threat = max(0, (S.hollow - 45) / 55)
        eyes = '<div class="eyes"><i></i><i></i></div>' if S.hollow >= 70 else ""
        flash = '<div class="flash"></div>' if S.flash else ""
        S.flash = False
        md(f'<div class="frame scene"><img src="{img_b64(lev["image"])}" alt="{esc(lev["name"])}">'
           f'<div class="vign"></div><div class="threat" style="opacity:{threat:.2f};background:radial-gradient(ellipse at 80% 45%, #7a0a1e, transparent 70%)"></div>'
           f'{eyes}{flash}<div class="cap">{"The seal glows green. The Moon Door hums." if solved else "A cyan sigil pulses on the far wall."}</div></div>')
        md('<div style="height:.9rem"></div>')
        entries = "".join(
            f'<p style="margin:.15rem 0;{"" if n == 0 else "opacity:.55;font-size:1rem"}">{esc(m)}</p>'
            for n, m in enumerate(S.log[:3]))
        md(f'<div class="panel"><p class="kicker" style="margin-bottom:.4rem">What you notice</p>{entries}</div>')

    with side:
        hud = meter("Health", S.health, "linear-gradient(90deg,#7E2034,#C2465F)")
        hud += meter("Lantern oil", S.oil, "linear-gradient(90deg,#9A5A1E,#E8A050)")
        hc = "#6BE1FF" if S.hollow < 45 else ("#E8A050" if S.hollow < 75 else "#FF3B55")
        state = "distant" if S.hollow < 45 else ("stirring" if S.hollow < 75 else "very close")
        hud += meter("The Hollow", S.hollow, hc, right=state)
        seals = "".join(
            f'<span title="{esc(l["name"])}" style="display:inline-block;width:26px;height:26px;margin-right:6px;border-radius:50%;'
            f'border:1px solid {"#9DF5BF" if i in S.clues else ("var(--cyan)" if i == S.level else "rgba(255,255,255,.2)")};'
            f'background:{"rgba(157,245,191,.25)" if i in S.clues else "transparent"}"></span>'
            for i, l in enumerate(LEVELS))
        md(f'<div class="panel">{hud}<div style="font-family:Cinzel,serif;font-size:.8rem;letter-spacing:.08em;'
           f'color:var(--muted);margin-bottom:.35rem">Seals broken</div>{seals}</div>')
        md('<div style="height:.8rem"></div>')
        if S.dialogue:
            render_dialogue()
            return
        busy = False
        st.button(f"Speak with {lev['speaker'].lower()}", width="stretch", disabled=busy, on_click=talk)
        st.button("Seal already broken" if solved else "Examine the cyan seal", type="primary" if not solved else "secondary",
                  width="stretch", disabled=busy or solved, on_click=open_seal)
        last = S.level == len(LEVELS) - 1
        st.button("Walk through to freedom" if (solved and last) else "Open the Moon Door",
                  type="primary" if solved else "secondary", width="stretch", disabled=busy, on_click=moon_door)
        st.button("Search the room", width="stretch", disabled=busy, on_click=search_room)
        st.button(f"Lantern flash · {S.oil}% oil", width="stretch", disabled=busy or S.oil < 30, on_click=lantern_flash)
        md(f'<p class="muted" style="font-size:.95rem;margin-top:.6rem">Every action draws the Hollow nearer. '
           f'A lantern flash drives it back but burns oil, which slowly refills as you explore.</p>')


def screen_puzzle():
    top_bar()
    lev = LEVELS[S.level]
    _, mid, _ = st.columns([.12, 1, .12])
    with mid:
        md(f'<div style="text-align:center"><p class="kicker">Seal {S.level + 1} · {esc(lev["name"])}</p>'
           '<h2 class="title-md">The Witness\'s cipher</h2>'
           '<p class="muted" style="margin:0 auto;max-width:52ch">Each letter on the seal has been pushed two places forward in the alphabet. '
           'Walk every letter two steps back to read the message.</p></div>')
        md(cipher_tiles(lev["cipher"]))
        with st.form("seal_form", clear_on_submit=False, border=False):
            st.text_input("Your decoded sentence", key="answer_box", placeholder="Type the sentence you read on the seal",
                          label_visibility="collapsed")
            a, b, c = st.columns([1.3, 1, 1])
            a.form_submit_button("Break the seal", type="primary", width="stretch", on_click=submit_answer)
            b.form_submit_button("Show hint", width="stretch", on_click=lambda: S.__setitem__("hint_shown", True))
            c.form_submit_button("Step away", width="stretch", on_click=go, args=("play",))
        if S.feedback:
            md(f'<p style="text-align:center;color:#FF9AAA;margin-top:.6rem">{esc(S.feedback)}</p>')
        if S.hint_shown:
            md(f'<p style="text-align:center;color:var(--ember)">{esc(lev["hint"])} The first word, {esc(lev["cipher"].split()[0])}, '
               f'reads as {esc(lev["answer"].split()[0])}.</p>')
        with st.expander("Open the cipher wheel"):
            cipher_wheel()
        cost = ("On Nightmare a wrong answer returns you to the first seal." if S.settings["difficulty"] == "Nightmare"
                else f"A wrong answer costs {diff()['wrong']} health.")
        md(f'<p class="muted" style="text-align:center;font-size:.95rem;margin-top:.8rem">Health {S.health}. {cost}</p>')


def screen_journal():
    top_bar()
    md('<h2 class="title-md">Manor journal</h2>')
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        for i, lev in enumerate(LEVELS):
            solved = i in S.clues
            active = i == S.level and not solved
            status, color = (("Broken", "#9DF5BF") if solved else (("Active", "#E8A050") if active else ("Sealed", "#8D7F96")))
            inner = (cipher_tiles(lev["answer"] if solved else lev["cipher"], solved=solved, small=True) if (solved or active) else
                     '<p class="muted" style="margin:.4rem 0 0">This page is still blank. Break the earlier seals to fill it in.</p>')
            md(f'<div class="panel" style="margin-bottom:.8rem"><h4 style="margin:0">Seal {i+1}: {esc(lev["name"])}'
               f'<span class="badge" style="color:{color};border-color:{color}">{status}</span></h4>{inner}</div>')
    with right:
        if S.level not in S.clues:
            obj = f'Decode the cyan seal in {esc(LEVELS[S.level]["name"])}.'
        elif S.level < len(LEVELS) - 1:
            obj = 'The seal is broken. Open the Moon Door to go deeper.'
        else:
            obj = 'Every seal is broken. Walk through the Moon Door.'
        flower = "flower_memory" in S.quest_flags
        md(f'<div class="panel"><p class="kicker">Current objective</p><p>{obj}</p>'
           f'<p class="kicker" style="margin-top:1rem">Flower memory</p><p class="{"done" if flower else "muted"}">'
           f'{"Restored. The Witness will remember more at the end." if flower else "Not yet restored. Find it among the side stories."}</p>'
           '<p class="kicker" style="margin-top:1rem">Survival notes</p>'
           '<p class="muted" style="font-size:1.02rem">Speaking with spirits barely stirs the Hollow. Searching and forcing doors draws it fast. '
           'Save your lantern flash for when its eyes appear.</p></div>')
        md('<div style="height:.8rem"></div>')
        with st.expander("Cipher wheel", expanded=True):
            cipher_wheel()
        back_button("Close journal", key="close_journal")


def screen_level_complete():
    lev = LEVELS[S.level]
    _, mid, _ = st.columns([.2, 1, .2])
    with mid:
        md(f'<div style="text-align:center;margin-top:5vh"><p class="kicker">Seal {S.level+1} broken</p>'
           f'<h1 class="title-xl" style="font-size:clamp(2rem,4.5vw,3.4rem)">The seal gives way</h1></div>')
        md(cipher_tiles(lev["answer"], solved=True))
        md(f'<p class="lede" style="margin:0 auto 1.4rem;text-align:center">The words burn green for a moment, then sink into the stone. '
           f'Beyond the Moon Door, {esc(LEVELS[S.level+1]["name"])} is waiting.</p>')
        a, b = st.columns(2)
        a.button("Continue to the next chapter", type="primary", width="stretch", on_click=next_chapter)
        b.button("Return to the room", width="stretch", on_click=go, args=("play",))


def screen_ending(victory=True):
    if victory:
        complete = "flower_memory" in S.quest_flags
        title, body = ENDING_COMPLETE if complete else ENDING_PARTIAL
        image = "drawingroom.png" if complete else "room.png"
    else:
        title, body, image = ("The manor claims you",
                              "Your lantern gutters out and the Hollow's hands close for the last time. "
                              "The house adds your name to the ledger, then carefully scratches it away. Try another path.",
                              "passage.png")
    a, b = st.columns([1.1, 1], gap="large", vertical_alignment="center")
    with a:
        md(f'<div class="frame scene"><img src="{img_b64(image)}" alt=""><div class="vign"></div></div>')
    with b:
        md(f'<p class="kicker">{"Ending" if victory else "Game over"}</p><h1 class="title-xl" style="font-size:clamp(2.2rem,4.6vw,3.6rem)">{esc(title)}</h1>')
        md(f'<p class="lede" style="max-width:44ch">{esc(body)}</p>')
        if victory and "flower_memory" not in S.quest_flags:
            md('<p class="muted">There is a fuller ending. Restore the flower memory in the side stories and break the seals again.</p>')
        c1, c2 = st.columns(2)
        c1.button("Play again", type="primary", width="stretch", on_click=new_game)
        c2.button("Main menu", width="stretch", on_click=go, args=("title",))


HUB_CARDS = [
    ("Flower Memory", "Match six pairs and restore a memory of the kindest soul.", "drawingroom.png", "flower_memory"),
    ("Ghost Signal", "Watch the ghost's growing sequence of sigils, then repeat it.", "painting.png", "ghost_signal"),
    ("Candle Order", "Light five candles in the order hidden in the nursery rhyme.", "candle.png", "candle_order"),
]


def screen_hub():
    top_bar(in_game=False)
    md('<h2 class="title-md">The manor\'s side stories</h2><p class="muted" style="margin-top:-.4rem">'
       'Small rooms off the main hall. Completing them changes how the story ends.</p>')
    cols = st.columns(3, gap="medium")
    for col, (name, desc, image, flag) in zip(cols, HUB_CARDS):
        with col:
            done = flag in S.quest_flags
            md(f'<div class="card"><img src="{img_b64(image, 600)}" alt=""><div class="body"><h4>{esc(name)}'
               f'{" <span class=done>✓</span>" if done else ""}</h4><p>{esc(desc)}</p></div></div>')
            st.button("Play again" if done else "Play", key=f"hub_{name}", width="stretch", on_click=start_minigame, args=(name,))
    md('<div style="height:1rem"></div>')
    c = st.columns(3, gap="medium")
    c[0].button("Quest board", width="stretch", on_click=go, args=("quests",))
    c[1].button("Lost chapters", width="stretch", on_click=go, args=("stories",))
    c[2].button("Seasonal themes", width="stretch", on_click=go, args=("themes",))
    md('<div style="height:.6rem"></div>')
    back_button("Back", target=S.get("hub_return", "title"), key="hub_back")


def screen_minigame():
    top_bar(in_game=False)
    mg = S.minigame
    name = mg["name"]
    md(f'<h2 class="title-md" style="text-align:center">{esc(name)}</h2>')
    _, mid, _ = st.columns([.15, 1, .15])
    with mid:
        if name == "Flower Memory":
            md('<p class="muted" style="text-align:center">Turn two cards at a time. A match restores one memory.</p>')
            grid = st.container(key="flowers")
            for row in range(2):
                cols = grid.columns(6, gap="small")
                for c in range(6):
                    i = row * 6 + c
                    shown = i in mg["matched"] or i in mg["revealed"]
                    label = mg["cards"][i] if shown else "✦"
                    cols[c].button(label, key=f"fl_{i}", width="stretch",
                                   type="primary" if i in mg["matched"] else "secondary",
                                   disabled=i in mg["matched"], on_click=flower_click, args=(i,))
            md(f'<p style="text-align:center;margin-top:.8rem">{esc(mg["feedback"] or "")}</p>'
               f'<p class="muted" style="text-align:center">Pairs {len(mg["matched"])//2} of 6 · Turns {mg["moves"]}</p>')
        elif name == "Ghost Signal":
            labels = ["Rose", "Moon", "Flame", "Eye"]
            colors = ["#CA5B87", "#6DB9D5", "#D0B168", "#9C76D3"]
            if mg["phase"] == "show":
                md('<p class="muted" style="text-align:center">Memorise the order the sigils light up.</p>')
                tiles = "".join(
                    f'<div style="background:{colors[s]};color:#140a14;animation-delay:{k*0.7:.1f}s">{labels[s]}</div>'
                    for k, s in enumerate(mg["sequence"]))
                md(f'<div class="sigils" key="{mg["round"]}">{tiles}</div>')
                st.button("I have it, let me repeat", type="primary", width="stretch", on_click=signal_ready)
            else:
                md(f'<p class="muted" style="text-align:center">Repeat the sequence. {len(mg["player"])} of {len(mg["sequence"])} entered.</p>')
                cols = st.container(key="sigils").columns(4)
                for i, col in enumerate(cols):
                    col.button(labels[i], key=f"sg_{i}", width="stretch", disabled=mg["phase"] == "done",
                               on_click=signal_click, args=(i,))
            md(f'<p style="text-align:center;margin-top:.8rem">{esc(mg["feedback"])}</p>'
               f'<p class="muted" style="text-align:center">Sequence length {len(mg["sequence"])} of 5</p>')
        elif name == "Candle Order":
            labels = ["Flame", "Rose", "Star", "Moon", "Thorn"]
            heights = [96, 120, 84, 132, 108]
            md('<p class="lede" style="text-align:center;margin:0 auto">"First the flame, then the rose, the star, the moon, and last the thorn."</p>')
            candles = "".join(
                f'<div class="candle" style="height:{h}px">{"<div class=fl></div>" if i in mg["lit"] else ""}</div>'
                for i, h in enumerate(heights))
            md(f'<div class="candles" style="margin-top:2.2rem">{candles}</div>')
            cols = st.columns(5)
            for i, col in enumerate(cols):
                col.button(labels[i], key=f"cd_{i}", width="stretch", disabled=i in mg["lit"],
                           on_click=candle_click, args=(i,))
            md(f'<p style="text-align:center;margin-top:.8rem">{esc(mg["feedback"])}</p>'
               f'<p class="muted" style="text-align:center">Candles lit {len(mg["lit"])} of 5</p>')
        md('<div style="height:.6rem"></div>')
        a, b = st.columns(2)
        a.button("Restart", width="stretch", on_click=start_minigame, args=(name,))
        b.button("Back to side stories", width="stretch", on_click=go, args=("hub",))


def screen_quests():
    top_bar(in_game=False)
    md('<h2 class="title-md">Quest board</h2>')
    for kind, title, desc, flag in QUESTS:
        done = len(S.clues) == len(LEVELS) or S.won if flag == "seals" else flag in S.quest_flags
        tag = "Main" if kind == "main" else "Optional"
        md(f'<div class="panel" style="margin-bottom:.6rem;display:flex;gap:1rem;align-items:center">'
           f'<div style="font-size:1.4rem;width:1.6rem;color:{"#9DF5BF" if done else "var(--brass)"}">{"✓" if done else "◇"}</div>'
           f'<div><h4 style="margin:0">{esc(title)}<span class="badge" style="color:var(--muted);border-color:var(--brass-dim)">{tag}</span></h4>'
           f'<p class="muted" style="margin:0">{esc(desc)}</p></div></div>')
    back_button("Back to side stories", target="hub", key="q_back")


def screen_stories():
    top_bar(in_game=False)
    md('<h2 class="title-md">The manor\'s lost chapters</h2><p class="muted" style="margin-top:-.4rem">Choose a memory. Every story changes how the house feels.</p>')
    cols = st.columns(4, gap="medium")
    for i, (col, (title, image, pages)) in enumerate(zip(cols, STORIES)):
        with col:
            md(f'<div class="card"><img src="{img_b64(image, 600)}" alt=""><div class="body"><h4>{esc(title)}</h4>'
               f'<p>{esc(pages[0][:88])}…</p></div></div>')
            st.button("Read", key=f"st_{i}", width="stretch", on_click=read_story, args=(i,))
    md('<div style="height:.6rem"></div>')
    back_button("Back to side stories", target="hub", key="s_back")


def screen_story():
    title, image, pages = STORIES[S.story_idx]
    p = S.story_page
    a, b = st.columns([1, 1.1], gap="large", vertical_alignment="center")
    with a:
        md(f'<div class="frame scene"><img src="{img_b64(image)}" alt=""><div class="vign"></div></div>')
    with b:
        md(f'<p class="kicker">Page {p+1} of {len(pages)}</p><h2 class="title-md">{esc(title)}</h2>')
        md(f'<div class="dlg" style="min-height:9rem">{typed(pages[p])}</div>')
        c1, c2, c3 = st.columns(3)
        c1.button("Previous page", width="stretch", disabled=p == 0,
                  on_click=lambda: S.__setitem__("story_page", S.story_page - 1))
        c2.button("Next page", type="primary", width="stretch", disabled=p == len(pages) - 1,
                  on_click=lambda: S.__setitem__("story_page", S.story_page + 1))
        c3.button("All chapters", width="stretch", on_click=go, args=("stories",))


def screen_themes():
    top_bar(in_game=False)
    md('<h2 class="title-md">Seasonal realms</h2><p class="muted" style="margin-top:-.4rem">Pick a visual mood for the manor. It changes the accent light and the drifting particles.</p>')
    cols = st.columns(5, gap="small")
    for col, (name, th) in zip(cols, SEASON_THEMES.items()):
        with col:
            active = name == S.settings["active_theme"]
            md(f'<div class="panel" style="text-align:center;border-color:{th["accent"] if active else "var(--brass-dim)"};min-height:205px">'
               f'<div style="width:64px;height:64px;margin:.2rem auto .7rem;border-radius:50%;'
               f'background:radial-gradient(circle at 40% 35%, {th["particle"]}, {th["accent"]} 45%, #12060f 100%);'
               f'box-shadow:0 0 26px -2px {th["accent"]}"></div><h4 style="margin:0 0 .3rem;font-size:.98rem">{esc(name)}</h4>'
               f'<p class="muted" style="font-size:.98rem;line-height:1.35;margin:0">{esc(th["info"])}</p></div>')
            st.button("Active" if active else "Use this", key=f"th_{name}", width="stretch", disabled=active,
                      on_click=set_theme, args=(name,))
    md('<div style="height:.6rem"></div>')
    back_button("Back to side stories", target="hub", key="t_back")


def screen_character():
    md('<h2 class="title-md" style="text-align:center">Choose your hero</h2>')
    _, mid, _ = st.columns([.25, 1, .25])
    with mid:
        k = S.settings["character_type"] % 4
        cloak = CLOAKS[S.settings["character_color"] % len(CLOAKS)]
        md(f'<div class="panel" style="text-align:center">{hero_svg(k, cloak, 240)}'
           f'<h3 style="margin:.4rem 0 0">{esc(HEROES[k])}</h3>'
           f'<p class="muted" style="margin:0">{esc(CLOAK_NAMES[S.settings["character_color"] % len(CLOAKS)])} cloak</p></div>')
        md('<div style="height:.6rem"></div>')
        a, b = st.columns(2)
        a.button("Previous hero", width="stretch", on_click=set_setting, args=("character_type", (k - 1) % 4))
        b.button("Next hero", width="stretch", on_click=set_setting, args=("character_type", (k + 1) % 4))
        md('<p class="kicker" style="text-align:center;margin-top:1rem">Cloak colour</p>')
        cc = st.columns(len(CLOAKS))
        for i, col in enumerate(cc):
            col.button(CLOAK_NAMES[i], key=f"cl_{i}", width="stretch",
                       type="primary" if i == S.settings["character_color"] % len(CLOAKS) else "secondary",
                       on_click=set_setting, args=("character_color", i))
        md('<div style="height:.6rem"></div>')
        back_button("Save and go back", key="char_back")


def screen_settings():
    md('<h2 class="title-md" style="text-align:center">Settings</h2>')
    _, mid, _ = st.columns([.22, 1, .22])
    with mid:
        md('<p class="kicker">Difficulty</p>')
        cols = st.columns(3)
        for col, name in zip(cols, DIFFICULTY):
            col.button(name, key=f"d_{name}", width="stretch",
                       type="primary" if S.settings["difficulty"] == name else "secondary",
                       on_click=set_setting, args=("difficulty", name))
        md(f'<p class="muted" style="margin-top:.3rem">{esc(diff()["desc"])}</p><hr class="rule">')
        md('<p class="kicker">Appearance</p>')
        dm = st.toggle("Dark manor (turn off for a parchment light mode)", value=S.settings.get("dark_mode", True))
        if dm != S.settings.get("dark_mode", True):
            set_setting("dark_mode", dm)
            st.rerun()
        md('<hr class="rule"><p class="kicker">Pygame edition</p><p class="muted" style="margin-top:0">'
           'These are shared with main.py and take effect when you launch the 3D version.</p>')
        for label, key in (("Master volume", "master_volume"), ("Music volume", "music_volume"), ("Sound effects", "sfx_volume")):
            v = st.slider(label, 0, 100, int(S.settings.get(key, 0.5) * 100), key=f"sl_{key}")
            if v / 100 != S.settings.get(key):
                set_setting(key, v / 100)
        mm = st.toggle("Radar minimap", value=S.settings.get("minimap", True))
        hb = st.toggle("Head bobbing", value=S.settings.get("head_bob", True))
        if mm != S.settings.get("minimap") or hb != S.settings.get("head_bob"):
            S.settings.update(minimap=mm, head_bob=hb)
            persist_settings()
        md('<div style="height:.6rem"></div>')
        a, b = st.columns(2)

        def reset_defaults():
            S.settings = dict(DEFAULT_SETTINGS)
            for k in list(S.keys()):
                if str(k).startswith("sl_"):
                    del S[k]
            persist_settings()
        a.button("Reset to defaults", width="stretch", on_click=reset_defaults)
        with b:
            back_button("Done", key="set_back")


def screen_howto():
    md('<h2 class="title-md" style="text-align:center">How to survive the manor</h2>')
    _, mid, _ = st.columns([.18, 1, .18])
    steps = [
        ("Listen first", "Speak with the spirit in each chapter. Their words point toward the hidden message and barely disturb the Hollow."),
        ("Break the seal", "Examine the cyan seal. Every letter is shifted two places forward, so walk each one two steps back. C becomes A, V becomes T."),
        ("Open the Moon Door", "Once the seal is broken the door will let you through to the next chapter. The third door leads out."),
        ("Keep the Hollow back", "Searching and forcing doors draws it closer. When its eyes appear, use a lantern flash to drive it away."),
        ("Mind your health", "If the Hollow reaches you, or you give a wrong answer, you lose health. On Nightmare a wrong answer sends you back to the first seal."),
        ("Find the fuller ending", "Restore the flower memory in the side stories before breaking the last seal and the Witness will remember her name."),
    ]
    with mid:
        for n, (h, body) in enumerate(steps, 1):
            md(f'<div class="panel" style="margin-bottom:.55rem;display:flex;gap:1.1rem;align-items:flex-start">'
               f'<div style="font-family:Cinzel,serif;font-size:1.5rem;color:var(--brass);width:1.6rem">{n}</div>'
               f'<div><h4 style="margin:0">{esc(h)}</h4><p class="muted" style="margin:0">{esc(body)}</p></div></div>')
        md('<div style="height:.4rem"></div>')
        back_button("Back", key="how_back")


@st.cache_data(show_spinner=False)
def explorer_template():
    with open(os.path.join(BASE_DIR, "explore3d.html"), "r", encoding="utf-8") as f:
        return f.read()


def screen_explore():
    top_bar(in_game=False)
    md('<p class="kicker">Explore in 3D</p><h2 class="title-md" style="margin-top:0">Walk the manor yourself</h2>'
       '<p class="muted" style="margin-top:-.3rem">Click inside the view first so it can hear your keys, then walk with WASD '
       'and drag the mouse to look. Find the Witness and the cyan seal, decode it, then reach the Moon Door.</p>')
    data = {
        "levels": [{k: lev[k] for k in ("name", "map", "start", "exit", "clue", "enemy", "friend", "answer", "cipher",
                                         "hint", "speaker", "intro", "opening", "choices")} for lev in LEVELS],
        "dialogues": DIALOGUES,
        "difficulty": DIFFICULTY,
        "diffName": S.settings["difficulty"],
        "flower": "flower_memory" in S.quest_flags,
        "volume": float(S.settings.get("master_volume", .65)) * float(S.settings.get("sfx_volume", .8)),
        "sens": float(S.settings.get("sensitivity", .0022)),
        "bob": bool(S.settings.get("head_bob", True)),
        "ending_complete": ENDING_COMPLETE, "ending_partial": ENDING_PARTIAL,
        "sounds": {"background": audio_b64("background.mp3"),
                   "footsteps": audio_b64("footsteps.mp3")},
        "tex": {"floor": img_b64("floor.png", 256), "ceiling": img_b64("ceiling.png", 256),
                **{f"wall{i}": img_b64(lev["image"], 512) for i, lev in enumerate(LEVELS)}},
    }
    page = explorer_template().replace("__DATA__", json.dumps(data)).replace("__ACCENT__", ACCENT)
    components.html(page, height=700, scrolling=False)
    md(f'<p class="muted" style="font-size:1rem">Difficulty: {esc(S.settings["difficulty"])}. Change it in Settings before you start. '
       'Progress in 3D mode is kept in this browser, separate from the point and click mode.</p>')


# ----------------------------------------------------------------------------
# Router
# ----------------------------------------------------------------------------
inject_css()
particles()

SCREENS = {
    "title": screen_title, "play": screen_play, "puzzle": screen_puzzle, "journal": screen_journal,
    "level_complete": screen_level_complete, "victory": lambda: screen_ending(True),
    "failure": lambda: screen_ending(False), "hub": screen_hub, "minigame": screen_minigame,
    "quests": screen_quests, "stories": screen_stories, "story": screen_story, "themes": screen_themes,
    "character": screen_character, "explore": screen_explore, "settings": screen_settings, "howto": screen_howto,
}
SCREENS.get(S.screen, screen_title)()
