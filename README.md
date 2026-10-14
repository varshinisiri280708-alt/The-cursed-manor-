# Cryptic Escape: The Cursed Manor

A single-entry-point Pygame gothic-horror puzzle adventure. The upgrade preserves the original ray-cast mansion, three chapters, The Hollow, the Witness, Caesar seals, flower-memory puzzle, settings, and procedural vector artwork/audio.

## Run locally

Use Python 3.10 or newer.

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

macOS/Linux:
```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## Controls

- **W / A / S / D**: move
- **Mouse**: look around
- **Arrow keys**: turn
- **E**: interact with the Witness, cyan seal, or Moon Door
- **F**: open the flower-memory puzzle
- **J**: open the journal
- **1–3**: choose a dialogue option
- **Enter / Space / click**: finish or advance dialogue text
- **Esc**: pause / return from a sub-screen

## Improvements in this version

- Cleaned Markdown-escaped characters so the Python source is executable.
- Added settings validation to avoid crashes from malformed settings JSON.
- Made saved clue data defensive against malformed values.
- Save files now retain the solved flower-memory state.
- Dialogue lines reveal with a typewriter effect; input first finishes the current line before advancing.
- Added an in-game journal showing decoded seals, flower-memory status, and the current objective.
- Added two reachable ending variants: restoring the Witness's flower memory unlocks the more complete ending.
- Preserved the original Pygame rendering approach and avoided external art dependencies.

## Test status

- Python syntax compilation: **passed**.
- Caesar cipher round-trip checks for all three seals: **passed**.
- Grid reachability checks for each chapter's exit, clue, friend, and enemy positions: **passed**.
- Full interactive runtime test: **not run in this environment** because Pygame is not installed and package download access is unavailable. Install dependencies on your computer before launching the game.

Save and settings files (`savegame.json` and `settings.json`) are created beside the game when it runs.

## Streamlit edition (web UI)

A point and click version of the manor that runs in the browser. It uses the same story, three cipher seals, dialogue, side stories, mini games and seasonal themes, and reads and writes the same `savegame.json` and `settings.json`, so you can switch between the two versions.

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Files added for this edition:

- `app.py` the Streamlit interface (title screen, chapters, cipher seals, journal, side stories, mini games, themes, hero select, settings, endings)
- `game_data.py` the story text, maps and puzzle data shared by the web UI
- `explore3d.html` the browser 3D engine used by the 3D mode
- `.streamlit/config.toml` dark theme defaults

### Explore in 3D (inside Streamlit)

Click **Explore the manor in 3D** on the title screen, or **3D mode** in the top bar. This is a browser version of the Pygame ray caster: textured walls, floor and ceiling from `assets/`, the floating Witness, the cyan seal, the Moon Door, and the Hollow hunting you.

- Click inside the view first so it receives your keys
- **W A S D** move, **hold the left mouse button and drag** (or arrow keys) to look
- **Shift** sprint, **Space** or right click lantern flash, **E** interact
- **J** journal, **M** minimap, **Esc** pause

Mouse look uses dragging because Streamlit runs custom HTML inside a sandboxed frame that blocks pointer lock. The code lives in `explore3d.html`.

How the point and click mode plays: each chapter shows its room artwork with actions beside it. Speak with the spirit, examine the cyan seal, search the room, open the Moon Door, or use a lantern flash. Every action draws the Hollow nearer; when its eyes appear, flash the lantern or you lose health. Restoring the flower memory before the last seal unlocks the fuller ending.


## Sound

The game includes procedural sound effects (menu clicks, cipher success/failure, lantern flash, footsteps, whispers, and threat heartbeat) and a quiet synthesized haunted-room ambience. No external sound downloads are required. In the browser 3D explorer, click **New Game** or **Continue** once to enable audio; browsers require a user gesture before sound can start. The ambience follows the configured master/music volume in the desktop version and the configured sound volume in the browser explorer.


## Sound assets

The 3D browser explorer uses the supplied audio files in `assets/sounds/`:
- `background.mp3` — looping haunted-mansion ambience (starts after a player interaction).
- `footsteps.mp3` — footsteps while moving.

The Streamlit app embeds these audio files into the 3D iframe so they can play even though the game view is rendered inside `components.html`. Browser autoplay restrictions mean audio begins after clicking **Begin chapter 1** or **Continue**.
