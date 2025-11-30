"""
Сервіс клавіатури.
Керує перемиканням розкладки (EN/UA) та глобальними хоткеями.
"""

import sys
import platform
import subprocess


# Для Windows
if platform.system() == "Windows":
    import win32api
    import win32gui
    import keyboard

# Для Linux (X11)
elif platform.system() == "Linux":
    from pynput import keyboard as pynput_keyboard


class KeyboardService:

    def __init__(self, callback=None):
        self.current_layout = "EN"
        self.callback = callback

        self.layouts_win = {"EN": "00000409", "UA": "00000422"}
        self.layouts_linux = {"EN": "us", "UA": "ua"}

        self._start_listener()
        self._apply_layout()

    def _start_listener(self):
        system = platform.system()
        if system == "Windows":
            keyboard.add_hotkey("alt+shift", self.toggle_layout)
        elif system == "Linux":
            listener = pynput_keyboard.Listener(on_press=self._on_key_press)
            listener.start()
        else:
            print(f"KeyboardLayoutManager: OS {system} не підтримується.")

    # ------------------- Linux -------------------
    def _on_key_press(self, key):
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
        print("Toggled layout")
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

    def _set_windows_layout(self):
        try:
            lid = self.layouts_win[self.current_layout]

            win32api.LoadKeyboardLayout(lid, 1)

            hwnd = win32gui.GetForegroundWindow()

            if hwnd:
                lang_id_int = int(lid, 16)

                win32api.PostMessage(hwnd, 0x0050, 0, lang_id_int)

        except Exception as e:
            print(f"Windows API Error: {e}")

    def _set_linux_layout(self):
        try:
            target_lang = self.layouts_linux[self.current_layout]

            second_lang = "us" if target_lang == "ua" else "ua"

            cmd = [
                "setxkbmap",
                "-layout",
                f"{target_lang},{second_lang}",
                "-option",
                "grp:alt_shift_toggle",
            ]

            subprocess.Popen(cmd)

        except Exception as e:
            print(f"Не вдалося змінити розкладку Linux: {e}")
