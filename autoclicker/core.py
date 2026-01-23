import time
import random
import threading
import math
from pynput.mouse import Button, Controller

MS_PER_SEC = 1000

DEFAULT_INTERVAL_MS = 100
DEFAULT_RANDOM_INTERVAL_MS = 0
DEFAULT_EXP_MEAN_INTERVAL_MS = 313
DEFAULT_HOLD_TIME_ENABLED = True
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
DEFAULT_THINKING_PAUSE_MEAN_MS = 4000
DEFAULT_THINKING_PAUSE_STD_MS = 1500
DEFAULT_THINKING_PAUSE_MIN_CLICKS = 10
DEFAULT_THINKING_PAUSE_MAX_CLICKS = 20
DEFAULT_FATIGUE_ENABLED = True
DEFAULT_FATIGUE_THRESHOLD_INTERVAL_MS = 100
DEFAULT_FATIGUE_DURATION_MS = 3000
DEFAULT_FATIGUE_COOLDOWN_DURATION_MS = 15000
DEFAULT_FATIGUE_COOLDOWN_MIN_INTERVAL_MS = 500
MIN_SLEEP_MS = 1
IDLE_SLEEP_MS = 100

HOLD_TIME_MEAN_MS = DEFAULT_HOLD_TIME_MEAN_MS
HOLD_TIME_STD_MS = DEFAULT_HOLD_TIME_STD_MS
DRIFT_STEP_MIN = DEFAULT_DRIFT_STEP_MIN
DRIFT_STEP_MAX = DEFAULT_DRIFT_STEP_MAX
DRIFT_RESET_MIN = DEFAULT_DRIFT_RESET_MIN
DRIFT_RESET_MAX = DEFAULT_DRIFT_RESET_MAX


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
                 interval_mode="Uniform", exp_mean_interval_ms=DEFAULT_EXP_MEAN_INTERVAL_MS,
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
                 app=None):
        super().__init__()
        self.rand = rand if rand else random
        self.now = time_provider if time_provider else time.perf_counter
        self.sleep = sleep_fn if sleep_fn else time.sleep
        self.mouse = mouse if mouse else Controller()
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

    def run(self):
        while self.program_running:
            while self.running:
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
                    self.mouse.position = (final_x, final_y)

                click_count = 2 if current_click_type.lower() == "double" else 1

                if self.human_like and self.hold_time_enabled:
                    for i in range(click_count):
                        self.mouse.press(current_button)
                        self.sleep(self._sample_hold_time())
                        self.mouse.release(current_button)
                        if click_count == 2 and i == 0:
                            self.sleep(ms_to_sec(self.rand.uniform(DOUBLE_CLICK_GAP_MIN_MS, DOUBLE_CLICK_GAP_MAX_MS)))
                else:
                    self.mouse.click(current_button, click_count)

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
