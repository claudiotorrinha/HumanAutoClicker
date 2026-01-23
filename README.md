# HumanAutoClicker v1.2

A professional-grade, modern autoclicker built with Python and CustomTkinter, designed to simulate natural human behavior.

## Material Design 3.0 UI (v1.2)
- **Humanized Hold**: Simulates natural finger press duration (5-15ms) and double-click gaps.
- **Hold-to-Click**: Optional mode to only click while the hotkey is depressed.
- **Responsive / Dynamic Sizing**: The window automatically adjusts height based on expanded cards. No more dead space or scrollbars.
- **Card-Based Interface**: Settings are grouped into sleek, rounded "cards" (General, Positioning, Advanced).
- **Segmented Controls**: Modern toggle bars for click types and buttons.
- **Branding**: Unique fingerprint + cursor logo for v1.2.

## ⚠️ Disclaimer
**This software is provided for educational purposes only.**
The author is not responsible for how you use this application or any consequences that may arise from its use (e.g., bans in games or services). Use it responsibly and at your own risk.

## Features

### 🖱️ Human-like Clicking
- **Drift & Correction**: Simulates natural hand recoil. The mouse drifts slightly and corrects itself, mimicking imperfect human aim.
- **Flexible Timing**: Set click intervals with randomized offsets for undetectable automation.
- **Micro-second Precision**: Supports precise decimal values (e.g., `0.001s`).

### 🎯 Positioning Control
- **Current Position**: Click where the mouse is.
- **Pick Location**: Press **F8** to lock onto a specific screen coordinate.
- **Spread/Jitter**: Define a radius for random click distribution.

### ⚙️ Advanced Options
- **Click Types**: Left/Right mouse buttons, Single/Double click.
- **Repetition**: Run infinitely or set a specific click limit.
- **Always on Top**: Keep the window floating above games or other applications.

### 🎨 Personalization
- **Theme Switching**: Toggle between **Dark Mode** and **Light Mode**.
- **Save on Close**: Configuration is saved when you exit the app.
- **State Persistence**: The app remembers which cards were open/closed.

## Global Hotkeys
- **F6**: Start / Stop Clicking
- **F8**: Pick Mouse Location

## Installation & Usage

### Running the Executable
Simply navigate to the `dist/` folder and run `HumanAutoClicker.exe`. No installation required.

### Developer Setup (Source)
1. Install dependencies:
   ```bash
   pip install customtkinter pynput pyinstaller
   ```
2. Run the script:
   ```bash
   python autoclicker.py
   ```

## Building
To create the standalone executable:
```bash
python -m PyInstaller --noconfirm --onefile --windowed --name "HumanAutoClicker" --clean --collect-all customtkinter autoclicker.py
```
