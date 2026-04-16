# Fall-Guys-RPC

[![Windows](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Steam Supported](https://img.shields.io/badge/Steam-Supported-1b2838?logo=steam&logoColor=white)](https://store.steampowered.com)
[![Epic Games](https://img.shields.io/badge/Epic%20Games-Coming%20Soon-444444?logo=epicgames&logoColor=white)](https://store.epicgames.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Support Server](https://img.shields.io/badge/Discord-Support%20Server-5865F2?logo=discord&logoColor=white)](https://discord.gg/tCWRxbmAwp)

Fall-Guys-RPC is a lightweight tray app that updates Discord Rich Presence while you play Fall Guys.

## Features

- Runs in background (no command prompt on launch)
- Shows a tray icon with menu options:
   - Open: opens live logs
   - Close: exits the app
- Uses a shared Discord application ID (no user-side app setup required)
- Detects show/round information from logs
- Keeps retrying if Discord or Fall Guys is not detected

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
