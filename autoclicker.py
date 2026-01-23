
import time
import random
import threading
import json
import os
import math
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image
from pynput.mouse import Button, Controller
from pynput.keyboard import Listener, Key

# Configuration for aesthetic - Material 3 inspired colors
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue") # We will override specific colors

# Font Configuration
FONT_HEADER = ("Segoe UI", 20, "bold")
FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_BODY = ("Segoe UI", 12)
FONT_SMALL = ("Segoe UI", 10)

class AutoClicker(threading.Thread):
    def __init__(self, interval, random_interval, click_type, button,
                 target_pos=None, random_pos_offset=(0,0), click_limit=0,
                 human_like=False, app=None):
        super().__init__()
        self.mouse = Controller()
        self.app = app
        self.interval = interval
        self.random_interval = random_interval
        self.click_type = click_type.lower()
        self.button_key = button # Store the name 'left' or 'right'
        self.button = Button.left if button.lower() == 'left' else Button.right
        self.click_limit = click_limit
        self.target_pos = target_pos
        self.random_pos_offset = random_pos_offset
        self.human_like = human_like
        self.running = False
        self.program_running = True
        self.click_count = 0
        
        self.drift_x = 0
        self.drift_y = 0

    def start_clicking(self):
        self.running = True
        self.click_count = 0
        self.drift_x = 0
        self.drift_y = 0

    def stop_clicking(self):
        self.running = False

    def exit(self):
        self.stop_clicking()
        self.program_running = False

    def run(self):
        while self.program_running:
            while self.running:
                target_x, target_y = self.target_pos if self.target_pos else self.mouse.position
                current_button = self.button
                current_click_type = self.click_type

                final_x, final_y = target_x, target_y

                # Random Drift Offset
                if self.random_pos_offset:
                    range_x, range_y = self.random_pos_offset
                    if range_x > 0 or range_y > 0:
                        if self.human_like:
                            drift_step_x = random.uniform(-1.5, 0.5)
                            drift_step_y = random.uniform(-1.5, 0.5)
                            self.drift_x += drift_step_x
                            self.drift_y += drift_step_y
                            if (abs(self.drift_x) > range_x) or (abs(self.drift_y) > range_y):
                                self.drift_x = random.uniform(-2, 2)
                                self.drift_y = random.uniform(-2, 2)
                            final_x += int(self.drift_x)
                            final_y += int(self.drift_y)
                        else:
                            final_x += random.randint(-range_x, range_x) if range_x > 0 else 0
                            final_y += random.randint(-range_y, range_y) if range_y > 0 else 0

                # Move to target if not current position
                if self.target_pos or (self.random_pos_offset and (self.random_pos_offset[0] > 0 or self.random_pos_offset[1] > 0)):
                     self.mouse.position = (final_x, final_y)

                # Clicking Execution
                click_count = 2 if current_click_type.lower() == 'double' else 1

                if self.human_like:
                    for i in range(click_count):
                        self.mouse.press(current_button)
                        time.sleep(random.uniform(0.005, 0.015)) # Humanized but snappy
                        self.mouse.release(current_button)
                        if click_count == 2 and i == 0:
                            time.sleep(random.uniform(0.005, 0.015)) # Small gap between double clicks
                else:
                    self.mouse.click(current_button, click_count)

                self.click_count += click_count

                # Update status periodically
                if self.click_limit > 0 and self.click_count >= self.click_limit:
                    self.stop_clicking()
                    if self.app: self.app.after(0, self.app.stop_clicking_ui)
                    break

                # Global interval
                p_delay = self.interval
                if self.random_interval > 0:
                    p_delay += random.uniform(0, self.random_interval)

                time.sleep(max(0.001, p_delay))
            
            time.sleep(0.1) 

class CollapsibleCard(ctk.CTkFrame):
    def __init__(self, master, title="", expanded=True, **kwargs):
        super().__init__(master, fg_color=("gray95", "gray20"), corner_radius=12, **kwargs) # Material Card Style
        self.columnconfigure(0, weight=1)
        self.expanded = expanded
        
        # Header (Clickable)
        self.title_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.title_frame.pack(fill="x", expand=True, padx=5, pady=2)
        self.title_frame.bind("<Button-1>", self.toggle)
        
        self.toggle_label = ctk.CTkLabel(self.title_frame, text="▼" if expanded else "▶", width=20, font=FONT_TITLE)
        self.toggle_label.pack(side="left", padx=(10, 5))
        self.toggle_label.bind("<Button-1>", self.toggle)
        
        self.label = ctk.CTkLabel(self.title_frame, text=title, font=FONT_TITLE)
        self.label.pack(side="left", padx=5)
        self.label.bind("<Button-1>", self.toggle)

        # Content Area
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        if expanded:
             self.content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def toggle(self, event=None):
        if not self.expanded:
            self.content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
            self.toggle_label.configure(text="▼")
            self.expanded = True
        else:
            self.content_frame.forget()
            self.toggle_label.configure(text="▶")
            self.expanded = False
        
        # Trigger parent resize if possible
        if self.master:
             try:
                 self.master.update_idletasks()
                 # Try to resize window if needed, specifically for the App
                 if hasattr(self.winfo_toplevel(), 'adjust_size'):
                     self.winfo_toplevel().adjust_size()
             except:
                 pass

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("HumanAutoClicker v1.2")
        # Set Application Icon
        try:
             self.iconbitmap("app_icon.ico")
        except:
             pass # Fail quietly if icon not found during dev

        self.click_thread = None
        self.hotkey_listener = None
        self.is_recording_hotkey = None # Tracks if we are waiting for a key press
        
        self.hotkey_start_var = ctk.StringVar(value="F6")
        self.hotkey_pick_var = ctk.StringVar(value="F8")
        self.hold_to_click_var = ctk.BooleanVar(value=False)
        
        # Trace hotkey changes to update UI
        self.hotkey_start_var.trace_add("write", self.update_hk_labels)
        
        self.grid_columnconfigure(0, weight=1)
        
        # Main Container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.create_header()
        self.create_cards()
        self.create_controls()

        self.setup_hotkey_listener()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.load_config()
        self.toggle_repeat_entry()
        self.toggle_pos_inputs()
        self.status_updater()
        
        # Initial resize
        self.after(100, self.adjust_size)

    def adjust_size(self):
        self.update_idletasks()
        # Find the active container (tab) or the main container
        req_height = self.main_container.winfo_reqheight() + 40
        
        # Enforce a minimum width but allow height to be dynamic
        self.geometry(f"400x{req_height}")

    def on_tab_change(self):
        self.adjust_size()

    def create_header(self):
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent", height=50)
        self.header_frame.pack(fill="x", pady=(0, 10))
        
        # Logo + Text
        try:
            # Load and resize logo
            logo_img = ctk.CTkImage(light_image=Image.open("app_icon.png"),
                                    dark_image=Image.open("app_icon.png"),
                                    size=(40, 40))
            self.logo_label = ctk.CTkLabel(self.header_frame, text="", image=logo_img)
            self.logo_label.pack(side="left", padx=(10, 10))
        except Exception as e:
            print(f"Logo not found: {e}")

        ctk.CTkLabel(self.header_frame, text="HumanAutoClicker", font=FONT_HEADER).pack(side="left", anchor="center")

    def create_cards(self):
        # Create Tabview
        self.tabview = ctk.CTkTabview(self.main_container, command=self.on_tab_change)
        self.tabview.pack(fill="both", expand=True, pady=5)
        
        self.tab_general = self.tabview.add("General")
        self.tab_advanced = self.tabview.add("Advanced")

        # --- TAB 1: GENERAL ---
        # Card 1: Click Settings
        self.card_main = CollapsibleCard(self.tab_general, title="Click Settings", expanded=True)
        self.card_main.pack(fill="x", pady=5)
        
        # Interval Row
        int_row = ctk.CTkFrame(self.card_main.content_frame, fg_color="transparent")
        int_row.pack(fill="x", pady=5)
        
        ctk.CTkLabel(int_row, text="Interval (s)", font=FONT_BODY).pack(side="left")
        self.interval_var = ctk.StringVar(value="0.1")
        self.interval_entry = ctk.CTkEntry(int_row, width=60, textvariable=self.interval_var)
        self.interval_entry.pack(side="right")
        
        # Random Row
        rand_row = ctk.CTkFrame(self.card_main.content_frame, fg_color="transparent")
        rand_row.pack(fill="x", pady=5)
        ctk.CTkLabel(rand_row, text="Randomness (±s)", font=FONT_BODY).pack(side="left")
        self.random_interval_var = ctk.StringVar(value="0.0")
        self.random_interval_entry = ctk.CTkEntry(rand_row, width=60, textvariable=self.random_interval_var)
        self.random_interval_entry.pack(side="right")
        
        # Type & Button
        type_row = ctk.CTkFrame(self.card_main.content_frame, fg_color="transparent")
        type_row.pack(fill="x", pady=10)
        
        self.button_var = ctk.StringVar(value="Left")
        self.lr_seg = ctk.CTkSegmentedButton(type_row, values=["Left", "Right"], variable=self.button_var)
        self.lr_seg.pack(fill="x", pady=(0,5))
        
        self.click_type_var = ctk.StringVar(value="Single")
        self.sd_seg = ctk.CTkSegmentedButton(type_row, values=["Single", "Double"], variable=self.click_type_var)
        self.sd_seg.pack(fill="x")

        # Card 2: Positioning (In General Tab)
        self.card_pos = CollapsibleCard(self.tab_general, title="Positioning", expanded=True)
        self.card_pos.pack(fill="x", pady=5)
        
        self.current_pos_var = ctk.BooleanVar(value=True)
        self.pos_switch = ctk.CTkSwitch(self.card_pos.content_frame, text="At Cursor Location", variable=self.current_pos_var, command=self.toggle_pos_inputs, font=FONT_BODY)
        self.pos_switch.pack(anchor="w", pady=5)
        
        pos_input_frame = ctk.CTkFrame(self.card_pos.content_frame, fg_color="transparent")
        pos_input_frame.pack(fill="x", pady=5)
        
        self.pick_pos_btn = ctk.CTkButton(pos_input_frame, text="Pick (F8)", command=self.pick_location_mode, width=80, height=28, font=FONT_BODY)
        self.pick_pos_btn.pack(side="left")
        
        self.pos_y_var = ctk.StringVar()
        self.pos_y_entry = ctk.CTkEntry(pos_input_frame, width=50, placeholder_text="Y", textvariable=self.pos_y_var)
        self.pos_y_entry.pack(side="right", padx=2)
        self.pos_x_var = ctk.StringVar()
        self.pos_x_entry = ctk.CTkEntry(pos_input_frame, width=50, placeholder_text="X", textvariable=self.pos_x_var)
        self.pos_x_entry.pack(side="right", padx=2)

        spread_frame = ctk.CTkFrame(self.card_pos.content_frame, fg_color="transparent")
        spread_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(spread_frame, text="Spread (±px)", font=FONT_BODY).pack(side="left")
        
        self.offset_y_var = ctk.StringVar(value="0")
        self.offset_y_entry = ctk.CTkEntry(spread_frame, width=50, textvariable=self.offset_y_var)
        self.offset_y_entry.pack(side="right", padx=2)
        self.offset_x_var = ctk.StringVar(value="0")
        self.offset_x_entry = ctk.CTkEntry(spread_frame, width=50, textvariable=self.offset_x_var)
        self.offset_x_entry.pack(side="right", padx=2)
        
        self.human_like_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(self.card_pos.content_frame, text="Humanized Behavior", variable=self.human_like_var, font=FONT_BODY).pack(anchor="w", pady=10)

        # --- TAB 2: ADVANCED ---
        self.card_adv = CollapsibleCard(self.tab_advanced, title="Advanced Settings", expanded=True)
        self.card_adv.pack(fill="x", pady=5)
        
        rep_frame = ctk.CTkFrame(self.card_adv.content_frame, fg_color="transparent")
        rep_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(rep_frame, text="Repeat limit:", font=FONT_BODY).pack(side="left")
        
        self.repeat_mode_var = ctk.StringVar(value="infinite")
        self.repeat_limit_var = ctk.StringVar(value="100")
        
        self.repeat_switch = ctk.CTkSwitch(rep_frame, text="Infinite", command=self.toggle_repeat_switch, onvalue="infinite", offvalue="limit", variable=self.repeat_mode_var)
        self.repeat_switch.pack(side="right")
        
        self.repeat_entry = ctk.CTkEntry(self.card_adv.content_frame, placeholder_text="Count", textvariable=self.repeat_limit_var)
        self.repeat_entry.pack(fill="x", pady=5)

        ctk.CTkLabel(self.card_adv.content_frame, text="Global Hotkeys", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10,5))
        
        hk_frame = ctk.CTkFrame(self.card_adv.content_frame, fg_color="transparent")
        hk_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(hk_frame, text="Start / Stop", font=FONT_BODY).pack(side="left")
        self.start_hk_btn = ctk.CTkButton(hk_frame, textvariable=self.hotkey_start_var, width=100, height=28, 
                                           fg_color=("gray80", "gray30"), text_color=("black", "white"),
                                           command=lambda: self.start_recording("start"))
        self.start_hk_btn.pack(side="right")

        hk_frame2 = ctk.CTkFrame(self.card_adv.content_frame, fg_color="transparent")
        hk_frame2.pack(fill="x", pady=2)
        ctk.CTkLabel(hk_frame2, text="Pick Location", font=FONT_BODY).pack(side="left")
        self.pick_hk_btn = ctk.CTkButton(hk_frame2, textvariable=self.hotkey_pick_var, width=100, height=28,
                                          fg_color=("gray80", "gray30"), text_color=("black", "white"),
                                          command=lambda: self.start_recording("pick"))
        self.pick_hk_btn.pack(side="right")

        ctk.CTkLabel(self.card_adv.content_frame, text="Behavior", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10,5))
        
        self.hold_switch = ctk.CTkSwitch(self.card_adv.content_frame, text="Hold to Click Mode", variable=self.hold_to_click_var, font=FONT_BODY)
        self.hold_switch.pack(anchor="w", pady=5)
        
        self.always_on_top_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(self.card_adv.content_frame, text="Always on Top", variable=self.always_on_top_var, command=self.toggle_always_on_top, font=FONT_BODY).pack(anchor="w", pady=5)
        
        self.theme_var = ctk.StringVar(value="Dark")
        ctk.CTkSwitch(self.card_adv.content_frame, text="Light Mode", onvalue="Light", offvalue="Dark", variable=self.theme_var, command=self.toggle_theme, font=FONT_BODY).pack(anchor="w", pady=5)


    def create_controls(self):
        self.control_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.control_frame.pack(fill="x", pady=10)
        
        # Floating Action Button Style (Large, Round)
        self.start_btn = ctk.CTkButton(self.control_frame, text="START (F6)", command=self.start_clicking, 
                                       fg_color="#4CAF50", hover_color="#45a049", 
                                       height=50, corner_radius=25, font=("Segoe UI", 16, "bold"))
        self.start_btn.pack(side="left", expand=True, fill="x", padx=5)
        
        self.stop_btn = ctk.CTkButton(self.control_frame, text="STOP", command=self.stop_clicking_ui, 
                                      fg_color="#f44336", hover_color="#d32f2f", 
                                      state="disabled", height=50, corner_radius=25, font=("Segoe UI", 16, "bold"))
        self.stop_btn.pack(side="right", expand=True, fill="x", padx=5)
        
        self.status_var = ctk.StringVar(value="Ready")
        self.status_bar = ctk.CTkLabel(self.main_container, textvariable=self.status_var, font=FONT_SMALL, text_color="gray")
        self.status_bar.pack(pady=0)

    def toggle_always_on_top(self):
        self.attributes('-topmost', self.always_on_top_var.get())

    def toggle_theme(self):
        ctk.set_appearance_mode(self.theme_var.get())

    def toggle_pos_inputs(self):
        state = "disabled" if self.current_pos_var.get() else "normal"
        self.pick_pos_btn.configure(state=state)
        self.pos_x_entry.configure(state=state)
        self.pos_y_entry.configure(state=state)

    def toggle_repeat_switch(self):
        self.toggle_repeat_entry()

    def toggle_repeat_entry(self):
        # If infinite, disable entry
        if self.repeat_mode_var.get() == "infinite":
            self.repeat_entry.configure(state="disabled")
        else:
            self.repeat_entry.configure(state="normal")
        self.adjust_size() # Input might change layout slightly? No, but good practice.
        
    def update_hk_labels(self, *args):
        hk = self.hotkey_start_var.get()
        self.start_btn.configure(text=f"START ({hk})")

    def start_recording(self, target):
        self.is_recording_hotkey = target
        if target == "start":
            self.start_hk_btn.configure(text="Recording...", fg_color="#FF9800")
        else:
            self.pick_hk_btn.configure(text="Recording...", fg_color="#FF9800")
        self.status_var.set(f"RECORDING: Press new key for {target}")

    def key_to_str(self, key):
        try:
            # Handle standard characters
            if hasattr(key, 'char') and key.char:
                return key.char.upper()
            # Handle special keys (F1-F12, etc)
            k_str = str(key).replace('Key.', '').upper()
            return k_str
        except:
            return str(key).upper()

    def pick_location_mode(self):
        hk = self.hotkey_pick_var.get()
        self.status_var.set(f"PICK MODE: Move mouse and press {hk}")
        self.update()

    def setup_hotkey_listener(self):
        def on_press(key):
            try:
                k_str = self.key_to_str(key)
                
                # Handle Recording
                if self.is_recording_hotkey:
                    if self.is_recording_hotkey == "start":
                        self.hotkey_start_var.set(k_str)
                        self.start_hk_btn.configure(fg_color=("gray80", "gray30"))
                    else:
                        self.hotkey_pick_var.set(k_str)
                        self.pick_hk_btn.configure(fg_color=("gray80", "gray30"))
                    
                    self.is_recording_hotkey = None
                    self.status_var.set(f"Bound to {k_str}")
                    return

                # Normal Hotkey Actions
                if k_str == self.hotkey_start_var.get():
                    if self.is_clicking():
                        # If in Hold mode, we handle stop on release, but toggle is still allowed
                        if not self.hold_to_click_var.get():
                            self.after(0, self.stop_clicking_ui)
                    else:
                        self.after(0, self.start_clicking)
                        
                elif k_str == self.hotkey_pick_var.get():
                    mouse_pos = self.mouse_controller.position
                    self.after(0, lambda: self.set_picked_location(mouse_pos))
                    
            except Exception as e:
                print(f"Hotkey Error: {e}")

        def on_release(key):
            if self.hold_to_click_var.get():
                k_str = self.key_to_str(key)
                if k_str == self.hotkey_start_var.get() and self.is_clicking():
                    self.after(0, self.stop_clicking_ui)
        
        try:
            self.mouse_controller = Controller()
            self.hotkey_listener = Listener(on_press=on_press, on_release=on_release)
            self.hotkey_listener.start()
        except:
             print("Failed to start hotkey listener")

    def set_picked_location(self, pos):
        if not self.current_pos_var.get():
            self.pos_x_var.set(str(pos[0]))
            self.pos_y_var.set(str(pos[1]))
            self.status_var.set(f"Position set to {pos}")

    def is_clicking(self):
        return self.click_thread and self.click_thread.running

    def start_clicking(self):
        if self.is_clicking():
            return

        try:
            interval = float(self.interval_var.get())
            rand_interval = float(self.random_interval_var.get())
            
            click_limit = 0
            if self.repeat_mode_var.get() == "limit":
                click_limit = int(self.repeat_limit_var.get())

            target_pos = None
            rand_pos_offset = (0, 0)
            
            if not self.current_pos_var.get():
                try:
                    px = int(self.pos_x_var.get())
                    py = int(self.pos_y_var.get())
                    target_pos = (px, py)
                except ValueError:
                    messagebox.showerror("Error", "Invalid Coordinate values")
                    return

            try:
                ox = int(self.offset_x_var.get())
                oy = int(self.offset_y_var.get())
                rand_pos_offset = (ox, oy)
            except ValueError:
                pass

            if self.click_thread and self.click_thread.is_alive():
                 self.click_thread.exit()

            self.click_thread = AutoClicker(
                interval=interval,
                random_interval=rand_interval,
                click_type=self.click_type_var.get(),
                button=self.button_var.get(),
                target_pos=target_pos,
                random_pos_offset=rand_pos_offset,
                click_limit=click_limit,
                human_like=self.human_like_var.get(),
                app=self
            )
            
            self.click_thread.start()
            self.click_thread.start_clicking()
            
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            hk = self.hotkey_start_var.get()
            self.status_var.set(f"RUNNING... Press {hk} to Stop")
            
        except ValueError:
            messagebox.showerror("Error", "Invalid Numeric Input")

    def stop_clicking_ui(self):
        if self.click_thread:
            self.click_thread.stop_clicking()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_var.set("Stopped")

    def update_status(self):
        if self.is_clicking():
            msg = f"RUNNING... {self.click_thread.click_count}"
            if self.click_thread.click_limit > 0:
                msg += f" / {self.click_thread.click_limit}"
            self.status_var.set(msg)

    def status_updater(self):
        self.update_status()
        self.after(100, self.status_updater)

    def on_close(self):
        if self.click_thread and self.click_thread.is_alive():
            self.click_thread.exit()
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except:
                pass
        self.save_config()
        self.destroy()
    
    def get_config_path(self):
        return "autoclicker_config.json"

    def save_config(self):
        config = {
            "interval": self.interval_var.get(),
            "random_interval": self.random_interval_var.get(),
            "button": self.button_var.get(),
            "click_type": self.click_type_var.get(),
            "repeat_mode": self.repeat_mode_var.get(),
            "repeat_limit": self.repeat_limit_var.get(),
            "use_current_pos": self.current_pos_var.get(),
            "pos_x": self.pos_x_var.get(),
            "pos_y": self.pos_y_var.get(),
            "offset_x": self.offset_x_var.get(),
            "offset_y": self.offset_y_var.get(),
            "always_on_top": self.always_on_top_var.get(),
            "theme": self.theme_var.get(),
            "human_like": self.human_like_var.get(),
            # Save Card States
            "card_main_expanded": self.card_main.expanded,
            "card_pos_expanded": self.card_pos.expanded,
            "card_adv_expanded": self.card_adv.expanded,
            "hotkey_start": self.hotkey_start_var.get(),
            "hotkey_pick": self.hotkey_pick_var.get(),
            "hold_to_click": self.hold_to_click_var.get()
        }
        try:
            with open(self.get_config_path(), 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def load_config(self):
        try:
            if os.path.exists(self.get_config_path()):
                with open(self.get_config_path(), 'r') as f:
                    config = json.load(f)
                    
                self.interval_var.set(config.get("interval", "0.1"))
                self.random_interval_var.set(config.get("random_interval", "0.0"))
                button_val = config.get("button", "Left")
                if isinstance(button_val, str):
                    button_val = button_val.capitalize()
                if button_val not in ("Left", "Right"):
                    button_val = "Left"
                self.button_var.set(button_val)

                click_type_val = config.get("click_type", "Single")
                if isinstance(click_type_val, str):
                    click_type_val = click_type_val.capitalize()
                if click_type_val not in ("Single", "Double"):
                    click_type_val = "Single"
                self.click_type_var.set(click_type_val)
                self.repeat_mode_var.set(config.get("repeat_mode", "infinite"))
                self.repeat_limit_var.set(config.get("repeat_limit", "100"))
                self.current_pos_var.set(config.get("use_current_pos", True))
                self.pos_x_var.set(config.get("pos_x", ""))
                self.pos_y_var.set(config.get("pos_y", ""))
                self.offset_x_var.set(config.get("offset_x", "0"))
                self.offset_y_var.set(config.get("offset_y", "0"))
                
                self.always_on_top_var.set(config.get("always_on_top", False))
                self.attributes('-topmost', self.always_on_top_var.get())
                
                loaded_theme = config.get("theme", "Dark")
                self.theme_var.set(loaded_theme)
                ctk.set_appearance_mode(loaded_theme)
                
                self.human_like_var.set(config.get("human_like", False))
                self.hotkey_start_var.set(config.get("hotkey_start", "F6"))
                self.hotkey_pick_var.set(config.get("hotkey_pick", "F8"))
                self.hold_to_click_var.set(config.get("hold_to_click", False))
                # Restore Card States
                if not config.get("card_main_expanded", True): self.card_main.toggle()
                if not config.get("card_pos_expanded", True): self.card_pos.toggle()
                if not config.get("card_adv_expanded", True): self.card_adv.toggle()

                self.toggle_repeat_entry()
                self.toggle_pos_inputs()
                self.adjust_size()

        except Exception as e:
            print(f"Failed to load config: {e}")

if __name__ == '__main__':
    app = App()
    app.mainloop()
