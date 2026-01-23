import random

from autoclicker.core import AutoClicker, MS_PER_SEC, ms_to_sec


class FakeClock:
    def __init__(self):
        self.current = 0.0

    def perf_counter(self):
        return self.current

    def sleep(self, seconds):
        self.current += seconds


class FakeMouse:
    def __init__(self):
        self.position = (0, 0)
        self.press_count = 0
        self.release_count = 0
        self.click_calls = 0

    def press(self, button):
        self.press_count += 1

    def release(self, button):
        self.release_count += 1

    def click(self, button, count):
        self.click_calls += 1
        self.press_count += count
        self.release_count += count


class FastHoldClicker(AutoClicker):
    def _sample_hold_time(self):
        return ms_to_sec(1)


class TraceRandom(random.Random):
    def __init__(self, seed=7):
        super().__init__(seed)
        self.uniform_calls = 0
        self.randint_calls = 0
        self.gauss_calls = 0

    def uniform(self, a, b):
        self.uniform_calls += 1
        return super().uniform(a, b)

    def randint(self, a, b):
        self.randint_calls += 1
        return super().randint(a, b)

    def gauss(self, mu, sigma):
        self.gauss_calls += 1
        return super().gauss(mu, sigma)


def build_clicker(clicker_cls=AutoClicker, max_clicks=8, seed=7, rand=None, **overrides):
    clock = FakeClock()
    sleep_log = []
    clicker_ref = {}

    def sleep_fn(seconds):
        clock.sleep(seconds)
        sleep_log.append(seconds * MS_PER_SEC)
        clicker = clicker_ref.get("clicker")
        if clicker and clicker.click_count >= max_clicks:
            clicker.running = False
            clicker.program_running = False

    params = {
        "interval_ms": 10,
        "random_interval_ms": 0,
        "click_type": "single",
        "button": "left",
        "interval_mode": "Uniform",
        "click_limit": max_clicks,
        "human_like": True,
        "thinking_pause_enabled": False,
        "fatigue_enabled": False,
    }
    params.update(overrides)

    if rand is None:
        rand = random.Random(seed)

    clicker = clicker_cls(
        **params,
        rand=rand,
        time_provider=clock.perf_counter,
        sleep_fn=sleep_fn,
        mouse=FakeMouse(),
    )
    clicker_ref["clicker"] = clicker
    return clicker, sleep_log


def run_clicker(clicker):
    clicker.start_clicking()
    clicker.run()


def assert_has_pause(sleeps_ms, threshold_ms, label):
    if not any(duration >= threshold_ms for duration in sleeps_ms):
        raise AssertionError(f"{label}: expected pause >= {threshold_ms}ms")


def assert_no_pause(sleeps_ms, threshold_ms, label):
    if any(duration >= threshold_ms for duration in sleeps_ms):
        raise AssertionError(f"{label}: unexpected pause >= {threshold_ms}ms")


def test_thinking_pause_toggle():
    clicker_off, sleeps_off = build_clicker(
        max_clicks=6,
        thinking_pause_enabled=False,
        thinking_pause_mean_ms=4000,
        thinking_pause_std_ms=0,
        thinking_pause_min_clicks=2,
        thinking_pause_max_clicks=2,
        fatigue_enabled=False,
    )
    run_clicker(clicker_off)
    assert_no_pause(sleeps_off, 1000, "Thinking pause disabled")

    clicker_on, sleeps_on = build_clicker(
        max_clicks=6,
        thinking_pause_enabled=True,
        thinking_pause_mean_ms=4000,
        thinking_pause_std_ms=0,
        thinking_pause_min_clicks=2,
        thinking_pause_max_clicks=2,
        fatigue_enabled=False,
    )
    run_clicker(clicker_on)
    assert_has_pause(sleeps_on, 1000, "Thinking pause enabled")


def test_fatigue_toggle():
    clicker_on, sleeps_on = build_clicker(
        clicker_cls=FastHoldClicker,
        max_clicks=40,
        interval_ms=10,
        fatigue_enabled=True,
        fatigue_threshold_interval_ms=100,
        fatigue_duration_ms=200,
        fatigue_cooldown_duration_ms=500,
        fatigue_cooldown_min_interval_ms=500,
        thinking_pause_enabled=False,
    )
    run_clicker(clicker_on)
    assert_has_pause(sleeps_on, 500, "Fatigue enabled")

    clicker_off, sleeps_off = build_clicker(
        clicker_cls=FastHoldClicker,
        max_clicks=40,
        interval_ms=10,
        fatigue_enabled=False,
        fatigue_threshold_interval_ms=100,
        fatigue_duration_ms=200,
        fatigue_cooldown_duration_ms=500,
        fatigue_cooldown_min_interval_ms=500,
        thinking_pause_enabled=False,
    )
    run_clicker(clicker_off)
    assert_no_pause(sleeps_off, 500, "Fatigue disabled")


def test_hold_time_toggle():
    clicker_on, _ = build_clicker(
        max_clicks=5,
        hold_time_enabled=True,
        hold_time_mean_ms=150,
        hold_time_std_ms=0,
        thinking_pause_enabled=False,
        fatigue_enabled=False,
    )
    run_clicker(clicker_on)
    if clicker_on.mouse.click_calls != 0:
        raise AssertionError("Hold time enabled: expected press/release clicks")

    clicker_off, _ = build_clicker(
        max_clicks=5,
        hold_time_enabled=False,
        thinking_pause_enabled=False,
        fatigue_enabled=False,
    )
    run_clicker(clicker_off)
    if clicker_off.mouse.click_calls == 0:
        raise AssertionError("Hold time disabled: expected click calls")


def test_drift_toggle():
    rand_on = TraceRandom(11)
    clicker_on, _ = build_clicker(
        max_clicks=6,
        rand=rand_on,
        random_pos_offset=(5, 5),
        drift_enabled=True,
        hold_time_enabled=False,
        thinking_pause_enabled=False,
        fatigue_enabled=False,
    )
    run_clicker(clicker_on)
    if rand_on.uniform_calls == 0:
        raise AssertionError("Drift enabled: expected uniform calls")

    rand_off = TraceRandom(11)
    clicker_off, _ = build_clicker(
        max_clicks=6,
        rand=rand_off,
        random_pos_offset=(5, 5),
        drift_enabled=False,
        hold_time_enabled=False,
        thinking_pause_enabled=False,
        fatigue_enabled=False,
    )
    run_clicker(clicker_off)
    if rand_off.uniform_calls != 0:
        raise AssertionError("Drift disabled: expected no uniform calls")


def run_all_tests():
    tests = [
        test_thinking_pause_toggle,
        test_fatigue_toggle,
        test_hold_time_toggle,
        test_drift_toggle,
    ]
    for test in tests:
        test()
        print(f"[PASS] {test.__name__}")


if __name__ == "__main__":
    run_all_tests()
