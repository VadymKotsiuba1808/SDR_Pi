"""
Сервіс клавіатури.
Керує перемиканням розкладки (EN/UA) та глобальними хоткеями.
"""

import subprocess
from app.protocols import OSService


class KeyboardService:

    def __init__(self, system: OSService, callback=None):
        self.system_service = system

        self.callback = callback

        self._setup_state_variables()

        self._init_os_modules()

        self._start_listener()
        self._apply_layout()

    def _setup_state_variables(self):
        self.current_layout = "EN"
        self.layouts_win = {"EN": "00000409", "UA": "00000422"}
        self.layouts_linux = {"EN": "us", "UA": "ua"}

    def _init_os_modules(self):
        """Імпортує потрібні модулі залежно від ОС."""
        self.win32api = self.win32gui = self.keyboard = None
        self.pynput_keyboard = None

        if self.system_service.is_windows:
            import win32api
            import win32gui
            import keyboard

            self.win32api = win32api
            self.win32gui = win32gui
            self.keyboard = keyboard
        elif self.system_service.is_linux:
            from pynput import keyboard as pynput_keyboard
            import subprocess

            self.pynput_keyboard = pynput_keyboard
            self.subprocess = subprocess

    def _start_listener(self):
        if self.system_service.is_windows:
            self.keyboard.add_hotkey("alt+shift", self.toggle_layout)
        elif self.system_service.is_linux:
            listener = self.pynput_keyboard.Listener(on_press=self._on_key_press)
            listener.start()
        else:
            print(f"KeyboardLayoutManager: OS не підтримується.")

    # ------------------- Linux -------------------
    def _on_key_press(self, key):
        try:
            if (
                key == self.pynput_keyboard.Key.shift
                and self.pynput_keyboard.Controller().pressed(
                    self.pynput_keyboard.Key.alt_l
                )
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
        if self.system_service.is_windows:
            self._set_windows_layout()
        elif self.system_service.is_linux:
            self._set_linux_layout()
        else:
            print("OS не підтримується")

    def _set_windows_layout(self):
        try:
            lid = self.layouts_win[self.current_layout]

            self.win32api.LoadKeyboardLayout(lid, 1)

            hwnd = self.win32gui.GetForegroundWindow()

            if hwnd:
                lang_id_int = int(lid, 16)

                self.win32api.PostMessage(hwnd, 0x0050, 0, lang_id_int)

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
