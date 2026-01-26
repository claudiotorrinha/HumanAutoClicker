import time
import random
import threading
import math
import sys
from pynput.mouse import Button, Controller

MS_PER_SEC = 1000

DEFAULT_INTERVAL_MS = 100
DEFAULT_RANDOM_INTERVAL_MS = 0
DEFAULT_EXP_MEAN_INTERVAL_MS = 80
DEFAULT_HOLD_TIME_ENABLED = False
DEFAULT_HOLD_TIME_MEAN_MS = 133
DEFAULT_HOLD_TIME_STD_MS = 83
DOUBLE_CLICK_GAP_MIN_MS = 5
DOUBLE_CLICK_GAP_MAX_MS = 15
DEFAULT_DRIFT_ENABLED = True
DEFAULT_DRIFT_STEP_MIN = -2
DEFAULT_DRIFT_STEP_MAX = 1
DEFAULT_DRIFT_RESET_MIN = -2
DEFAULT_DRIFT_RESET_MAX = 2
DEFAULT_THINKING_PAUSE_ENABLED = True
DEFAULT_THINKING_PAUSE_MEAN_MS = 1500
DEFAULT_THINKING_PAUSE_STD_MS = 800
DEFAULT_THINKING_PAUSE_MIN_CLICKS = 120
DEFAULT_THINKING_PAUSE_MAX_CLICKS = 150
DEFAULT_FATIGUE_ENABLED = True
DEFAULT_FATIGUE_THRESHOLD_INTERVAL_MS = 100
DEFAULT_FATIGUE_DURATION_MS = 3000
DEFAULT_FATIGUE_COOLDOWN_DURATION_MS = 1000
DEFAULT_FATIGUE_COOLDOWN_MIN_INTERVAL_MS = 500
MIN_SLEEP_MS = 1
IDLE_SLEEP_MS = 100

HOLD_TIME_MEAN_MS = DEFAULT_HOLD_TIME_MEAN_MS
HOLD_TIME_STD_MS = DEFAULT_HOLD_TIME_STD_MS
DRIFT_STEP_MIN = DEFAULT_DRIFT_STEP_MIN
DRIFT_STEP_MAX = DEFAULT_DRIFT_STEP_MAX
DRIFT_RESET_MIN = DEFAULT_DRIFT_RESET_MIN
DRIFT_RESET_MAX = DEFAULT_DRIFT_RESET_MAX

IS_WINDOWS = sys.platform.startswith("win")

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
MK_LBUTTON = 0x0001
MK_RBUTTON = 0x0002

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)

    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.WindowFromPoint.argtypes = [POINT]
    _user32.WindowFromPoint.restype = wintypes.HWND
    _user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
    _user32.ScreenToClient.restype = wintypes.BOOL
    _user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    _user32.PostMessageW.restype = wintypes.BOOL
    _user32.IsWindow.argtypes = [wintypes.HWND]
    _user32.IsWindow.restype = wintypes.BOOL
else:
    _user32 = None


def get_foreground_window_handle():
    if not IS_WINDOWS:
        return None
    hwnd = _user32.GetForegroundWindow()
    return hwnd or None


def get_window_at_point(x, y):
    if not IS_WINDOWS:
        return None
    pt = POINT(int(x), int(y))
    hwnd = _user32.WindowFromPoint(pt)
    return hwnd or None


def _make_lparam(x, y):
    x = max(0, int(x))
    y = max(0, int(y))
    return (y & 0xFFFF) << 16 | (x & 0xFFFF)


if IS_WINDOWS:
    class Win32BackgroundClicker:
        def __init__(self, hwnd):
            self.hwnd = hwnd

        def is_valid(self):
            return bool(self.hwnd) and bool(_user32.IsWindow(self.hwnd))

        def _screen_to_client(self, x, y):
            pt = POINT(int(x), int(y))
            if not _user32.ScreenToClient(self.hwnd, ctypes.byref(pt)):
                return None
            return pt.x, pt.y

        def _post(self, msg, wparam, x, y):
            if not self.is_valid():
                return False
            client = self._screen_to_client(x, y)
            if client is None:
                return False
            lparam = _make_lparam(*client)
            return bool(_user32.PostMessageW(self.hwnd, msg, wparam, lparam))

        def press(self, x, y, button):
            if button == Button.left:
                return self._post(WM_LBUTTONDOWN, MK_LBUTTON, x, y)
            return self._post(WM_RBUTTONDOWN, MK_RBUTTON, x, y)

        def release(self, x, y, button):
            if button == Button.left:
                return self._post(WM_LBUTTONUP, 0, x, y)
            return self._post(WM_RBUTTONUP, 0, x, y)
else:
    Win32BackgroundClicker = None


def ms_to_sec(ms):
    return ms / MS_PER_SEC


def coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def safe_int(value, default):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


class AutoClicker(threading.Thread):
    def __init__(self, interval_ms, random_interval_ms, click_type, button,
                 interval_mode="Exponential", exp_mean_interval_ms=DEFAULT_EXP_MEAN_INTERVAL_MS,
                 target_pos=None, random_pos_offset=(0, 0), click_limit=0,
                 human_like=False,
                 hold_time_enabled=DEFAULT_HOLD_TIME_ENABLED,
                 hold_time_mean_ms=DEFAULT_HOLD_TIME_MEAN_MS,
                 hold_time_std_ms=DEFAULT_HOLD_TIME_STD_MS,
                 drift_enabled=DEFAULT_DRIFT_ENABLED,
                 drift_step_min=DEFAULT_DRIFT_STEP_MIN,
                 drift_step_max=DEFAULT_DRIFT_STEP_MAX,
                 drift_reset_min=DEFAULT_DRIFT_RESET_MIN,
                 drift_reset_max=DEFAULT_DRIFT_RESET_MAX,
                 thinking_pause_enabled=DEFAULT_THINKING_PAUSE_ENABLED,
                 thinking_pause_mean_ms=DEFAULT_THINKING_PAUSE_MEAN_MS,
                 thinking_pause_std_ms=DEFAULT_THINKING_PAUSE_STD_MS,
                 thinking_pause_min_clicks=DEFAULT_THINKING_PAUSE_MIN_CLICKS,
                 thinking_pause_max_clicks=DEFAULT_THINKING_PAUSE_MAX_CLICKS,
                 fatigue_enabled=DEFAULT_FATIGUE_ENABLED,
                 fatigue_threshold_interval_ms=DEFAULT_FATIGUE_THRESHOLD_INTERVAL_MS,
                 fatigue_duration_ms=DEFAULT_FATIGUE_DURATION_MS,
                 fatigue_cooldown_duration_ms=DEFAULT_FATIGUE_COOLDOWN_DURATION_MS,
                 fatigue_cooldown_min_interval_ms=DEFAULT_FATIGUE_COOLDOWN_MIN_INTERVAL_MS,
                 rand=None,
                 time_provider=None,
                 sleep_fn=None,
                 mouse=None,
                 background_click_enabled=False,
                 background_click_handle=None,
                 background_clicker=None,
                 app=None):
        super().__init__()
        self.rand = rand if rand else random
        self.now = time_provider if time_provider else time.perf_counter
        self.sleep = sleep_fn if sleep_fn else time.sleep
        self.mouse = mouse if mouse else Controller()
        self.background_click_enabled = background_click_enabled
        self.background_click_handle = background_click_handle
        self.background_clicker = background_clicker
        if self.background_click_enabled and self.background_clicker is None and Win32BackgroundClicker:
            self.background_clicker = Win32BackgroundClicker(self.background_click_handle)
        self.app = app
        self.interval_ms = interval_ms
        self.random_interval_ms = random_interval_ms
        self.interval_mode = interval_mode
        self.exp_mean_interval_ms = exp_mean_interval_ms
        self.click_type = click_type.lower()
        self.button_key = button
        self.button = Button.left if button.lower() == "left" else Button.right
        self.click_limit = click_limit
        self.target_pos = target_pos
        self.random_pos_offset = random_pos_offset
        self.human_like = human_like
        self.hold_time_enabled = hold_time_enabled
        self.hold_time_mean_ms = hold_time_mean_ms
        self.hold_time_std_ms = hold_time_std_ms
        self.drift_enabled = drift_enabled
        self.drift_step_min = drift_step_min
        self.drift_step_max = drift_step_max
        self.drift_reset_min = drift_reset_min
        self.drift_reset_max = drift_reset_max
        self.thinking_pause_enabled = thinking_pause_enabled
        self.thinking_pause_mean_ms = thinking_pause_mean_ms
        self.thinking_pause_std_ms = thinking_pause_std_ms
        self.thinking_pause_min_clicks = thinking_pause_min_clicks
        self.thinking_pause_max_clicks = thinking_pause_max_clicks
        self.fatigue_enabled = fatigue_enabled
        self.fatigue_threshold_interval_ms = fatigue_threshold_interval_ms
        self.fatigue_duration_ms = fatigue_duration_ms
        self.fatigue_cooldown_duration_ms = fatigue_cooldown_duration_ms
        self.fatigue_cooldown_min_interval_ms = fatigue_cooldown_min_interval_ms
        self.running = False
        self.program_running = True
        self.click_count = 0

        self.drift_x = 0
        self.drift_y = 0
        self.last_action_time = None
        self.jitter_duration = 0
        self.cooldown_end_time = 0
        self.next_thinking_click = self.rand.randint(self.thinking_pause_min_clicks, self.thinking_pause_max_clicks)

    def start_clicking(self):
        self.running = True
        self.click_count = 0
        self.drift_x = 0
        self.drift_y = 0
        self.last_action_time = None
        self.jitter_duration = 0
        self.cooldown_end_time = 0
        self.next_thinking_click = self.rand.randint(self.thinking_pause_min_clicks, self.thinking_pause_max_clicks)

    def stop_clicking(self):
        self.running = False

    def exit(self):
        self.stop_clicking()
        self.program_running = False

    def _sample_positive_gauss_ms(self, mean_ms, std_ms, min_value_ms=MIN_SLEEP_MS):
        value = self.rand.gauss(mean_ms, std_ms)
        while value < min_value_ms:
            value = self.rand.gauss(mean_ms, std_ms)
        return value

    def _sample_hold_time(self):
        return ms_to_sec(self._sample_positive_gauss_ms(self.hold_time_mean_ms, self.hold_time_std_ms))

    def _use_background_clicker(self):
        if not self.background_click_enabled or not self.background_clicker:
            return False
        is_valid = getattr(self.background_clicker, "is_valid", None)
        return is_valid() if callable(is_valid) else True

    def _press_button(self, button, x, y):
        if self.background_click_enabled:
            if self._use_background_clicker():
                self.background_clicker.press(x, y, button)
            return
        self.mouse.press(button)

    def _release_button(self, button, x, y):
        if self.background_click_enabled:
            if self._use_background_clicker():
                self.background_clicker.release(x, y, button)
            return
        self.mouse.release(button)

    def _click_button(self, button, x, y, count):
        if self.background_click_enabled:
            if not self._use_background_clicker():
                return
            for i in range(count):
                self.background_clicker.press(x, y, button)
                self.background_clicker.release(x, y, button)
                if count == 2 and i == 0:
                    self.sleep(ms_to_sec(DOUBLE_CLICK_GAP_MIN_MS))
            return
        self.mouse.click(button, count)

    def run(self):
        while self.program_running:
            while self.running:
                if self.background_click_enabled and not self._use_background_clicker():
                    self.stop_clicking()
                    if self.app:
                        self.app.after(0, self.app.stop_clicking_ui)
                    break
                if self.human_like and self.fatigue_enabled:
                    now = self.now()
                    if self.last_action_time is not None:
                        delta_ms = (now - self.last_action_time) * MS_PER_SEC
                        if delta_ms < self.fatigue_threshold_interval_ms:
                            self.jitter_duration += delta_ms
                        else:
                            self.jitter_duration = 0
                    self.last_action_time = now

                    if self.jitter_duration >= self.fatigue_duration_ms:
                        self.cooldown_end_time = now + ms_to_sec(self.fatigue_cooldown_duration_ms)
                        self.jitter_duration = 0

                target_x, target_y = self.target_pos if self.target_pos else self.mouse.position
                current_button = self.button
                current_click_type = self.click_type

                final_x, final_y = target_x, target_y

                if self.random_pos_offset:
                    range_x, range_y = self.random_pos_offset
                    if range_x > 0 or range_y > 0:
                        if self.human_like and self.drift_enabled:
                            drift_step_x = self.rand.uniform(self.drift_step_min, self.drift_step_max)
                            drift_step_y = self.rand.uniform(self.drift_step_min, self.drift_step_max)
                            self.drift_x += drift_step_x
                            self.drift_y += drift_step_y
                            if (abs(self.drift_x) > range_x) or (abs(self.drift_y) > range_y):
                                self.drift_x = self.rand.uniform(self.drift_reset_min, self.drift_reset_max)
                                self.drift_y = self.rand.uniform(self.drift_reset_min, self.drift_reset_max)
                            final_x += int(self.drift_x)
                            final_y += int(self.drift_y)
                        else:
                            final_x += self.rand.randint(-range_x, range_x) if range_x > 0 else 0
                            final_y += self.rand.randint(-range_y, range_y) if range_y > 0 else 0

                if self.target_pos or (self.random_pos_offset and (self.random_pos_offset[0] > 0 or self.random_pos_offset[1] > 0)):
                    if not self._use_background_clicker():
                        self.mouse.position = (final_x, final_y)

                click_count = 2 if current_click_type.lower() == "double" else 1

                if self.human_like and self.hold_time_enabled:
                    for i in range(click_count):
                        self._press_button(current_button, final_x, final_y)
                        self.sleep(self._sample_hold_time())
                        self._release_button(current_button, final_x, final_y)
                        if click_count == 2 and i == 0:
                            self.sleep(ms_to_sec(self.rand.uniform(DOUBLE_CLICK_GAP_MIN_MS, DOUBLE_CLICK_GAP_MAX_MS)))
                else:
                    self._click_button(current_button, final_x, final_y, click_count)

                self.click_count += click_count

                if self.click_limit > 0 and self.click_count >= self.click_limit:
                    self.stop_clicking()
                    if self.app:
                        self.app.after(0, self.app.stop_clicking_ui)
                    break

                thinking_pause_ms = 0
                if self.human_like and self.thinking_pause_enabled and self.click_count >= self.next_thinking_click:
                    thinking_pause_ms = self._sample_positive_gauss_ms(self.thinking_pause_mean_ms, self.thinking_pause_std_ms)
                    self.next_thinking_click = self.click_count + self.rand.randint(self.thinking_pause_min_clicks, self.thinking_pause_max_clicks)

                if self.interval_mode == "Exponential":
                    mean_interval_ms = max(MIN_SLEEP_MS, self.exp_mean_interval_ms)
                    p_delay_ms = -math.log(1.0 - self.rand.random()) * mean_interval_ms
                else:
                    p_delay_ms = self.interval_ms
                    if self.random_interval_ms > 0:
                        p_delay_ms += self.rand.uniform(0, self.random_interval_ms)

                if self.human_like and self.thinking_pause_enabled:
                    p_delay_ms += thinking_pause_ms
                if self.human_like and self.fatigue_enabled and self.now() < self.cooldown_end_time:
                    p_delay_ms = max(p_delay_ms, self.fatigue_cooldown_min_interval_ms)

                self.sleep(ms_to_sec(max(MIN_SLEEP_MS, p_delay_ms)))

            self.sleep(ms_to_sec(IDLE_SLEEP_MS))
