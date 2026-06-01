from typing import cast

from PyQt6 import uic
from PyQt6.QtCore import QCoreApplication, QEvent, QTranslator
from PyQt6.QtWidgets import QWidget

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED
from app.protocols import LangSettings
from app.services.keyboard_service import KeyboardService
from app.ui.ui_keyboard_widget import Ui_KeyboardWidget


class KeyboardWidget(QWidget):
    """
    Віджет для відображення та зміни поточної розкладки клавіатури.

    Він інтегрується з KeyboardService для синхронізації стану розкладки між
    GUI та системними налаштуваннями. Також обробляє зміну мови інтерфейсу
    додатка через QTranslator.

    Attributes:
        settings_service (LangSettings): Сервіс для роботи з налаштуваннями мови.
        keyboard_service (KeyboardService): Сервіс для керування розкладкою клавіатури.
        translator (QTranslator): Об'єкт для перекладу інтерфейсу.
        ui (Ui_KeyboardWidget): Об'єкт згенерованого або завантаженого UI.
    """

    def __init__(
        self,
        settings: LangSettings,
        keyboard_service: KeyboardService,
        parent: QWidget | None = None,
    ) -> None:
        """
        Ініціалізує віджет клавіатури.

        Args:
            settings: Сервіс налаштувань мови.
            keyboard_service: Сервіс керування розкладкою.
            parent: Батьківський віджет.
        """
        super().__init__(parent)

        self.settings_service = settings
        self.keyboard_service = keyboard_service

        self._load_ui()
        self._setup_state_variables()
        self._adjust_fields()
        self._connect_handlers()
        self._load_language()

    def changeEvent(self, a0: QEvent | None) -> None:
        """
        Обробляє подію зміни стану віджета.

        Зокрема реагує на QEvent.Type.LanguageChange для оновлення текстів у UI
        при зміні мови перекладу.

        Args:
            a0: Об'єкт події.
        """
        event = a0
        if event and event.type() == QEvent.Type.LanguageChange:
            if DEV_COMPILED_UI_USING_ENABLED:
                # RetranslateUi викликається для оновлення всіх рядків UI згідно з новим перекладачем
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        """
        Завантажує інтерфейс користувача.

        Використовує або скомпільований Python-файл UI, або динамічно завантажує .ui файл
        залежно від константи DEV_COMPILED_UI_USING_ENABLED.
        """
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_KeyboardWidget()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/keyboard_widget.ui", self)
            self.ui = cast(Ui_KeyboardWidget, self)

    def _setup_state_variables(self) -> None:
        """Ініціалізує змінні стану та встановлює зворотний виклик для сервісу клавіатури."""
        self.translator = QTranslator()
        # Встановлюємо callback, щоб сервіс міг оновити UI при зміні розкладки ззовні
        self.keyboard_service.set_callback(self.update_ui_silent)

    def _adjust_fields(self) -> None:
        """Синхронізує початковий стан UI з поточним станом сервісу клавіатури."""
        self.update_ui_silent(self.keyboard_service.current_layout)

    def _connect_handlers(self) -> None:
        """Підключає обробники подій для елементів інтерфейсу."""
        self.ui.langComboBox.currentTextChanged.connect(self._on_ui_change)

    def _load_language(self) -> None:
        """
        Завантажує файл перекладу на основі поточних налаштувань.

        Використовує QTranslator для завантаження .qm файлів з теки i18n.
        """
        lang_code = self.settings_service.lang_code

        if lang_code is None:
            return

        QCoreApplication.removeTranslator(self.translator)

        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
        else:
            # Логування помилки завантаження перекладу (можливо, файл відсутній)
            print(f"Помилка: не вдалося завантажити {path}")

    def update_ui_silent(self, layout_code: str) -> None:
        """
        Оновлює обрану мову у ComboBox без виклику подій зміни.

        Це необхідно для запобігання рекурсивних викликів, коли UI оновлюється
        у відповідь на зміну стану сервісу.

        Args:
            layout_code: Код розкладки (наприклад, "UA" або "EN").
        """
        self.ui.langComboBox.blockSignals(True)

        index = self.ui.langComboBox.findText(layout_code)
        if index != -1:
            self.ui.langComboBox.setCurrentIndex(index)

        self.ui.langComboBox.blockSignals(False)

    def _on_ui_change(self, text: str) -> None:
        """
        Обробляє зміну вибору мови користувачем у ComboBox.

        Args:
            text: Новий обраний текст (код розкладки).
        """
        if self.keyboard_service.current_layout != text:
            # Викликаємо перемикання розкладки у сервісі
            self.keyboard_service.toggle_layout()
