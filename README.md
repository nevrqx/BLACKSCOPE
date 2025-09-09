# BLACKSCOPE — CS2 Cheat (for study)

Directly: this is a cheat client for Counter‑Strike 2 on Windows. It adds an ESP overlay, optional aimbot, and trigger feature. The project is intended for learning and research (overlays, rendering, hotkeys, config persistence, etc.).

You are fully responsible for installation, usage, and any consequences. Using cheats may violate game Terms of Service and local laws. You use this software at your own risk.

## Demo

<p align="center">
  <img src="assets/demo.gif" alt="BLACKSCOPE demo: ESP overlay, aim assist, trigger feature" width="900" />
  <br/>
  <em>ESP elements (boxes, health, nicknames), optional aimbot and trigger.</em>
  <br/>
  <small>Rendered via in‑app overlay (PySide6 + Win32).</small>
</p>

## Features

- ESP overlay with style options
  - Boxes (classic, corner, capsule), lines/radius, nicknames, weapon, bomb
  - Health bar (incl. gradient), opacity/alpha
  - Neon outline, head hitbox highlight, on‑screen FPS and overlay FPS cap
- Aimbot (optional)
  - Hold‑to‑aim hotkey, FOV radius, bone selection (head/chest), offsets
  - Snap or smoothed targeting, humanization, reaction/pause tuning
  - Sticky aim, separate smoothing while firing
- Trigger (optional)
  - Hold key or Always mode, radius threshold, click delay
- Hit feedback
  - Hitmarker, timing and floating damage
- UI/UX
  - Custom title bar, modern toggles, themes, DPI‑aware fonts/icons
- Local settings
  - Config stored at `%LOCALAPPDATA%/temp/PyIt/config.json`

## Repository Contents

- `blackscorpe.py` — main PySide6 GUI client and overlay logic
- `app.ico` — app icon (UI and PyInstaller builds)
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

If PowerShell blocks script execution when activating the venv, run once (for current user):

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

The portable binary will appear at `dist/BLACKSCOPE.exe`. Do not commit `build/`, `dist/`, or `*.spec`.

## Cleaning build artifacts (optional)

- Folders: `build/`, `dist/`, `.venv/`, `.buildvenv/`
- Files: `*.spec`, temporary archives (`*.zip`, `*.7z`, `*.rar`, …)

## Configuration location

- Settings directory: `%LOCALAPPDATA%/temp/PyIt/`
- Main config: `%LOCALAPPDATA%/temp/PyIt/config.json`
- Profiles: `%LOCALAPPDATA%/temp/PyIt/configs/`

## Pros and Cons

Pros
- Modern PySide6 UI, DPI‑aware rendering, custom widgets
- Highly configurable ESP/aim/trigger with smoothing and humanization
- Offline‑first; no external licensing server required
- Can be packaged into a single `.exe`

Cons
- Windows‑only stack (PySide6 + Win32 + memory tooling)
- Game updates can break offsets and require maintenance
- No guarantees of undetectability; bans and other consequences are possible

## Security suggestions

- Use only on test accounts and in controlled environments
- Do not store sensitive keys in plain text; use OS‑protected storage/DPAPI
- Prefer offline mode; if you add networking, pin TLS and validate hosts
- Add integrity checks for downloaded offsets and handle timeouts/failures
- Sign binaries and publish SHAs; avoid unsigned auto‑updaters

## Contribution ideas

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

## Responsibility and legal risks

This project is a CS2 cheat and is provided solely for study and research. Using such tools may violate game Terms of Service and/or the laws of your jurisdiction. You accept full responsibility for installation, usage, and any consequences: bans, sanctions, loss of account access, legal risks, etc. The authors and contributors bear no responsibility.

 
