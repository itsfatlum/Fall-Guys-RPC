# Fall-Guys-RPC

[![Windows](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Steam Supported](https://img.shields.io/badge/Steam-Supported-1b2838?logo=steam&logoColor=white)](https://store.steampowered.com)
[![Epic Games](https://img.shields.io/badge/Epic%20Games-Coming%20Soon-444444?logo=epicgames&logoColor=white)](https://store.epicgames.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Support Server](https://img.shields.io/badge/Discord-Support%20Server-5865F2?logo=discord&logoColor=white)](https://discord.gg/tCWRxbmAwp)

Simple Discord Rich Presence for Fall Guys.

## Features

<img src="assets/In_Lobby.png" alt="In Lobby Example" width="350"/>

- Shows "In Lobby" with the Fall Guys icon when in the lobby
- Displays party size as "x of y" next to the people icon in the lobby
- Shows the correct show icon and name in-game (Solos, Duos, Squads, etc.)
- Displays the current map name under the show name in-game
- Shows "Players Alive (x of y)" as the state in-game
- Automatically formats show and map names for readability
- Uses your custom Discord asset images for show icons

## What You Can Also Do

- Add more Discord asset images for new shows or custom events
- Customize the display text for show, map, or party size
- Adjust the logic to extract more accurate player counts from logs
- Add support for additional platforms (e.g., Epic Games)
- Change the tray icon or add more tray menu options
- Extend presence to show round number, time elapsed, or other stats
- Localize the display for different languages
- Add error logging or a debug mode for troubleshooting

## Platform Support

- Steam: supported now
- Epic Games: coming soon

## Download / Install

### 1. EXE (Recommended)

Run directly:

```powershell
Steam/Fall-Guys-RPC.exe
```

After launch, use the tray icon to open logs or close the app.

### 2. Manual Installation (Python)

Install dependencies:

```powershell
pip install -r Steam/requirements.txt
```

Run from source:

```powershell
python Steam/main.py
```

## Build EXE

```powershell
pyinstaller Fall-Guys-RPC.spec
```

Then move `dist/Fall-Guys-RPC.exe` into the `Steam` folder.

## Logs

Live logs are available from the tray menu and stored at:

```text
C:/Users/<your-user>/AppData/Local/Fall-Guys-RPC/rpc.log
```

## Troubleshooting

If status does not update on Discord:

- Ensure Discord desktop app is running
- Ensure Fall Guys is running
- Open tray icon menu and click Open to view live logs
- Check the log file path shown above

## Support

If you need help, join the support server:

https://discord.gg/tCWRxbmAwp
