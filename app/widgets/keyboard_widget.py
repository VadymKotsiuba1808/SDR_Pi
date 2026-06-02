from typing import cast

from PyQt6 import uic
from PyQt6.QtCore import QCoreApplication, QEvent, QTranslator
from PyQt6.QtWidgets import QWidget

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED
from app.core.logging_config import get_logger
from app.protocols import LangSettings
from app.services.keyboard_service import KeyboardService
from app.ui.ui_keyboard_widget import Ui_KeyboardWidget

logger = get_logger(__name__)


class KeyboardWidget(QWidget):
    """
    Віджет для відображення та зміни поточної розкладки клавіатури.

    Інтегрується з `KeyboardService` для синхронізації стану розкладки між
    GUI та системними налаштуваннями. Обробляє зміну мови інтерфейсу.
    """

    def __init__(
        self,
        settings: LangSettings,
        keyboard_service: KeyboardService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.settings_service = settings
        self.keyboard_service = keyboard_service

        self._load_ui()
        self._setup_state_variables()
        self._adjust_fields()
        self._connect_handlers()
        self._load_language()

    def changeEvent(self, a0: QEvent | None) -> None:
        event = a0
        if event and event.type() == QEvent.Type.LanguageChange:
            if DEV_COMPILED_UI_USING_ENABLED:
                # Оновлення всіх рядків UI згідно з новим перекладачем
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        """Завантажує інтерфейс користувача (динамічно або скомпільований)."""
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_KeyboardWidget()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/keyboard_widget.ui", self)
            self.ui = cast(Ui_KeyboardWidget, self)

    def _setup_state_variables(self) -> None:
        """Ініціалізує змінні стану та встановлює callback для сервісу."""
        self.translator = QTranslator()
        self.keyboard_service.set_callback(self.update_ui_silent)

    def _adjust_fields(self) -> None:
        """Синхронізує початковий стан UI з поточним станом сервісу."""
        self.update_ui_silent(self.keyboard_service.current_layout)

    def _connect_handlers(self) -> None:
        """Підключає обробники подій для елементів інтерфейсу."""
        self.ui.langComboBox.currentTextChanged.connect(self._on_ui_change)

    def _load_language(self) -> None:
        """Завантажує файл перекладу на основі поточних налаштувань."""
        lang_code = self.settings_service.lang_code

        if lang_code is None:
            return

        QCoreApplication.removeTranslator(self.translator)

        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
        else:
            logger.error(f"Не вдалося завантажити файл перекладу: {path}")

    def update_ui_silent(self, layout_code: str) -> None:
        """Оновлює мову у ComboBox без виклику сигналів."""
        self.ui.langComboBox.blockSignals(True)

        index = self.ui.langComboBox.findText(layout_code)
        if index != -1:
            self.ui.langComboBox.setCurrentIndex(index)

        self.ui.langComboBox.blockSignals(False)

    def _on_ui_change(self, text: str) -> None:
        if self.keyboard_service.current_layout != text:
            self.keyboard_service.toggle_layout()
