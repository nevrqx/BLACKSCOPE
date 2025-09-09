# BLACKSCOPE

Clean project structure, ready for GitHub.

---

# Overview

BLACKSCOPE is a Windows overlay client built with PySide6 that provides ESP visualization, an optional aim assist, and a trigger feature for first‑person shooters. The UI focuses on clarity, performance, and configurability, and the app can be packaged into a single portable executable.

Important: This project is provided for educational and research purposes only. Using game automation or memory tools can violate game Terms of Service and local laws. You are solely responsible for how you use this software.

## Demo

<p align="center">
  <img src="assets/demo.gif" alt="BLACKSCOPE demo: ESP overlay, aim assist, trigger feature" width="900" />
  <br/>
  <em>Demonstration of ESP overlay elements (boxes, health, nicknames), optional aim assist and trigger behavior.</em>
  <br/>
  <small>Rendered via the in-app overlay on Windows (PySide6 + Win32).</small>
</p>

## Key Features

- ESP overlay with customizable styles
  - Boxes (classic, corner, capsule), line/radius, nicknames, weapon, bomb ESP
  - Health bar with optional gradient fill and opacity/alpha controls
  - Neon outline option, head hitbox highlight, on‑screen FPS indicator and FPS cap for the overlay
- Aim assist (optional)
  - Hold‑to‑aim hotkey, FOV radius, bone selection (head/chest), screen/bias offsets
  - Snap or smoothed targeting with humanization and reaction/pause tuning
  - Sticky snap and separate smoothing while firing
- Trigger feature (optional)
  - Hold key or Always mode, radius threshold, click delay
- Hit feedback
  - Hitmarker with configurable duration and floating damage indicators
- Polished UX
  - Custom title bar, modern toggle switches, accent themes, DPI‑aware fonts/icons
- Offline‑first settings and licensing placeholders
  - Settings persisted under `%LOCALAPPDATA%/temp/PyIt/config.json`
  - Network licensing is disabled; the UI remains compatible with future backends

## Repository Contents

- `blackscorpe.py` — main PySide6 GUI client and overlay logic
- `index.html` — optional, standalone local page for managing keys via browser LocalStorage (no server)
- `app.ico` — app icon (used in UI and PyInstaller builds)
- `requirements.txt` — Python dependencies
- `.gitignore` — ignores venv/build/dist/spec and similar artifacts
- `README.md` — this file

Build and environment folders like `build/`, `dist/`, `.venv/`, `.buildvenv/`, and `*.spec` should not be committed—they are covered by `.gitignore`.

## Requirements

- Windows 10/11
- Python 3.10+ recommended

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt
```

If PowerShell blocks script execution when activating the venv, run once (as current user):

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Running

```powershell
python blackscorpe.py
```

## Packaging to EXE (optional)

```powershell
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --icon app.ico --name BLACKSCOPE blackscorpe.py
```

The portable binary will appear at `dist/BLACKSCOPE.exe`. Do not commit `build/`, `dist/`, or `*.spec` files.

## Cleaning build artifacts (optional)

- Folders: `build/`, `dist/`, `.venv/`, `.buildvenv/`
- Files: `*.spec`, temporary archives (`*.zip`, `*.7z`, `*.rar`, …)

## Configuration location

- Settings directory: `%LOCALAPPDATA%/temp/PyIt/`
- Main config: `%LOCALAPPDATA%/temp/PyIt/config.json`
- Multiple profiles live under: `%LOCALAPPDATA%/temp/PyIt/configs/`

## Pros and Cons

Pros
- Modern PySide6 UI with DPI‑aware rendering and custom widgets
- Highly configurable ESP/aim/trigger system with smoothness and humanization controls
- Offline‑first: works without external licensing servers
- Packagable into a single `.exe` for easy distribution

Cons
- Windows‑only stack (PySide6 + Win32 + memory tooling)
- Game updates can break offsets and require maintenance
- Undetectability is not guaranteed; misuse can lead to bans or other consequences

## Security and Safety Suggestions

- Use on test accounts and in controlled environments only
- Avoid storing any sensitive keys in plain text; consider OS‑protected storage or DPAPI
- Prefer offline mode; if you add networking, pin TLS and validate hosts
- Add integrity checks for downloaded offsets and handle timeouts/failures gracefully
- If distributing binaries, sign them and publish SHAs; avoid auto‑updaters that fetch unsigned code

## Contribution Ideas

- Add per‑game/process profiles and auto‑profile switching
- Expand ESP styles (skeletons, occlusion checks, visibility coloring)
- Improve aim assist with predictive smoothing, velocity‑aware targeting, recoil compensation
- Implement robust hotkey capture (mouse buttons 4/5, modifiers) and in‑UI key binding
- Telemetry‑free crash reporting and structured logging with toggles
- Safer config handling: schema validation and migration steps
- Optional plug‑in system for features to be enabled/disabled at runtime

## Roadmap (proposals)

- Modularize overlay rendering layers and add tests for math/projection helpers
- Abstract memory access behind interfaces for easier portability and mocking
- Optional network licensing (opt‑in), rate‑limited with secure server‑side checks
- In‑app profile sharing/export/import with checksums

## Disclaimer

This software is for research and educational purposes only. The authors and contributors are not responsible for any misuse, violations of Terms of Service, bans, or legal consequences. Use at your own risk.

## Лицензии/ключи

`index.html` работает полностью локально и использует LocalStorage браузера для хранения данных ключей. Сервер не требуется.
