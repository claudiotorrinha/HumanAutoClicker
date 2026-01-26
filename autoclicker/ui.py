import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageOps
from pynput.mouse import Controller
from pynput.keyboard import Listener

from .config import read_config, write_config
from .core import (
    AutoClicker,
    MS_PER_SEC,
    DEFAULT_INTERVAL_MS,
    DEFAULT_RANDOM_INTERVAL_MS,
    DEFAULT_EXP_MEAN_INTERVAL_MS,
    DEFAULT_HOLD_TIME_ENABLED,
    DEFAULT_HOLD_TIME_MEAN_MS,
    DEFAULT_HOLD_TIME_STD_MS,
    DEFAULT_DRIFT_ENABLED,
    DEFAULT_DRIFT_STEP_MIN,
    DEFAULT_DRIFT_STEP_MAX,
    DEFAULT_DRIFT_RESET_MIN,
    DEFAULT_DRIFT_RESET_MAX,
    DEFAULT_THINKING_PAUSE_ENABLED,
    DEFAULT_THINKING_PAUSE_MEAN_MS,
    DEFAULT_THINKING_PAUSE_STD_MS,
    DEFAULT_THINKING_PAUSE_MIN_CLICKS,
    DEFAULT_THINKING_PAUSE_MAX_CLICKS,
    DEFAULT_FATIGUE_ENABLED,
    DEFAULT_FATIGUE_THRESHOLD_INTERVAL_MS,
    DEFAULT_FATIGUE_DURATION_MS,
    DEFAULT_FATIGUE_COOLDOWN_DURATION_MS,
    DEFAULT_FATIGUE_COOLDOWN_MIN_INTERVAL_MS,
    get_foreground_window_handle,
    get_window_at_point,
    coerce_bool,
    safe_int,
)

UI_SCALE = 1.0
MIN_FONT_SIZE = 10
STATUS_UPDATE_INTERVAL_MS = 100
DEFAULT_WINDOW_WIDTH = 500
DEFAULT_WINDOW_HEIGHT = 520
MIN_WINDOW_WIDTH = 480
MIN_WINDOW_HEIGHT = 520


def ui(value, min_value=1):
    return max(min_value, int(round(value * UI_SCALE)))


def font_size(size):
    return max(MIN_FONT_SIZE, int(round(size * UI_SCALE)))


FONT_HEADER = ("Bahnschrift", font_size(20), "bold")
FONT_TITLE = ("Bahnschrift", font_size(14), "bold")
FONT_BODY = ("Bahnschrift", font_size(12))
FONT_SMALL = ("Bahnschrift", font_size(10))


def resource_path(filename):
    base_dir = getattr(sys, "_MEIPASS", None)
    if base_dir:
        return os.path.join(base_dir, filename)
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    candidate = os.path.join(project_dir, filename)
    if os.path.exists(candidate):
        return candidate
    return filename


class ToolTip:
    def __init__(self, widget, text, delay_ms=400):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.tip = None
        self.after_id = None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.on_click, add="+")
        widget.bind("<FocusIn>", self.show_now, add="+")
        widget.bind("<FocusOut>", self.hide, add="+")

    def schedule(self, _event=None):
        self.cancel()
        self.after_id = self.widget.after(self.delay_ms, self.show)

    def cancel(self):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def show(self):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        try:
            self.tip.attributes("-topmost", True)
        except tk.TclError:
            pass
        theme = str(self.widget.tk.call("ttk::style", "theme", "use")).lower()
        is_dark = "dark" in theme
        bg = "#2b2b2b" if is_dark else "#f5f5f5"
        fg = "#f2f2f2" if is_dark else "#1c1c1c"
        label = tk.Label(
            self.tip,
            text=self.text,
            background=bg,
            foreground=fg,
            relief="solid",
            borderwidth=1,
            justify="left",
            wraplength=260,
        )
        label.pack(ipadx=6, ipady=4)
        self.tip.lift()

    def show_now(self, _event=None):
        self.cancel()
        self.show()

    def hide(self, _event=None):
        self.cancel()
        if self.tip:
            self.tip.destroy()
            self.tip = None

    def on_click(self, _event=None):
        if self.tip:
            self.hide()
        else:
            self.show_now()


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.theme_mode = "light"
        self.info_icon_labels = []
        self.info_icon_images = {}

        self.init_theme()
        self.apply_theme("dark")

        self.title("HumanAutoClicker v1.2")
        self.minsize(ui(MIN_WINDOW_WIDTH), ui(MIN_WINDOW_HEIGHT))
        self.geometry(f"{ui(DEFAULT_WINDOW_WIDTH)}x{ui(DEFAULT_WINDOW_HEIGHT)}")
        self.resizable(True, True)
        try:
            self.iconbitmap(resource_path("app_icon.ico"))
        except:
            pass

        self.click_thread = None
        self.hotkey_listener = None
        self.is_recording_hotkey = None

        self.default_button_style = "TButton"
        self.accent_button_style = "Accent.TButton"
        self.switch_style = "Switch.TCheckbutton"

        self.hotkey_start_var = tk.StringVar(value="F6")
        self.hotkey_pick_var = tk.StringVar(value="F8")
        self.hold_to_click_var = tk.BooleanVar(value=False)
        self.background_click_var = tk.BooleanVar(value=False)
        self.hk_hint_var = tk.StringVar()

        self.hotkey_start_var.trace_add("write", self.update_hk_labels)
        self.hotkey_pick_var.trace_add("write", self.update_hk_labels)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_container = ttk.Frame(self, padding=(ui(12), ui(12)))
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.rowconfigure(1, weight=1)

        self.create_header()
        self.create_tabs()
        self.create_controls()

        self.setup_hotkey_listener()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.load_config()
        self.update_hk_labels()
        self.toggle_timing_mode()
        self.toggle_repeat_entry()
        self.toggle_pos_inputs()
        self.update_human_settings()
        self.status_updater()

        self.after_idle(self.set_initial_geometry)

    def init_theme(self):
        self._theme_provider = None
        try:
            import sv_ttk
            self.sv_ttk = sv_ttk
            self._theme_provider = "sv_ttk"
        except Exception:
            base_dir = os.path.dirname(__file__)
            project_dir = os.path.abspath(os.path.join(base_dir, os.pardir))
            theme_dirs = [
                os.path.join(base_dir, "themes", "sun-valley"),
                os.path.join(project_dir, "themes", "sun-valley"),
            ]
            for theme_dir in theme_dirs:
                candidates = [
                    os.path.join(theme_dir, "sun-valley.tcl"),
                    os.path.join(theme_dir, "sv.tcl"),
                ]
                for candidate in candidates:
                    if os.path.exists(candidate):
                        try:
                            self.tk.call("source", candidate)
                            self._theme_provider = "tcl"
                            break
                        except tk.TclError:
                            pass
                if self._theme_provider == "tcl":
                    break
        if self._theme_provider is None:
            print("Sun Valley theme not found; using default ttk theme.")

    def init_styles(self):
        self.style = ttk.Style(self)
        self.style.configure("Info.TLabel", font=FONT_SMALL)

    def apply_theme(self, theme_name):
        mode = "light" if str(theme_name).lower().startswith("l") else "dark"
        self.theme_mode = mode
        if self._theme_provider == "sv_ttk":
            try:
                self.sv_ttk.set_theme(mode)
            except Exception:
                pass
        elif self._theme_provider == "tcl":
            try:
                self.tk.call("ttk::style", "theme", "use", f"sun-valley-{mode}")
                self.tk.call("event", "generate", ".", "<<ThemeChanged>>")
            except tk.TclError:
                pass
        self.init_styles()
        self.refresh_info_icons()
        self.refresh_logo()

    def set_initial_geometry(self):
        self.update_tab_geometry()

    def update_tab_geometry(self, _event=None):
        if not hasattr(self, "main_container"):
            return
        if str(self.state()) == "zoomed":
            return
        self.update_idletasks()
        if hasattr(self, "tabs"):
            current_tab = self.tabs.select()
            if current_tab:
                tab_frame = self.nametowidget(current_tab)
                tab_req_height = tab_frame.winfo_reqheight()
                tab_req_width = tab_frame.winfo_reqwidth()
                if tab_req_height > 1:
                    self.tabs.configure(height=tab_req_height)
                if tab_req_width > 1:
                    self.tabs.configure(width=tab_req_width)
        self.update_idletasks()
        req_width = self.main_container.winfo_reqwidth()
        req_height = self.main_container.winfo_reqheight()
        min_width = max(req_width, ui(MIN_WINDOW_WIDTH))
        min_height = req_height
        self.minsize(min_width, min_height)
        target_width = max(self.winfo_width(), min_width)
        target_height = max(req_height, min_height)
        if self.winfo_height() != target_height or self.winfo_width() < min_width:
            self.geometry(f"{target_width}x{target_height}")

    def create_info_icon_image(self, size, fg, bg, border):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        pad = 1
        draw.ellipse((pad, pad, size - pad - 1, size - pad - 1), fill=bg, outline=border)
        center = size // 2
        draw.ellipse((center - 1, pad + 2, center + 1, pad + 4), fill=fg)
        draw.line((center, pad + 6, center, size - pad - 3), fill=fg, width=2)
        return ImageTk.PhotoImage(img)

    def invert_image_rgba(self, image):
        rgb = image.convert("RGB")
        inv_rgb = ImageOps.invert(rgb)
        alpha = image.getchannel("A")
        return Image.merge("RGBA", (*inv_rgb.split(), alpha))

    def build_logo_variants(self, logo_src):
        logo_size = (ui(36), ui(36))
        mark_size = (ui(84), ui(84))
        variants = {}
        for mode, src in (("light", logo_src), ("dark", self.invert_image_rgba(logo_src))):
            logo_img = ImageTk.PhotoImage(src.resize(logo_size))
            mark = src.copy()
            alpha = mark.getchannel("A").point(lambda p: int(p * 0.12))
            mark.putalpha(alpha)
            mark_img = ImageTk.PhotoImage(mark.resize(mark_size))
            variants[mode] = (logo_img, mark_img)
        return variants

    def refresh_logo(self):
        if not hasattr(self, "logo_variants"):
            return
        variant = self.logo_variants.get(self.theme_mode)
        if not variant:
            return
        logo_img, mark_img = variant
        if hasattr(self, "logo_label"):
            self.logo_label.configure(image=logo_img)
            self.logo_label.image = logo_img
        if hasattr(self, "logo_mark"):
            self.logo_mark.configure(image=mark_img)
            self.logo_mark.image = mark_img

    def ensure_info_icons(self):
        if not self.info_icon_images:
            icon_size = ui(14)
            self.info_icon_images = {
                "light": self.create_info_icon_image(
                    icon_size, fg="#2f60d8", bg="#e9effb", border="#2f60d8"
                ),
                "dark": self.create_info_icon_image(
                    icon_size, fg="#f2f2f2", bg="#3a3a3a", border="#8fa8ff"
                ),
            }

    def refresh_info_icons(self):
        if not self.info_icon_labels:
            return
        self.ensure_info_icons()
        icon = self.info_icon_images.get(self.theme_mode)
        if not icon:
            return
        for label in self.info_icon_labels:
            label.configure(image=icon)
            label.image = icon

    def add_info_icon(self, parent, text):
        self.ensure_info_icons()
        icon = self.info_icon_images.get(self.theme_mode)
        label = ttk.Label(parent, image=icon, style="Info.TLabel", cursor="question_arrow", padding=(ui(2), 0))
        label.image = icon
        ToolTip(label, text)
        self.info_icon_labels.append(label)
        return label

    def make_row(self, parent, row, pady=None):
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=ui(4) if pady is None else pady)
        frame.columnconfigure(0, weight=1)
        return frame

    def add_labeled_entry(self, parent, row, label_text, text_var, width=10, help_text=None):
        frame = self.make_row(parent, row)
        ttk.Label(frame, text=label_text, font=FONT_BODY).grid(row=0, column=0, sticky="w")
        entry_column = 1
        if help_text:
            icon = self.add_info_icon(frame, help_text)
            icon.grid(row=0, column=1, sticky="e", padx=(ui(6), 0))
            entry_column = 2
        entry = ttk.Entry(frame, textvariable=text_var, width=width)
        entry.grid(row=0, column=entry_column, sticky="e")
        return entry

    def add_labeled_combo(self, parent, row, label_text, text_var, values, width=14, help_text=None):
        frame = self.make_row(parent, row)
        ttk.Label(frame, text=label_text, font=FONT_BODY).grid(row=0, column=0, sticky="w")
        combo_column = 1
        if help_text:
            icon = self.add_info_icon(frame, help_text)
            icon.grid(row=0, column=1, sticky="e", padx=(ui(6), 0))
            combo_column = 2
        combo = ttk.Combobox(frame, textvariable=text_var, values=values, state="readonly", width=width)
        combo.grid(row=0, column=combo_column, sticky="e")
        return combo

    def set_row_visibility(self, frame, visible):
        if not frame:
            return
        if visible:
            frame.grid()
        else:
            frame.grid_remove()

    def create_header(self):
        self.header_frame = ttk.Frame(self.main_container)
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, ui(10)))
        self.header_frame.columnconfigure(1, weight=1)

        try:
            logo_src = Image.open(resource_path("app_icon.png")).convert("RGBA")
            self.logo_variants = self.build_logo_variants(logo_src)
            self.logo_img, self.logo_mark_img = self.logo_variants.get(self.theme_mode, (None, None))
            self.logo_label = ttk.Label(self.header_frame, image=self.logo_img)
            self.logo_label.grid(row=0, column=0, rowspan=2, padx=ui(8), pady=ui(6))

            self.logo_mark = ttk.Label(self.header_frame, image=self.logo_mark_img)
            self.logo_mark.place(relx=1.0, x=-ui(6), y=ui(6), anchor="ne")
            self.logo_mark.lower()
        except Exception as e:
            print(f"Logo not found: {e}")

        ttk.Label(
            self.header_frame,
            text="HumanAutoClicker",
            font=FONT_HEADER,
        ).grid(row=0, column=1, sticky="w", padx=(0, ui(8)), pady=(ui(6), 0))

        ttk.Label(
            self.header_frame,
            text="Lightweight, human-like clicks in one view",
            font=FONT_SMALL,
        ).grid(row=1, column=1, sticky="w", padx=(0, ui(8)), pady=(0, ui(6)))

        ttk.Label(
            self.header_frame,
            textvariable=self.hk_hint_var,
            font=FONT_SMALL,
            padding=(ui(8), ui(4)),
        ).grid(row=0, column=2, rowspan=2, sticky="e", padx=ui(8), pady=ui(6))

    def create_section(self, parent, title, row):
        section = ttk.LabelFrame(parent, text=title, padding=(ui(10), ui(6)))
        section.grid(row=row, column=0, sticky="ew", pady=ui(6))
        section.columnconfigure(0, weight=1)
        return section
    def create_tabs(self):
        self.tabs = ttk.Notebook(self.main_container)
        self.tabs.grid(row=1, column=0, sticky="nsew", pady=ui(4))
        self.tabs.bind("<<NotebookTabChanged>>", self.update_tab_geometry)

        self.tab_frames = []
        for name in ("Click", "Position", "Behavior", "Human"):
            frame = ttk.Frame(self.tabs, padding=(ui(6), ui(6)))
            frame.columnconfigure(0, weight=1)
            self.tabs.add(frame, text=name)
            self.tab_frames.append(frame)

        click_tab, position_tab, behavior_tab, human_tab = self.tab_frames

        timing_section = self.create_section(click_tab, "Timing", 0)
        self.interval_var = tk.StringVar(value=str(DEFAULT_INTERVAL_MS))
        self.interval_entry = self.add_labeled_entry(timing_section, 0, "Interval (ms)", self.interval_var)
        self.random_interval_var = tk.StringVar(value=str(DEFAULT_RANDOM_INTERVAL_MS))
        self.random_interval_entry = self.add_labeled_entry(
            timing_section,
            1,
            "Randomness (+/- ms)",
            self.random_interval_var,
            help_text="Adds a random amount (0 to value) to each interval.",
        )
        self.timing_model_var = tk.StringVar(value="Exponential")
        self.timing_model_combo = self.add_labeled_combo(
            timing_section,
            2,
            "Timing Model",
            self.timing_model_var,
            ["Uniform", "Exponential"],
            help_text="Uniform uses the base interval. Exponential clusters clicks around the mean.",
        )
        self.timing_model_combo.bind("<<ComboboxSelected>>", self.toggle_timing_mode)
        self.exp_mean_interval_var = tk.StringVar(value=str(DEFAULT_EXP_MEAN_INTERVAL_MS))
        self.exp_mean_interval_entry = self.add_labeled_entry(
            timing_section,
            3,
            "Mean Interval (ms)",
            self.exp_mean_interval_var,
            help_text="Mean interval used by the exponential model.",
        )

        click_type_section = self.create_section(click_tab, "Click Type", 1)
        self.button_var = tk.StringVar(value="Left")
        self.button_combo = self.add_labeled_combo(
            click_type_section,
            0,
            "Mouse Button",
            self.button_var,
            ["Left", "Right"],
        )
        self.click_type_var = tk.StringVar(value="Single")
        self.click_type_combo = self.add_labeled_combo(
            click_type_section,
            1,
            "Click Type",
            self.click_type_var,
            ["Single", "Double"],
        )

        location_section = self.create_section(position_tab, "Location", 0)
        self.current_pos_var = tk.BooleanVar(value=False)
        self.pos_switch = ttk.Checkbutton(
            location_section,
            text="At Cursor Location",
            variable=self.current_pos_var,
            command=self.toggle_pos_inputs,
            style=self.switch_style,
        )
        self.pos_switch.grid(row=0, column=0, sticky="w", pady=ui(4))

        pos_input_frame = ttk.Frame(location_section)
        pos_input_frame.grid(row=1, column=0, sticky="ew", pady=ui(4))
        pos_input_frame.columnconfigure(0, weight=1)

        self.pick_pos_btn = ttk.Button(
            pos_input_frame,
            text="Pick (F8)",
            command=self.pick_location_mode,
        )
        self.pick_pos_btn.grid(row=0, column=0, sticky="w")

        ttk.Label(pos_input_frame, text="X", font=FONT_BODY).grid(row=0, column=1, sticky="e", padx=(ui(6), ui(2)))
        self.pos_x_var = tk.StringVar(value="500")
        self.pos_x_entry = ttk.Entry(pos_input_frame, width=6, textvariable=self.pos_x_var)
        self.pos_x_entry.grid(row=0, column=2, sticky="e")

        ttk.Label(pos_input_frame, text="Y", font=FONT_BODY).grid(row=0, column=3, sticky="e", padx=(ui(6), ui(2)))
        self.pos_y_var = tk.StringVar(value="500")
        self.pos_y_entry = ttk.Entry(pos_input_frame, width=6, textvariable=self.pos_y_var)
        self.pos_y_entry.grid(row=0, column=4, sticky="e")

        spread_section = self.create_section(position_tab, "Spread", 1)
        spread_frame = self.make_row(spread_section, 0)
        ttk.Label(spread_frame, text="Spread (+/- px)", font=FONT_BODY).grid(row=0, column=0, sticky="w")
        ttk.Label(spread_frame, text="X", font=FONT_BODY).grid(row=0, column=1, sticky="e", padx=(ui(6), ui(2)))
        self.offset_x_var = tk.StringVar(value="15")
        self.offset_x_entry = ttk.Entry(spread_frame, width=6, textvariable=self.offset_x_var)
        self.offset_x_entry.grid(row=0, column=2, sticky="e")
        ttk.Label(spread_frame, text="Y", font=FONT_BODY).grid(row=0, column=3, sticky="e", padx=(ui(6), ui(2)))
        self.offset_y_var = tk.StringVar(value="15")
        self.offset_y_entry = ttk.Entry(spread_frame, width=6, textvariable=self.offset_y_var)
        self.offset_y_entry.grid(row=0, column=4, sticky="e")
        spread_help = self.add_info_icon(
            spread_frame,
            "Random offset around the target position each click.",
        )
        spread_help.grid(row=0, column=5, sticky="e", padx=(ui(6), 0))

        repeat_section = self.create_section(behavior_tab, "Repeat", 0)
        rep_frame = self.make_row(repeat_section, 0)
        ttk.Label(rep_frame, text="Repeat limit", font=FONT_BODY).grid(row=0, column=0, sticky="w")
        self.repeat_mode_var = tk.StringVar(value="infinite")
        self.repeat_limit_var = tk.StringVar(value="100")
        self.repeat_switch = ttk.Checkbutton(
            rep_frame,
            text="Infinite",
            command=self.toggle_repeat_entry,
            onvalue="infinite",
            offvalue="limit",
            variable=self.repeat_mode_var,
            style=self.switch_style,
        )
        self.repeat_switch.grid(row=0, column=1, sticky="e")
        rep_help = self.add_info_icon(
            rep_frame,
            "Infinite keeps clicking until stopped. Disable to set a count.",
        )
        rep_help.grid(row=0, column=2, sticky="e", padx=(ui(6), 0))

        self.repeat_entry = ttk.Entry(repeat_section, textvariable=self.repeat_limit_var, width=10)
        self.repeat_entry.grid(row=1, column=0, sticky="ew", pady=ui(4))

        hotkeys_section = self.create_section(behavior_tab, "Hotkeys", 1)
        hk_frame = self.make_row(hotkeys_section, 0, pady=ui(2))
        ttk.Label(hk_frame, text="Start / Stop", font=FONT_BODY).grid(row=0, column=0, sticky="w")
        self.start_hk_btn = ttk.Button(
            hk_frame,
            text=self.hotkey_start_var.get(),
            command=lambda: self.start_recording("start"),
        )
        self.start_hk_btn.grid(row=0, column=1, sticky="e")

        hk_frame2 = self.make_row(hotkeys_section, 1, pady=ui(2))
        ttk.Label(hk_frame2, text="Pick Location", font=FONT_BODY).grid(row=0, column=0, sticky="w")
        self.pick_hk_btn = ttk.Button(
            hk_frame2,
            text=self.hotkey_pick_var.get(),
            command=lambda: self.start_recording("pick"),
        )
        self.pick_hk_btn.grid(row=0, column=1, sticky="e")

        background_section = self.create_section(behavior_tab, "Background Clicking", 2)
        bg_row = ttk.Frame(background_section)
        bg_row.grid(row=0, column=0, sticky="ew", pady=ui(2))
        bg_row.columnconfigure(0, weight=1)
        self.background_click_switch = ttk.Checkbutton(
            bg_row,
            text="Enable Background Clicks",
            variable=self.background_click_var,
            style=self.switch_style,
        )
        self.background_click_switch.grid(row=0, column=0, sticky="w")
        bg_help = self.add_info_icon(
            bg_row,
            "Captures the window under the target position when you press Start; the cursor won't move.",
        )
        bg_help.grid(row=0, column=1, sticky="e", padx=(ui(6), 0))

        app_section = self.create_section(behavior_tab, "App", 3)
        hold_row = ttk.Frame(app_section)
        hold_row.grid(row=0, column=0, sticky="ew", pady=ui(2))
        hold_row.columnconfigure(0, weight=1)
        self.hold_switch = ttk.Checkbutton(
            hold_row,
            text="Hold to Click Mode",
            variable=self.hold_to_click_var,
            style=self.switch_style,
        )
        self.hold_switch.grid(row=0, column=0, sticky="w")
        hold_help = self.add_info_icon(
            hold_row,
            "Clicks only while the start hotkey is held down.",
        )
        hold_help.grid(row=0, column=1, sticky="e", padx=(ui(6), 0))

        self.always_on_top_var = tk.BooleanVar(value=True)
        self.always_on_top_switch = ttk.Checkbutton(
            app_section,
            text="Always on Top",
            variable=self.always_on_top_var,
            command=self.toggle_always_on_top,
            style=self.switch_style,
        )
        self.always_on_top_switch.grid(row=1, column=0, sticky="w", pady=ui(2))

        self.theme_var = tk.StringVar(value="Dark")
        self.theme_switch = ttk.Checkbutton(
            app_section,
            text="Light Mode",
            onvalue="Light",
            offvalue="Dark",
            variable=self.theme_var,
            command=self.toggle_theme,
            style=self.switch_style,
        )
        self.theme_switch.grid(row=2, column=0, sticky="w", pady=ui(2))

        human_section = self.create_section(human_tab, "Humanized Behavior", 0)
        human_row = ttk.Frame(human_section)
        human_row.grid(row=0, column=0, sticky="ew", pady=ui(2))
        human_row.columnconfigure(0, weight=1)
        self.human_like_var = tk.BooleanVar(value=True)
        self.human_like_switch = ttk.Checkbutton(
            human_row,
            text="Enable Humanized Behavior",
            variable=self.human_like_var,
            command=self.update_human_settings,
            style=self.switch_style,
        )
        self.human_like_switch.grid(row=0, column=0, sticky="w")
        human_help = self.add_info_icon(
            human_row,
            "Adds variable hold time, drift, and optional pauses/cooldown.",
        )
        human_help.grid(row=0, column=1, sticky="e", padx=(ui(6), 0))

        hold_section = self.create_section(human_tab, "Hold Time", 1)
        hold_row = ttk.Frame(hold_section)
        hold_row.grid(row=0, column=0, sticky="ew", pady=ui(2))
        hold_row.columnconfigure(0, weight=1)
        self.hold_time_enabled_var = tk.BooleanVar(value=DEFAULT_HOLD_TIME_ENABLED)
        self.hold_time_switch = ttk.Checkbutton(
            hold_row,
            text="Enabled",
            variable=self.hold_time_enabled_var,
            command=self.update_human_settings,
            style=self.switch_style,
        )
        self.hold_time_switch.grid(row=0, column=0, sticky="w")
        hold_help = self.add_info_icon(
            hold_row,
            "Mouse down duration per click (Gaussian).",
        )
        hold_help.grid(row=0, column=1, sticky="e", padx=(ui(6), 0))

        self.hold_time_mean_var = tk.StringVar(value=str(DEFAULT_HOLD_TIME_MEAN_MS))
        self.hold_time_mean_entry = self.add_labeled_entry(hold_section, 1, "Mean (ms)", self.hold_time_mean_var, width=8)
        self.hold_time_mean_row = self.hold_time_mean_entry.master

        self.hold_time_std_var = tk.StringVar(value=str(DEFAULT_HOLD_TIME_STD_MS))
        self.hold_time_std_entry = self.add_labeled_entry(hold_section, 2, "Std (ms)", self.hold_time_std_var, width=8)
        self.hold_time_std_row = self.hold_time_std_entry.master

        drift_section = self.create_section(human_tab, "Cursor Drift", 2)
        drift_row = ttk.Frame(drift_section)
        drift_row.grid(row=0, column=0, sticky="ew", pady=ui(2))
        drift_row.columnconfigure(0, weight=1)
        self.drift_enabled_var = tk.BooleanVar(value=DEFAULT_DRIFT_ENABLED)
        self.drift_switch = ttk.Checkbutton(
            drift_row,
            text="Enabled",
            variable=self.drift_enabled_var,
            command=self.update_human_settings,
            style=self.switch_style,
        )
        self.drift_switch.grid(row=0, column=0, sticky="w")
        drift_help = self.add_info_icon(
            drift_row,
            "Slow drift within the spread range when spread is enabled.",
        )
        drift_help.grid(row=0, column=1, sticky="e", padx=(ui(6), 0))

        drift_step_frame = self.make_row(drift_section, 1)
        self.drift_step_row = drift_step_frame
        ttk.Label(drift_step_frame, text="Step (min/max px)", font=FONT_BODY).grid(row=0, column=0, sticky="w")
        ttk.Label(drift_step_frame, text="Min", font=FONT_BODY).grid(row=0, column=1, sticky="e", padx=(ui(6), ui(2)))
        self.drift_step_min_var = tk.StringVar(value=str(DEFAULT_DRIFT_STEP_MIN))
        self.drift_step_min_entry = ttk.Entry(drift_step_frame, width=5, textvariable=self.drift_step_min_var)
        self.drift_step_min_entry.grid(row=0, column=2, sticky="e")
        ttk.Label(drift_step_frame, text="Max", font=FONT_BODY).grid(row=0, column=3, sticky="e", padx=(ui(6), ui(2)))
        self.drift_step_max_var = tk.StringVar(value=str(DEFAULT_DRIFT_STEP_MAX))
        self.drift_step_max_entry = ttk.Entry(drift_step_frame, width=5, textvariable=self.drift_step_max_var)
        self.drift_step_max_entry.grid(row=0, column=4, sticky="e")

        drift_reset_frame = self.make_row(drift_section, 2)
        self.drift_reset_row = drift_reset_frame
        ttk.Label(drift_reset_frame, text="Reset (min/max px)", font=FONT_BODY).grid(row=0, column=0, sticky="w")
        ttk.Label(drift_reset_frame, text="Min", font=FONT_BODY).grid(row=0, column=1, sticky="e", padx=(ui(6), ui(2)))
        self.drift_reset_min_var = tk.StringVar(value=str(DEFAULT_DRIFT_RESET_MIN))
        self.drift_reset_min_entry = ttk.Entry(drift_reset_frame, width=5, textvariable=self.drift_reset_min_var)
        self.drift_reset_min_entry.grid(row=0, column=2, sticky="e")
        ttk.Label(drift_reset_frame, text="Max", font=FONT_BODY).grid(row=0, column=3, sticky="e", padx=(ui(6), ui(2)))
        self.drift_reset_max_var = tk.StringVar(value=str(DEFAULT_DRIFT_RESET_MAX))
        self.drift_reset_max_entry = ttk.Entry(drift_reset_frame, width=5, textvariable=self.drift_reset_max_var)
        self.drift_reset_max_entry.grid(row=0, column=4, sticky="e")

        thinking_section = self.create_section(human_tab, "Thinking Pause", 3)
        thinking_row = ttk.Frame(thinking_section)
        thinking_row.grid(row=0, column=0, sticky="ew", pady=ui(2))
        thinking_row.columnconfigure(0, weight=1)
        self.thinking_pause_enabled_var = tk.BooleanVar(value=DEFAULT_THINKING_PAUSE_ENABLED)
        self.thinking_pause_switch = ttk.Checkbutton(
            thinking_row,
            text="Enabled",
            variable=self.thinking_pause_enabled_var,
            command=self.update_human_settings,
            style=self.switch_style,
        )
        self.thinking_pause_switch.grid(row=0, column=0, sticky="w")
        thinking_help = self.add_info_icon(
            thinking_row,
            "Occasional pauses after a random number of clicks.",
        )
        thinking_help.grid(row=0, column=1, sticky="e", padx=(ui(6), 0))

        self.thinking_pause_mean_var = tk.StringVar(value=str(DEFAULT_THINKING_PAUSE_MEAN_MS))
        self.thinking_pause_mean_entry = self.add_labeled_entry(thinking_section, 1, "Mean (ms)", self.thinking_pause_mean_var, width=8)
        self.thinking_pause_mean_row = self.thinking_pause_mean_entry.master

        self.thinking_pause_std_var = tk.StringVar(value=str(DEFAULT_THINKING_PAUSE_STD_MS))
        self.thinking_pause_std_entry = self.add_labeled_entry(thinking_section, 2, "Std (ms)", self.thinking_pause_std_var, width=8)
        self.thinking_pause_std_row = self.thinking_pause_std_entry.master

        clicks_frame = self.make_row(thinking_section, 3)
        self.thinking_pause_clicks_row = clicks_frame
        ttk.Label(clicks_frame, text="Every (min/max clicks)", font=FONT_BODY).grid(row=0, column=0, sticky="w")
        ttk.Label(clicks_frame, text="Min", font=FONT_BODY).grid(row=0, column=1, sticky="e", padx=(ui(6), ui(2)))
        self.thinking_pause_min_clicks_var = tk.StringVar(value=str(DEFAULT_THINKING_PAUSE_MIN_CLICKS))
        self.thinking_pause_min_clicks_entry = ttk.Entry(clicks_frame, width=5, textvariable=self.thinking_pause_min_clicks_var)
        self.thinking_pause_min_clicks_entry.grid(row=0, column=2, sticky="e")
        ttk.Label(clicks_frame, text="Max", font=FONT_BODY).grid(row=0, column=3, sticky="e", padx=(ui(6), ui(2)))
        self.thinking_pause_max_clicks_var = tk.StringVar(value=str(DEFAULT_THINKING_PAUSE_MAX_CLICKS))
        self.thinking_pause_max_clicks_entry = ttk.Entry(clicks_frame, width=5, textvariable=self.thinking_pause_max_clicks_var)
        self.thinking_pause_max_clicks_entry.grid(row=0, column=4, sticky="e")

        fatigue_section = self.create_section(human_tab, "Fatigue Modeling", 4)
        fatigue_row = ttk.Frame(fatigue_section)
        fatigue_row.grid(row=0, column=0, sticky="ew", pady=ui(2))
        fatigue_row.columnconfigure(0, weight=1)
        self.fatigue_enabled_var = tk.BooleanVar(value=DEFAULT_FATIGUE_ENABLED)
        self.fatigue_switch = ttk.Checkbutton(
            fatigue_row,
            text="Enabled",
            variable=self.fatigue_enabled_var,
            command=self.update_human_settings,
            style=self.switch_style,
        )
        self.fatigue_switch.grid(row=0, column=0, sticky="w")
        fatigue_help = self.add_info_icon(
            fatigue_row,
            "If clicking too fast for too long, enforces a slower cooldown.",
        )
        fatigue_help.grid(row=0, column=1, sticky="e", padx=(ui(6), 0))

        self.fatigue_threshold_interval_var = tk.StringVar(value=str(DEFAULT_FATIGUE_THRESHOLD_INTERVAL_MS))
        self.fatigue_threshold_interval_entry = self.add_labeled_entry(
            fatigue_section,
            1,
            "Jitter threshold (ms)",
            self.fatigue_threshold_interval_var,
            width=8,
        )
        self.fatigue_threshold_row = self.fatigue_threshold_interval_entry.master

        self.fatigue_duration_var = tk.StringVar(value=str(DEFAULT_FATIGUE_DURATION_MS))
        self.fatigue_duration_entry = self.add_labeled_entry(
            fatigue_section,
            2,
            "Jitter duration (ms)",
            self.fatigue_duration_var,
            width=8,
        )
        self.fatigue_duration_row = self.fatigue_duration_entry.master

        self.fatigue_cooldown_duration_var = tk.StringVar(value=str(DEFAULT_FATIGUE_COOLDOWN_DURATION_MS))
        self.fatigue_cooldown_duration_entry = self.add_labeled_entry(
            fatigue_section,
            3,
            "Cooldown (ms)",
            self.fatigue_cooldown_duration_var,
            width=8,
        )
        self.fatigue_cooldown_row = self.fatigue_cooldown_duration_entry.master

        self.fatigue_cooldown_min_interval_var = tk.StringVar(value=str(DEFAULT_FATIGUE_COOLDOWN_MIN_INTERVAL_MS))
        self.fatigue_cooldown_min_interval_entry = self.add_labeled_entry(
            fatigue_section,
            4,
            "Cooldown min interval (ms)",
            self.fatigue_cooldown_min_interval_var,
            width=8,
        )
        self.fatigue_cooldown_min_row = self.fatigue_cooldown_min_interval_entry.master
    def create_controls(self):
        self.control_frame = ttk.Frame(self.main_container)
        self.control_frame.grid(row=2, column=0, sticky="ew", pady=ui(8))
        self.control_frame.columnconfigure(0, weight=1)
        self.control_frame.columnconfigure(1, weight=1)

        self.start_btn = ttk.Button(
            self.control_frame,
            text="START (F6)",
            command=self.start_clicking,
            style=self.accent_button_style,
        )
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, ui(6)))

        self.stop_btn = ttk.Button(
            self.control_frame,
            text="STOP",
            command=self.stop_clicking_ui,
        )
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=(ui(6), 0))
        self.stop_btn.configure(state="disabled")

        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(
            self.main_container,
            textvariable=self.status_var,
            font=FONT_SMALL,
            anchor="w",
            padding=(ui(8), ui(4)),
        )
        self.status_bar.grid(row=3, column=0, sticky="ew")

    def toggle_always_on_top(self):
        self.attributes("-topmost", coerce_bool(self.always_on_top_var.get()))

    def toggle_theme(self):
        self.apply_theme(self.theme_var.get())

    def toggle_pos_inputs(self):
        state = "disabled" if coerce_bool(self.current_pos_var.get()) else "normal"
        self.pick_pos_btn.configure(state=state)
        self.pos_x_entry.configure(state=state)
        self.pos_y_entry.configure(state=state)

    def toggle_timing_mode(self, _event=None):
        is_exp = self.timing_model_var.get() == "Exponential"
        self.interval_entry.configure(state="disabled" if is_exp else "normal")
        self.random_interval_entry.configure(state="disabled" if is_exp else "normal")
        self.exp_mean_interval_entry.configure(state="normal" if is_exp else "disabled")

    def toggle_repeat_entry(self):
        if self.repeat_mode_var.get() == "infinite":
            self.repeat_entry.configure(state="disabled")
        else:
            self.repeat_entry.configure(state="normal")

    def parse_int(self, value, min_value=None, allow_zero=True):
        number = int(value)
        if min_value is not None and number < min_value:
            raise ValueError
        if not allow_zero and number == 0:
            raise ValueError
        return number

    def update_human_settings(self):
        human_enabled = coerce_bool(self.human_like_var.get())
        hold_enabled = human_enabled and coerce_bool(self.hold_time_enabled_var.get())
        hold_state = "normal" if hold_enabled else "disabled"
        self.hold_time_mean_entry.configure(state=hold_state)
        self.hold_time_std_entry.configure(state=hold_state)
        self.set_row_visibility(self.hold_time_mean_row, hold_enabled)
        self.set_row_visibility(self.hold_time_std_row, hold_enabled)

        drift_enabled = human_enabled and coerce_bool(self.drift_enabled_var.get())
        drift_state = "normal" if drift_enabled else "disabled"
        self.drift_step_min_entry.configure(state=drift_state)
        self.drift_step_max_entry.configure(state=drift_state)
        self.drift_reset_min_entry.configure(state=drift_state)
        self.drift_reset_max_entry.configure(state=drift_state)
        self.set_row_visibility(self.drift_step_row, drift_enabled)
        self.set_row_visibility(self.drift_reset_row, drift_enabled)

        thinking_enabled = human_enabled and coerce_bool(self.thinking_pause_enabled_var.get())
        thinking_state = "normal" if thinking_enabled else "disabled"
        self.thinking_pause_mean_entry.configure(state=thinking_state)
        self.thinking_pause_std_entry.configure(state=thinking_state)
        self.thinking_pause_min_clicks_entry.configure(state=thinking_state)
        self.thinking_pause_max_clicks_entry.configure(state=thinking_state)
        self.set_row_visibility(self.thinking_pause_mean_row, thinking_enabled)
        self.set_row_visibility(self.thinking_pause_std_row, thinking_enabled)
        self.set_row_visibility(self.thinking_pause_clicks_row, thinking_enabled)

        fatigue_enabled = human_enabled and coerce_bool(self.fatigue_enabled_var.get())
        fatigue_state = "normal" if fatigue_enabled else "disabled"
        self.fatigue_threshold_interval_entry.configure(state=fatigue_state)
        self.fatigue_duration_entry.configure(state=fatigue_state)
        self.fatigue_cooldown_duration_entry.configure(state=fatigue_state)
        self.fatigue_cooldown_min_interval_entry.configure(state=fatigue_state)
        self.set_row_visibility(self.fatigue_threshold_row, fatigue_enabled)
        self.set_row_visibility(self.fatigue_duration_row, fatigue_enabled)
        self.set_row_visibility(self.fatigue_cooldown_row, fatigue_enabled)
        self.set_row_visibility(self.fatigue_cooldown_min_row, fatigue_enabled)

        self.after(0, self.update_tab_geometry)

    def update_hk_labels(self, *args):
        hk = self.hotkey_start_var.get()
        if hasattr(self, "start_btn"):
            self.start_btn.configure(text=f"START ({hk})")
        if hasattr(self, "start_hk_btn") and self.is_recording_hotkey != "start":
            self.start_hk_btn.configure(text=self.hotkey_start_var.get())
        if hasattr(self, "pick_hk_btn") and self.is_recording_hotkey != "pick":
            self.pick_hk_btn.configure(text=self.hotkey_pick_var.get())
        if hasattr(self, "hk_hint_var"):
            pick = self.hotkey_pick_var.get()
            self.hk_hint_var.set(f"Hotkeys: {hk} / {pick}")

    def start_recording(self, target):
        self.is_recording_hotkey = target
        if target == "start":
            self.start_hk_btn.configure(text="Recording...", style=self.accent_button_style)
        else:
            self.pick_hk_btn.configure(text="Recording...", style=self.accent_button_style)
        self.status_var.set(f"RECORDING: Press new key for {target}")

    def key_to_str(self, key):
        try:
            if hasattr(key, "char") and key.char:
                return key.char.upper()
            k_str = str(key).replace("Key.", "").upper()
            return k_str
        except:
            return str(key).upper()

    def pick_location_mode(self):
        hk = self.hotkey_pick_var.get()
        self.status_var.set(f"PICK MODE: Move mouse and press {hk}")
        self.update_idletasks()

    def setup_hotkey_listener(self):
        def on_press(key):
            try:
                k_str = self.key_to_str(key)

                if self.is_recording_hotkey:
                    if self.is_recording_hotkey == "start":
                        self.hotkey_start_var.set(k_str)
                        self.start_hk_btn.configure(style=self.default_button_style)
                    else:
                        self.hotkey_pick_var.set(k_str)
                        self.pick_hk_btn.configure(style=self.default_button_style)

                    self.is_recording_hotkey = None
                    self.update_hk_labels()
                    self.status_var.set(f"Bound to {k_str}")
                    return

                if k_str == self.hotkey_start_var.get():
                    if self.is_clicking():
                        if not coerce_bool(self.hold_to_click_var.get()):
                            self.after(0, self.stop_clicking_ui)
                    else:
                        self.after(0, self.start_clicking)

                elif k_str == self.hotkey_pick_var.get():
                    mouse_pos = self.mouse_controller.position
                    self.after(0, lambda: self.set_picked_location(mouse_pos))

            except Exception as e:
                print(f"Hotkey Error: {e}")

        def on_release(key):
            if coerce_bool(self.hold_to_click_var.get()):
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
            timing_mode = self.timing_model_var.get()
            if timing_mode == "Exponential":
                exp_mean_interval_ms = self.parse_int(self.exp_mean_interval_var.get(), min_value=1, allow_zero=False)
                interval_ms = DEFAULT_INTERVAL_MS
                rand_interval_ms = 0
            else:
                interval_ms = self.parse_int(self.interval_var.get(), min_value=1, allow_zero=False)
                rand_interval_ms = self.parse_int(self.random_interval_var.get(), min_value=0, allow_zero=True)
                exp_mean_interval_ms = DEFAULT_EXP_MEAN_INTERVAL_MS

            click_limit = 0
            if self.repeat_mode_var.get() == "limit":
                click_limit = self.parse_int(self.repeat_limit_var.get(), min_value=1, allow_zero=False)

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

            background_click_enabled = coerce_bool(self.background_click_var.get())
            background_click_handle = None
            if background_click_enabled:
                if target_pos is None:
                    mouse_controller = getattr(self, "mouse_controller", None) or Controller()
                    target_pos = mouse_controller.position
                target_x, target_y = target_pos
                background_click_handle = get_window_at_point(target_x, target_y) or get_foreground_window_handle()
                if not background_click_handle:
                    messagebox.showerror(
                        "Error",
                        "Unable to detect a target window. Bring the target app to the front and try again.",
                    )
                    return

            human_enabled = coerce_bool(self.human_like_var.get())
            hold_time_enabled = human_enabled and coerce_bool(self.hold_time_enabled_var.get())
            hold_time_mean_ms = DEFAULT_HOLD_TIME_MEAN_MS
            hold_time_std_ms = DEFAULT_HOLD_TIME_STD_MS
            if hold_time_enabled:
                hold_time_mean_ms = self.parse_int(self.hold_time_mean_var.get(), min_value=1, allow_zero=False)
                hold_time_std_ms = self.parse_int(self.hold_time_std_var.get(), min_value=0, allow_zero=True)

            drift_enabled = human_enabled and coerce_bool(self.drift_enabled_var.get())
            drift_step_min = DEFAULT_DRIFT_STEP_MIN
            drift_step_max = DEFAULT_DRIFT_STEP_MAX
            drift_reset_min = DEFAULT_DRIFT_RESET_MIN
            drift_reset_max = DEFAULT_DRIFT_RESET_MAX
            if drift_enabled:
                drift_step_min = self.parse_int(self.drift_step_min_var.get())
                drift_step_max = self.parse_int(self.drift_step_max_var.get())
                drift_reset_min = self.parse_int(self.drift_reset_min_var.get())
                drift_reset_max = self.parse_int(self.drift_reset_max_var.get())
                if drift_step_min > drift_step_max or drift_reset_min > drift_reset_max:
                    raise ValueError

            thinking_pause_enabled = human_enabled and coerce_bool(self.thinking_pause_enabled_var.get())
            thinking_pause_mean_ms = DEFAULT_THINKING_PAUSE_MEAN_MS
            thinking_pause_std_ms = DEFAULT_THINKING_PAUSE_STD_MS
            thinking_pause_min_clicks = DEFAULT_THINKING_PAUSE_MIN_CLICKS
            thinking_pause_max_clicks = DEFAULT_THINKING_PAUSE_MAX_CLICKS
            if thinking_pause_enabled:
                thinking_pause_mean_ms = self.parse_int(self.thinking_pause_mean_var.get(), min_value=1, allow_zero=False)
                thinking_pause_std_ms = self.parse_int(self.thinking_pause_std_var.get(), min_value=0, allow_zero=True)
                thinking_pause_min_clicks = self.parse_int(self.thinking_pause_min_clicks_var.get(), min_value=1, allow_zero=False)
                thinking_pause_max_clicks = self.parse_int(self.thinking_pause_max_clicks_var.get(), min_value=1, allow_zero=False)
                if thinking_pause_max_clicks < thinking_pause_min_clicks:
                    raise ValueError

            fatigue_enabled = human_enabled and coerce_bool(self.fatigue_enabled_var.get())
            fatigue_threshold_interval_ms = DEFAULT_FATIGUE_THRESHOLD_INTERVAL_MS
            fatigue_duration_ms = DEFAULT_FATIGUE_DURATION_MS
            fatigue_cooldown_duration_ms = DEFAULT_FATIGUE_COOLDOWN_DURATION_MS
            fatigue_cooldown_min_interval_ms = DEFAULT_FATIGUE_COOLDOWN_MIN_INTERVAL_MS
            if fatigue_enabled:
                fatigue_threshold_interval_ms = self.parse_int(self.fatigue_threshold_interval_var.get(), min_value=1, allow_zero=False)
                fatigue_duration_ms = self.parse_int(self.fatigue_duration_var.get(), min_value=1, allow_zero=False)
                fatigue_cooldown_duration_ms = self.parse_int(self.fatigue_cooldown_duration_var.get(), min_value=1, allow_zero=False)
                fatigue_cooldown_min_interval_ms = self.parse_int(self.fatigue_cooldown_min_interval_var.get(), min_value=1, allow_zero=False)

            if self.click_thread and self.click_thread.is_alive():
                self.click_thread.exit()

            self.click_thread = AutoClicker(
                interval_ms=interval_ms,
                random_interval_ms=rand_interval_ms,
                click_type=self.click_type_var.get(),
                button=self.button_var.get(),
                interval_mode=timing_mode,
                exp_mean_interval_ms=exp_mean_interval_ms,
                target_pos=target_pos,
                random_pos_offset=rand_pos_offset,
                click_limit=click_limit,
                human_like=human_enabled,
                hold_time_enabled=hold_time_enabled,
                hold_time_mean_ms=hold_time_mean_ms,
                hold_time_std_ms=hold_time_std_ms,
                drift_enabled=drift_enabled,
                drift_step_min=drift_step_min,
                drift_step_max=drift_step_max,
                drift_reset_min=drift_reset_min,
                drift_reset_max=drift_reset_max,
                thinking_pause_enabled=thinking_pause_enabled,
                thinking_pause_mean_ms=thinking_pause_mean_ms,
                thinking_pause_std_ms=thinking_pause_std_ms,
                thinking_pause_min_clicks=thinking_pause_min_clicks,
                thinking_pause_max_clicks=thinking_pause_max_clicks,
                fatigue_enabled=fatigue_enabled,
                fatigue_threshold_interval_ms=fatigue_threshold_interval_ms,
                fatigue_duration_ms=fatigue_duration_ms,
                fatigue_cooldown_duration_ms=fatigue_cooldown_duration_ms,
                fatigue_cooldown_min_interval_ms=fatigue_cooldown_min_interval_ms,
                background_click_enabled=background_click_enabled,
                background_click_handle=background_click_handle,
                app=self
            )

            self.click_thread.start()
            self.click_thread.start_clicking()

            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            hk = self.hotkey_start_var.get()
            self.status_var.set(f"RUNNING... Press {hk} to Stop")

        except ValueError:
            messagebox.showerror("Error", "Invalid numeric input (use whole milliseconds).")

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
        self.after(STATUS_UPDATE_INTERVAL_MS, self.status_updater)

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

    def save_config(self):
        config = {
            "interval_ms": safe_int(self.interval_var.get(), DEFAULT_INTERVAL_MS),
            "random_interval_ms": safe_int(self.random_interval_var.get(), DEFAULT_RANDOM_INTERVAL_MS),
            "timing_model": self.timing_model_var.get(),
            "exp_mean_interval_ms": safe_int(self.exp_mean_interval_var.get(), DEFAULT_EXP_MEAN_INTERVAL_MS),
            "button": self.button_var.get(),
            "click_type": self.click_type_var.get(),
            "repeat_mode": self.repeat_mode_var.get(),
            "repeat_limit": safe_int(self.repeat_limit_var.get(), 100),
            "use_current_pos": self.current_pos_var.get(),
            "pos_x": self.pos_x_var.get(),
            "pos_y": self.pos_y_var.get(),
            "offset_x": safe_int(self.offset_x_var.get(), 0),
            "offset_y": safe_int(self.offset_y_var.get(), 0),
            "always_on_top": self.always_on_top_var.get(),
            "theme": self.theme_var.get(),
            "human_like": self.human_like_var.get(),
            "hold_time_enabled": self.hold_time_enabled_var.get(),
            "hold_time_mean_ms": safe_int(self.hold_time_mean_var.get(), DEFAULT_HOLD_TIME_MEAN_MS),
            "hold_time_std_ms": safe_int(self.hold_time_std_var.get(), DEFAULT_HOLD_TIME_STD_MS),
            "drift_enabled": self.drift_enabled_var.get(),
            "drift_step_min_px": safe_int(self.drift_step_min_var.get(), DEFAULT_DRIFT_STEP_MIN),
            "drift_step_max_px": safe_int(self.drift_step_max_var.get(), DEFAULT_DRIFT_STEP_MAX),
            "drift_reset_min_px": safe_int(self.drift_reset_min_var.get(), DEFAULT_DRIFT_RESET_MIN),
            "drift_reset_max_px": safe_int(self.drift_reset_max_var.get(), DEFAULT_DRIFT_RESET_MAX),
            "thinking_pause_enabled": self.thinking_pause_enabled_var.get(),
            "thinking_pause_mean_ms": safe_int(self.thinking_pause_mean_var.get(), DEFAULT_THINKING_PAUSE_MEAN_MS),
            "thinking_pause_std_ms": safe_int(self.thinking_pause_std_var.get(), DEFAULT_THINKING_PAUSE_STD_MS),
            "thinking_pause_min_clicks": safe_int(self.thinking_pause_min_clicks_var.get(), DEFAULT_THINKING_PAUSE_MIN_CLICKS),
            "thinking_pause_max_clicks": safe_int(self.thinking_pause_max_clicks_var.get(), DEFAULT_THINKING_PAUSE_MAX_CLICKS),
            "fatigue_enabled": self.fatigue_enabled_var.get(),
            "fatigue_threshold_interval_ms": safe_int(self.fatigue_threshold_interval_var.get(), DEFAULT_FATIGUE_THRESHOLD_INTERVAL_MS),
            "fatigue_duration_ms": safe_int(self.fatigue_duration_var.get(), DEFAULT_FATIGUE_DURATION_MS),
            "fatigue_cooldown_duration_ms": safe_int(self.fatigue_cooldown_duration_var.get(), DEFAULT_FATIGUE_COOLDOWN_DURATION_MS),
            "fatigue_cooldown_min_interval_ms": safe_int(self.fatigue_cooldown_min_interval_var.get(), DEFAULT_FATIGUE_COOLDOWN_MIN_INTERVAL_MS),
            "background_click_enabled": self.background_click_var.get(),
            "hotkey_start": self.hotkey_start_var.get(),
            "hotkey_pick": self.hotkey_pick_var.get(),
            "hold_to_click": self.hold_to_click_var.get()
        }
        write_config(config)

    def load_config(self):
        try:
            config = read_config()
            if not config:
                return

            interval_ms = config.get("interval_ms")
            if interval_ms is None:
                legacy_interval = config.get("interval")
                if legacy_interval is not None:
                    try:
                        interval_ms = float(legacy_interval) * MS_PER_SEC
                    except ValueError:
                        interval_ms = DEFAULT_INTERVAL_MS
            interval_ms = safe_int(interval_ms, DEFAULT_INTERVAL_MS)
            self.interval_var.set(str(interval_ms))

            random_interval_ms = config.get("random_interval_ms")
            if random_interval_ms is None:
                legacy_random = config.get("random_interval")
                if legacy_random is not None:
                    try:
                        random_interval_ms = float(legacy_random) * MS_PER_SEC
                    except ValueError:
                        random_interval_ms = DEFAULT_RANDOM_INTERVAL_MS
            random_interval_ms = safe_int(random_interval_ms, DEFAULT_RANDOM_INTERVAL_MS)
            self.random_interval_var.set(str(random_interval_ms))
            timing_model = config.get("timing_model", "Exponential")
            if timing_model not in ("Uniform", "Exponential"):
                timing_model = "Exponential"
            self.timing_model_var.set(timing_model)
            exp_mean_interval_ms = config.get("exp_mean_interval_ms")
            if exp_mean_interval_ms is None:
                legacy_lambda = config.get("lambda_rate")
                if legacy_lambda is not None:
                    try:
                        legacy_lambda = float(legacy_lambda)
                        if legacy_lambda > 0:
                            exp_mean_interval_ms = MS_PER_SEC / legacy_lambda
                    except ValueError:
                        exp_mean_interval_ms = DEFAULT_EXP_MEAN_INTERVAL_MS
            exp_mean_interval_ms = safe_int(exp_mean_interval_ms, DEFAULT_EXP_MEAN_INTERVAL_MS)
            self.exp_mean_interval_var.set(str(exp_mean_interval_ms))
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
            self.repeat_limit_var.set(str(safe_int(config.get("repeat_limit"), 100)))
            self.current_pos_var.set(coerce_bool(config.get("use_current_pos", False)))
            self.pos_x_var.set(config.get("pos_x", "500"))
            self.pos_y_var.set(config.get("pos_y", "500"))
            self.offset_x_var.set(str(safe_int(config.get("offset_x"), 15)))
            self.offset_y_var.set(str(safe_int(config.get("offset_y"), 15)))

            self.always_on_top_var.set(coerce_bool(config.get("always_on_top", True)))
            self.attributes("-topmost", self.always_on_top_var.get())

            loaded_theme = config.get("theme", "Dark")
            self.theme_var.set(loaded_theme)
            self.apply_theme(loaded_theme)

            self.human_like_var.set(coerce_bool(config.get("human_like", True)))
            self.hold_time_enabled_var.set(coerce_bool(config.get("hold_time_enabled", DEFAULT_HOLD_TIME_ENABLED)))
            self.hold_time_mean_var.set(str(safe_int(config.get("hold_time_mean_ms"), DEFAULT_HOLD_TIME_MEAN_MS)))
            self.hold_time_std_var.set(str(safe_int(config.get("hold_time_std_ms"), DEFAULT_HOLD_TIME_STD_MS)))

            self.drift_enabled_var.set(coerce_bool(config.get("drift_enabled", DEFAULT_DRIFT_ENABLED)))
            self.drift_step_min_var.set(str(safe_int(config.get("drift_step_min_px"), DEFAULT_DRIFT_STEP_MIN)))
            self.drift_step_max_var.set(str(safe_int(config.get("drift_step_max_px"), DEFAULT_DRIFT_STEP_MAX)))
            self.drift_reset_min_var.set(str(safe_int(config.get("drift_reset_min_px"), DEFAULT_DRIFT_RESET_MIN)))
            self.drift_reset_max_var.set(str(safe_int(config.get("drift_reset_max_px"), DEFAULT_DRIFT_RESET_MAX)))

            self.thinking_pause_enabled_var.set(coerce_bool(config.get("thinking_pause_enabled", DEFAULT_THINKING_PAUSE_ENABLED)))
            self.thinking_pause_mean_var.set(str(safe_int(config.get("thinking_pause_mean_ms"), DEFAULT_THINKING_PAUSE_MEAN_MS)))
            self.thinking_pause_std_var.set(str(safe_int(config.get("thinking_pause_std_ms"), DEFAULT_THINKING_PAUSE_STD_MS)))
            self.thinking_pause_min_clicks_var.set(str(safe_int(config.get("thinking_pause_min_clicks"), DEFAULT_THINKING_PAUSE_MIN_CLICKS)))
            self.thinking_pause_max_clicks_var.set(str(safe_int(config.get("thinking_pause_max_clicks"), DEFAULT_THINKING_PAUSE_MAX_CLICKS)))

            self.fatigue_enabled_var.set(coerce_bool(config.get("fatigue_enabled", DEFAULT_FATIGUE_ENABLED)))
            self.fatigue_threshold_interval_var.set(str(safe_int(config.get("fatigue_threshold_interval_ms"), DEFAULT_FATIGUE_THRESHOLD_INTERVAL_MS)))
            self.fatigue_duration_var.set(str(safe_int(config.get("fatigue_duration_ms"), DEFAULT_FATIGUE_DURATION_MS)))
            self.fatigue_cooldown_duration_var.set(str(safe_int(config.get("fatigue_cooldown_duration_ms"), DEFAULT_FATIGUE_COOLDOWN_DURATION_MS)))
            self.fatigue_cooldown_min_interval_var.set(str(safe_int(config.get("fatigue_cooldown_min_interval_ms"), DEFAULT_FATIGUE_COOLDOWN_MIN_INTERVAL_MS)))
            self.background_click_var.set(coerce_bool(config.get("background_click_enabled", False)))
            self.hotkey_start_var.set(config.get("hotkey_start", "F6"))
            self.hotkey_pick_var.set(config.get("hotkey_pick", "F8"))
            self.hold_to_click_var.set(coerce_bool(config.get("hold_to_click", False)))
            self.toggle_repeat_entry()
            self.toggle_pos_inputs()
            self.update_human_settings()

        except Exception as e:
            print(f"Failed to load config: {e}")
