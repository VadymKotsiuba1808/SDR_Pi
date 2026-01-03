from datetime import datetime
from typing import List, Set, Optional

from PyQt6.QtWidgets import (
    QDialog,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QWidget,
)
from PyQt6.QtCore import Qt, QTime, QEvent, QCoreApplication, QTranslator
from PyQt6 import uic
from PyQt6.QtGui import QFont, QColor

from app.protocols import LogDialogSettings
from app.ui.ui_log_dialog import Ui_LogDialog
from app.widgets.chart_widget import ChartWidget
from app.models.log_entries import LogEntry
from app.models.detection_event import DetectionEvent, DetectionType
from app.models.object_class import ObjectClass
from app.services.log_service import LogService


class LogDialog(QDialog):
    """
    Сторінка логів.
    Відображає історію, графіки та дозволяє фільтрувати події.
    """

    def __init__(
        self,
        log_service: LogService,
        classes: List[ObjectClass],
        settings_service: LogDialogSettings,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.log_service = log_service
        self.classes = classes
        self.settings_service = settings_service

        self._load_ui()
        self._setup_state_variables()
        self._adjust_fields()
        self._load_sessions_list()
        self._connect_handlers()

        if self.ui.cmbSessions.count() > 0:
            self._on_session_changed()

        self._load_language()
        print("[LogDialog] Initialized.")

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            if self.settings_service.compiled_ui_using_enabled:
                print("[LogDialog] Language change detected, updating UI...")
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        if self.settings_service.compiled_ui_using_enabled:
            self.ui = Ui_LogDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/log_dialog.ui", self)
            self.ui = self

    def _setup_state_variables(self) -> None:
        self.translator = QTranslator()
        self.all_entries: List[LogEntry] = []
        self.filtered_entries: List[LogEntry] = []

    def _adjust_fields(self) -> None:
        self._populate_class_cmb()
        self._setup_table_style()
        self._init_charts()
        self._load_sessions_list()

    def _populate_class_cmb(self):
        self.ui.cmbFilterClass.clear()
        self.ui.cmbFilterClass.addItem("Всі")

        for class_obj in self.classes:
            self.ui.cmbFilterClass.addItem(class_obj.name)

        self.ui.cmbFilterClass.setCurrentIndex(0)

    def _setup_table_style(self) -> None:
        """Налаштування вигляду таблиці."""
        t = self.ui.tableLogs
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setWordWrap(True)

        header = t.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        t.setColumnWidth(0, 120)  # Time
        t.setColumnWidth(1, 120)  # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Name/ID
        t.setColumnWidth(3, 140)  # Class
        t.setColumnWidth(4, 180)  # Freq
        t.setColumnWidth(5, 150)  # Dist/Angle
        t.setColumnWidth(6, 100)  # Status

    def _init_charts(self) -> None:
        """Ініціалізація віджетів графіків для кожної вкладки."""
        self.chart_gen = ChartWidget(self.settings_service)
        self.ui.layoutChartGen.addWidget(self.chart_gen)

        self.chart_path = ChartWidget(self.settings_service)
        self.chart_path.set_chart_type("path")
        self.ui.layoutChartPath.addWidget(self.chart_path)

        self.chart_signal = ChartWidget(self.settings_service)
        self.chart_signal.set_chart_type("signal")
        self.ui.layoutChartSignal.addWidget(self.chart_signal)

        self.chart_sit = ChartWidget(self.settings_service)
        self.chart_sit.set_chart_type("radar_snapshot")
        self.ui.layoutChartRadarSit.addWidget(self.chart_sit)

    def _load_sessions_list(self) -> None:
        sessions = self.log_service.get_available_sessions()
        print(f"[LogDialog] Found {len(sessions)} available sessions.")

        self.ui.cmbSessions.clear()
        for s in sessions:
            self.ui.cmbSessions.addItem(s.label, s.filename)

    def _connect_handlers(self) -> None:
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

    def _load_language(self) -> None:
        lang_code = self.settings_service.lang_code
        if lang_code is None:
            return

        QCoreApplication.removeTranslator(self.translator)
        path = f"app/i18n/qm/app_{lang_code}.qm"
        if self.translator.load(path):
            QCoreApplication.installTranslator(self.translator)
        else:
            print(f"[LogDialog] Error: Failed to load translation file: {path}")

    def _on_session_changed(self) -> None:
        fname = self.ui.cmbSessions.currentData()
        if fname:
            print(f"[LogDialog] Loading session data form file: {fname}")
            self.all_entries = self.log_service.load_session_data(fname)

            if self.all_entries:
                try:
                    times = [
                        datetime.fromisoformat(e.timestamp) for e in self.all_entries
                    ]
                    if times:
                        min_time = min(times).time()
                        max_time = max(times).time()
                        self.ui.inpTimeStart.setTime(min_time)
                        self.ui.inpTimeEnd.setTime(max_time)
                except ValueError:
                    pass

            self._apply_filters()

    def _apply_filters(self) -> None:
        print("[LogDialog] Applying filters...")

        name_filter = self.ui.inpFilterName.text().lower()

        class_filter: str = None
        if self.ui.cmbFilterClass.currentIndex() != 0:
            class_filter = self.ui.cmbFilterClass.currentText().lower()

        type_idx = self.ui.cmbFilterType.currentIndex()

        dist_min = self.ui.inpDistMin.value()
        dist_max = self.ui.inpDistMax.value()
        angle_min = self.ui.inpAngleMin.value()
        angle_max = self.ui.inpAngleMax.value()

        time_start = self.ui.inpTimeStart.time()
        time_end = self.ui.inpTimeEnd.time()

        res: List[LogEntry] = []

        for e in self.all_entries:
            payload = e.payload

            # 1. Time Filter
            try:
                dt = datetime.fromisoformat(e.timestamp).time()
                if not (time_start <= dt <= time_end):
                    continue
            except ValueError:
                pass

            # 2. Type Filter
            if type_idx == 1 and not e.is_detection:
                continue
            if type_idx == 2 and not e.is_false_alarm:
                continue

            # 3. Class Filter
            if class_filter:
                obj_class = getattr(payload, "object_class", "")

                if class_filter != obj_class.lower():
                    continue

            # 4. Text Search (Name, ID, Class)
            if name_filter:
                det_id = getattr(payload, "id", getattr(payload, "detection_id", ""))
                name = getattr(payload, "name", "")

                search_text = f"{name} {det_id}".lower()

                if name_filter not in search_text:
                    continue

            # 5. Numeric Filters (Only for detections)
            if e.is_detection:
                if not (dist_min <= payload.distance <= dist_max):
                    continue
                if not (angle_min <= payload.angle <= angle_max):
                    continue

            res.append(e)

        self.filtered_entries = res
        print(f"[LogDialog] Filter result: {len(res)} entries found.")

        self._populate_ui_with_data()

    def _reset_filters(self) -> None:
        print("[LogDialog] Resetting filters.")
        self.ui.inpFilterName.clear()
        self.ui.cmbFilterType.setCurrentIndex(0)
        self.ui.cmbFilterClass.setCurrentIndex(0)
        self.ui.inpDistMin.setValue(0)
        self.ui.inpDistMax.setValue(5000)
        self.ui.inpAngleMin.setValue(0)
        self.ui.inpAngleMax.setValue(360)

        self.ui.inpTimeStart.setTime(QTime(0, 0))
        self.ui.inpTimeEnd.setTime(QTime(23, 59))

        self._apply_filters()

    def _populate_ui_with_data(self) -> None:
        """Оновлення всіх елементів UI на основі filtered_entries."""
        self._fill_table(self.filtered_entries)
        self._fill_objects_combo()
        self._fill_times_combo()

        self._on_tab_changed()

    def _get_false_ids(self) -> Set[str]:
        return {
            e.payload.detection_id
            for e in self.all_entries
            if e.is_false_alarm and hasattr(e.payload, "detection_id")
        }

    def _fill_table(self, entries: List[LogEntry]) -> None:
        t = self.ui.tableLogs
        t.setRowCount(0)

        sorted_entries = sorted(entries, key=lambda x: x.timestamp, reverse=True)
        false_ids = self._get_false_ids()

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
                data: DetectionEvent = entry.payload
                t.setItem(row_idx, 1, QTableWidgetItem(data.type))

                short_id = data.id[:8]
                name_item = QTableWidgetItem(f"{data.name}\nID: {short_id}...")
                name_item.setToolTip(f"Full ID: {data.id}")
                t.setItem(row_idx, 2, name_item)

                t.setItem(row_idx, 3, QTableWidgetItem(data.object_class))
                formatted_frequency: str
                if data.type == DetectionType.RF:
                    formatted_frequency = f"{(data.frequency / 1_000_000_000):.3f} GHz"
                else:
                    formatted_frequency = f"{(data.frequency):.0f} Hz"
                t.setItem(
                    row_idx,
                    4,
                    QTableWidgetItem(formatted_frequency),
                )
                t.setItem(
                    row_idx,
                    5,
                    QTableWidgetItem(f"{data.distance}km / {data.angle:.0f}°"),
                )

                status_text = "False" if data.id in false_ids else "True"
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
                t.setItem(row_idx, 6, QTableWidgetItem("-"))

        t.resizeRowsToContents()

    def _fill_objects_combo(self) -> None:
        """Оновлює список унікальних об'єктів у фільтрах."""
        current_id = self.ui.cmbTargetObject.currentData()
        self.ui.cmbTargetObject.clear()

        seen = set()
        for e in self.filtered_entries:
            if e.is_detection:
                key = (e.payload.id, e.payload.name)
                if key not in seen:
                    seen.add(key)
                    # key[0] is ID (str), key[1] is Name
                    short_id = key[0][:6]
                    self.ui.cmbTargetObject.addItem(f"{key[1]} ({short_id})", key[0])

        if current_id:
            idx = self.ui.cmbTargetObject.findData(current_id)
            if idx >= 0:
                self.ui.cmbTargetObject.setCurrentIndex(idx)

    def _fill_times_combo(self) -> None:
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

    def _on_tab_changed(self) -> None:
        idx = self.ui.tabWidget.currentIndex()
        if idx == 0:
            pass
            # self._update_general_tab()
        elif idx == 1:
            self._update_general_tab()
        elif idx == 2:
            self._update_object_tab()
        elif idx == 3:
            self._update_situation_tab()

    def _update_general_tab(self) -> None:
        idx = self.ui.cmbChartTypeGeneral.currentIndex()
        t = "timeline"
        if idx == 1:
            t = "bar"

        self.chart_gen.set_chart_type(t)

        detections = [e.payload for e in self.filtered_entries if e.is_detection]
        false_ids = self._get_false_ids()

        self.chart_gen.set_data(detections, false_ids)

    def _update_object_tab(self) -> None:
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

        false_ids = self._get_false_ids()

        self.chart_path.set_data(obj_data, false_ids)
        self.chart_signal.set_data(obj_data, false_ids)

    def _update_situation_tab(self) -> None:
        time_str = self.ui.cmbSituationTime.currentText()
        if not time_str:
            self.chart_sit.set_data([])
            return

        try:
            sel_dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return

        active_objects: List[DetectionEvent] = []

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

        false_ids = self._get_false_ids()
        self.chart_sit.set_data(active_objects, false_ids)
