import re
import sys
import time
import ctypes
import threading
import subprocess
from pathlib import Path

import psutil
from pypresence import Presence
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

CLIENT_ID = "1494263420709503076"

# Steam and Epic Games both write to this Unity log location on Windows.
LOG_FILE = Path.home() / "AppData" / "LocalLow" / "Mediatonic" / "FallGuys_client" / "Player.log"
POLL_INTERVAL_SECONDS = 5
RECONNECT_DELAY_SECONDS = 10

ROUND_CONTEXT_PATTERN = re.compile(
    r"(?:assumed to be|\[Round\s+\d+\s+\|)\s*([a-z0-9][a-z0-9_-]*)(?=[\]|.,\s]|$)",
    re.IGNORECASE,
)
CREATIVE_ROUND_PATTERN = re.compile(r"round with id:\s*([A-Za-z0-9_-]+)", re.IGNORECASE)
SELECTED_SHOW_PATTERN = re.compile(r"Selected show is\s+([a-z0-9_]+)", re.IGNORECASE)
MATCHMAKING_PATTERN = re.compile(r"Begin matchmaking\s+([a-z0-9_]+)", re.IGNORECASE)
LOBBY_CAPACITY_PATTERN = re.compile(r"LobbyCapacity\s*=\s*(\d+)", re.IGNORECASE)
LOBBY_HINT_PATTERN = re.compile(
    r"returning to main menu|created core party|creating lobby result success|state.?mainmenu|state.?matchmaking|state.?reloadingtomainmenu",
    re.IGNORECASE,
)
BETWEEN_ROUNDS_HINT_PATTERN = re.compile(
    r"state.?qualification|state.?roundreadyup|readyroundresponse|server is asking us to start loading the level|gamemessageserverstartloadinglevel received|Replacing FGClient\..+ with FGClient\.StateGameLoading|waitandloadlevel|showloadinggamescreenandloadlevel",
    re.IGNORECASE,
)
INGAME_HINT_PATTERN = re.compile(
    r"starting the game\.|finished loading game level|onplayerspawned|Replacing FGClient\.StateGameLoading with FGClient\.StateGameInProgress|Changing state from Countdown to Playing",
    re.IGNORECASE,
)

# Remove manual mappings for shows and rounds
SHOW_ASSET_KEYS = {
    "casual": "show_explore",
    "casual_show": "show_explore",
    "game": "show_game",
    "ranked knockout": "show_ranked_knockout",
    "ranked_show_knockout": "show_ranked_knockout",
    "knockout": "show_knockout",
    "creator spotlight": "show_creator_spotlight",
    "spotlight_mode": "show_creator_spotlight",
    "spotlight": "show_creator_spotlight",
    "explore": "show_explore",
    "solos": "show_solos",
    "duos": "show_duos",
    "squads": "show_squads",
}

FRIENDLY_NAME_OVERRIDES = {
    "knockout_spookyslingers_opener": "Spooky Slingers",
    "ranked_bigfans_opener": "Big Fans",
    "ranked_fulltilt_opener": "Full Tilt",
    "round_chompchomp_squads": "Chomp Chomp",
    "round_chompchomp": "Chomp Chomp",
}

DEFAULT_STATE = {
    "game": "Unknown Show",
    "map": "",
    "status": "Waiting for Fall Guys",
    "party_size": 1,
    "party_max": 4,
}

GAME_PROCESS_CANDIDATES = {
    "fallguys_client.exe",
    "fallguys_client_game.exe",
    "fallguys.exe",
}

SMALL_ASSET = "fallguys_icon"
DEFAULT_LARGE_ASSET = "show_game"

APP_DATA_DIR = Path.home() / "AppData" / "Local" / "Fall-Guys-RPC"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
APP_LOG_FILE = APP_DATA_DIR / "rpc.log"

should_exit = False
rpc_thread = None
single_instance_mutex = None


def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    try:
        with open(APP_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def get_asset_key(game_name):
    if not game_name:
        return DEFAULT_LARGE_ASSET
    return SHOW_ASSET_KEYS.get(game_name.strip().lower(), DEFAULT_LARGE_ASSET)


def is_explore_show(show_code):
    code = (show_code or "").strip().lower()
    return "explore" in code or code in {"casual", "casual_show"}


def is_spotlight_show(show_code):
    code = (show_code or "").strip().lower()
    return "spotlight" in code


def hides_map(show_code):
    return is_explore_show(show_code) or is_spotlight_show(show_code)


def is_ranked_knockout_show(show_code):
    code = (show_code or "").strip().lower()
    return "ranked" in code and "knockout" in code


def get_show_asset_key(show_code):
    # Try to match asset keys based on known patterns
    code = show_code.lower()
    if is_explore_show(code):
        return "show_explore"
    if is_spotlight_show(code):
        return "show_creator_spotlight"
    if is_ranked_knockout_show(code):
        return "show_ranked_knockout"
    if "solo" in code:
        return "show_solos"
    if "duo" in code:
        return "show_duos"
    if "squad" in code:
        return "show_squads"
    if "knockout" in code:
        return "show_knockout"
    if "creator_spotlight" in code:
        return "show_creator_spotlight"
    return DEFAULT_LARGE_ASSET


def get_classic_show_name(show_code):
    code = show_code.lower()
    if is_explore_show(code):
        return "Explore"
    if is_spotlight_show(code):
        return "Creator Spotlight"
    if is_ranked_knockout_show(code):
        return "Ranked Knockout"
    if "knockout" in code:
        return "Knockout"
    if "squad" in code:
        return "Squads"
    if "duo" in code:
        return "Duos"
    if "solo" in code:
        return "Solos"
    return auto_friendly_name(show_code)

def auto_friendly_name(code):
    code = (code or "").strip()
    override = FRIENDLY_NAME_OVERRIDES.get(code.lower())
    if override:
        return override
    code = re.sub(r'^(round_|show_)', '', code)
    code = re.sub(r'^(ranked_|knockout_)', '', code)
    code = re.sub(r'(_main_show|_show|_solos|_duos|_squads|_2022|_main|_opener)$', '', code)
    return ' '.join(word.capitalize() for word in code.split('_') if word)

def get_last_log_lines(num_lines=3000):
    if not LOG_FILE.exists():
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return lines[-num_lines:] if lines else []
    except Exception as exc:
        log(f"Failed to read Fall Guys log: {exc}")
        return []


def extract_round_info(log_lines):
    for line in reversed(log_lines):
        match = ROUND_CONTEXT_PATTERN.search(line)
        if match:
            return match.group(1)
        match = CREATIVE_ROUND_PATTERN.search(line)
        if match:
            return match.group(1)
    return None


def extract_show_info(log_lines):
    for line in reversed(log_lines):
        match = SELECTED_SHOW_PATTERN.search(line)
        if match:
            return match.group(1)
        match = MATCHMAKING_PATTERN.search(line)
        if match:
            return match.group(1)
    return None


def detect_session_phase(log_lines):
    for line in reversed(log_lines):
        if INGAME_HINT_PATTERN.search(line):
            return "in_game"
        if BETWEEN_ROUNDS_HINT_PATTERN.search(line):
            return "between_rounds"
        if LOBBY_HINT_PATTERN.search(line):
            return "lobby"
    return "unknown"


def extract_lobby_capacity(log_lines):
    for line in reversed(log_lines):
        match = LOBBY_CAPACITY_PATTERN.search(line)
        if match:
            try:
                return max(1, int(match.group(1)))
            except Exception:
                return 4
    return 4


def is_game_running():
    try:
        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if name in GAME_PROCESS_CANDIDATES:
                return True
            if "fallguys" in name and name.endswith(".exe"):
                return True
    except Exception as exc:
        log(f"Process check failed: {exc}")
    return False


def update_discord_rpc(client, game_state):
    show_code = game_state.get("game", "Unknown Show")
    round_code = game_state.get("map", "")
    show_value = get_classic_show_name(show_code) if show_code else "Unknown Show"
    map_value = auto_friendly_name(round_code) if round_code else "Unknown Map"
    show_asset = get_show_asset_key(show_code)
    session_phase = game_state.get("session_phase", "unknown")

    party_size = max(1, int(game_state.get("party_size", 1)))
    party_max = max(party_size, int(game_state.get("party_max", 4)), 1)

    if session_phase == "in_game":
        state_value = None
        party_size_field = [party_size, party_max]
        if hides_map(show_code):
            details_value = f"Show: {show_value}"
        else:
            details_value = f"Show: {show_value} | Map: {map_value}"
        large_image = show_asset
        large_text = show_value
    elif session_phase == "between_rounds":
        state_value = None
        party_size_field = [party_size, party_max]
        details_value = "Selecting next round"
        large_image = DEFAULT_LARGE_ASSET
        large_text = "Fall Guys"
    elif session_phase == "lobby":
        state_value = None
        party_size_field = [party_size, party_max]
        details_value = "In Lobby"
        large_image = DEFAULT_LARGE_ASSET
        large_text = "Fall Guys"
    else:
        state_value = "Waiting for Fall Guys"
        party_size_field = [party_size, party_max]
        details_value = "Waiting for Fall Guys"
        large_image = DEFAULT_LARGE_ASSET
        large_text = "Fall Guys"

    party_size_field[0] = max(1, party_size_field[0])
    party_size_field[1] = max(party_size_field[0], party_size_field[1], 1)

    payload = {
        "details": details_value,
        "large_image": large_image,
        "large_text": large_text,
    }
    if state_value:
        payload["state"] = state_value

    # Show small icon only during active match gameplay.
    if session_phase == "in_game":
        payload["small_image"] = SMALL_ASSET
        payload["small_text"] = "Fall-Guys-RPC"
        payload["party_size"] = party_size_field
    elif session_phase == "lobby":
        payload["party_size"] = party_size_field
    elif session_phase == "between_rounds":
        payload["party_size"] = party_size_field
    else:
        payload["party_size"] = party_size_field

    log(f"Discord RPC payload: {payload}")
    client.update(**payload)


def create_tray_icon_image():
    # Prefer the same image used while building the exe icon.
    icon_candidates = [
        Path(r"C:\Users\fatlu\Downloads\fallguys_icon.png"),
        Path(sys.executable).parent / "fallguys_icon.png",
    ]
    for icon_path in icon_candidates:
        if icon_path.exists():
            try:
                return Image.open(icon_path).convert("RGBA")
            except Exception:
                pass

    # Fallback icon if external file is missing.
    image = Image.new("RGBA", (64, 64), (30, 144, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill=(255, 255, 255, 255))
    draw.ellipse((18, 18, 46, 46), fill=(30, 144, 255, 255))
    return image


def open_console(_icon, _item):
    # Show live logs in a separate terminal window.
    try:
        cmd = (
            "powershell -NoProfile -NoExit -Command "
            f"\"Get-Content -Path '{APP_LOG_FILE}' -Wait\""
        )
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
    except Exception as exc:
        log(f"Failed to open console window: {exc}")


def close_program(icon, _item):
    global should_exit
    should_exit = True
    try:
        icon.stop()
    except Exception:
        pass


def build_state(log_lines):
    current_state = DEFAULT_STATE.copy()
    show_info = extract_show_info(log_lines)
    round_info = extract_round_info(log_lines)
    session_phase = detect_session_phase(log_lines)

    current_state["game"] = show_info or "Unknown Show"

    # Lobby must override stale round/show values from previous match logs.
    if session_phase == "lobby":
        current_state["map"] = ""
        current_state["status"] = "In Lobby"
        current_state["party_size"] = 1
        current_state["party_max"] = extract_lobby_capacity(log_lines)
    elif session_phase == "in_game":
        current_state["map"] = round_info or "Unknown Map"
        if show_info:
            current_state["status"] = f"Playing {show_info}"
        else:
            current_state["status"] = "Playing Fall Guys"
        current_state["party_size"] = 1
        current_state["party_max"] = extract_lobby_capacity(log_lines)
    elif session_phase == "between_rounds":
        current_state["map"] = ""
        current_state["status"] = "Selecting next round"
        current_state["party_size"] = 1
        current_state["party_max"] = extract_lobby_capacity(log_lines)
    else:
        current_state["map"] = ""
        current_state["status"] = "Waiting for Fall Guys"
        current_state["party_size"] = 1
        current_state["party_max"] = 4

    current_state["session_phase"] = session_phase
    return current_state


def run_rpc_background():
    global should_exit
    game_was_running = None

    while not should_exit:
        client = None
        try:
            client = Presence(CLIENT_ID)
            client.connect()
            log("Connected to Discord RPC")

            while not should_exit:
                game_running = is_game_running()
                if not game_running:
                    if game_was_running is not False:
                        try:
                            client.clear()
                            log("Cleared Discord RPC because Fall Guys is not running")
                        except Exception as exc:
                            log(f"Failed to clear Discord RPC: {exc}")
                    game_was_running = False
                    time.sleep(POLL_INTERVAL_SECONDS)
                    continue

                game_was_running = True
                log_lines = get_last_log_lines()
                state = build_state(log_lines)

                try:
                    update_discord_rpc(client, state)
                    log(f"Updated RPC: {state['game']} | {state['map']}")
                except Exception as exc:
                    log(f"Failed to update Discord RPC: {exc}")

                time.sleep(POLL_INTERVAL_SECONDS)

        except Exception as exc:
            log(f"Discord connection loop error: {exc}")
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

        if not should_exit:
            log(f"Retrying Discord connection in {RECONNECT_DELAY_SECONDS} seconds")
            time.sleep(RECONNECT_DELAY_SECONDS)

    log("RPC worker stopped")


def acquire_single_instance():
    global single_instance_mutex

    if sys.platform != "win32":
        return True

    single_instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Fall-Guys-RPC")
    if not single_instance_mutex:
        log("Unable to create single-instance mutex; continuing anyway")
        return True

    if ctypes.windll.kernel32.GetLastError() == 183:
        log("Another Fall-Guys-RPC instance is already running; exiting")
        return False

    return True


def main():
    global rpc_thread

    log("Application started")
    if not acquire_single_instance():
        return

    rpc_thread = threading.Thread(target=run_rpc_background, daemon=True)
    rpc_thread.start()

    menu = Menu(
        MenuItem("Open", open_console),
        MenuItem("Close", close_program),
    )
    tray_icon = Icon("Fall-Guys-RPC", create_tray_icon_image(), "Fall-Guys-RPC", menu)
    tray_icon.run()


if __name__ == "__main__":
    main()
