import sys
import platform
import subprocess

# Для Windows
if platform.system() == "Windows":
    import win32api
    import win32con
    import win32gui
    import keyboard

# Для Linux (X11)
elif platform.system() == "Linux":
    from pynput import keyboard as pynput_keyboard


class KeyboardService:
    """
    Клас для керування мовою клавіатури з програми.
    Підтримує Windows та Linux (X11).
    """

    def __init__(self, callback=None):
        """
        callback: функція, яку викликаємо після зміни розкладки
                  наприклад, для оновлення QLabel в PyQt6
        """
        self.current_layout = "EN"
        self.callback = callback  # функція для UI

        # Словники для Windows / Linux
        self.layouts_win = {"EN": "00000409", "UA": "00000422"}
        self.layouts_linux = {"EN": "us", "UA": "ua"}

        # Запуск прослуховування клавіш
        self._start_listener()

    def _start_listener(self):
        system = platform.system()
        if system == "Windows":
            # Використовуємо бібліотеку keyboard
            keyboard.add_hotkey("alt+shift", self.toggle_layout)
        elif system == "Linux":
            # Використовуємо pynput для перехоплення Alt+Shift
            listener = pynput_keyboard.Listener(on_press=self._on_key_press)
            listener.start()
        else:
            print(f"KeyboardLayoutManager: OS {system} не підтримується.")

    # ------------------- Linux -------------------
    def _on_key_press(self, key):
        """
        Linux: простий перехоплювач Alt+Shift
        """
        try:
            if (
                key == pynput_keyboard.Key.shift
                and pynput_keyboard.Controller().pressed(pynput_keyboard.Key.alt_l)
            ):
                self.toggle_layout()
        except Exception:
            pass

    def set_callback(self, callback):
        self.callback = callback

    def toggle_layout(self):
        """
        Переключаємо мову між EN/UA
        """
        self.current_layout = "UA" if self.current_layout == "EN" else "EN"
        self._apply_layout()
        if self.callback:
            self.callback(self.current_layout)

    def _apply_layout(self):
        """
        Встановлює розкладку у системі
        """
        system = platform.system()
        if system == "Windows":
            self._set_windows_layout()
        elif system == "Linux":
            self._set_linux_layout()
        else:
            print("OS не підтримується")

    # ------------------- Windows -------------------
    def _set_windows_layout(self):
        lid = self.layouts_win[self.current_layout]
        try:
            win32api.LoadKeyboardLayout(lid, 1)
        except Exception as e:
            print(f"Не вдалося змінити розкладку Windows: {e}")

    # ------------------- Linux -------------------
    def _set_linux_layout(self):
        layout = self.layouts_linux[self.current_layout]
        try:
            subprocess.call(["setxkbmap", layout])
        except Exception as e:
            print(f"Не вдалося змінити розкладку Linux: {e}")
