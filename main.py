import math
import json
import os
import random
import sys
from array import array

import pygame

# ==============================================================================
# Cryptic Escape: The Cursed Manor — Deluxe Edition
# Pure Pygame; zero external assets required.
# ------------------------------------------------------------------------------
# Features:
# - Pseudo-3D Raycasting Engine with Distance Shading & Torch Flicker
# - Dynamic 1D Depth Buffer (prevents sprites from clipping through walls)
# - Real-time HUD Minimap / Radar (Toggleable with 'M')
# - Sprint & Stamina Mechanics (Hold 'SHIFT') with Head-Bobbing & Footstep SFX
# - Lantern Flash Stun Defense ('SPACE' or Right Click) to blind The Hollow
# - In-Game Journal & Caesar Cipher Codex ('J') with built-in decoder wheel
# - Tension Heartbeat System (procedural audio accelerates as the monster nears)
# - Branching Dialogue with The Witness
# - Caesar Cipher Puzzle Mechanics
# - Character Customization Atelier & Settings Menu (Story/Normal/Nightmare)
# - Full Persistence (savegame.json & settings.json)
# ==============================================================================

pygame.init()
pygame.display.set_caption("Cryptic Escape: The Cursed Manor — Deluxe Edition")
WIDTH, HEIGHT = 1100, 680
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
clock = pygame.time.Clock()

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
SAVE_FILE = os.path.join(BASE_DIR, "savegame.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

FONT = pygame.font.SysFont("georgia", 22)
SMALL = pygame.font.SysFont("georgia", 16)
TINY = pygame.font.SysFont("georgia", 13)
TITLE = pygame.font.SysFont("georgia", 42, bold=True)
BIG = pygame.font.SysFont("georgia", 54, bold=True)

DEFAULT_SETTINGS = {
    "master_volume": 0.65,
    "music_volume": 0.35,
    "sfx_volume": 0.8,
    "sensitivity": 0.0022,
    "dark_mode": True,
    "character_color": 2,
    "character_type": 0,
    "difficulty": "Normal",
    "minimap": True,
    "head_bob": True
}

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {**default, **data}
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return default.copy()

settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)

# External room artwork. Images are mapped onto the ray-cast wall surfaces,
# so they follow the game's pseudo-3D perspective instead of being flat overlays.
ASSET_DIR = os.path.join(BASE_DIR, "assets")
def load_room_texture(filename, fallback_color):
    path = os.path.join(ASSET_DIR, filename)
    try:
        image = pygame.image.load(path).convert()
        return pygame.transform.smoothscale(image, (512, 256))
    except (pygame.error, OSError):
        fallback = pygame.Surface((512, 256))
        fallback.fill(fallback_color)
        return fallback

ROOM_TEXTURES = [
    load_room_texture("livingroom.png", (65, 35, 40)),
    load_room_texture("painting.png", (35, 55, 48)),
    load_room_texture("passage.png", (25, 30, 42)),
]

def load_surface_texture(filename, fallback_size, fallback_color):
    """Load a high-detail texture from assets/ or beside the game file."""
    for path in (os.path.join(ASSET_DIR, filename), os.path.join(BASE_DIR, filename)):
        try:
            return pygame.image.load(path).convert()
        except (pygame.error, OSError):
            continue
    surface = pygame.Surface(fallback_size)
    surface.fill(fallback_color)
    return surface

# User-provided octagonal ceiling and geometric wooden floor.
CEILING_TEXTURE = load_surface_texture("ceiling.png", (512, 512), (24, 12, 24))
FLOOR_TEXTURE = load_surface_texture("floor.png", (512, 512), (55, 35, 24))
EXTRA_ROOM_TEXTURES = [
    load_room_texture("drawingroom.png", (25, 40, 38)),
    load_room_texture("room.png", (35, 35, 42)),
]
ROOM_TEXTURES.extend(EXTRA_ROOM_TEXTURES)
DINING_TEXTURE = load_room_texture("candle.png", (45, 30, 25))
save_data = load_json(SAVE_FILE, {"level": 0, "health": 100, "clues": [], "won": False})

LEVELS = [
    {
        "name": "The Forgotten Foyer",
        "map": [
            "111111111111",
            "100000000001",
            "101110011101",
            "100010000001",
            "100010111101",
            "100000100001",
            "101100100101",
            "100000000001",
            "111111111111"
        ],
        "start": (1.5, 1.5), "exit": (10.5, 7.5), "clue": (5.5, 3.5),
        "answer": "THE KEY IS UNDER THE CANDLE",
        "hint": "Caesar shift: move each letter 2 steps backward.",
        "enemy": (8.5, 5.5), "friend": (3.5, 5.5),
        "intro": "A portrait follows your gaze. Beneath it, fresh dust spells your name. Somewhere upstairs, a dinner bell rings for a family that died a century ago."
    },
    {
        "name": "The Whispering Library",
        "map": [
            "111111111111",
            "100000000001",
            "101101110101",
            "100000000001",
             "111011011101",
            "100000000001",
            "101110110101",
            "100000000001",
            "111111111111"
        ],
        "start": (1.5, 1.5), "exit": (10.5, 7.5), "clue": (7.5, 3.5),
        "answer": "THE SECRET PASSAGE IS EAST",
        "hint": "Shift every letter BACK by two positions.",
        "enemy": (9.5, 5.5), "friend": (4.5, 3.5),
        "intro": "The books whisper a name that was scratched from every family record. One book is warm, as if someone has just closed it, though the dust on its cover is untouched."
    },
    {
        "name": "The Moonlit Crypt",
        "map": [
            "111111111111",
            "100000000001",
            "101011110101",
            "100000000001",
            "101110111101",
            "100000000001",
            "101011110101",
            "100000000001",
            "111111111111"
        ],
        "start": (1.5, 1.5), "exit": (10.5, 7.5), "clue": (5.5, 5.5),
        "answer": "THE LIGHT WILL SET YOU FREE",
        "hint": "Decode the seal with shift -2, then unlock the moon door.",
        "enemy": (9.5, 3.5), "friend": (3.5, 5.5),
        "intro": "The dead do not want revenge. They want the truth to stay buried. Blue light spills from the sealed doorway, and a voice behind it asks whether you came to remember or to forgive."
    }
]

def caesar(value, shift):
    out = []
    for ch in value.upper():
        if "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + shift) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)

for lev in LEVELS:
    lev["cipher"] = caesar(lev["answer"], 2)

level_index = max(0, min(int(save_data.get("level", 0)), len(LEVELS) - 1))
health = max(1, min(100, int(save_data.get("health", 100))))
stamina = 100.0
lantern_oil = 100.0
clues_found = set(save_data.get("clues", []))
if save_data.get("won"):
    level_index, health, clues_found = 0, 100, set()

player_x, player_y = LEVELS[level_index]["start"]
player_angle = 0.0
mode = "menu"
settings_return_mode = "menu"
is_running = True
message = "The manor has been waiting for you."
message_timer = 4.0
wrong_answer_timer = 0.0
puzzle_input = ""
puzzle_feedback = ""
enemy_x, enemy_y = LEVELS[level_index]["enemy"]
enemy_alert = False
enemy_stunned = 0.0
damage_cooldown = 0.0
dialogue_index = 0
dialogue_choices = []
dialogue_speaker = ""
dialogue_lines = []
current_dialogue = "intro"
slider_drag = None
ambient_time = 0.0
step_cycle = 0.0
bob_offset = 0.0
screen_flash = 0.0
heartbeat_timer = 0.0
footstep_timer = 0.0
depth_buffer = []

# Deluxe story and mini-game state
quest_flags = set(save_data.get("quest_flags", []))
mini_game_state = {"name": "", "cards": [], "revealed": [], "matched": set(), "sequence": [],
                   "player_sequence": [], "phase": "ready", "timer": 0.0, "round": 1,
                   "candles": [0, 0, 0, 0, 0], "feedback": ""}
menu_petal_seed = [random.random() for _ in range(34)]
active_theme = settings.get("active_theme", "Haunted")
SEASON_THEMES = {
    "Haunted": {"accent": (165, 111, 206), "particle": (173, 153, 211), "subtitle": "The portraits are watching."},
    "Halloween": {"accent": (255, 112, 42), "particle": (255, 135, 49), "subtitle": "Pumpkins glow where no candle burns."},
    "Christmas": {"accent": (83, 220, 151), "particle": (245, 248, 255), "subtitle": "A silent snowfall covers old footprints."},
    "Winter Snow": {"accent": (122, 204, 255), "particle": (232, 246, 255), "subtitle": "The manor sleeps beneath blue frost."},
    "Blood Moon": {"accent": (224, 65, 100), "particle": (240, 90, 115), "subtitle": "Tonight, the moon remembers everything."},
}
if active_theme not in SEASON_THEMES:
    active_theme = "Haunted"
season_particles = [{"x": random.random(), "y": random.random(), "speed": random.uniform(.035, .13), "phase": random.random()*6.28, "size": random.randint(1, 4)} for _ in range(100)]
story_pages = {
    "story_portrait": ("THE PORTRAIT THAT BLINKED", [
        "At 11:13, the portrait in the west hall blinked. Not both eyes. Just the left one, the eye painted over after the fire.",
        "You lift the frame. Behind it, someone has scratched: 'A family can bury a body. It cannot bury what the body remembers.'",
        "The painted girl is not the monster. She is the witness the family tried to erase. When you turn away, the portrait has changed: now there are four people in it, and one has no face."
    ]),
    "story_christmas": ("THE CHRISTMAS ROOM", [
        "The ballroom is frozen in the middle of a Christmas party from 1897. Paper stars hang motionless, and a tree glows with lights that have no wires.",
        "A music box plays a carol with one note missing. The missing note is the name of the child who was locked outside during the storm.",
        "You place a silver star on the tree. For one warm second, every ghost in the room looks alive. A small voice whispers, 'You remembered me.'"
    ]),
    "story_train": ("THE LAST TRAIN AT MIDNIGHT", [
        "A station platform waits under the cellar. A black train arrives every night, though the tracks end at a brick wall.",
        "Its conductor has no ticket punch, only a pocket watch stopped at the moment the manor's first secret was made.",
        "The train does not carry the dead away. It carries their forgotten memories back to the place that stole them. One empty seat bears your name."
    ]),
    "story_secret": ("THE FAMILY SECRET", [
        "The manor's founder did not seek eternal life. He feared that the truth about his family would outlive him.",
        "He sealed the truth inside three ciphers and made a guardian from every memory he had refused to face. That guardian became the Hollow.",
        "The Witness and the Hollow are two halves of the same lost child: one remembers the kindness, the other remembers the betrayal. Freeing one without hearing the other will leave the curse unfinished."
    ]),
}

QUESTS = [
    ("main", "Break the three cipher seals", "Decode the message hidden in each chapter."),
    ("optional", "The kindest soul", "Find the pink flower memory and learn why it matters."),
    ("optional", "A song without a singer", "Reproduce the ghostly signal in the music room."),
    ("optional", "Five lights, one truth", "Light the candles in the order revealed by the manor."),
    ("optional", "Collector of forgotten things", "Complete the flower-memory pairs."),
]

def set_game_mode(new_mode):
    """Central mode switcher guaranteeing mouse grab/visibility states remain synchronized."""
    global mode
    mode = new_mode
    if mode == "game":
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)
    else:
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)

# Procedural Sound Synthesizer (Zero audio files required)
def make_tone(freq=440, duration=0.10, volume=0.15, decay=False):
    sample_rate = 22050
    n = int(sample_rate * duration)
    buf = array("h")
    for i in range(n):
        fade = min(1.0, i / 250, (n - i) / 400)
        curr_freq = freq * (1.0 - 0.45 * (i / n)) if decay else freq
        val = int(32767 * volume * fade * math.sin(2 * math.pi * curr_freq * i / sample_rate))
        buf.append(max(-32767, min(32767, val)))
    return pygame.mixer.Sound(buffer=buf.tobytes())


def make_ambient(duration=2.0):
    """Create a soft, loopable haunted-room drone without external audio files."""
    sample_rate = 22050
    n = int(sample_rate * duration)
    buf = array("h")
    for i in range(n):
        t = i / sample_rate
        # Low layered tones and a very gentle pulse; quiet enough to sit under SFX.
        pulse = 0.72 + 0.28 * math.sin(2 * math.pi * 0.22 * t)
        wave = (0.55 * math.sin(2 * math.pi * 55.0 * t)
                + 0.28 * math.sin(2 * math.pi * 82.4 * t)
                + 0.17 * math.sin(2 * math.pi * 110.0 * t))
        val = int(32767 * 0.10 * pulse * wave)
        buf.append(max(-32767, min(32767, val)))
    return pygame.mixer.Sound(buffer=buf.tobytes())

try:
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=22050, size=-16, channels=1)
    sound_click = make_tone(660, 0.06, 0.13)
    sound_success = make_tone(880, 0.16, 0.18)
    sound_warning = make_tone(115, 0.22, 0.17)
    sound_whisper = make_tone(310, 0.10, 0.08)
    sound_heartbeat = make_tone(58, 0.09, 0.28, decay=True)
    sound_footstep = make_tone(130, 0.04, 0.06, decay=True)
    sound_flash = make_tone(540, 0.25, 0.22, decay=True)
    sound_ambient = make_ambient()
except Exception:
    sound_click = sound_success = sound_warning = sound_whisper = sound_heartbeat = sound_footstep = sound_flash = None
    sound_ambient = None

def play_sound(snd):
    if snd:
        try:
            vol = settings.get("master_volume", 0.65) * settings.get("sfx_volume", 0.8)
            snd.set_volume(max(0.0, min(1.0, vol)))
            snd.play()
        except Exception:
            pass

def persist_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass

def persist_save(won=False):
    data = {
        "level": level_index,
        "health": health,
        "clues": sorted(list(clues_found)),
        "won": won,
        "difficulty": settings.get("difficulty", "Normal"),
        "quest_flags": sorted(quest_flags)
    }
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass

def current_level():
    return LEVELS[level_index]

def map_cell(x, y):
    lev = current_level()
    ix, iy = int(x), int(y)
    if iy < 0 or iy >= len(lev["map"]) or ix < 0 or ix >= len(lev["map"][0]):
        return 1
    return int(lev["map"][iy][ix])

def can_move(x, y):
    return map_cell(x, y) == 0

def reset_level(idx):
    global level_index, player_x, player_y, player_angle, enemy_x, enemy_y, enemy_alert
    global health, stamina, lantern_oil, enemy_stunned
    level_index = idx
    lev = current_level()
    player_x, player_y = lev["start"]
    player_angle = 0.0
    enemy_x, enemy_y = lev["enemy"]
    enemy_alert = False
    enemy_stunned = 0.0
    health = 100
    stamina = 100.0
    lantern_oil = 100.0
    persist_save()

def set_message(txt, seconds=3.0):
    global message, message_timer
    message, message_timer = txt, seconds

def text(surface, value, x, y, font=FONT, color=None, center=False):
    if color is None:
        color = (239, 228, 248) if settings.get("dark_mode", True) else (38, 28, 48)
    img = font.render(str(value), True, color)
    rect = img.get_rect()
    if center:
        rect.center = (int(x), int(y))
    else:
        rect.topleft = (int(x), int(y))
    surface.blit(img, rect)
    return rect

def wrap_text(value, font, max_width):
    words = value.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def panel(surface, rect, alpha=225):
    box = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    if settings.get("dark_mode", True):
        pygame.draw.rect(box, (9, 9, 24, alpha), box.get_rect(), border_radius=14)
        pygame.draw.rect(box, (156, 104, 220, 235), box.get_rect(), 2, border_radius=14)
    else:
        pygame.draw.rect(box, (248, 242, 255, alpha), box.get_rect(), border_radius=14)
        pygame.draw.rect(box, (93, 65, 143, 235), box.get_rect(), 2, border_radius=14)
    surface.blit(box, rect[:2])

def draw_button(label, rect, active=False):
    r = pygame.Rect(rect)
    hover = r.collidepoint(pygame.mouse.get_pos())
    dark = settings.get("dark_mode", True)
    fill = (48, 31, 74) if dark else (226, 213, 243)
    if hover or active:
        fill = (105, 53, 143) if dark else (194, 164, 227)
    pygame.draw.rect(screen, fill, r, border_radius=10)
    pygame.draw.rect(screen, (210, 166, 255), r, 2, border_radius=10)
    text(screen, label, r.centerx, r.centery, SMALL, center=True)
    return r

def draw_seasonal_effects():
    """Lightweight animated seasonal particles; all art is drawn with Pygame primitives."""
    theme = SEASON_THEMES.get(active_theme, SEASON_THEMES["Haunted"])
    accent = theme["accent"]
    for i, particle in enumerate(season_particles):
        x = int((particle["x"] * WIDTH + math.sin(ambient_time * 1.3 + particle["phase"]) * 20) % WIDTH)
        particle["y"] += particle["speed"] * (0.55 if active_theme == "Halloween" else 1.0) / 60.0
        if particle["y"] > 1.02:
            particle["y"] = -0.02
            particle["x"] = random.random()
        y = int(particle["y"] * HEIGHT)
        size = particle["size"]
        if active_theme in ("Christmas", "Winter Snow"):
            pygame.draw.circle(screen, theme["particle"], (x, y), max(1, size-1))
            if size >= 3:
                pygame.draw.line(screen, (255,255,255), (x-size-1,y), (x+size+1,y), 1)
        elif active_theme == "Halloween":
            pygame.draw.ellipse(screen, theme["particle"], (x, y, size*2+2, size+2))
            pygame.draw.line(screen, theme["particle"], (x+size,y+size), (x+size+3,y+size+4), 1)
        elif active_theme == "Blood Moon":
            pygame.draw.circle(screen, theme["particle"], (x,y), max(1,size//2))
        else:
            pygame.draw.ellipse(screen, theme["particle"], (x,y,size*2+1,max(2,size)))
    if active_theme == "Halloween":
        # Tiny bats drift across the upper edge.
        for i in range(5):
            bx = int((i * WIDTH / 5 + ambient_time * (18 + i*3)) % WIDTH)
            by = int(HEIGHT * .12 + math.sin(ambient_time*1.7+i)*12)
            flap = int(3 + abs(math.sin(ambient_time*8+i))*5)
            pygame.draw.polygon(screen, (30, 15, 36), [(bx,by+3),(bx-9,by-flap),(bx-7,by+5),(bx,by+2),(bx+7,by-flap),(bx+9,by+4)])
    elif active_theme == "Christmas":
        # Warm fairy lights along the top frame.
        for i in range(16):
            lx = int((i + .5) * WIDTH / 16)
            ly = 12 + int(math.sin(i*.8)*4)
            glow = int(150 + 90*(.5+.5*math.sin(ambient_time*3+i)))
            pygame.draw.circle(screen, (glow, min(255,glow), 100), (lx,ly), 3)
    elif active_theme == "Haunted":
        # Wandering will-o'-wisps.
        for i in range(3):
            wx = int(WIDTH*(.18 + i*.31) + math.sin(ambient_time*.55+i*2)*28)
            wy = int(HEIGHT*(.34 + .08*math.sin(ambient_time+i)))
            r = 4 + int(2*(.5+.5*math.sin(ambient_time*4+i)))
            pygame.draw.circle(screen, (120, 225, 205), (wx,wy), r+5, 1)
            pygame.draw.circle(screen, (177,255,231), (wx,wy), r)


def draw_wall_paintings():
    """Animated gothic portraits on the near wall edges, with blinking eyes and shifting frames."""
    for side in (0, 1):
        w = max(70, int(WIDTH * .095)); h = max(100, int(HEIGHT * .23))
        x = 18 if side == 0 else WIDTH - w - 18
        y = int(HEIGHT * (.24 + .012 * math.sin(ambient_time * .6 + side)))
        frame = SEASON_THEMES.get(active_theme, SEASON_THEMES["Haunted"])["accent"]
        pygame.draw.rect(screen, (14, 9, 19), (x-5,y-5,w+10,h+10), border_radius=3)
        pygame.draw.rect(screen, frame, (x-3,y-3,w+6,h+6), 3, border_radius=3)
        pygame.draw.rect(screen, (48, 32, 43), (x,y,w,h))
        # Silhouette and candlelit face
        cx, cy = x+w//2, y+int(h*.43)
        pygame.draw.ellipse(screen, (21, 18, 29), (cx-w*.28, y+h*.53, w*.56, h*.42))
        pygame.draw.ellipse(screen, (139, 116, 118), (cx-w*.17, cy-h*.20, w*.34, h*.39))
        pygame.draw.arc(screen, (205, 180, 174), (cx-w*.18,cy-h*.22,w*.36,h*.42), math.pi, 2*math.pi, 2)
        blink = (int(ambient_time*1.7 + side*2.4) % 9) == 0
        eye_y = cy-int(h*.02)
        if not blink:
            pygame.draw.circle(screen, (239, 70, 94), (cx-int(w*.07),eye_y), max(2,int(w*.018)))
            pygame.draw.circle(screen, (239, 70, 94), (cx+int(w*.07),eye_y), max(2,int(w*.018)))
        else:
            pygame.draw.line(screen, (35,15,24), (cx-int(w*.12),eye_y),(cx-int(w*.03),eye_y),2)
            pygame.draw.line(screen, (35,15,24), (cx+int(w*.03),eye_y),(cx+int(w*.12),eye_y),2)
        # Gilded plaque beneath each portrait
        pygame.draw.rect(screen, (90, 61, 48), (x+w*.18,y+h*.83,w*.64,max(9,h*.08)))
        if side == 0:
            text(screen, "THE LOST", cx, y+h*.87, TINY, (238,204,157), center=True)
        else:
            text(screen, "THE UNNAMED", cx, y+h*.87, TINY, (238,204,157), center=True)


def draw_menu_background():
    dark = settings.get("dark_mode", True)
    screen.fill((5, 6, 19) if dark else (224, 219, 239))
    moon = (225, 222, 255) if dark else (255, 250, 218)
    pygame.draw.circle(screen, moon, (int(WIDTH * 0.78), int(HEIGHT * 0.20)), 46)
    pygame.draw.circle(screen, (9, 10, 29) if dark else (224, 219, 239),
                       (int(WIDTH * 0.805), int(HEIGHT * 0.17)), 41)
    for i in range(55):
        x = (i * 97 + 23) % WIDTH
        y = (i * 47 + 13) % int(HEIGHT * 0.55)
        pygame.draw.circle(screen, (145, 129, 188) if dark else (125, 112, 151), (x, y), 1)
    ground = int(HEIGHT * 0.70)
    for i in range(14):
        x = int(i * WIDTH / 13)
        h = 105 + (i * 47 % 150)
        color = (16, 13, 38) if dark else (82, 72, 111)
        pygame.draw.rect(screen, color, (x, ground - h, 72, h + 130))
        pygame.draw.polygon(screen, (26, 18, 49) if dark else (103, 87, 132),
                            [(x - 9, ground - h), (x + 36, ground - h - 48), (x + 81, ground - h)])
        for wy in range(ground - h + 18, ground - 10, 29):
            pygame.draw.arc(screen, (101, 66, 128), (x + 22, wy, 22, 27), 0, math.pi, 2)
    for i in range(7):
        y = int(HEIGHT * 0.72 + i * 21)
        pygame.draw.line(screen, (55, 42, 83) if dark else (181, 168, 206), (0, y), (WIDTH, y - 20), 2)

def trigger_lantern_flash():
    """Unleashes a blinding radiant flash stunning The Hollow and pushing it back."""
    global lantern_oil, screen_flash, enemy_stunned, enemy_x, enemy_y
    if lantern_oil < 30.0:
        set_message("Lantern oil too low! Rest to replenish.", 2.0)
        play_sound(sound_warning)
        return
    lantern_oil -= 30.0
    screen_flash = 1.0
    enemy_stunned = 3.5
    play_sound(sound_flash)
    dx, dy = enemy_x - player_x, enemy_y - player_y
    dist = max(0.1, math.hypot(dx, dy))
    push_x = enemy_x + (dx / dist) * 2.0
    push_y = enemy_y + (dy / dist) * 2.0
    if can_move(push_x, enemy_y):
        enemy_x = push_x
    if can_move(enemy_x, push_y):
        enemy_y = push_y
    set_message("RADIANT FLASH! The Hollow is blinded and repelled!", 3.0)

def draw_gothic_monster(cx, cy, size, phase=0, stunned=False):
    s = max(12, int(size))
    pygame.draw.ellipse(screen, (2, 2, 8), (int(cx - s * 0.42), int(cy + s * 0.30), int(s * 0.84), int(s * 0.20)))
    pts = [(cx - s * 0.30, cy - s * 0.18), (cx - s * 0.42, cy + s * 0.32), (cx - s * 0.20, cy + s * 0.22),
           (cx - s * 0.08, cy + s * 0.42), (cx + s * 0.02, cy + s * 0.23), (cx + s * 0.19, cy + s * 0.38),
           (cx + s * 0.39, cy + s * 0.26), (cx + s * 0.28, cy - s * 0.20)]
    body_color = (25, 20, 40) if not stunned else (60, 45, 90)
    pygame.draw.polygon(screen, body_color, pts)
    pygame.draw.ellipse(screen, (34, 19, 47), (int(cx - s * 0.30), int(cy - s * 0.40), int(s * 0.60), int(s * 0.64)))
    pygame.draw.arc(screen, (89, 44, 103), (int(cx - s * 0.29), int(cy - s * 0.35), int(s * 0.58), int(s * 0.64)), 0.2, 2.8, max(1, s // 35))
    pygame.draw.ellipse(screen, (4, 3, 12), (int(cx - s * 0.20), int(cy - s * 0.20), int(s * 0.40), int(s * 0.32)))
    eye_y = int(cy - s * 0.04)
    eye_r = max(2, int(s * 0.045))
    flicker = 210 + int(35 * math.sin(phase * 8))
    eye = (140, 180, 255) if stunned else (255, max(25, flicker // 5), max(35, flicker // 4))
    pygame.draw.circle(screen, eye, (int(cx - s * 0.09), eye_y), eye_r)
    pygame.draw.circle(screen, eye, (int(cx + s * 0.09), eye_y), eye_r)
    pygame.draw.circle(screen, (255, 210, 218), (int(cx - s * 0.09), eye_y), max(1, eye_r // 2))
    pygame.draw.circle(screen, (255, 210, 218), (int(cx + s * 0.09), eye_y), max(1, eye_r // 2))
    pygame.draw.line(screen, (49, 27, 62), (int(cx - s * 0.15), int(cy - s * 0.27)), (int(cx - s * 0.30), int(cy - s * 0.53)), max(2, s // 22))
    pygame.draw.line(screen, (49, 27, 62), (int(cx - s * 0.30), int(cy - s * 0.53)), (int(cx - s * 0.34), int(cy - s * 0.62)), max(1, s // 30))
    pygame.draw.line(screen, (49, 27, 62), (int(cx + s * 0.15), int(cy - s * 0.27)), (int(cx + s * 0.29), int(cy - s * 0.50)), max(2, s // 22))
    pygame.draw.line(screen, (49, 27, 62), (int(cx + s * 0.29), int(cy - s * 0.50)), (int(cx + s * 0.36), int(cy - s * 0.58)), max(1, s // 30))
    if stunned:
        text(screen, "BLINDED", cx, cy - s * 0.55, TINY, (180, 220, 255), center=True)

def draw_friendly_spirit(cx, cy, size, phase):
    s = max(12, int(size))
    aura = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
    pygame.draw.circle(aura, (65, 200, 255, 35), (s, s), int(s * 0.75))
    screen.blit(aura, (int(cx - s), int(cy - s)))
    pygame.draw.ellipse(screen, (65, 204, 235), (int(cx - s * 0.28), int(cy - s * 0.25 + math.sin(phase * 3) * 3), int(s * 0.56), int(s * 0.62)))
    pygame.draw.circle(screen, (203, 252, 255), (int(cx - s * 0.10), int(cy - s * 0.02)), max(2, int(s * 0.05)))
    pygame.draw.circle(screen, (203, 252, 255), (int(cx + s * 0.10), int(cy - s * 0.02)), max(2, int(s * 0.05)))
    pygame.draw.arc(screen, (20, 104, 145), (int(cx - s * 0.11), int(cy + s * 0.04), int(s * 0.22), int(s * 0.13)), math.pi, 2 * math.pi, 2)

def draw_minimap():
    if not settings.get("minimap", True):
        return
    lev = current_level()
    mw, mh = len(lev["map"][0]), len(lev["map"])
    tile_size = 9
    map_w, map_h = mw * tile_size, mh * tile_size
    pad = 16
    rect = (WIDTH - map_w - pad - 12, pad, map_w + 12, map_h + 30)
    panel(screen, rect, 205)
    text(screen, "RADAR (M)", rect[0] + rect[2] // 2, rect[1] + 10, TINY, (180, 160, 210), center=True)

    ox, oy = rect[0] + 6, rect[1] + 22
    for my in range(mh):
        for mx in range(mw):
            c = lev["map"][my][mx]
            r = pygame.Rect(ox + mx * tile_size, oy + my * tile_size, tile_size - 1, tile_size - 1)
            if c == "1":
                pygame.draw.rect(screen, (48, 36, 68), r, border_radius=2)
            else:
                pygame.draw.rect(screen, (16, 12, 28), r, border_radius=2)

    def to_map(wx, wy):
        return int(ox + wx * tile_size), int(oy + wy * tile_size)

    # Clue sigil
    if level_index not in clues_found:
        cx, cy = to_map(*lev["clue"])
        pygame.draw.circle(screen, (32, 195, 232), (cx, cy), 3)

    # Exit
    ex, ey = to_map(*lev["exit"])
    pygame.draw.circle(screen, (255, 210, 80), (ex, ey), 3)

    # Witness
    fx, fy = to_map(*lev["friend"])
    pygame.draw.circle(screen, (90, 220, 255), (fx, fy), 3)

    # Monster (blinks if close or alert)
    if enemy_alert or math.hypot(enemy_x - player_x, enemy_y - player_y) < 5.5:
        mx, my = to_map(enemy_x, enemy_y)
        flicker_color = (255, 40, 80) if int(ambient_time * 8) % 2 == 0 else (180, 20, 40)
        pygame.draw.circle(screen, flicker_color, (mx, my), 4)

    # Player dot and sight cone line
    px, py = to_map(player_x, player_y)
    pygame.draw.circle(screen, (240, 230, 255), (px, py), 3)
    dir_x = px + int(math.cos(player_angle) * 8)
    dir_y = py + int(math.sin(player_angle) * 8)
    pygame.draw.line(screen, (160, 110, 255), (px, py), (dir_x, dir_y), 2)

def draw_world():
    global depth_buffer
    level = current_level()
    horizon = (HEIGHT // 2) + int(bob_offset if settings.get("head_bob", True) else 0)
    
    dark = settings.get("dark_mode", True)

# Select a room theme automatically for each level
    if level_index == 0:
    # Level 1: Haunted Mansion - warm, spooky brown
        ceiling_color = (24, 12, 12)
        floor_color = (45, 25, 20)
        wall_tint = (0.68, 0.42, 0.28)
        glow_color = (220, 100, 45, 28)

    elif level_index == 1:
    # Level 2: Whispering Library - eerie green
        ceiling_color = (7, 22, 17)
        floor_color = (15, 39, 28)
        wall_tint = (0.32, 0.58, 0.42)
        glow_color = (55, 220, 125, 25)

    else:
    # Level 3: Moonlit Crypt - cold blue
        ceiling_color = (7, 10, 30)
        floor_color = (15, 22, 48)
        wall_tint = (0.32, 0.42, 0.72)
        glow_color = (70, 110, 255, 28)

    screen.fill((5, 5, 15) if dark else (184, 177, 199))
    # Perspective-projected repeating ceiling/floor tiles.  The source images are
    # tiled many times across each scanline so they behave like surface materials,
    # not one giant picture stretched over the whole screen.
    pygame.draw.rect(screen, ceiling_color if dark else (219, 213, 230), (0, 0, WIDTH, horizon))
    pygame.draw.rect(screen, floor_color if dark else (117, 105, 131), (0, horizon, WIDTH, HEIGHT - horizon))
    if dark and horizon > 2:
        tw, th = CEILING_TEXTURE.get_size()
        fw, fh = FLOOR_TEXTURE.get_size()
        tile_step = 3
        tint_rgb = (int(255 * wall_tint[0]), int(255 * wall_tint[1]), int(255 * wall_tint[2]))

        # Ceiling: small repeating tiles near the horizon, larger toward the top.
        for sy in range(0, max(1, horizon - 1), tile_step):
            depth = max(0.10, (horizon - sy) / max(1, HEIGHT * 0.62))
            tile_w = max(18, min(260, int(34 + depth * 115)))
            tile_h = max(8, min(th, int(18 + depth * 90)))
            tile = pygame.transform.smoothscale(CEILING_TEXTURE, (tile_w, tile_h))
            tile.fill(tint_rgb, special_flags=pygame.BLEND_RGB_MULT)
            row = tile.subsurface((0, min(tile_h - 1, tile_h // 2), tile_w, 1))
            offset = int((player_angle * 32 + player_x * 17) % tile_w)
            for sx in range(-tile_w + offset, WIDTH, tile_w):
                screen.blit(row, (sx, sy))

        # Floor: repeating wooden geometry, with larger tiles toward the camera.
        for sy in range(horizon + 1, HEIGHT, tile_step):
            depth = max(0.08, (sy - horizon) / max(1, HEIGHT - horizon))
            tile_w = max(16, min(320, int(20 + depth * 210)))
            tile_h = max(8, min(fh, int(12 + depth * 120)))
            tile = pygame.transform.smoothscale(FLOOR_TEXTURE, (tile_w, tile_h))
            tile.fill(tint_rgb, special_flags=pygame.BLEND_RGB_MULT)
            row = tile.subsurface((0, min(tile_h - 1, tile_h // 2), tile_w, 1))
            offset = int((player_angle * 48 + player_x * 23) % tile_w)
            for sx in range(-tile_w + offset, WIDTH, tile_w):
                screen.blit(row, (sx, sy))

    # Raycast the world and texture each wall column with the supplied artwork.
    # The hit coordinate selects a horizontal strip of the room image; distance
    # shading preserves depth and keeps the result consistent with the 3D maze.
    fov = math.pi / 3
    ray_count = max(180, WIDTH // 4)
    col_w = WIDTH / ray_count
    depth_buffer = [99.0] * ray_count
    room_texture = ROOM_TEXTURES[level_index % len(ROOM_TEXTURES)]
    tex_w, tex_h = room_texture.get_size()

    for ray in range(ray_count):
        ray_angle = player_angle - fov / 2 + fov * ray / ray_count
        sin_a, cos_a = math.sin(ray_angle), math.cos(ray_angle)
        depth = 0.05
        rx, ry = player_x, player_y
        while depth < 16:
            rx, ry = player_x + cos_a * depth, player_y + sin_a * depth
            if map_cell(rx, ry):
                break
            depth += 0.04
        corrected = max(0.05, depth * math.cos(ray_angle - player_angle))
        depth_buffer[ray] = corrected
        wall_h = max(1, min(int(HEIGHT * 1.5), int(HEIGHT / (corrected + 0.12))))
        x = int(ray * col_w)
        y = int(horizon - wall_h / 2)

        # Use the fractional hit position as the texture's U coordinate.
        fx, fy = rx - math.floor(rx), ry - math.floor(ry)
        u = fy if abs(cos_a) > abs(sin_a) else fx
        tex_x = max(0, min(tex_w - 1, int(u * (tex_w - 1))))
        strip = room_texture.subsurface((tex_x, 0, 1, tex_h))
        wall_column = pygame.transform.scale(strip, (max(1, int(col_w) + 1), wall_h))

        # Distance-based darkness plus the chapter's color palette.
        shade = max(0.18, min(0.86, 1.0 / (1.0 + corrected * 0.18)))
        tint = wall_tint if dark else (0.88, 0.82, 0.92)
        wall_column.fill((int(255 * shade * tint[0]),
                          int(255 * shade * tint[1]),
                          int(255 * shade * tint[2])), special_flags=pygame.BLEND_RGB_MULT)
        screen.blit(wall_column, (x, y))

    # Ambient Torchlight Glow
    glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    flicker_r = int(WIDTH * 0.5 + math.sin(ambient_time * 6) * 10)
    
    pygame.draw.ellipse(
        glow,
        glow_color if dark else (255, 230, 190, 22),

        (WIDTH * 0.25, HEIGHT * 0.40, flicker_r, int(HEIGHT * 0.72)))
    screen.blit(glow, (0, 0))

    # Sprites Depth Checking
    def project(wx, wy, kind, label):
        dx, dy = wx - player_x, wy - player_y
        dist = math.hypot(dx, dy)
        if dist < 0.15:
            return
        rel = (math.atan2(dy, dx) - player_angle + math.pi) % (2 * math.pi) - math.pi
        if abs(rel) > fov * 0.6:
            return

        ray_idx = int(((rel + fov / 2) / fov) * ray_count)
        if 0 <= ray_idx < ray_count and dist > depth_buffer[ray_idx] + 0.35:
            return

        sx = WIDTH / 2 + (rel / (fov / 2)) * (WIDTH / 2)
        size = min(HEIGHT * 0.82, HEIGHT / (dist + 0.15) * 0.36)
        sy = horizon + HEIGHT / (dist + 0.3) * 0.22

        if kind == "enemy":
            draw_gothic_monster(sx, sy, size * 1.7, ambient_time, enemy_stunned > 0)
        elif kind == "friend":
            draw_friendly_spirit(sx, sy, size * 1.2, ambient_time)
        elif kind == "clue":
            pulse = 1 + 0.10 * math.sin(ambient_time * 4)
            r = max(4, int(size * 0.22 * pulse))
            pygame.draw.circle(screen, (32, 195, 232), (int(sx), int(sy)), r + 5, 2)
            pygame.draw.circle(screen, (104, 240, 255), (int(sx), int(sy)), r)
            pygame.draw.circle(screen, (230, 255, 255), (int(sx), int(sy)), max(2, r // 3))
        else:
            pygame.draw.circle(screen, (255, 181, 80), (int(sx), int(sy)), max(5, int(size * 0.25)))
            pygame.draw.circle(screen, (255, 240, 183), (int(sx), int(sy)), max(2, int(size * 0.12)))

        if dist < 3.4:
            label_color = (232, 215, 255) if dark else (45, 28, 59)
            text(screen, label, sx, sy + size * 0.52, TINY, label_color, center=True)

    sprites = [
        (*level["friend"], "friend", "THE WITNESS"),
        (*level["exit"], "exit", "MOON DOOR"),
        (enemy_x, enemy_y, "enemy", "THE HOLLOW")
    ]
    if level_index not in clues_found:
        sprites.append((*level["clue"], "clue", "CRYPT"))

    sprites.sort(key=lambda s: math.hypot(s[0] - player_x, s[1] - player_y), reverse=True)
    for sp in sprites:
        project(*sp)

    # Flash effect overlay
    if screen_flash > 0:
        flash_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        alpha = int(screen_flash * 200)
        flash_surf.fill((255, 250, 220, alpha))
        screen.blit(flash_surf, (0, 0))

    # Heartbeat vignette when threat is close
    dist_to_enemy = math.hypot(enemy_x - player_x, enemy_y - player_y)
    if dist_to_enemy < 4.0:
        vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        threat_alpha = int((1.0 - dist_to_enemy / 4.0) * 90 * (0.6 + 0.4 * math.sin(ambient_time * 9)))
        vignette.fill((160, 20, 40, threat_alpha))
        screen.blit(vignette, (0, 0))

    # Animated paintings and seasonal atmosphere
    draw_wall_paintings()
    draw_seasonal_effects()

    # HUD Panels
    panel(screen, (16, 14, 310, 132), 205)
    text(screen, level["name"], 30, 22, SMALL)

    # Health bar
    text(screen, f"HP   {health:03d}", 30, 46, TINY, (255, 120, 150))
    pygame.draw.rect(screen, (55, 30, 54), (95, 48, 195, 10), border_radius=4)
    pygame.draw.rect(screen, (232, 65, 112), (95, 48, int(195 * health / 100), 10), border_radius=4)

    # Stamina bar
    text(screen, f"STM  {int(stamina):03d}", 30, 68, TINY, (120, 230, 160))
    pygame.draw.rect(screen, (30, 55, 40), (95, 70, 195, 10), border_radius=4)
    pygame.draw.rect(screen, (60, 210, 130), (95, 70, int(195 * stamina / 100), 10), border_radius=4)

    # Lantern Oil bar
    text(screen, f"OIL  {int(lantern_oil):03d}", 30, 90, TINY, (245, 200, 100))
    pygame.draw.rect(screen, (55, 50, 30), (95, 92, 195, 10), border_radius=4)
    pygame.draw.rect(screen, (245, 190, 70), (95, 92, int(195 * lantern_oil / 100), 10), border_radius=4)

    text(screen, f"DIFF: {settings.get('difficulty','Normal').upper()}", 30, 116, TINY, (199, 170, 238))

    # Controls hints
    text(screen, "WASD: Move  •  SHIFT: Sprint  •  SPACE/RMB: Lantern Stun  •  J: Journal  •  Q: Quests  •  M: Radar  •  E: Interact",
         WIDTH // 2, HEIGHT - 22, TINY, (230, 220, 245), center=True)

    draw_minimap()

    if message_timer > 0:
        panel(screen, (WIDTH // 2 - 320, 91, 640, 45), 215)
        text(screen, message, WIDTH // 2, 113, SMALL, center=True)

def draw_journal():
    draw_world()
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    screen.blit(overlay, (0, 0))

    panel(screen, (WIDTH // 2 - 380, 45, 760, HEIGHT - 90), 245)
    text(screen, "MANOR JOURNAL & CIPHER CODEX", WIDTH // 2, 75, TITLE, center=True)

    y = 135
    text(screen, "CHAPTER SEALS & PROGRESS", WIDTH // 2 - 330, y, SMALL, (216, 177, 255))
    y += 26
    for i, lev in enumerate(LEVELS):
        status = "[SOLVED]" if i in clues_found else ("[ACTIVE]" if i == level_index else "[LOCKED]")
        color = (130, 240, 160) if i in clues_found else ((240, 200, 110) if i == level_index else (160, 150, 180))
        text(screen, f"Seal {i + 1}: {lev['name']} — {status}", WIDTH // 2 - 330, y, SMALL, color)
        y += 24
        if i in clues_found or i == level_index:
            text(screen, f"   Cipher: {lev['cipher']}", WIDTH // 2 - 330, y, TINY, (190, 225, 255))
            y += 20
            if i in clues_found:
                text(screen, f"   Decoded: {lev['answer']}", WIDTH // 2 - 330, y, TINY, (140, 255, 180))
                y += 22

    y += 10
    text(screen, "CAESAR CIPHER WHEEL (SHIFT -2)", WIDTH // 2 - 330, y, SMALL, (216, 177, 255))
    y += 28

    plain = "A B C D E F G H I J K L M N O P Q R S T U V W X Y Z"
    cipher = "C D E F G H I J K L M N O P Q R S T U V W X Y Z A B"
    text(screen, f"Encoded (+2):   {cipher}", WIDTH // 2 - 330, y, TINY, (245, 170, 170))
    y += 22
    text(screen, f"Decoded (-2):   {plain}", WIDTH // 2 - 330, y, TINY, (160, 245, 180))
    y += 30

    text(screen, "SURVIVAL TACTICS", WIDTH // 2 - 330, y, SMALL, (216, 177, 255))
    y += 24
    tactics = [
        "• Hold SHIFT to sprint away when The Hollow charges at you.",
        "• Press SPACE to trigger the Lantern Flash. It blinds and pushes the beast back.",
        "• Your Lantern Oil recharges slowly over time while resting."
    ]
    for tac in tactics:
        text(screen, tac, WIDTH // 2 - 330, y, TINY, (220, 215, 235))
        y += 20

    back_btn = draw_button("Close Journal (J / ESC)", (WIDTH // 2 - 130, HEIGHT - 95, 260, 42))
    return back_btn

def start_dialogue(kind="intro"):
    global dialogue_index, dialogue_choices, dialogue_speaker, dialogue_lines, current_dialogue
    current_dialogue = kind
    dialogue_index = 0
    if kind == "intro":
        dialogue_speaker = ("THE WITNESS" if level_index == 0 else ("THE TRAPPED CARETAKER" if level_index == 1 else "THE HOLLOW"))
        level_openings = [
            [current_level()["intro"], "The owner removed one name from every ledger, portrait, and birth record. The ink is newer than the pages around it.", "I heard the master say: 'If the house forgets her, the world will follow.' Find the brass register in the west hall.", "The candle marks the place where the missing page was hidden. Do not trust the family tree hanging above it."],
            [current_level()["intro"], "I am the caretaker. I locked myself in this wing when the portraits began changing at twelve. Each frame shows a different version of the same night.", "The clock does not measure time here; it counts the lies still believed. When it strikes midnight, look at the portrait with no eyes.", "I hid the winding key inside a music box. The tune is backwards because the room remembers events in reverse."],
            [current_level()["intro"], "You were summoned because you carry the only memory the family could not steal: the choice made before the fire.", "I am called the Hollow because they carved every name from me. I guarded the truth, but the lock became my prison.", "Three seals remain. Break them to uncover who called you here—and decide whether the truth will free the dead or bind the living."],
        ]
        dialogue_lines = level_openings[level_index][:]
        dialogue_choices = ([ ("Ask about the erased name", "identity"), ("Ask about the Hollow", "hollow"), ("Leave quietly", "close") ] if level_index == 0 else ([ ("Ask about the changing portraits", "history"), ("Ask about the clock", "mirror"), ("Leave quietly", "close") ] if level_index == 1 else [ ("Ask why I was summoned", "history"), ("Ask about the three seals", "hollow"), ("Leave quietly", "close") ]))
    elif kind == "identity":
        dialogue_speaker = "THE WITNESS"
        dialogue_lines = [
            "I was once the manor's youngest daughter. The fire took my face, not my memory.",
            "My name is written in the cipher you are about to solve. Read it, and I may remember the rest.",
            "I hid the first key beneath a candle before the fire began. The flame never touched it; the family simply stopped looking.",
            "When the portrait eyes turn toward the window, someone in the room is lying."
        ]
        dialogue_choices = [("Ask what happened here", "history"), ("Return to the clue", "close")]
    elif kind == "hollow":
        dialogue_speaker = "THE WITNESS"
        dialogue_lines = [
            "The Hollow was a keeper, not a killer. Someone taught it to hunt anyone carrying the truth.",
            "If it catches you, do not curse it. Ask what it is protecting.",
            "I heard it speak once. It said, 'I kept the promise even after everyone forgot what was promised.'",
            "The red in its eyes is not rage. It is the last light from the room where the truth was buried."
        ]
        dialogue_choices = [("Ask about the curse", "history"), ("Return to the clue", "close")]
    elif kind == "flower_story":
        dialogue_speaker = "THE WITNESS"
        dialogue_lines = [
            "Those flowers were planted by someone who refused to let the house become cruel.",
            "Each petal held a memory. The family tried to burn the memories, but kindness grows back in strange places.",
            "If you restore the flower pattern, I may remember the name I lost."
        ]
        dialogue_choices = [("I will restore it", "close"), ("Who planted them?", "history")]
    elif kind == "mirror":
        dialogue_speaker = "THE WITNESS"
        dialogue_lines = [
            "Do not trust the mirror when it shows you a room you have not entered.",
            "The reflection is not predicting your future. It is remembering a past the house stole from you."
        ]
        dialogue_choices = [("Return to exploring", "close"), ("Ask about the stolen memory", "history")]
    elif kind in story_pages:
        dialogue_speaker, dialogue_lines = story_pages[kind]
        dialogue_choices = [("Read the next memory", "story_next"), ("Return to stories", "story_gallery")]
    elif kind == "history":
        dialogue_speaker = "THE WITNESS"
        dialogue_lines = [
            "The family tried to trade a memory for immortality. They chose the memory of their own crime.",
            "Three seals hold that stolen memory. Break them, and the manor will have to remember.",
            "The first seal tells you where the key was hidden. The second reveals who opened the passage. The last asks whether the guilty deserve to be heard.",
            "Do not rush to destroy the Hollow. It is the lock as much as it is the jailer."
        ]    
        dialogue_choices = [("Return to the clue", "close")]
    set_game_mode("dialogue")

def draw_dialogue():
    draw_world()
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 115))
    screen.blit(overlay, (0, 0))
    box = (WIDTH // 2 - 390, HEIGHT - 260, 780, 230)
    panel(screen, box, 242)
    pygame.draw.circle(screen, (25, 44, 62), (box[0] + 72, box[1] + 76), 43)
    pygame.draw.circle(screen, (93, 223, 247), (box[0] + 72, box[1] + 76), 43, 2)
    pygame.draw.ellipse(screen, (92, 225, 245), (box[0] + 52, box[1] + 51, 40, 52))
    pygame.draw.circle(screen, (235, 255, 255), (box[0] + 64, box[1] + 69), 4)
    pygame.draw.circle(screen, (235, 255, 255), (box[0] + 80, box[1] + 69), 4)
    text(screen, dialogue_speaker, box[0] + 135, box[1] + 18, SMALL, (139, 225, 255))
    line = dialogue_lines[min(dialogue_index, len(dialogue_lines) - 1)]
    for i, row in enumerate(wrap_text(line, SMALL, 590)[:3]):
        text(screen, row, box[0] + 135, box[1] + 48 + i * 23, SMALL)
    if dialogue_index >= len(dialogue_lines) - 1:
        for i, (label, _) in enumerate(dialogue_choices):
            draw_button(f"{i + 1}. {label}", (box[0] + 135 + (i % 2) * 300, box[1] + 142 + (i // 2) * 43, 280, 35))
        text(screen, "Choose with mouse or press 1–3", box[0] + 135, box[1] + 208, TINY, (184, 165, 205))
    else:
        text(screen, "Press ENTER / SPACE or click to continue", box[0] + 135, box[1] + 190, TINY, (184, 165, 205))

def choose_dialogue(index):
    global dialogue_index, dialogue_choices
    if index < 0 or index >= len(dialogue_choices):
        return
    action = dialogue_choices[index][1]
    play_sound(sound_click)
    if action == "story_next":
        if dialogue_index < len(dialogue_lines)-1:
            dialogue_index += 1
        else:
            dialogue_choices = [("Return to stories", "story_gallery"), ("Keep exploring", "close")]
        return
    if action == "story_gallery":
        set_game_mode("story_gallery")
    elif action == "close":
        set_game_mode("game")
        set_message("The Witness's words linger in the cold air.", 3)
    else:
        start_dialogue(action)

def interact():
    global puzzle_input, puzzle_feedback
    lev = current_level()
    clue_dist = math.hypot(lev["clue"][0] - player_x, lev["clue"][1] - player_y)
    exit_dist = math.hypot(lev["exit"][0] - player_x, lev["exit"][1] - player_y)
    friend_dist = math.hypot(lev["friend"][0] - player_x, lev["friend"][1] - player_y)
    if friend_dist < 1.5:
        start_dialogue("flower_story" if "flower_memory" in quest_flags else "intro")
        return
    if clue_dist < 1.45 and level_index not in clues_found:
        puzzle_input, puzzle_feedback = "", ""
        set_game_mode("puzzle")
        return
    if exit_dist < 1.5:
        if level_index not in clues_found:
            set_message("The moon seal is closed. Decode the Witness's message first.", 4)
            play_sound(sound_warning)
        elif level_index < len(LEVELS) - 1:
            reset_level(level_index + 1)
            set_message("The staircase descends. Something below has heard you.", 4)
            play_sound(sound_success)
            start_dialogue("intro")
        else:
            persist_save(won=True)
            set_game_mode("victory")
            play_sound(sound_success)
        return
    set_message("Nothing close enough. Find the cyan sigil or the floating Witness.", 2.5)

def submit_puzzle():
    global puzzle_feedback, wrong_answer_timer

    answer = "".join(ch for ch in puzzle_input.strip().upper() if ch.isalpha())
    expected = "".join(ch for ch in current_level()["answer"] if ch.isalpha())

    if answer == expected:
        clues_found.add(level_index)
        persist_save()
        puzzle_feedback = "CORRECT! SEAL BROKEN! WELL DONE!"
        play_sound(sound_success)

        if level_index < len(LEVELS) - 1:
            # Show a celebration screen and let the player choose to continue.
            set_game_mode("level_complete")
        else:
            # The final cipher completes the whole game.
            persist_save(won=True)
            set_game_mode("victory")
    else:
        puzzle_feedback = "WRONG ANSWER! Returning to the beginning..."
        play_sound(sound_warning)
        wrong_answer_timer = 2.5
        set_game_mode("wrong_answer")


def draw_settings():
    draw_menu_background()
    panel(screen, (WIDTH // 2 - 310, 25, 620, HEIGHT - 50), 240)
    text(screen, "SETTINGS", WIDTH // 2, 56, TITLE, center=True)
    items = [("Master volume", "master_volume", 108), ("Music volume", "music_volume", 166),
             ("Sound effects", "sfx_volume", 224), ("Mouse sensitivity", "sensitivity", 282)]
    sliders = []
    for label, key, y in items:
        text(screen, label, WIDTH // 2 - 235, y, SMALL)
        shown = f"{int(settings[key] * 100)}%" if "volume" in key else f"{settings[key] * 1000:.1f}"
        text(screen, shown, WIDTH // 2 + 230, y, SMALL)
        r = pygame.Rect(WIDTH // 2 - 235, y + 24, 470, 9)
        lo, hi = (0.0, 1.0) if "volume" in key else (0.0008, 0.005)
        pygame.draw.rect(screen, (62, 48, 83), r, border_radius=5)
        ratio = max(0.0, min(1.0, (settings[key] - lo) / (hi - lo)))
        pygame.draw.rect(screen, (171, 106, 240), (r.x, r.y, int(r.w * ratio), r.h), border_radius=5)
        pygame.draw.circle(screen, (244, 228, 255), (r.x + int(r.w * ratio), r.centery), 8)
        sliders.append((key, r, lo, hi))

    text(screen, "Radar overlay", WIDTH // 2 - 235, 342, SMALL)
    radar_btn = draw_button("ENABLED" if settings.get("minimap", True) else "DISABLED", (WIDTH // 2 + 85, 334, 150, 34))

    text(screen, "Head bobbing", WIDTH // 2 - 235, 388, SMALL)
    bob_btn = draw_button("ENABLED" if settings.get("head_bob", True) else "DISABLED", (WIDTH // 2 + 85, 380, 150, 34))

    text(screen, "Interface theme", WIDTH // 2 - 235, 434, SMALL)
    theme = draw_button("DARK MODE: ON" if settings.get("dark_mode", True) else "LIGHT MODE: ON", (WIDTH // 2 + 35, 426, 200, 34))

    text(screen, "Difficulty", WIDTH // 2 - 235, 480, SMALL)
    diff_rects = {}
    for i, diff in enumerate(["Story", "Normal", "Nightmare"]):
        diff_rects[diff] = draw_button(diff, (WIDTH // 2 - 40 + i * 105, 472, 98, 34), settings.get("difficulty") == diff)

    reset = draw_button("Reset defaults", (WIDTH // 2 - 220, 532, 190, 38))
    back = draw_button("Back", (WIDTH // 2 + 30, 532, 190, 38))
    buttons = {"theme": theme, "radar": radar_btn, "bob": bob_btn, "reset": reset, "back": back, **diff_rects}
    return sliders, buttons

def draw_customize():
    draw_menu_background()
    panel(screen, (WIDTH // 2 - 300, 55, 600, HEIGHT - 110), 240)
    text(screen, "CHARACTER SELECT", WIDTH // 2, 88, TITLE, center=True)
    names = ["Manor Hunter", "Moon Witch", "Royal Knight", "Phantom"]
    idx = int(settings.get("character_type", 0)) % len(names)
    colors = [(35, 31, 50), (43, 76, 111), (105, 35, 65), (43, 87, 65), (118, 98, 139)]
    cloak = colors[int(settings.get("character_color", 2)) % len(colors)]
    cx, cy = WIDTH // 2, 245
    pygame.draw.ellipse(screen, (2, 2, 9), (cx-90, cy+80, 180, 27))
    if idx == 0:
        pygame.draw.polygon(screen, cloak, [(cx-68,cy+95),(cx-48,cy+5),(cx-25,cy-10),(cx+25,cy-10),(cx+48,cy+5),(cx+68,cy+95)])
        pygame.draw.ellipse(screen,(214,170,139),(cx-25,cy-62,50,62))
        pygame.draw.arc(screen,(30,18,35),(cx-28,cy-75,56,72),math.pi,2*math.pi,10)
    elif idx == 1:
        pygame.draw.polygon(screen, cloak, [(cx-75,cy+95),(cx-40,cy-8),(cx+40,cy-8),(cx+75,cy+95)])
        pygame.draw.polygon(screen,(40,25,62),[(cx-40,cy-48),(cx,cy-112),(cx+40,cy-48)])
        pygame.draw.ellipse(screen,(214,184,166),(cx-22,cy-58,44,55))
    elif idx == 2:
        pygame.draw.polygon(screen, cloak, [(cx-65,cy+95),(cx-55,cy-4),(cx+55,cy-4),(cx+65,cy+95)])
        pygame.draw.rect(screen,(150,160,180),(cx-31,cy-65,62,64),border_radius=9)
        pygame.draw.rect(screen,(55,65,85),(cx-22,cy-45,44,9),border_radius=3)
        pygame.draw.polygon(screen,(190,195,210),[(cx-30,cy-65),(cx-20,cy-88),(cx,cy-72),(cx+20,cy-88),(cx+30,cy-65)])
    else:
        pygame.draw.polygon(screen, cloak, [(cx-75,cy+95),(cx-55,cy-25),(cx-30,cy-50),(cx+30,cy-50),(cx+55,cy-25),(cx+75,cy+95),(cx+35,cy+75),(cx,cy+98),(cx-35,cy+75)])
        pygame.draw.ellipse(screen,(195,220,235),(cx-28,cy-72,56,68))
        pygame.draw.ellipse(screen,(25,30,55),(cx-20,cy-48,12,8))
        pygame.draw.ellipse(screen,(25,30,55),(cx+8,cy-48,12,8))
    text(screen, "Choose your hero", WIDTH // 2, 365, FONT, center=True)
    text(screen, names[idx], WIDTH // 2, 400, SMALL, (216,177,255), center=True)
    left = draw_button("◀ Previous", (WIDTH//2-205, 450, 165, 43))
    right = draw_button("Next ▶", (WIDTH//2+40, 450, 165, 43))
    back = draw_button("Save & Back", (WIDTH//2-105, 515, 210, 43))
    return left, right, back


def draw_puzzle():
    draw_world()
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 155))
    screen.blit(overlay, (0, 0))
    panel(screen, (WIDTH // 2 - 355, HEIGHT // 2 - 210, 710, 420), 245)
    text(screen, "THE WITNESS' CIPHER", WIDTH // 2, HEIGHT // 2 - 165, TITLE, center=True)
    text(screen, "Decode this message. Caesar shift: -2", WIDTH // 2, HEIGHT // 2 - 112, SMALL, center=True)
    text(screen, current_level()["cipher"], WIDTH // 2, HEIGHT // 2 - 66, BIG, (107, 225, 255), center=True)
    text(screen, current_level()["hint"], WIDTH // 2, HEIGHT // 2 - 18, SMALL, center=True)
    inp = pygame.Rect(WIDTH // 2 - 270, HEIGHT // 2 + 24, 540, 48)
    pygame.draw.rect(screen, (25, 18, 42), inp, border_radius=8)
    pygame.draw.rect(screen, (161, 116, 226), inp, 2, border_radius=8)
    cursor = "▌" if (pygame.time.get_ticks() // 450) % 2 == 0 else ""
    text(screen, puzzle_input + cursor, inp.x + 14, inp.y + 10, FONT, (245, 235, 255))
    text(screen, "Type the full decoded sentence and press ENTER. Press J for Journal wheel. ESC closes.",
         WIDTH // 2, HEIGHT // 2 + 94, SMALL, center=True)
    if puzzle_feedback:
        color = (125, 255, 180) if "Correct" in puzzle_feedback else (255, 145, 160)
        text(screen, puzzle_feedback, WIDTH // 2, HEIGHT // 2 + 145, SMALL, color, center=True)

def draw_overlay(title, subtitle, buttons):
    draw_menu_background()
    panel(screen, (WIDTH // 2 - 310, HEIGHT // 2 - 235, 620, 470), 240)
    text(screen, title, WIDTH // 2, HEIGHT // 2 - 168, TITLE, center=True)
    for i, line in enumerate(wrap_text(subtitle, SMALL, 520)[:2]):
        text(screen, line, WIDTH // 2, HEIGHT // 2 - 118 + i * 22, SMALL, center=True)
    rects = {}
    start_y = HEIGHT // 2 - 48
    for i, label in enumerate(buttons):
        rects[label] = draw_button(label, (WIDTH // 2 - 165, start_y + i * 57, 330, 43))
    return rects

def draw_instructions():
    draw_menu_background()
    panel(screen, (WIDTH // 2 - 380, 50, 760, HEIGHT - 100), 242)
    text(screen, "HOW TO SURVIVE", WIDTH // 2, 80, TITLE, center=True)
    instructions = [
        ("MOVE", "W / A / S / D — walk and strafe. Arrow keys can also turn."),
        ("SPRINT", "Hold LEFT SHIFT to sprint. Consumes stamina."),
        ("LANTERN STUN", "Press SPACE or RIGHT CLICK to emit a blinding flash. Stuns the monster!"),
        ("JOURNAL", "Press J to view solved seals, notes, and the built-in cipher wheel."),
        ("RADAR", "Press M to toggle the real-time mini-map radar overlay."),
        ("CIPHERS", "Seals use Caesar cipher (+2). Shift letters backward by 2 (e.g. C -> A)."),
        ("INTERACT", "Press E near the floating Witness, cyan sigil, or Moon Door."),
    ]
    y = 132
    for head, body in instructions:
        text(screen, head, WIDTH // 2 - 320, y, SMALL, (181, 134, 237))
        y += 22
        for line in wrap_text(body, SMALL, 640):
            text(screen, line, WIDTH // 2 - 320, y, SMALL)
            y += 20
        y += 6
    back = draw_button("Back to Menu", (WIDTH // 2 - 115, HEIGHT - 92, 230, 40))
    return back

def find_button(rects, pos):
    for label, rect in rects.items():
        if rect.collidepoint(pos):
            return label
    return None

def difficulty_values():
    return {
        "Story": (1.05, 0.45, 2.8),
        "Normal": (1.0, 0.70, 5.5),
        "Nightmare": (0.78, 1.05, 7.2)
    }.get(
        settings.get("difficulty", "Normal"),
        (1.0, 0.7, 5.5)
    )

def draw_3d_title_menu():
    """Animated pseudo-3D gothic title screen, rendered with native Pygame shapes."""
    t = ambient_time
    screen.fill((5, 5, 18))
    # Deep night gradient
    for y in range(0, HEIGHT, 4):
        k = y / max(1, HEIGHT)
        col = (int(7 + 10*k), int(7 + 2*k), int(22 + 18*k))
        pygame.draw.rect(screen, col, (0, y, WIDTH, 4))
    # Moon and slow halo
    mx, my = int(WIDTH*.78 + math.sin(t*.16)*12), int(HEIGHT*.20)
    for radius, alpha in ((86, 18), (68, 24), (54, 35)):
        glow = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (170, 135, 225, alpha), (radius, radius), radius)
        screen.blit(glow, (mx-radius, my-radius))
    pygame.draw.circle(screen, (235, 225, 255), (mx, my), 39)
    pygame.draw.circle(screen, (17, 12, 35), (mx+15, my-10), 35)
    # Distant 3D silhouettes and perspective fog
    ground = int(HEIGHT*.70)
    for layer in range(4):
        col = (13+layer*3, 10+layer*2, 30+layer*5)
        ybase = ground + layer*14
        for i in range(11):
            x = int(i*WIDTH/10 - 45 + math.sin(t*.12+layer)*8)
            w = 85 + layer*14
            h = 110 + ((i*53+layer*37) % 130) + layer*15
            pygame.draw.rect(screen, col, (x, ybase-h, w, h+120))
            pygame.draw.polygon(screen, col, [(x-10,ybase-h),(x+w//2,ybase-h-55-layer*5),(x+w+10,ybase-h)])
            for wy in range(ybase-h+22, ybase-12, 32):
                pygame.draw.arc(screen, (76, 44, 91), (x+w//2-10,wy,20,27), 0, math.pi, 2)
    # A framed glimpse of the candlelit dining hall introduces the manor's
    # lost banquet and uses the fourth supplied image in the title scene.
    try:
        card_w, card_h = int(WIDTH * 0.27), int(HEIGHT * 0.29)
        dining_card = pygame.transform.smoothscale(DINING_TEXTURE, (card_w, card_h))
        card_x, card_y = int(WIDTH * 0.055), int(HEIGHT * 0.34)
        pygame.draw.rect(screen, (105, 73, 43), (card_x - 7, card_y - 7, card_w + 14, card_h + 14), border_radius=5)
        pygame.draw.rect(screen, (222, 177, 102), (card_x - 4, card_y - 4, card_w + 8, card_h + 8), 2, border_radius=4)
        screen.blit(dining_card, (card_x, card_y))
        shade = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        shade.fill((8, 5, 18, 55))
        screen.blit(shade, (card_x, card_y))
    except pygame.error:
        pass

    # Central mansion, faux perspective walls, tower roofs
    cx = int(WIDTH*.72); base = int(HEIGHT*.78); mansion_w = int(min(WIDTH*.42, 460))
    left, right = cx-mansion_w//2, cx+mansion_w//2
    wall_top = int(HEIGHT*.31 + math.sin(t*.6)*2)
    pygame.draw.polygon(screen, (35, 22, 48), [(left,base),(left+40,wall_top+35),(right-35,wall_top),(right,base)])
    pygame.draw.polygon(screen, (18, 13, 30), [(left,base),(left+40,wall_top+35),(left+40,base-100)])
    pygame.draw.polygon(screen, (52, 29, 59), [(left+40,wall_top+35),(cx,wall_top-75),(right-35,wall_top)])
    pygame.draw.polygon(screen, (25, 17, 39), [(cx-48,wall_top+18),(cx,wall_top-100),(cx+48,wall_top+18)])
    pygame.draw.polygon(screen, (12, 10, 24), [(cx-30,base),(cx-30,base-112),(cx,base-145),(cx+30,base-112),(cx+30,base)])
    pygame.draw.arc(screen, (181, 115, 202), (cx-30,base-145,cx+30-(cx-30),90), 0, math.pi, 2)
    # Windows breathe with supernatural light
    for wx, wy in [(left+82,wall_top+90),(left+145,wall_top+110),(right-150,wall_top+82),(right-88,wall_top+100),(cx-82,wall_top+38),(cx+56,wall_top+38)]:
        pulse = int(28 + 25*(.5+.5*math.sin(t*2.0+wx)))
        pygame.draw.rect(screen, (pulse+35, 45, pulse+70), (wx,wy,22,36), border_radius=8)
        pygame.draw.line(screen, (120,84,145), (wx+11,wy),(wx+11,wy+36),1)
    # Perspective path towards the entrance
    pygame.draw.polygon(screen, (24, 18, 35), [(cx-34,base),(cx+34,base),(WIDTH*.93,HEIGHT),(WIDTH*.48,HEIGHT)])
    for i in range(1,8):
        yy = base + (HEIGHT-base)*(i/8)**1.8
        pygame.draw.line(screen, (73, 48, 82), (cx-34-(i*10),yy),(cx+34+(i*10),yy),1)
    # Floating rose petals with looping trajectories
    for i, seed in enumerate(menu_petal_seed):
        x = int((seed*WIDTH + math.sin(t*.65+i)*28) % WIDTH)
        y = int((seed*HEIGHT + t*(18+(i%5)*7)) % HEIGHT)
        r = 2 + (i%3)
        pygame.draw.ellipse(screen, (125+(i%3)*22, 48, 91+(i%4)*20), (x,y,r*2,r), 0)
    draw_seasonal_effects()
    # Vignette edges and cinematic title plaque
    vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(vignette, (0,0,0,80), (0,0,WIDTH,HEIGHT), 24)
    screen.blit(vignette, (0,0))
    plaque = pygame.Rect(int(WIDTH*.055), int(HEIGHT*.12), int(WIDTH*.43), int(HEIGHT*.74))
    panel(screen, plaque, 238)
    # gold inner frame
    pygame.draw.rect(screen, (174,128,91), plaque.inflate(-14,-14), 1, border_radius=12)
    title_y = plaque.y + 48
    title_shadow = BIG.render("CRYPTIC ESCAPE", True, (65, 30, 72))
    title_front = BIG.render("CRYPTIC ESCAPE", True, (246, 222, 239))
    title_shadow_rect = title_shadow.get_rect(center=(plaque.centerx+3,title_y+4))
    title_front_rect = title_front.get_rect(center=(plaque.centerx,title_y))
    screen.blit(title_shadow,title_shadow_rect)
    screen.blit(title_front,title_front_rect)
    text(screen, "THE CURSED MANOR", plaque.centerx, title_y+45, FONT, (221,170,202), center=True)
    text(screen, "A 3D GOTHIC PUZZLE ADVENTURE", plaque.centerx, title_y+72, TINY, (187,170,210), center=True)
    labels = ["New Game", "Continue", "Mini Games & Tasks", "Customize Character", "Settings", "How to Play", "Quit"]
    rects = {}
    if HEIGHT < 620:
        start_y = plaque.y + 174
        for i,label in enumerate(labels):
            col, row = i % 2, i // 2
            r = pygame.Rect(plaque.centerx-172+col*180, start_y+row*43, 166, 35)
            rects[label] = draw_button(label, r, active=(i==0 and int(t*1.4)%5==0))
        text(screen, "WASD TO EXPLORE  •  E TO INTERACT  •  J FOR JOURNAL", plaque.centerx, plaque.bottom-12, TINY, (177,160,197), center=True)
    else:
        start_y = plaque.y + 145
        gap = min(51, max(38, (plaque.height - 190) // 6))
        for i,label in enumerate(labels):
            r = pygame.Rect(plaque.centerx-145, start_y+i*gap, 290, 38)
            rects[label] = draw_button(label, r, active=(i==0 and int(t*1.4)%5==0))
        text(screen, "WASD TO EXPLORE  •  E TO INTERACT  •  J FOR JOURNAL", plaque.centerx, plaque.bottom-26, TINY, (177,160,197), center=True)
    text(screen, SEASON_THEMES.get(active_theme, SEASON_THEMES["Haunted"])["subtitle"], int(WIDTH*.74), int(HEIGHT*.91), SMALL, (229,190,215), center=True)
    return rects

def draw_hub(title="THE MANOR'S SIDE STORIES"):
    draw_menu_background()
    panel(screen,(WIDTH//2-350,42,700,HEIGHT-84),245)
    text(screen,title,WIDTH//2,78,TITLE,center=True)
    cards = [
        ("Flower Memory", "Match six pairs. Restore a memory of the kindest soul."),
        ("Ghost Signal", "Repeat the ghost's growing sequence of lights."),
        ("Candle Order", "Light five candles in the order hidden in the rhyme."),
        ("Quest Board", "Review your main objective and optional tasks."),
        ("Story Chapters", "Read four hidden stories from the manor's past."),
        ("Theme Gallery", "Switch between Haunted, Halloween, Christmas and snow."),
        ("Back to Title", "Return to the mansion gates.")
    ]
    rects={}
    for i,(name,desc) in enumerate(cards):
        col=i%2; row=i//2
        x=WIDTH//2-315+col*325; y=118+row*112
        r=pygame.Rect(x,y,300,94)
        pygame.draw.rect(screen,(27,18,43),r,border_radius=12)
        pygame.draw.rect(screen,(157,103,178) if i<3 else (174,137,102),r,2,border_radius=12)
        text(screen,name,r.centerx,r.y+22,SMALL,(245,215,237),center=True)
        for j,line in enumerate(wrap_text(desc,TINY,260)[:2]): text(screen,line,r.centerx,r.y+47+j*16,TINY,(198,184,211),center=True)
        rects[name]=r
    return rects

def draw_story_gallery():
    draw_menu_background()
    draw_seasonal_effects()
    panel(screen, (WIDTH//2-365, 42, 730, HEIGHT-84), 246)
    text(screen, "THE MANOR'S LOST CHAPTERS", WIDTH//2, 77, TITLE, center=True)
    text(screen, "Choose a memory. Every story changes how the house feels.", WIDTH//2, 111, SMALL, (205,184,220), center=True)
    cards = [("The Portrait That Blinked", "story_portrait"), ("The Christmas Room", "story_christmas"),
             ("The Last Train at Midnight", "story_train"), ("The Family Secret", "story_secret")]
    rects = {}
    for i, (label, key) in enumerate(cards):
        col, row = i % 2, i // 2
        r = pygame.Rect(WIDTH//2-330+col*340, 150+row*145, 315, 116)
        pygame.draw.rect(screen, (24,16,37), r, border_radius=12)
        pygame.draw.rect(screen, SEASON_THEMES.get(active_theme, SEASON_THEMES["Haunted"])["accent"], r, 2, border_radius=12)
        # little animated painting thumbnail
        pygame.draw.rect(screen, (100,65,52), (r.x+14,r.y+17,55,72), 4)
        pygame.draw.ellipse(screen, (168,140,145), (r.x+29,r.y+31,25,29))
        pygame.draw.ellipse(screen, (25,19,31), (r.x+22,r.y+57,39,27))
        text(screen, label, r.centerx+28, r.y+35, SMALL, (246,220,240), center=True)
        text(screen, "Read this chapter", r.centerx+28, r.y+66, TINY, (197,178,212), center=True)
        rects[label] = (r, key)
    back = draw_button("Back to Side Stories", (WIDTH//2-135, HEIGHT-76, 270, 38))
    rects["Back to Side Stories"] = (back, "back")
    return rects


def draw_theme_gallery():
    draw_menu_background()
    draw_seasonal_effects()
    panel(screen, (WIDTH//2-365, 42, 730, HEIGHT-84), 246)
    text(screen, "SEASONAL REALMS", WIDTH//2, 78, TITLE, center=True)
    text(screen, "Pick a visual mood. Press T during gameplay to cycle themes.", WIDTH//2, 112, SMALL, (205,184,220), center=True)
    descriptions = {
        "Haunted": "Will-o'-wisps and watchful portraits", "Halloween": "Bats, ember leaves and pumpkin glow",
        "Christmas": "Snowfall and twinkling fairy lights", "Winter Snow": "Quiet blue frost and drifting snow",
        "Blood Moon": "Crimson motes beneath a cursed sky"
    }
    rects = {}
    for i, (name, info) in enumerate(descriptions.items()):
        col, row = i%2, i//2
        r = pygame.Rect(WIDTH//2-325+col*335, 150+row*100, 310, 78)
        accent = SEASON_THEMES[name]["accent"]
        pygame.draw.rect(screen, (23,16,36), r, border_radius=11)
        pygame.draw.rect(screen, accent, r, 3 if name == active_theme else 1, border_radius=11)
        # seasonal preview orb
        pygame.draw.circle(screen, accent, (r.x+34,r.centery), 15)
        pygame.draw.circle(screen, (245,235,255), (r.x+29,r.centery-5), 5)
        text(screen, name + ("  ✓" if name == active_theme else ""), r.x+62, r.y+18, SMALL, (248,225,245))
        text(screen, info, r.x+62, r.y+45, TINY, (196,181,210))
        rects[name] = r
    back = draw_button("Back to Side Stories", (WIDTH//2-135, HEIGHT-75, 270, 38))
    rects["Back to Side Stories"] = back
    return rects


def draw_quest_board():
    draw_menu_background()
    panel(screen,(WIDTH//2-370,45,740,HEIGHT-90),245)
    text(screen,"QUEST BOARD",WIDTH//2,78,TITLE,center=True)
    y=140
    for kind,title,desc in QUESTS:
        done = (title=="Break the three cipher seals" and len(clues_found)==len(LEVELS)) or \
               (title=="The kindest soul" and "flower_memory" in quest_flags) or \
               (title=="A song without a singer" and "ghost_signal" in quest_flags) or \
               (title=="Five lights, one truth" and "candle_order" in quest_flags) or \
               (title=="Collector of forgotten things" and "flower_memory" in quest_flags)
        pygame.draw.circle(screen,(123,238,168) if done else (218,168,225),(WIDTH//2-315,y+8),6)
        text(screen,("✓ " if done else "◇ ")+title,WIDTH//2-294,y,SMALL,(143,245,181) if done else (231,207,239))
        for j,line in enumerate(wrap_text(desc,TINY,580)[:2]): text(screen,line,WIDTH//2-294,y+24+j*18,TINY,(193,181,207))
        y+=78
    back=draw_button("Back to Side Stories",(WIDTH//2-135,HEIGHT-94,270,42))
    return back

def start_minigame(name):
    mini_game_state.update({"name":name,"cards":[],"revealed":[],"matched":set(),"sequence":[],"player_sequence":[],"phase":"ready","timer":0.0,"round":1,"candles":[0,0,0,0,0],"feedback":""})
    if name=="Flower Memory":
        deck=["ROSE","ROSE","LILY","LILY","IRIS","IRIS","VIOLET","VIOLET","DAISY","DAISY","LOTUS","LOTUS"]
        random.shuffle(deck); mini_game_state["cards"]=deck
    elif name=="Ghost Signal":
        mini_game_state["sequence"]=[random.randrange(4)]
        mini_game_state["phase"]="show"; mini_game_state["timer"]=1.05
    elif name=="Candle Order":
        mini_game_state["sequence"]=[0,1,2,3,4]
    set_game_mode("minigame_play")

def draw_minigame():
    draw_menu_background()
    name=mini_game_state["name"]
    panel(screen,(WIDTH//2-360,35,720,HEIGHT-70),245)
    text(screen,name.upper(),WIDTH//2,70,TITLE,center=True)
    rects={}
    if name=="Flower Memory":
        text(screen,"Find all six flower pairs. A match restores one memory.",WIDTH//2,110,SMALL,center=True)
        card_w,card_h=92,78; gap=12; total=6*card_w+5*gap; sx=WIDTH//2-total//2; sy=160
        for i,sym in enumerate(mini_game_state["cards"]):
            row,col=divmod(i,6); r=pygame.Rect(sx+col*(card_w+gap),sy+row*(card_h+gap),card_w,card_h)
            visible=i in mini_game_state["revealed"] or i in mini_game_state["matched"]
            pygame.draw.rect(screen,(81,36,75) if visible else (35,24,55),r,border_radius=10)
            pygame.draw.rect(screen,(232,161,207) if visible else (136,93,165),r,2,border_radius=10)
            text(screen,sym if visible else "✦",r.centerx,r.centery,SMALL,(255,220,237),center=True)
            rects[str(i)]=r
        if len(mini_game_state["matched"])==12:
            mini_game_state["feedback"]="Memory restored! The Witness remembers the garden."
            quest_flags.add("flower_memory"); persist_save()
            text(screen,"MEMORY RESTORED!",WIDTH//2,HEIGHT-125,FONT,(144,255,190),center=True)
        else: text(screen,mini_game_state["feedback"] or f"Pairs found: {len(mini_game_state['matched'])//2} / 6",WIDTH//2,HEIGHT-125,SMALL,(226,196,231),center=True)
    elif name=="Ghost Signal":
        text(screen,"Watch the sequence, then repeat it using the four sigils.",WIDTH//2,116,SMALL,center=True)
        colors=[(202,91,135),(109,185,213),(208,177,104),(156,118,211)]
        active=-1
        if mini_game_state["phase"]=="show":
            mini_game_state["timer"]-=1/60
            total=len(mini_game_state["sequence"])*0.55+0.5
            elapsed=total-mini_game_state["timer"]
            idx=int(elapsed/0.55)
            active=mini_game_state["sequence"][idx] if idx < len(mini_game_state["sequence"]) and elapsed % 0.55 < 0.36 else -1
            if mini_game_state["timer"]<=0: mini_game_state["phase"]="input"; mini_game_state["player_sequence"]=[]
            text(screen,"MEMORIZE THE LIGHTS",WIDTH//2,155,SMALL,(238,207,245),center=True)
        for i in range(4):
            r=pygame.Rect(WIDTH//2-210+(i%2)*230,205+(i//2)*145,180,110)
            c=colors[i] if i==active else tuple(int(v*.45) for v in colors[i])
            pygame.draw.rect(screen,c,r,border_radius=18); pygame.draw.rect(screen,(245,222,247),r,2,border_radius=18)
            text(screen,["ROSE","MOON","FLAME","EYE"][i],r.centerx,r.centery,SMALL,(255,247,255),center=True); rects[str(i)]=r
        text(screen,mini_game_state["feedback"] or f"Sequence length: {len(mini_game_state['sequence'])}",WIDTH//2,HEIGHT-100,SMALL,(226,196,231),center=True)
    elif name=="Candle Order":
        text(screen,"The nursery rhyme says: Flame, Rose, Star, Moon, Thorn.",WIDTH//2,118,SMALL,center=True)
        colors=[(211,178,103),(194,83,128),(144,163,228),(161,132,201),(98,160,115)]
        labels=["FLAME","ROSE","STAR","MOON","THORN"]
        for i in range(5):
            x=WIDTH//2-270+i*110; y=215
            glow=mini_game_state["candles"][i]
            pygame.draw.ellipse(screen,(colors[i] if glow else (48,37,56)),(x,y,64,90))
            pygame.draw.rect(screen,(106,83,113),(x+24,y+53,16,67),border_radius=4)
            if glow:
                pygame.draw.circle(screen,(*colors[i],100),(x+32,y+12),28)
                pygame.draw.ellipse(screen,(255,229,166),(x+24,y-3,16,35))
            text(screen,labels[i],x+32,y+135,TINY,(239,217,242),center=True)
            rects[str(i)]=pygame.Rect(x-8,y-8,80,145)
        text(screen,"Click candles in the correct order. Clicked candles stay lit.",WIDTH//2,420,SMALL,center=True)
        text(screen,mini_game_state["feedback"] or f"Candles lit: {sum(mini_game_state['candles'])}/5",WIDTH//2,HEIGHT-100,SMALL,(226,196,231),center=True)
    back=draw_button("Back to Side Stories",(WIDTH//2-135,HEIGHT-70,270,38))
    rects["Back to Side Stories"]=back
    return rects

def handle_minigame_click(key):
    st=mini_game_state
    if st["name"]=="Flower Memory":
        i=int(key)
        if i in st["matched"] or i in st["revealed"]: return
        st["revealed"].append(i)
        if len(st["revealed"])==2:
            a,b=st["revealed"]
            if st["cards"][a]==st["cards"][b]:
                st["matched"].update((a,b)); st["revealed"]=[]; play_sound(sound_success)
            else:
                st["feedback"]="Not a pair. Keep their positions in mind."
                # Cards remain visible until next click; the next click hides the mismatch.
                st["phase"]="hide_next"
        elif st["phase"]=="hide_next":
            st["revealed"]=[i]; st["phase"]="ready"
    elif st["name"]=="Ghost Signal" and st["phase"]=="input":
        val=int(key); st["player_sequence"].append(val)
        if st["player_sequence"][-1]!=st["sequence"][len(st["player_sequence"])-1]:
            st["feedback"]="The signal broke. Try the sequence again."
            st["player_sequence"]=[]; st["phase"]="show"; st["timer"]=1.0
        elif len(st["player_sequence"])==len(st["sequence"]):
            if len(st["sequence"])>=5:
                st["feedback"]="Signal restored! A hidden melody returns."
                quest_flags.add("ghost_signal"); persist_save()
            else:
                st["sequence"].append(random.randrange(4)); st["phase"]="show"; st["timer"]=1.0; st["round"]+=1
                st["feedback"]="Correct. The ghost adds another note..."
    elif st["name"]=="Candle Order":
        i=int(key); expected=st["sequence"][sum(st["candles"])]
        if i==expected:
            st["candles"][i]=1; play_sound(sound_success)
            if sum(st["candles"])==5:
                st["feedback"]="The passage opens. The candle task is complete."
                quest_flags.add("candle_order"); persist_save()
        else:
            st["candles"]=[0,0,0,0,0]; st["feedback"]="A candle gutters out. Read the rhyme and try again."
            play_sound(sound_warning)

def main():
    global WIDTH, HEIGHT, screen, is_running, player_x, player_y, player_angle
    # main() advances dialogue lines in response to keyboard input.
    # Declare this global so Python does not treat it as an uninitialized local.
    global dialogue_index
    global enemy_x, enemy_y, enemy_alert, enemy_stunned, health, stamina, lantern_oil
    global message_timer, damage_cooldown, puzzle_input, puzzle_feedback, settings, level_index, clues_found
    global wrong_answer_timer
    global slider_drag, ambient_time, step_cycle, bob_offset, screen_flash, heartbeat_timer, footstep_timer

    set_game_mode("menu")
    ambient_channel = None
    if sound_ambient:
        try:
            ambient_channel = sound_ambient.play(loops=-1)
        except Exception:
            ambient_channel = None

    while is_running:
        dt = min(0.04, clock.tick(60) / 1000.0)
        ambient_time += dt
        # Keep the haunted ambience subtle and respect the music/master sliders.
        if ambient_channel:
            try:
                music_vol = float(settings.get("master_volume", 0.65)) * float(settings.get("music_volume", 0.35))
                mode_factor = 0.95 if mode == "game" else (0.35 if mode in ("pause", "settings", "instructions") else 0.55)
                ambient_channel.set_volume(max(0.0, min(1.0, music_vol * mode_factor)))
            except Exception:
                pass
        message_timer = max(0.0, message_timer - dt)
        if mode == "minigame_play" and mini_game_state.get("name") == "Flower Memory" and mini_game_state.get("phase") == "hide_next":
            mini_game_state["timer"] += dt
            if mini_game_state["timer"] >= 0.7:
                mini_game_state["revealed"] = []
                mini_game_state["phase"] = "ready"
                mini_game_state["timer"] = 0.0
        if mode == "wrong_answer":
            wrong_answer_timer = max(0.0, wrong_answer_timer - dt)
            if wrong_answer_timer <= 0:
                clues_found.clear()
                puzzle_input = ""
                puzzle_feedback = ""
                reset_level(0)
                set_message("A new attempt begins. Decode the first seal!", 4.0)
                set_game_mode("menu")
        damage_cooldown = max(0.0, damage_cooldown - dt)
        screen_flash = max(0.0, screen_flash - dt * 2.5)
        if enemy_stunned > 0:
            enemy_stunned = max(0.0, enemy_stunned - dt)

        # Passive oil regeneration
        lantern_oil = min(100.0, lantern_oil + dt * 4.0)

        mouse_delta = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                persist_save()
                persist_settings()
                is_running = False

            elif event.type == pygame.VIDEORESIZE:
                WIDTH, HEIGHT = max(800, event.w), max(500, event.h)
                screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

            elif event.type == pygame.KEYDOWN:
                if mode == "dialogue" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if dialogue_index < len(dialogue_lines) - 1:
                        dialogue_index += 1
                    else:
                        choose_dialogue(0)
                elif mode == "dialogue" and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    if dialogue_index >= len(dialogue_lines) - 1:
                        choose_dialogue(event.key - pygame.K_1)
                elif event.key == pygame.K_ESCAPE:
                    if mode == "game":
                        set_game_mode("pause")
                    elif mode in ("puzzle", "dialogue", "journal"):
                        set_game_mode("game")
                    elif mode == "settings":
                        set_game_mode(settings_return_mode)
                    elif mode in ("customize", "instructions", "minigames", "quest_board", "story_gallery", "theme_gallery"):
                        set_game_mode("menu" if mode in ("customize", "instructions") else "minigames")
                    elif mode == "minigame_play":
                        set_game_mode("minigames")
                    elif mode == "pause":
                        set_game_mode("game")
                    elif mode in ("victory", "failure", "level_complete", "wrong_answer"):
                        set_game_mode("menu")
                elif mode == "game" and event.key == pygame.K_e:
                    interact()
                elif mode == "game" and event.key == pygame.K_j:
                    set_game_mode("journal")
                elif mode == "journal" and event.key == pygame.K_j:
                    set_game_mode("game")
                elif mode == "game" and event.key == pygame.K_m:
                    settings["minimap"] = not settings.get("minimap", True)
                    persist_settings()
                elif mode == "game" and event.key == pygame.K_SPACE:
                    trigger_lantern_flash()
                elif mode == "puzzle":
                    if event.key == pygame.K_RETURN:
                        submit_puzzle()
                    elif event.key == pygame.K_BACKSPACE:
                        puzzle_input = puzzle_input[:-1]
                    elif event.key == pygame.K_j:
                        set_game_mode("journal")
                    elif event.unicode and event.unicode.isprintable() and len(puzzle_input) < 65:
                        puzzle_input += event.unicode.upper()
                elif mode == "game" and event.key == pygame.K_l:
                    if math.hypot(current_level()["friend"][0]-player_x, current_level()["friend"][1]-player_y) < 4.0:
                        start_dialogue("mirror")
                    else:
                        set_message("The lantern catches a face in the stonework. It is yours.", 2.5)
                elif mode == "game" and event.key == pygame.K_q:
                    set_game_mode("quest_board")
                elif mode == "game" and event.key == pygame.K_t:
                    global active_theme
                    names = list(SEASON_THEMES)
                    active_theme = names[(names.index(active_theme) + 1) % len(names)] if active_theme in names else names[0]
                    settings["active_theme"] = active_theme
                    persist_settings()
                    set_message("Seasonal realm changed: " + active_theme, 2.5)

            elif event.type == pygame.MOUSEMOTION and mode == "game":
                if pygame.mouse.get_focused():
                    mouse_delta += event.rel[0]

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if mode == "game" and event.button == 3:  # Right Click
                    trigger_lantern_flash()
                elif mode == "journal":
                    back = draw_journal()
                    if back.collidepoint(event.pos):
                        set_game_mode("game")
                elif mode == "minigames":
                    clicked = find_button(draw_hub(), event.pos)
                    if clicked in ("Flower Memory", "Ghost Signal", "Candle Order"):
                        start_minigame(clicked)
                    elif clicked == "Quest Board":
                        set_game_mode("quest_board")
                    elif clicked == "Story Chapters":
                        set_game_mode("story_gallery")
                    elif clicked == "Theme Gallery":
                        set_game_mode("theme_gallery")
                    elif clicked == "Back to Title":
                        set_game_mode("menu")
                elif mode == "story_gallery":
                    rects = draw_story_gallery()
                    for label, item in rects.items():
                        r, key = item
                        if r.collidepoint(event.pos):
                            if key == "back":
                                set_game_mode("minigames")
                            else:
                                start_dialogue(key)
                            break
                elif mode == "theme_gallery":
                    rects = draw_theme_gallery()
                    clicked = find_button(rects, event.pos)
                    if clicked in SEASON_THEMES:
                        active_theme = clicked
                        settings["active_theme"] = active_theme
                        persist_settings()
                    elif clicked == "Back to Side Stories":
                        set_game_mode("minigames")
                elif mode == "quest_board":
                    back = draw_quest_board()
                    if back.collidepoint(event.pos):
                        set_game_mode("minigames")
                elif mode == "minigame_play":
                    rects = draw_minigame()
                    clicked = find_button(rects, event.pos)
                    if clicked == "Back to Side Stories":
                        set_game_mode("minigames")
                    elif clicked is not None:
                        handle_minigame_click(clicked)
                elif mode == "settings":
                    sliders, rects = draw_settings()
                    for key, r, lo, hi in sliders:
                        if r.inflate(0, 18).collidepoint(event.pos):
                            slider_drag = (key, r, lo, hi)
                            break
                    if slider_drag is None:
                        clicked = find_button(rects, event.pos)
                        if clicked == "theme":
                            settings["dark_mode"] = not settings.get("dark_mode", True)
                            persist_settings()
                            play_sound(sound_click)
                        elif clicked == "radar":
                            settings["minimap"] = not settings.get("minimap", True)
                            persist_settings() 
                        elif clicked == "bob":
                            settings["head_bob"] = not settings.get("head_bob", True)
                            persist_settings()
                        elif clicked == "reset":
                            settings = DEFAULT_SETTINGS.copy()
                            persist_settings()
                        elif clicked == "back":
                            set_game_mode(settings_return_mode)
                        elif clicked in ("Story", "Normal", "Nightmare"):
                            settings["difficulty"] = clicked
                            persist_settings()

                elif mode == "menu":
                    rects = draw_3d_title_menu()
                    clicked = find_button(rects, event.pos)
                    play_sound(sound_click)
                    if clicked == "New Game":
                        clues_found.clear()
                        puzzle_input = ""
                        puzzle_feedback = ""
                        wrong_answer_timer = 0.0
                        reset_level(0)
                        start_dialogue("intro")
                    elif clicked == "Continue":
                        saved = load_json(SAVE_FILE, {"level": 0, "health": 100, "clues": [], "won": False})
                        clues_found = set(saved.get("clues", []))
                        reset_level(max(0, min(int(saved.get("level", 0)), len(LEVELS) - 1)))
                        health = max(1, min(100, int(saved.get("health", 100))))
                        set_game_mode("game")
                    elif clicked == "Mini Games & Tasks":
                        set_game_mode("minigames")
                    elif clicked == "Customize Character":
                        set_game_mode("customize")
                    elif clicked == "Settings":
                        settings_return_mode = "menu"
                        set_game_mode("settings")
                    elif clicked == "How to Play":
                        set_game_mode("instructions")
                    elif clicked == "Quit":
                        is_running = False

                elif mode == "pause":
                    rects = draw_overlay("PAUSED", "The manor is silent... for now.",
                                         ["Resume", "Journal", "Save Game", "Settings", "How to Play", "Main Menu"])
                    clicked = find_button(rects, event.pos)
                    if clicked == "Resume":
                        set_game_mode("game")
                    elif clicked == "Journal":
                        set_game_mode("journal")
                    elif clicked == "Save Game":
                        persist_save()
                        set_message("Progress saved.", 2)
                    elif clicked == "Settings":
                        settings_return_mode = "pause"
                        set_game_mode("settings")
                    elif clicked == "How to Play":
                        set_game_mode("instructions")
                    elif clicked == "Main Menu":
                        persist_save()
                        set_game_mode("menu")

                elif mode == "customize":
                    left, right, back = draw_customize()
                    if left.collidepoint(event.pos):
                        settings["character_type"] = (settings.get("character_type", 0) - 1) % 4
                    elif right.collidepoint(event.pos):
                        settings["character_type"] = (settings.get("character_type", 0) + 1) % 4
                    elif back.collidepoint(event.pos):
                        persist_settings()
                        set_game_mode("menu")

                elif mode == "dialogue":
                    # Forgiving clicks prevent getting stuck in a dialogue.
                    box = pygame.Rect(WIDTH // 2 - 390, HEIGHT - 260, 780, 230)
                    if dialogue_index < len(dialogue_lines) - 1:
                        dialogue_index += 1
                    else:
                        choice_hit = None
                        for i in range(len(dialogue_choices)):
                            r = pygame.Rect(box.x + 135 + (i % 2) * 300,
                                            box.y + 142 + (i // 2) * 43, 280, 35)
                            if r.collidepoint(event.pos):
                                choice_hit = i
                                break
                        if choice_hit is not None:
                            choose_dialogue(choice_hit)
                        elif box.collidepoint(event.pos) and dialogue_choices:
                            # If the click misses a button (e.g. after resizing),
                            # choose the first visible option rather than trapping the player.
                            choose_dialogue(0)

                elif mode == "instructions":
                    r = draw_instructions()
                    if r.collidepoint(event.pos):
                        set_game_mode("menu")

                elif mode == "level_complete":
                    rects = draw_overlay(
                        "LEVEL COMPLETE!",
                        "Congratulations! You broke the seal. Ready to explore the next level?",
                        ["Continue to Next Level", "Main Menu", "Quit"]
                    )
                    clicked = find_button(rects, event.pos)
                    if clicked == "Continue to Next Level":
                        if level_index < len(LEVELS) - 1:
                            reset_level(level_index + 1)
                            puzzle_input = ""
                            puzzle_feedback = ""
                            set_message("Welcome to " + current_level()["name"] + "!", 4.0)
                            play_sound(sound_success)
                            start_dialogue("intro")
                        else:
                            persist_save(won=True)
                            set_game_mode("victory")
                    elif clicked == "Main Menu":
                        set_game_mode("menu")
                    elif clicked == "Quit":
                        persist_save()
                        persist_settings()
                        is_running = False

                elif mode in ("victory", "failure"):
                    if mode == "victory":
                        title = "CURSE LIFTED!"
                        subtitle = "You solved every cipher and freed the Cursed Manor! You are the hero!"
                    else:
                        title = "THE MANOR CLAIMS YOU"
                        subtitle = "The Hollow has caught you. Try another path."
                    rects = draw_overlay(title, subtitle, ["Play Again", "Main Menu", "Quit"])
                    clicked = find_button(rects, event.pos)
                    if clicked == "Play Again":
                        clues_found.clear()
                        puzzle_input = ""
                        puzzle_feedback = ""
                        wrong_answer_timer = 0.0
                        reset_level(0)
                        start_dialogue("intro")
                    elif clicked == "Main Menu":
                        persist_save()
                        set_game_mode("menu")
                    elif clicked == "Quit":
                        persist_save()
                        persist_settings()
                        is_running = False
        if mode == "game":
            keys = pygame.key.get_pressed()

            # Sprinting and stamina
            sprinting = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and stamina > 5.0
            base_speed = 2.45
            if sprinting:
                base_speed *= 1.65
                stamina = max(0.0, stamina - dt * 28.0)
            else:
                stamina = min(100.0, stamina + dt * 18.0)

            move_speed = base_speed * dt
            forward = (1 if keys[pygame.K_w] or keys[pygame.K_UP] else 0) - (1 if keys[pygame.K_s] or keys[pygame.K_DOWN] else 0)
            strafe = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
            is_moving = forward != 0 or strafe != 0

            # Footstep and head-bobbing
            if is_moving:
                step_rate = 11.0 if sprinting else 7.0
                step_cycle += dt * step_rate
                bob_offset = math.sin(step_cycle) * (6.0 if sprinting else 3.5)
                footstep_timer += dt
                if footstep_timer > (0.28 if sprinting else 0.44):
                    footstep_timer = 0.0
                    play_sound(sound_footstep)
            else:
                bob_offset = 0.0
                footstep_timer = 0.0

            dx = (math.cos(player_angle) * forward - math.sin(player_angle) * strafe) * move_speed
            dy = (math.sin(player_angle) * forward + math.cos(player_angle) * strafe) * move_speed
            if can_move(player_x + dx, player_y):
                player_x += dx
            if can_move(player_x, player_y + dy):
                player_y += dy

            if pygame.mouse.get_focused():
                player_angle += mouse_delta * settings["sensitivity"]
            if keys[pygame.K_LEFT]:
                player_angle -= 1.8 * dt
            if keys[pygame.K_RIGHT]:
                player_angle += 1.8 * dt

            # AI & Monster Behavior
            damage_factor, enemy_speed, alert_range = difficulty_values()
            dist = math.hypot(enemy_x - player_x, enemy_y - player_y)

            # Heartbeat tension sound
            if dist < 4.5:
                heartbeat_timer += dt
                interval = max(0.32, dist * 0.18)
                if heartbeat_timer >= interval:
                    heartbeat_timer = 0.0
                    play_sound(sound_heartbeat)

            if dist < alert_range:
                enemy_alert = True

            if enemy_alert and enemy_stunned <= 0:
                if dist > 0.68:
                    vx, vy = player_x - enemy_x, player_y - enemy_y
                    length = max(0.001, math.hypot(vx, vy))
                    speed = enemy_speed * dt
                    nx, ny = enemy_x + (vx / length) * speed, enemy_y + (vy / length) * speed
                    if can_move(nx, enemy_y):
                        enemy_x = nx
                    if can_move(enemy_x, ny):
                        enemy_y = ny
                elif dist <= 0.68 and damage_cooldown <= 0:
                    damage = {"Story": 8, "Normal": 15, "Nightmare": 24}.get(settings.get("difficulty", "Normal"), 15)
                    health -= damage
                    damage_cooldown = 1.2 if settings.get("difficulty") != "Nightmare" else 0.95
                    play_sound(sound_warning)
                    set_message("THE HOLLOW STRUCK YOU! RUN OR FLASH YOUR LANTERN!", 2.2)
                    if health <= 0:
                        health = 0
                        persist_save()
                        set_game_mode("failure")

            if dist < 2.5 and random.random() < 0.008:
                play_sound(sound_whisper)

        # Rendering by mode
        if mode == "game":
            draw_world()
        elif mode == "journal":
            draw_journal()
        elif mode == "puzzle":
            draw_puzzle()
        elif mode == "dialogue":
            draw_dialogue()
        elif mode == "menu":
            draw_3d_title_menu()
        elif mode == "minigames":
            draw_hub()
        elif mode == "quest_board":
            draw_quest_board()
        elif mode == "story_gallery":
            draw_story_gallery()
        elif mode == "theme_gallery":
            draw_theme_gallery()
        elif mode == "minigame_play":
            draw_minigame()
        elif mode == "settings":
            draw_settings()
        elif mode == "customize":
            draw_customize()
        elif mode == "instructions":
            draw_instructions()
        elif mode == "pause":
            draw_overlay("PAUSED", "The manor is silent... for now.",
                         ["Resume", "Journal", "Save Game", "Settings", "How to Play", "Main Menu"])
        elif mode == "level_complete":
            draw_overlay("LEVEL COMPLETE!", "Congratulations! You broke the seal. Ready to explore the next level?",
                         ["Continue to Next Level", "Main Menu", "Quit"])
        elif mode == "wrong_answer":
            draw_overlay("INCORRECT CIPHER!", "That answer was wrong. Returning to the beginning shortly.",
                         ["Please Wait"])
        elif mode == "victory":
            draw_overlay("CURSE LIFTED!", "You solved every cipher and freed the Cursed Manor! You are the hero!",
                         ["Play Again", "Main Menu", "Quit"])
        elif mode == "failure":
            draw_overlay("THE MANOR CLAIMS YOU", "The Hollow has caught you. Try another path.",
                         ["Play Again", "Main Menu", "Quit"])

        pygame.display.flip()

    persist_save()
    persist_settings()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        crash_path = os.path.join(BASE_DIR, "crash_log.txt")
        try:
            with open(crash_path, "w", encoding="utf-8") as crash_file:
                traceback.print_exc(file=crash_file)
        except OSError:
            pass
        try:
            pygame.quit()
        except Exception:
            pass
        raise