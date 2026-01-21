
import time
import random
import threading
import json
import os
import math
import customtkinter as ctk
from tkinter import messagebox
from pynput.mouse import Button, Controller
from pynput.keyboard import Listener, Key

# Configuration for aesthetic
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

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
        
        # Human-like drift state
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
                
                # 1. Determine Base Position
                if self.position:
                    target_x, target_y = self.position
                else:
                    target_x, target_y = self.mouse.position

                # 2. Calculate Final Position with Offset
                final_x, final_y = target_x, target_y
                
                if self.random_pos_offset:
                    range_x = self.random_pos_offset[0]
                    range_y = self.random_pos_offset[1]
                    
                    if range_x > 0 or range_y > 0:
                        if self.human_like:
                            # Human Drift Logic
                            drift_step_x = random.uniform(-1.5, 0.5) 
                            drift_step_y = random.uniform(-1.5, 0.5)
                            
                            self.drift_x += drift_step_x
                            self.drift_y += drift_step_y
                            
                            # Check boundaries
                            if (abs(self.drift_x) > range_x) or (abs(self.drift_y) > range_y):
                                # Reset close to center
                                self.drift_x = random.uniform(-2, 2)
                                self.drift_y = random.uniform(-2, 2)
                            
                            final_x += int(self.drift_x)
                            final_y += int(self.drift_y)
                            
                        else:
                            # Standard Random Logic
                            x_offset = random.randint(-range_x, range_x) if range_x > 0 else 0
                            y_offset = random.randint(-range_y, range_y) if range_y > 0 else 0
                            final_x += x_offset
                            final_y += y_offset

                # Apply Position
                if self.position or (self.random_pos_offset and (self.random_pos_offset[0] > 0 or self.random_pos_offset[1] > 0)):
                     self.mouse.position = (final_x, final_y)

                # Perform the click
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

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("HumanAutoClicker v1.0")
        self.geometry("500x800")
        self.resizable(False, False)

        self.click_thread = None
        self.hotkey_listener = None
        self.save_timer = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

        self.create_widgets()
        self.setup_hotkey_listener()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.load_config()
        self.status_updater()

    def create_widgets(self):
        # Header
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(20, 10))
        ctk.CTkLabel(self.header_frame, text="HumanAutoClicker", font=ctk.CTkFont(size=24, weight="bold")).pack()
        ctk.CTkLabel(self.header_frame, text="Advanced Automation Tool", font=ctk.CTkFont(size=12)).pack()

        # 1. Click Interval
        self.interval_frame = ctk.CTkFrame(self)
        self.interval_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.interval_frame.grid_columnconfigure((1, 3), weight=1)
        
        ctk.CTkLabel(self.interval_frame, text="Click Interval", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, pady=5, sticky="w", padx=10)
        
        ctk.CTkLabel(self.interval_frame, text="Seconds (e.g. 0.01):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.interval_var = ctk.StringVar(value="0.1")
        self.interval_entry = ctk.CTkEntry(self.interval_frame, width=80, textvariable=self.interval_var)
        self.interval_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(self.interval_frame, text="Random ± (s):").grid(row=1, column=2, padx=10, pady=5, sticky="w")
        self.random_interval_var = ctk.StringVar(value="0.0")
        self.random_interval_entry = ctk.CTkEntry(self.interval_frame, width=80, textvariable=self.random_interval_var)
        self.random_interval_entry.grid(row=1, column=3, padx=5, pady=5, sticky="ew")

        # 2. Click Options
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.options_frame.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(self.options_frame, text="Click Options", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, pady=5, sticky="w", padx=10)

        ctk.CTkLabel(self.options_frame, text="Mouse Button:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.button_var = ctk.StringVar(value="left")
        ctk.CTkRadioButton(self.options_frame, text="Left", variable=self.button_var, value="left", command=self.trigger_save).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkRadioButton(self.options_frame, text="Right", variable=self.button_var, value="right", command=self.trigger_save).grid(row=1, column=2, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(self.options_frame, text="Click Type:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.click_type_var = ctk.StringVar(value="single")
        ctk.CTkRadioButton(self.options_frame, text="Single", variable=self.click_type_var, value="single", command=self.trigger_save).grid(row=2, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkRadioButton(self.options_frame, text="Double", variable=self.click_type_var, value="double", command=self.trigger_save).grid(row=2, column=2, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(self.options_frame, text="Repeat:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.repeat_mode_var = ctk.StringVar(value="infinite")
        self.repeat_infinite_rb = ctk.CTkRadioButton(self.options_frame, text="Until Stopped", variable=self.repeat_mode_var, value="infinite", command=self.toggle_repeat_entry)
        self.repeat_infinite_rb.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        
        self.repeat_limit_rb = ctk.CTkRadioButton(self.options_frame, text="Times:", variable=self.repeat_mode_var, value="limit", command=self.toggle_repeat_entry)
        self.repeat_limit_rb.grid(row=3, column=2, padx=5, pady=5, sticky="w")
        
        self.repeat_limit_var = ctk.StringVar(value="100")
        self.repeat_entry = ctk.CTkEntry(self.options_frame, width=60, textvariable=self.repeat_limit_var)
        self.repeat_entry.grid(row=3, column=3, padx=5, pady=5, sticky="w")

        # 3. Position Settings
        self.pos_frame = ctk.CTkFrame(self)
        self.pos_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.pos_frame, text="Position Settings", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, pady=5, sticky="w", padx=10)

        self.current_pos_var = ctk.BooleanVar(value=True)
        self.pos_checkbox = ctk.CTkCheckBox(self.pos_frame, text="Click at current mouse position", variable=self.current_pos_var, command=self.toggle_pos_inputs)
        self.pos_checkbox.grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky="w")

        self.pick_pos_btn = ctk.CTkButton(self.pos_frame, text="Pick Location (F8)", command=self.pick_location_mode, width=120)
        self.pick_pos_btn.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.pos_x_var = ctk.StringVar()
        self.pos_y_var = ctk.StringVar()
        self.pos_x_entry = ctk.CTkEntry(self.pos_frame, width=60, placeholder_text="X", textvariable=self.pos_x_var)
        self.pos_x_entry.grid(row=2, column=1, padx=5, pady=5)
        self.pos_y_entry = ctk.CTkEntry(self.pos_frame, width=60, placeholder_text="Y", textvariable=self.pos_y_var)
        self.pos_y_entry.grid(row=2, column=2, padx=5, pady=5)

        ctk.CTkLabel(self.pos_frame, text="Spread (Radius):").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.offset_x_var = ctk.StringVar(value="0")
        self.offset_y_var = ctk.StringVar(value="0")
        self.offset_x_entry = ctk.CTkEntry(self.pos_frame, width=60, textvariable=self.offset_x_var)
        self.offset_x_entry.grid(row=3, column=1, padx=5, pady=5)
        self.offset_y_entry = ctk.CTkEntry(self.pos_frame, width=60, textvariable=self.offset_y_var)
        self.offset_y_entry.grid(row=3, column=2, padx=5, pady=5)
        
        # Human Like
        self.human_like_var = ctk.BooleanVar(value=False)
        self.human_like_chk = ctk.CTkSwitch(self.pos_frame, text="Human-like Drift", variable=self.human_like_var, command=self.trigger_save)
        self.human_like_chk.grid(row=4, column=0, columnspan=4, padx=10, pady=(10, 5), sticky="w")

        # 4. App Settings
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        
        self.always_on_top_var = ctk.BooleanVar(value=False)
        self.always_on_top_check = ctk.CTkSwitch(self.settings_frame, text="Always on Top", variable=self.always_on_top_var, command=self.toggle_always_on_top)
        self.always_on_top_check.pack(side="left", padx=20, pady=10)

        self.theme_var = ctk.StringVar(value="Dark")
        self.theme_switch = ctk.CTkSwitch(self.settings_frame, text="Light Mode", onvalue="Light", offvalue="Dark", variable=self.theme_var, command=self.toggle_theme)
        self.theme_switch.pack(side="right", padx=20, pady=10)

        self.toggle_pos_inputs()
        self.toggle_repeat_entry()

        # 5. Global Hotkeys Info & Control
        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        
        self.start_btn = ctk.CTkButton(self.control_frame, text="START (F6)", command=self.start_clicking, fg_color="green", hover_color="darkgreen", height=40)
        self.start_btn.pack(side="left", expand=True, padx=5)
        
        self.stop_btn = ctk.CTkButton(self.control_frame, text="STOP (F6)", command=self.stop_clicking_ui, fg_color="red", hover_color="darkred", state="disabled", height=40)
        self.stop_btn.pack(side="right", expand=True, padx=5)

        # Status Bar
        self.status_var = ctk.StringVar(value="Ready. Press F6 to Start/Stop.")
        self.status_bar = ctk.CTkLabel(self, textvariable=self.status_var, height=30, fg_color=("gray85", "gray20"))
        self.status_bar.grid(row=6, column=0, sticky="ew", padx=0, pady=0)
        
        self.bind_autosave()

    def bind_autosave(self):
        # Bind KeyRelease events to Entries
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
        if self.current_pos_var.get():
            self.pos_x_entry.configure(state="disabled")
            self.pos_y_entry.configure(state="disabled")
            self.pick_pos_btn.configure(state="disabled")
        else:
            self.pos_x_entry.configure(state="normal")
            self.pos_y_entry.configure(state="normal")
            self.pick_pos_btn.configure(state="normal")
        self.trigger_save()

    def toggle_repeat_entry(self):
        if self.repeat_mode_var.get() == "infinite":
            self.repeat_entry.configure(state="disabled")
        else:
            self.repeat_entry.configure(state="normal")
        self.trigger_save()

    def pick_location_mode(self):
        self.status_var.set("PICK MODE: Move mouse and press F8 to set position.")
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
        self.status_var.set("Stopped.")

    def update_status(self):
        if self.is_clicking():
            msg = f"RUNNING... Clicks: {self.click_thread.click_count}"
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
            "human_like": self.human_like_var.get()
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

                self.toggle_repeat_entry()
                self.toggle_pos_inputs()

        except Exception as e:
            print(f"Failed to load config: {e}")

if __name__ == '__main__':
    app = App()
    app.mainloop()
