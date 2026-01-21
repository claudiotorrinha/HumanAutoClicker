
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
                 position=None, random_pos_offset=(0,0), click_limit=0, 
                 human_like=False, app=None):
        super().__init__()
        self.mouse = Controller()
        self.app = app
        self.interval = interval
        self.random_interval = random_interval
        self.click_type = click_type
        self.button = Button.left if button == 'left' else Button.right
        self.click_limit = click_limit
        self.position = position
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
                target_x, target_y = 0, 0
                
                if self.position:
                    target_x, target_y = self.position
                else:
                    target_x, target_y = self.mouse.position

                final_x, final_y = target_x, target_y
                
                if self.random_pos_offset:
                    range_x = self.random_pos_offset[0]
                    range_y = self.random_pos_offset[1]
                    
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
                            x_offset = random.randint(-range_x, range_x) if range_x > 0 else 0
                            y_offset = random.randint(-range_y, range_y) if range_y > 0 else 0
                            final_x += x_offset
                            final_y += y_offset

                if self.position or (self.random_pos_offset and (self.random_pos_offset[0] > 0 or self.random_pos_offset[1] > 0)):
                     self.mouse.position = (final_x, final_y)

                if self.click_type == 'double':
                    self.mouse.click(self.button, 2)
                else: 
                    self.mouse.click(self.button, 1)
                
                self.click_count += 1
                
                if self.click_limit > 0 and self.click_count >= self.click_limit:
                    self.stop_clicking()
                    if self.app:
                        self.app.after(0, self.app.stop_clicking_ui)
                    break 

                sleep_interval = self.interval
                if self.random_interval > 0:
                    sleep_interval += random.uniform(0, self.random_interval)
                
                time.sleep(max(0.001, sleep_interval))
            
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

        self.title("HumanAutoClicker v1.1")
        # Set Application Icon
        try:
             self.iconbitmap("app_icon.ico")
        except:
             pass # Fail quietly if icon not found during dev

        self.click_thread = None
        self.hotkey_listener = None
        self.save_timer = None
        
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
        self.status_updater()
        
        # Initial resize
        self.after(100, self.adjust_size)

    def adjust_size(self):
        self.update_idletasks()
        req_height = self.main_container.winfo_reqheight() + 40 # Padding
        # Limit max height just in case, but let it grow
        self.geometry(f"400x{req_height}")

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
        # Card 1: Click Settings
        self.card_main = CollapsibleCard(self.main_container, title="Click Settings", expanded=True)
        self.card_main.pack(fill="x", pady=5)
        
        # Interval Row
        int_row = ctk.CTkFrame(self.card_main.content_frame, fg_color="transparent")
        int_row.pack(fill="x", pady=5)
        
        ctk.CTkLabel(int_row, text="Interval (s)", font=FONT_BODY).pack(side="left")
        self.interval_var = ctk.StringVar(value="0.1")
        self.interval_entry = ctk.CTkEntry(int_row, width=60, textvariable=self.interval_var)
        self.interval_entry.pack(side="right") # Right aligned
        
        # Random Row
        rand_row = ctk.CTkFrame(self.card_main.content_frame, fg_color="transparent")
        rand_row.pack(fill="x", pady=5)
        ctk.CTkLabel(rand_row, text="Randomness (±s)", font=FONT_BODY).pack(side="left")
        self.random_interval_var = ctk.StringVar(value="0.0")
        self.random_interval_entry = ctk.CTkEntry(rand_row, width=60, textvariable=self.random_interval_var)
        self.random_interval_entry.pack(side="right")
        
        # Type & Button - Using Segmented Buttons which fit Material Design better
        type_row = ctk.CTkFrame(self.card_main.content_frame, fg_color="transparent")
        type_row.pack(fill="x", pady=10)
        
        self.button_var = ctk.StringVar(value="left")
        self.lr_seg = ctk.CTkSegmentedButton(type_row, values=["Left", "Right"], variable=self.button_var, command=self.trigger_save)
        self.lr_seg.pack(fill="x", pady=(0,5))
        
        self.click_type_var = ctk.StringVar(value="single")
        self.sd_seg = ctk.CTkSegmentedButton(type_row, values=["Single", "Double"], variable=self.click_type_var, command=self.trigger_save)
        self.sd_seg.pack(fill="x")

        # Card 2: Positioning (Default Open)
        self.card_pos = CollapsibleCard(self.main_container, title="Positioning", expanded=True)
        self.card_pos.pack(fill="x", pady=5)
        
        self.current_pos_var = ctk.BooleanVar(value=True)
        self.pos_switch = ctk.CTkSwitch(self.card_pos.content_frame, text="At Cursor Location", variable=self.current_pos_var, command=self.toggle_pos_inputs, font=FONT_BODY)
        self.pos_switch.pack(anchor="w", pady=5)
        
        # Inputs Row
        pos_input_frame = ctk.CTkFrame(self.card_pos.content_frame, fg_color="transparent")
        pos_input_frame.pack(fill="x", pady=5)
        
        self.pick_pos_btn = ctk.CTkButton(pos_input_frame, text="Pick (F8)", command=self.pick_location_mode, width=80, height=28, font=FONT_BODY)
        self.pick_pos_btn.pack(side="left")
        
        self.pos_y_var = ctk.StringVar()
        ctk.CTkEntry(pos_input_frame, width=50, placeholder_text="Y", textvariable=self.pos_y_var).pack(side="right", padx=2)
        self.pos_x_var = ctk.StringVar()
        ctk.CTkEntry(pos_input_frame, width=50, placeholder_text="X", textvariable=self.pos_x_var).pack(side="right", padx=2)

        # Spread
        spread_frame = ctk.CTkFrame(self.card_pos.content_frame, fg_color="transparent")
        spread_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(spread_frame, text="Spread (±px)", font=FONT_BODY).pack(side="left")
        
        self.offset_y_var = ctk.StringVar(value="0")
        ctk.CTkEntry(spread_frame, width=50, textvariable=self.offset_y_var).pack(side="right", padx=2)
        self.offset_x_var = ctk.StringVar(value="0")
        ctk.CTkEntry(spread_frame, width=50, textvariable=self.offset_x_var).pack(side="right", padx=2)
        
        self.human_like_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(self.card_pos.content_frame, text="Human-like Drift", variable=self.human_like_var, command=self.trigger_save, font=FONT_BODY).pack(anchor="w", pady=10)

        # Card 3: Advanced (Default Open)
        self.card_adv = CollapsibleCard(self.main_container, title="Advanced", expanded=True)
        self.card_adv.pack(fill="x", pady=5)
        
        # Repeat
        rep_frame = ctk.CTkFrame(self.card_adv.content_frame, fg_color="transparent")
        rep_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(rep_frame, text="Repeat limit:", font=FONT_BODY).pack(side="left")
        
        self.repeat_mode_var = ctk.StringVar(value="infinite")
        self.repeat_limit_var = ctk.StringVar(value="100")
        
        # We'll use a switch logic for "Infinite" vs "Finite"
        self.repeat_switch = ctk.CTkSwitch(rep_frame, text="Infinite", command=self.toggle_repeat_switch, onvalue="infinite", offvalue="limit", variable=self.repeat_mode_var)
        self.repeat_switch.pack(side="right")
        
        self.repeat_entry = ctk.CTkEntry(self.card_adv.content_frame, placeholder_text="Count", textvariable=self.repeat_limit_var)
        self.repeat_entry.pack(fill="x", pady=5)

        ctk.CTkLabel(self.card_adv.content_frame, text="Application", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10,5))
        
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

    def bind_autosave(self):
        for entry in [self.interval_entry, self.random_interval_entry, self.repeat_entry, 
                      self.pos_x_entry, self.pos_y_entry, self.offset_x_entry, self.offset_y_entry]:
            try:
                entry.bind("<KeyRelease>", lambda e: self.trigger_save())
            except:
                pass

    def trigger_save(self, *args):
        if self.save_timer is not None:
            self.after_cancel(self.save_timer)
        self.save_timer = self.after(1000, self.save_config)

    def toggle_always_on_top(self):
        self.attributes('-topmost', self.always_on_top_var.get())
        self.trigger_save()

    def toggle_theme(self):
        ctk.set_appearance_mode(self.theme_var.get())
        self.trigger_save()

    def toggle_pos_inputs(self):
        state = "disabled" if self.current_pos_var.get() else "normal"
        self.pick_pos_btn.configure(state=state)
        self.pos_x_entry.configure(state=state)
        self.pos_y_entry.configure(state=state)
        self.trigger_save()

    def toggle_repeat_switch(self):
        self.toggle_repeat_entry()
        self.trigger_save()

    def toggle_repeat_entry(self):
        # If infinite, disable entry
        if self.repeat_mode_var.get() == "infinite":
            self.repeat_entry.configure(state="disabled")
        else:
            self.repeat_entry.configure(state="normal")
        self.adjust_size() # Input might change layout slightly? No, but good practice.
        self.trigger_save()
        
    def pick_location_mode(self):
        self.status_var.set("PICK MODE: Move mouse and press F8")
        self.update()

    def setup_hotkey_listener(self):
        def on_press(key):
            try:
                if key == Key.f6:
                    if self.is_clicking():
                        self.after(0, self.stop_clicking_ui)
                    else:
                        self.after(0, self.start_clicking)
                        
                if key == Key.f8:
                    mouse_pos = self.mouse_controller.position
                    self.after(0, lambda: self.set_picked_location(mouse_pos))
                    
            except Exception as e:
                print(e)
        
        try:
            self.mouse_controller = Controller()
            self.hotkey_listener = Listener(on_press=on_press)
            self.hotkey_listener.start()
        except:
             print("Failed to start hotkey listener")

    def set_picked_location(self, pos):
        if not self.current_pos_var.get():
            self.pos_x_var.set(str(pos[0]))
            self.pos_y_var.set(str(pos[1]))
            self.status_var.set(f"Position set to {pos}")
            self.trigger_save()

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

            position = None
            rand_pos_offset = (0, 0)
            
            if not self.current_pos_var.get():
                try:
                    px = int(self.pos_x_var.get())
                    py = int(self.pos_y_var.get())
                    position = (px, py)
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
                position=position,
                random_pos_offset=rand_pos_offset,
                click_limit=click_limit,
                human_like=self.human_like_var.get(),
                app=self
            )
            
            self.click_thread.start()
            self.click_thread.start_clicking()
            
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.status_var.set("RUNNING... Press F6 to Stop")
            
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
            "card_adv_expanded": self.card_adv.expanded
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
                self.button_var.set(config.get("button", "left"))
                self.click_type_var.set(config.get("click_type", "single"))
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
                
                # Restore Card States
                if not config.get("card_main_expanded", True): self.card_main.toggle()
                if config.get("card_pos_expanded", False): self.card_pos.toggle()
                if config.get("card_adv_expanded", False): self.card_adv.toggle()

                self.toggle_repeat_entry()
                self.toggle_pos_inputs()
                self.adjust_size()

        except Exception as e:
            print(f"Failed to load config: {e}")

if __name__ == '__main__':
    app = App()
    app.mainloop()
