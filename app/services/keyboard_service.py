import subprocess
from typing import Any, Callable, Optional

from app.protocols import OSService


class KeyboardService:
    """
    Сервіс керування розкладкою клавіатури та глобальними хоткеями.

    Забезпечує кросплатформну підтримку перемикання розкладки та відстеження
    натискань клавіш для виконання команд. Використовує низькорівневі API
    відповідних операційних систем.

    Attributes:
        system_service (OSService): Сервіс для визначення поточної операційної системи.
        callback (Optional[Callable[[str], None]]): Функція, що викликається при зміні розкладки.
        current_layout (str): Поточна активна розкладка ("EN" або "UA").
        layouts_win (dict[str, str]): Мапа ідентифікаторів розкладок для Windows.
        layouts_linux (dict[str, str]): Мапа кодів розкладок для Linux.
    """

    def __init__(
        self, system: OSService, callback: Optional[Callable[[str], None]] = None
    ) -> None:
        """
        Ініціалізує сервіс клавіатури.

        Args:
            system (OSService): Сервіс для визначення поточної ОС.
            callback (Optional[Callable[[str], None]]): Функція зворотного виклику
                при зміні розкладки. Приймає рядок з назвою нової розкладки.
        """
        self.system_service = system
        self.callback = callback

        self._setup_state_variables()
        self._init_os_modules()
        self._start_listener()
        self._apply_layout()

    def _setup_state_variables(self) -> None:
        """
        Налаштовує початкові значення змінних стану сервісу.

        Визначає коди розкладок для підтримуваних операційних систем.
        """
        self.current_layout = "EN"
        # 00000409 - English (United States), 00000422 - Ukrainian
        self.layouts_win = {"EN": "00000409", "UA": "00000422"}
        self.layouts_linux = {"EN": "us", "UA": "ua"}

    def _init_os_modules(self) -> None:
        """
        Динамічно імпортує модулі залежно від поточної операційної системи.

        !!! note
            Динамічний імпорт використовується для уникнення залежностей,
            які не можуть бути встановлені на іншій ОС (наприклад, win32api на Linux).
        """
        self.win32api: Any = None
        self.win32gui: Any = None
        self.keyboard: Any = None
        self.pynput_keyboard: Any = None

        if self.system_service.is_windows:
            import keyboard
            import win32api
            import win32gui

            self.win32api = win32api
            self.win32gui = win32gui
            self.keyboard = keyboard
        elif self.system_service.is_linux:
            import subprocess

            from pynput import keyboard as pynput_keyboard

            self.pynput_keyboard = pynput_keyboard
            self.subprocess = subprocess

    def _start_listener(self):
        if self.system_service.is_windows and self.keyboard:
            # Реєструємо глобальний хоткей для перемикання мови
            self.keyboard.add_hotkey("alt+shift", self.toggle_layout)
        elif self.system_service.is_linux and self.pynput_keyboard:
            # У Linux використовуємо Listener для відстеження комбінацій
            listener = self.pynput_keyboard.Listener(on_press=self._on_key_press)
            listener.start()
        else:
            print(
                "KeyboardLayoutManager: ОС не підтримується або модулі не завантажені."
            )

    def _on_key_press(self, key: Any) -> None:
        """
        Обробник натискання клавіш для Linux.

        Відстежує комбінацію Alt+Shift.

        Args:
            key: Об'єкт клавіші, яка була натиснута.
        """
        try:
            if (
                self.pynput_keyboard
                and key == self.pynput_keyboard.Key.shift
                and self.pynput_keyboard.Controller().pressed(
                    self.pynput_keyboard.Key.alt_l
                )
            ):
                self.toggle_layout()
        except Exception:
            # Ігноруємо помилки при обробці клавіш, щоб не переривати Listener
            pass

    def set_callback(self, callback: Callable[[str], None]) -> None:
        """
        Встановлює функцію зворотного виклику для сповіщення про зміну розкладки.

        Args:
            callback (Callable[[str], None]): Функція, що приймає назву нової розкладки.
        """
        self.callback = callback

    def toggle_layout(self) -> None:
        """
        Перемикає поточну розкладку між EN та UA циклічно.

        Після перемикання оновлює системну розкладку та викликає callback.
        """
        self.current_layout = "UA" if self.current_layout == "EN" else "EN"
        self._apply_layout()

        if self.callback:
            self.callback(self.current_layout)

    def _apply_layout(self) -> None:
        """
        Застосовує поточну розкладку безпосередньо в операційній системі.

        Викликає специфічні методи для Windows або Linux.
        """
        if self.system_service.is_windows:
            self._set_windows_layout()
        elif self.system_service.is_linux:
            self._set_linux_layout()
        else:
            print("KeyboardService: Поточна операційна система не підтримується")

    def _set_windows_layout(self) -> None:
        """
        Змінює розкладку в Windows через Win32 API.

        !!! info
            Метод спочатку завантажує розкладку в пам'ять поточного процесу,
            а потім надсилає повідомлення WM_INPUTLANGCHANGEREQUEST активному вікну,
            щоб змінити мову введення для користувача.
        """
        try:
            lid = self.layouts_win[self.current_layout]

            if self.win32api is None or self.win32gui is None:
                print("Windows API modules not loaded, cannot change layout.")
                return

            # Завантажуємо розкладку (KLF_ACTIVATE = 1)
            self.win32api.LoadKeyboardLayout(lid, 1)

            # Отримуємо дескриптор активного вікна
            hwnd = self.win32gui.GetForegroundWindow()

            if hwnd:
                lang_id_int = int(lid, 16)
                # 0x0050 - WM_INPUTLANGCHANGEREQUEST
                self.win32api.PostMessage(hwnd, 0x0050, 0, lang_id_int)

        except Exception as e:
            print(f"Windows API Error: {e}")

    def _set_linux_layout(self) -> None:
        """
        Змінює розкладку в Linux за допомогою утиліти setxkbmap.

        !!! note
            Використовується виклик зовнішньої команди для налаштування X11.
            Опція grp:alt_shift_toggle дозволяє системі також реагувати на стандартний хоткей.
        """
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

            # Виконуємо команду у фоновому режимі
            subprocess.Popen(cmd)

        except Exception as e:
            print(f"Не вдалося змінити розкладку Linux: {e}")
