"""
Game content for the Streamlit edition of Cryptic Escape: The Cursed Manor.

Everything here is copied from main.py (the Pygame edition) so both versions
tell the same story. main.py cannot be imported directly because it opens a
Pygame window at import time, so the data lives in this small module instead.
"""

def caesar(value, shift):
    out = []
    for ch in value.upper():
        if "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + shift) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)


LEVELS = [
    {
        "name": "The Forgotten Foyer",
        "map": ["111111111111", "100000000001", "101110011101", "100010000001", "100010111101",
                "100000100001", "101100100101", "100000000001", "111111111111"],
        "start": (1.5, 1.5), "exit": (10.5, 7.5), "clue": (5.5, 3.5), "enemy": (8.5, 5.5), "friend": (3.5, 5.5),
        "image": "livingroom.png",
        "answer": "THE KEY IS UNDER THE CANDLE",
        "hint": "Caesar shift: move each letter 2 steps backward.",
        "speaker": "The Witness",
        "intro": "A portrait follows your gaze. Beneath it, fresh dust spells your name. Somewhere upstairs, a dinner bell rings for a family that died a century ago.",
        "opening": [
            "The owner removed one name from every ledger, portrait, and birth record. The ink is newer than the pages around it.",
            "I heard the master say: 'If the house forgets her, the world will follow.' Find the brass register in the west hall.",
            "The candle marks the place where the missing page was hidden. Do not trust the family tree hanging above it.",
        ],
        "choices": [("Ask about the erased name", "identity"), ("Ask about the Hollow", "hollow"), ("Leave quietly", "close")],
        "search": [
            "Behind a cracked vase you find a dinner invitation dated 1897. One guest's name has been cut out with scissors.",
            "The fireplace is cold, yet the ash inside is still warm to the touch.",
            "A brass register lies open on the side table. Every page about the youngest daughter is missing.",
            "The window frost has a handprint on the inside. It is far too small to be yours.",
        ],
    },
    {
        "name": "The Whispering Library",
        "map": ["111111111111", "100000000001", "101101110101", "100000000001", "111011011101",
                "100000000001", "101110110101", "100000000001", "111111111111"],
        "start": (1.5, 1.5), "exit": (10.5, 7.5), "clue": (7.5, 3.5), "enemy": (9.5, 5.5), "friend": (4.5, 3.5),
        "image": "painting.png",
        "answer": "THE SECRET PASSAGE IS EAST",
        "hint": "Shift every letter BACK by two positions.",
        "speaker": "The Trapped Caretaker",
        "intro": "The books whisper a name that was scratched from every family record. One book is warm, as if someone has just closed it, though the dust on its cover is untouched.",
        "opening": [
            "I am the caretaker. I locked myself in this wing when the portraits began changing at twelve. Each frame shows a different version of the same night.",
            "The clock does not measure time here; it counts the lies still believed. When it strikes midnight, look at the portrait with no eyes.",
            "I hid the winding key inside a music box. The tune is backwards because the room remembers events in reverse.",
        ],
        "choices": [("Ask about the changing portraits", "history"), ("Ask about the clock", "mirror"), ("Leave quietly", "close")],
        "search": [
            "A ledger falls open on its own. The handwriting changes halfway through a sentence.",
            "The portrait nearest the stairs has no eyes. The paint where they should be is still wet.",
            "A music box sits on the shelf. When you wind it, the melody plays backwards.",
            "Every book on the east wall leans slightly, as if something behind them breathes.",
        ],
    },
    {
        "name": "The Moonlit Crypt",
        "map": ["111111111111", "100000000001", "101011110101", "100000000001", "101110111101",
                "100000000001", "101011110101", "100000000001", "111111111111"],
        "start": (1.5, 1.5), "exit": (10.5, 7.5), "clue": (5.5, 5.5), "enemy": (9.5, 3.5), "friend": (3.5, 5.5),
        "image": "passage.png",
        "answer": "THE LIGHT WILL SET YOU FREE",
        "hint": "Decode the seal with shift -2, then unlock the moon door.",
        "speaker": "The Hollow",
        "intro": "The dead do not want revenge. They want the truth to stay buried. Blue light spills from the sealed doorway, and a voice behind it asks whether you came to remember or to forgive.",
        "opening": [
            "You were summoned because you carry the only memory the family could not steal: the choice made before the fire.",
            "I am called the Hollow because they carved every name from me. I guarded the truth, but the lock became my prison.",
            "Three seals remain. Break them to uncover who called you here, and decide whether the truth will free the dead or bind the living.",
        ],
        "choices": [("Ask why I was summoned", "history"), ("Ask about the three seals", "hollow"), ("Leave quietly", "close")],
        "search": [
            "The wall here has collapsed into darkness. Cold air flows out of it, smelling faintly of roses.",
            "Names are carved into the floor stones. One has been chiseled away so deeply the stone has cracked.",
            "A lantern hangs on a hook, still burning. There is no oil in it.",
            "Something scrapes along the stone behind you, then stops when you turn.",
        ],
    },
]
for lev in LEVELS:
    lev["cipher"] = caesar(lev["answer"], 2)

DIALOGUES = {
    "identity": ("The Witness", [
        "I was once the manor's youngest daughter. The fire took my face, not my memory.",
        "My name is written in the cipher you are about to solve. Read it, and I may remember the rest.",
        "I hid the first key beneath a candle before the fire began. The flame never touched it; the family simply stopped looking.",
        "When the portrait eyes turn toward the window, someone in the room is lying.",
    ], [("Ask what happened here", "history"), ("Return to the room", "close")]),
    "hollow": ("The Witness", [
        "The Hollow was a keeper, not a killer. Someone taught it to hunt anyone carrying the truth.",
        "If it catches you, do not curse it. Ask what it is protecting.",
        "I heard it speak once. It said, 'I kept the promise even after everyone forgot what was promised.'",
        "The red in its eyes is not rage. It is the last light from the room where the truth was buried.",
    ], [("Ask about the curse", "history"), ("Return to the room", "close")]),
    "flower_story": ("The Witness", [
        "Those flowers were planted by someone who refused to let the house become cruel.",
        "Each petal held a memory. The family tried to burn the memories, but kindness grows back in strange places.",
        "If you restore the flower pattern, I may remember the name I lost.",
    ], [("I will restore it", "close"), ("Who planted them?", "history")]),
    "mirror": ("The Witness", [
        "Do not trust the mirror when it shows you a room you have not entered.",
        "The reflection is not predicting your future. It is remembering a past the house stole from you.",
    ], [("Return to exploring", "close"), ("Ask about the stolen memory", "history")]),
    "history": ("The Witness", [
        "The family tried to trade a memory for immortality. They chose the memory of their own crime.",
        "Three seals hold that stolen memory. Break them, and the manor will have to remember.",
        "The first seal tells you where the key was hidden. The second reveals who opened the passage. The last asks whether the guilty deserve to be heard.",
        "Do not rush to destroy the Hollow. It is the lock as much as it is the jailer.",
    ], [("Return to the room", "close")]),
}

STORIES = [
    ("The Portrait That Blinked", "drawingroom.png", [
        "At 11:13, the portrait in the west hall blinked. Not both eyes. Just the left one, the eye painted over after the fire.",
        "You lift the frame. Behind it, someone has scratched: 'A family can bury a body. It cannot bury what the body remembers.'",
        "The painted girl is not the monster. She is the witness the family tried to erase. When you turn away, the portrait has changed: now there are four people in it, and one has no face.",
    ]),
    ("The Christmas Room", "candle.png", [
        "The ballroom is frozen in the middle of a Christmas party from 1897. Paper stars hang motionless, and a tree glows with lights that have no wires.",
        "A music box plays a carol with one note missing. The missing note is the name of the child who was locked outside during the storm.",
        "You place a silver star on the tree. For one warm second, every ghost in the room looks alive. A small voice whispers, 'You remembered me.'",
    ]),
    ("The Last Train at Midnight", "room.png", [
        "A station platform waits under the cellar. A black train arrives every night, though the tracks end at a brick wall.",
        "Its conductor has no ticket punch, only a pocket watch stopped at the moment the manor's first secret was made.",
        "The train does not carry the dead away. It carries their forgotten memories back to the place that stole them. One empty seat bears your name.",
    ]),
    ("The Family Secret", "ceiling.png", [
        "The manor's founder did not seek eternal life. He feared that the truth about his family would outlive him.",
        "He sealed the truth inside three ciphers and made a guardian from every memory he had refused to face. That guardian became the Hollow.",
        "The Witness and the Hollow are two halves of the same lost child: one remembers the kindness, the other remembers the betrayal. Freeing one without hearing the other will leave the curse unfinished.",
    ]),
]

QUESTS = [
    ("main", "Break the three cipher seals", "Decode the message hidden in each chapter.", "seals"),
    ("optional", "The kindest soul", "Find the pink flower memory and learn why it matters.", "flower_memory"),
    ("optional", "A song without a singer", "Reproduce the ghostly signal in the music room.", "ghost_signal"),
    ("optional", "Five lights, one truth", "Light the candles in the order revealed by the manor.", "candle_order"),
    ("optional", "Collector of forgotten things", "Complete the flower memory pairs.", "flower_memory"),
]

# accent, particle colour, subtitle, particle style
SEASON_THEMES = {
    "Haunted":     {"accent": "#A56FCE", "particle": "#AD99D3", "subtitle": "The portraits are watching.", "fx": "wisp", "info": "Will o' wisps and watchful portraits"},
    "Halloween":   {"accent": "#FF702A", "particle": "#FF8731", "subtitle": "Pumpkins glow where no candle burns.", "fx": "ember", "info": "Bats, ember leaves and pumpkin glow"},
    "Christmas":   {"accent": "#53DC97", "particle": "#F5F8FF", "subtitle": "A silent snowfall covers old footprints.", "fx": "snow", "info": "Snowfall and twinkling fairy lights"},
    "Winter Snow": {"accent": "#7ACCFF", "particle": "#E8F6FF", "subtitle": "The manor sleeps beneath blue frost.", "fx": "snow", "info": "Quiet blue frost and drifting snow"},
    "Blood Moon":  {"accent": "#E04164", "particle": "#F05A73", "subtitle": "Tonight, the moon remembers everything.", "fx": "ember", "info": "Crimson motes beneath a cursed sky"},
}

HEROES = ["Manor Hunter", "Moon Witch", "Royal Knight", "Phantom"]
CLOAKS = ["#231F32", "#2B4C6F", "#692341", "#2B5741", "#76628B"]
CLOAK_NAMES = ["Midnight", "Deep sea", "Wine", "Moss", "Dusk"]

# 2D mode: hollow step per action, hit damage, wrong answer damage
# 3D mode: hollow speed, alert range and contact damage (same values as main.py)
DIFFICULTY = {
    "Story":     {"step": 6,  "hit": 20, "wrong": 10, "speed": 0.45, "alert": 2.8, "damage": 8, "desc": "A gentle haunting. The Hollow is slow and forgiving."},
    "Normal":    {"step": 10, "hit": 35, "wrong": 20, "speed": 0.70, "alert": 5.5, "damage": 15, "desc": "The intended experience. Every action draws it nearer."},
    "Nightmare": {"step": 15, "hit": 50, "wrong": 0,  "speed": 1.05, "alert": 7.2, "damage": 24, "desc": "One wrong cipher sends you back to the very first seal."},
}

ENDING_PARTIAL = (
    "Curse lifted",
    "The three seals shatter and moonlight floods the manor. The doors open onto a quiet dawn. "
    "Behind you, the Witness smiles, but she still cannot say her own name. Some memories in this house remain unclaimed.",
)
ENDING_COMPLETE = (
    "The name returns",
    "As the last seal breaks, the flower memory you restored blooms in the Witness's hands. "
    "She speaks her name aloud for the first time in a hundred years, and the Hollow, hearing it, finally rests. "
    "The manor does not just release you. It remembers her.",
)
