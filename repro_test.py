import time
import threading
from pynput.mouse import Button, Controller

class MockMouse:
    def __init__(self):
        self.press_count = 0
        self.release_count = 0
        self.position = (0, 0)
    
    def press(self, button):
        self.press_count += 1
        print(f"  [MOCK] Press {button}")
        
    def release(self, button):
        self.release_count += 1
        print(f"  [MOCK] Release {button}")

def test_double_click_logic(current_click_type, human_like=True):
    print(f"\n--- Testing: {current_click_type} (Humanized: {human_like}) ---")
    mock_mouse = MockMouse()
    current_button = Button.left
    click_count = 2 if current_click_type.lower() == 'double' else 1
    
    start_time = time.time()
    for i in range(click_count):
        mock_mouse.press(current_button)
        if human_like:
            # Short variable hold
            time.sleep(0.02) 
        mock_mouse.release(current_button)
        if click_count == 2 and i == 0:
            # Gap between clicks
            time.sleep(0.02)
    end_time = time.time()
    
    print(f"  Physical Presses: {mock_mouse.press_count}")
    print(f"  Physical Releases: {mock_mouse.release_count}")
    print(f"  Total Duration: {end_time - start_time:.4f}s")
    
    if current_click_type.lower() == 'double' and mock_mouse.press_count != 2:
        print("  [FAIL] Did not perform 2 clicks for 'double'")
    else:
        print("  [PASS] Physical click counts match")

if __name__ == "__main__":
    test_double_click_logic("Double", human_like=True)
    test_double_click_logic("Single", human_like=True)
    test_double_click_logic("Double", human_like=False)
