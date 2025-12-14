from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, QTime, QEvent, QCoreApplication
from PyQt6 import uic
from PyQt6.QtGui import QFont, QColor

from app.protocols import LogDialogSettings
from app.ui.ui_log_dialog import Ui_LogDialog
from app.widgets.chart_widget import LogChartWidget
from app.models.log_entries import LogEntry
from app.services.log_service import LogService


class LogDialog(QDialog):
    """
    Сторінка логів.
    Відображає історію, графіки та дозволяє фільтрувати події.
    """

    def __init__(self, settings_service: LogDialogSettings, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.settings_service = settings_service

        self._load_ui()

        self._setup_state_variables()

        self._setup_table_style()
        self._init_charts()

        self._load_sessions_list()
        self._connect_handlers()

        if self.ui.cmbSessions.count() > 0:
            self._on_session_changed()

        self._load_language()

    def changeEvent(self, event: QEvent):
        if event.type() == QEvent.Type.LanguageChange:
            if self.settings_service.compiled_ui_using_enabled:
                print("Зміна мови, оновлюю UI...")
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self):
        if self.settings_service.compiled_ui_using_enabled:
            self.ui = Ui_LogDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/log_dialog.ui", self)
            self.ui = self

    def _setup_state_variables(self):
        self.service = LogService()
        self.all_entries: list[LogEntry] = []
        self.filtered_entries: list[LogEntry] = []

    def _setup_table_style(self):
        """Налаштування вигляду таблиці."""
        t = self.ui.tableLogs
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setWordWrap(True)

        header = t.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        t.setColumnWidth(0, 120)
        t.setColumnWidth(1, 120)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        t.setColumnWidth(3, 140)
        t.setColumnWidth(4, 140)
        t.setColumnWidth(5, 150)
        t.setColumnWidth(6, 100)

    def _init_charts(self):
        """Ініціалізація віджетів графіків для кожної вкладки."""
        # 1. Загальний графік (Timeline/Bar)
        self.chart_gen = LogChartWidget(self.settings_service)
        self.ui.layoutChartGen.addWidget(self.chart_gen)

        # 2. Графіки по об'єкту (Path + Signal)
        self.chart_path = LogChartWidget(self.settings_service)
        self.chart_path.set_chart_type("path")
        self.ui.layoutChartPath.addWidget(self.chart_path)

        self.chart_signal = LogChartWidget(self.settings_service)
        self.chart_signal.set_chart_type("signal")
        self.ui.layoutChartSignal.addWidget(self.chart_signal)

        # 3. Радар ситуації
        self.chart_sit = LogChartWidget(self.settings_service)
        self.chart_sit.set_chart_type("radar_snapshot")
        self.ui.layoutChartRadarSit.addWidget(self.chart_sit)

    def _load_sessions_list(self):
        """Заповнення списку доступних файлів логів."""
        sessions = self.service.get_available_sessions()
        for s in sessions:
            self.ui.cmbSessions.addItem(s["label"], s["filename"])

    def _connect_handlers(self):
        self.ui.btnClose.clicked.connect(self.accept)

        self.ui.cmbSessions.currentIndexChanged.connect(self._on_session_changed)

        self.ui.btnApplyFilters.clicked.connect(self._apply_filters)
        self.ui.btnResetFilters.clicked.connect(self._reset_filters)

        self.ui.tabWidget.currentChanged.connect(self._on_tab_changed)
        self.ui.cmbChartTypeGeneral.currentIndexChanged.connect(
            self._update_general_tab
        )
        self.ui.cmbTargetObject.currentIndexChanged.connect(self._update_object_tab)
        self.ui.cmbSituationTime.currentIndexChanged.connect(self._update_situation_tab)

    def _load_language(self):
        lang_code = self.settings_service.lang_code

        if lang_code == None:
            return

        QCoreApplication.removeTranslator(self.translator)

        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
        else:
            print(f"Помилка: не вдалося завантажити {path}")

    def _on_session_changed(self):
        fname = self.ui.cmbSessions.currentData()
        if fname:
            print(f"[Logs] Loading session: {fname}")
            self.all_entries = self.service.load_session_data(fname)

            if self.all_entries:
                try:
                    times = [
                        datetime.fromisoformat(e.timestamp) for e in self.all_entries
                    ]
                    min_time = min(times).time()
                    max_time = max(times).time()
                    self.ui.inpTimeStart.setTime(min_time)
                    self.ui.inpTimeEnd.setTime(max_time)
                except ValueError:
                    pass

            self._apply_filters()

    def _apply_filters(self):
        """Логіка фільтрації записів."""
        name_filter = self.ui.inpFilterName.text().lower()
        type_idx = self.ui.cmbFilterType.currentIndex()  # 0=All, 1=Det, 2=False

        dist_min = self.ui.inpDistMin.value()
        dist_max = self.ui.inpDistMax.value()
        angle_min = self.ui.inpAngleMin.value()
        angle_max = self.ui.inpAngleMax.value()

        time_start = self.ui.inpTimeStart.time()
        time_end = self.ui.inpTimeEnd.time()

        res = []
        for e in self.all_entries:
            payload = e.payload

            try:
                dt = datetime.fromisoformat(e.timestamp).time()
                if not (time_start <= dt <= time_end):
                    continue
            except ValueError:
                pass

            if type_idx == 1 and not e.is_detection:
                continue
            if type_idx == 2 and not e.is_false_alarm:
                continue

            if name_filter:
                det_id = getattr(payload, "id", getattr(payload, "detection_id", ""))
                obj_class = getattr(payload, "object_class", "")
                search_text = f"{payload.name} {det_id} {obj_class}".lower()

                if name_filter not in search_text:
                    continue

            if e.is_detection:
                if not (dist_min <= payload.distance <= dist_max):
                    continue
                if not (angle_min <= payload.angle <= angle_max):
                    continue

            res.append(e)

        self.filtered_entries = res
        self._populate_ui_with_data()

    def _reset_filters(self):
        """Скидання фільтрів до значень за замовчуванням."""
        self.ui.inpFilterName.clear()
        self.ui.cmbFilterType.setCurrentIndex(0)
        self.ui.inpDistMin.setValue(0)
        self.ui.inpDistMax.setValue(50000)
        self.ui.inpAngleMin.setValue(0)
        self.ui.inpAngleMax.setValue(360)

        self.ui.inpTimeStart.setTime(QTime(0, 0))
        self.ui.inpTimeEnd.setTime(QTime(23, 59))

        self._apply_filters()

    def _populate_ui_with_data(self):
        """Оновлення всіх елементів UI на основі filtered_entries."""
        # 1. Таблиця
        self._fill_table(self.filtered_entries)

        # 2. Комбобокси
        self._fill_objects_combo()
        self._fill_times_combo()

        # 3. Активна вкладка графіків
        self._on_tab_changed()

    def _fill_table(self, entries: list[LogEntry]):
        """Заповнення таблиці даними."""
        t = self.ui.tableLogs
        t.setRowCount(0)

        sorted_entries = sorted(entries, key=lambda x: x.timestamp, reverse=True)

        false_ids = {
            e.payload.detection_id for e in self.all_entries if e.is_false_alarm
        }

        for entry in sorted_entries:
            row_idx = t.rowCount()
            t.insertRow(row_idx)

            try:
                dt = datetime.fromisoformat(entry.timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except ValueError:
                time_str = entry.timestamp

            t.setItem(row_idx, 0, QTableWidgetItem(time_str))

            if entry.is_detection:
                data = entry.payload
                t.setItem(row_idx, 1, QTableWidgetItem(data.type))

                # Назва + ID
                short_id = data.id[:16]
                name_item = QTableWidgetItem(f"{data.name}\nID: {short_id}...")
                name_item.setToolTip(f"Full ID: {data.id}")
                t.setItem(row_idx, 2, name_item)

                t.setItem(row_idx, 3, QTableWidgetItem(data.object_class))
                t.setItem(row_idx, 4, QTableWidgetItem(f"{data.frequency:.1f}"))
                t.setItem(
                    row_idx,
                    5,
                    QTableWidgetItem(f"{data.distance}m / {data.angle:.0f}°"),
                )

                status_text = "Ні" if data.id in false_ids else "Так"
                item_status = QTableWidgetItem(status_text)
                item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if data.id in false_ids:
                    item_status.setForeground(Qt.GlobalColor.yellow)
                t.setItem(row_idx, 6, item_status)

            elif entry.is_false_alarm:
                data = entry.payload

                type_item = QTableWidgetItem("FALSE ALARM")
                type_item.setForeground(Qt.GlobalColor.red)
                type_item.setFont(QFont("Roboto", 10, QFont.Weight.Bold))
                t.setItem(row_idx, 1, type_item)

                t.setItem(row_idx, 2, QTableWidgetItem(f"Ref: {data.name}"))
                t.setItem(row_idx, 3, QTableWidgetItem("-"))
                t.setItem(row_idx, 4, QTableWidgetItem("-"))
                t.setItem(row_idx, 5, QTableWidgetItem("-"))
                t.setItem(row_idx, 6, QTableWidgetItem("Marked by user"))

        t.resizeRowsToContents()

    def _fill_objects_combo(self):
        """Оновлює список унікальних об'єктів у фільтрах."""
        current_id = self.ui.cmbTargetObject.currentData()
        self.ui.cmbTargetObject.clear()

        seen = set()
        for e in self.filtered_entries:
            if e.is_detection:
                key = (e.payload.id, e.payload.name)
                if key not in seen:
                    seen.add(key)
                    self.ui.cmbTargetObject.addItem(f"{key[1]} ({key[0][:6]})", key[0])

        if current_id:
            idx = self.ui.cmbTargetObject.findData(current_id)
            if idx >= 0:
                self.ui.cmbTargetObject.setCurrentIndex(idx)

    def _fill_times_combo(self):
        """Оновлює список часових точок для 'ситуації'."""
        self.ui.cmbSituationTime.clear()
        timestamps = set()

        for e in self.filtered_entries:
            if e.is_detection:
                try:
                    dt = datetime.fromisoformat(e.timestamp)
                    time_key = dt.strftime("%Y-%m-%d %H:%M")
                    timestamps.add(time_key)
                except ValueError:
                    pass

        sorted_times = sorted(list(timestamps), reverse=True)
        for t in sorted_times:
            self.ui.cmbSituationTime.addItem(t)

    def _on_tab_changed(self):
        """Викликається при зміні вкладки для оновлення відповідного графіка."""
        idx = self.ui.tabWidget.currentIndex()
        if idx == 0:
            self._update_general_tab()
        elif idx == 1:
            self._update_general_tab()
        elif idx == 2:
            self._update_object_tab()
        elif idx == 3:
            self._update_situation_tab()

    def _update_general_tab(self):
        idx = self.ui.cmbChartTypeGeneral.currentIndex()
        t = "timeline"
        if idx == 1:
            t = "bar"

        self.chart_gen.set_chart_type(t)

        detections = [e.payload for e in self.filtered_entries if e.is_detection]
        false_ids = {
            e.payload.detection_id for e in self.all_entries if e.is_false_alarm
        }

        self.chart_gen.set_data(detections, false_ids)

    def _update_object_tab(self):
        target_id = self.ui.cmbTargetObject.currentData()
        if not target_id:
            self.chart_path.set_data([])
            self.chart_signal.set_data([])
            return

        obj_data = [
            e.payload
            for e in self.all_entries
            if e.is_detection and e.payload.id == target_id
        ]

        self.chart_path.set_data(obj_data)
        self.chart_signal.set_data(obj_data)

    def _update_situation_tab(self):
        time_str = self.ui.cmbSituationTime.currentText()
        if not time_str:
            self.chart_sit.set_data([])
            return

        try:
            sel_dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return

        active_objects = []
        for e in self.all_entries:
            if e.is_detection:
                try:
                    dt = datetime.fromisoformat(e.timestamp)
                    if (
                        dt.year == sel_dt.year
                        and dt.month == sel_dt.month
                        and dt.day == sel_dt.day
                        and dt.hour == sel_dt.hour
                        and dt.minute == sel_dt.minute
                    ):
                        active_objects.append(e.payload)
                except ValueError:
                    pass

        false_ids = {
            e.payload.detection_id for e in self.all_entries if e.is_false_alarm
        }
        self.chart_sit.set_data(active_objects, false_ids)
