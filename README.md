# HumanAutoClicker v1.2

A professional-grade, modern autoclicker built with Python + Tkinter (ttk) using the Sun Valley theme, designed to simulate natural human behavior.

## Sun Valley UI (v1.2)
- **Humanized Hold**: Simulates natural finger press duration (mean 133ms, std 83ms) and double-click gaps.
- **Hold-to-Click**: Optional mode to only click while the hotkey is depressed.
- **Resizable / Responsive Layout**: The window is resizable and adapts to the active tab content.
- **Tabbed Interface**: Settings are grouped into focused tabs (Click, Position, Behavior, Human).
- **Theme Toggle**: Switch between Light and Dark using the Sun Valley ttk theme.
- **Branding**: Unique fingerprint + cursor logo for v1.2.

## ⚠️ Disclaimer
**This software is provided for educational purposes only.**
The author is not responsible for how you use this application or any consequences that may arise from its use (e.g., bans in games or services). Use it responsibly and at your own risk.

## Features

### 🖱️ Human-like Clicking
- **Drift & Correction**: Simulates natural hand recoil. The mouse drifts slightly and corrects itself, mimicking imperfect human aim.
- **Flexible Timing**: Set click intervals with randomized offsets (all in ms).
- **Thinking Pauses**: Toggleable Gaussian pauses (default mean 1500ms, std 800ms, every 120-150 clicks).
- **Fatigue Modeling**: Toggleable jitter detection and cooldown (default 100ms threshold, 3000ms duration, 1000ms cooldown, 500ms min interval).
- **Millisecond Inputs**: Uses whole-millisecond values (e.g., `1` ms).

### 🎯 Positioning Control
- **Current Position**: Click where the mouse is.
- **Pick Location**: Press **F8** to lock onto a specific screen coordinate.
- **Spread/Jitter**: Define a radius for random click distribution.

### ⚙️ Advanced Options
- **Click Types**: Left/Right mouse buttons, Single/Double click.
- **Repetition**: Run infinitely or set a specific click limit.
- **Always on Top**: Keep the window floating above games or other applications.
- **Background Clicking (Windows)**: Captures the window under the target position when you press Start so the cursor won't move.

### 🎨 Personalization
- **Theme Switching**: Toggle between **Dark Mode** and **Light Mode** via Sun Valley ttk.
- **Save on Close**: Configuration is saved when you exit the app.
- **State Persistence**: The app remembers your last-used settings.

## Global Hotkeys
- **F6**: Start / Stop Clicking
- **F8**: Pick Mouse Location

## Installation & Usage

### Running the Executable
Simply navigate to the `dist/` folder and run `HumanAutoClicker.exe`. No installation required.

### Developer Setup (Source)
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Theme setup (choose one):
   - Install the Python package:
     ```bash
     pip install sv-ttk
     ```
   - Or download https://github.com/rdbende/Sun-Valley-ttk-theme and place the theme files under `themes/sun-valley/`.
3. Run the app:
   ```bash
   python -m autoclicker
   ```
   (Compatibility shim also works: `python autoclicker.py`)
4. (Optional) Run internal checks:
   ```bash
   python internal_tests.py
   ```

## Building
To create the standalone executable:
```bash
python -m PyInstaller --noconfirm --onefile --windowed --name "HumanAutoClicker" --clean --collect-all sv_ttk --exclude-module numpy --icon app_icon.ico autoclicker/__main__.py
```

If you use local theme files instead of `sv-ttk`, add:
```bash
--add-data "themes/sun-valley;themes/sun-valley"
```
