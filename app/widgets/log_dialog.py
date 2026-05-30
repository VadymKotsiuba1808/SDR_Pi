from datetime import datetime
from typing import List, Optional, Set, cast

from PyQt6 import uic
from PyQt6.QtCore import QCoreApplication, QEvent, Qt, QTime, QTranslator
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QTableWidgetItem,
    QWidget,
)

from app.core.constants import DEV_COMPILED_UI_USING_ENABLED
from app.models.detection_background import DetectionBackground
from app.models.detection_event import DetectionEvent
from app.models.log_entries import (
    FalseAlarmPayload,
    LogEntry,
    is_detection,
    is_false_alarm,
)
from app.models.object_class import ObjectClass
from app.models.source_type import SourceType
from app.protocols import LangSettings
from app.services.detection_background_service import DetectionBackgroundService
from app.services.log_service import LogService
from app.ui.ui_log_dialog import Ui_LogDialog
from app.utils.convert_measurement_unit import convert_hz_to_mhz
from app.utils.ui_utils import update_element_styles
from app.widgets.static_chart_widget import StaticChartWidget


class LogDialog(QDialog):
    """
    Сторінка логів.
    Відображає історію, графіки та дозволяє фільтрувати події.
    """

    def __init__(
        self,
        log_service: LogService,
        background_service: DetectionBackgroundService,
        classes: List[ObjectClass],
        settings_service: LangSettings,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.log_service = log_service
        self.background_service = background_service
        self.classes = classes
        self.settings_service = settings_service

        self._load_ui()
        self._setup_state_variables()
        self._adjust_fields()
        self._connect_handlers()

        if self.ui.cmbSessions.count() > 0:
            self._on_session_changed()

        self._load_language()
        print("[LogDialog] Initialized.")

    def changeEvent(self, a0: QEvent | None) -> None:
        event = a0
        if event and event.type() == QEvent.Type.LanguageChange:
            if DEV_COMPILED_UI_USING_ENABLED:
                print("[LogDialog] Language change detected, updating UI...")
                self.ui.retranslateUi(self)
        else:
            super().changeEvent(event)

    def _load_ui(self) -> None:
        if DEV_COMPILED_UI_USING_ENABLED:
            self.ui = Ui_LogDialog()
            self.ui.setupUi(self)
        else:
            uic.loadUi("app/ui/log_dialog.ui", self)
            self.ui = cast(Ui_LogDialog, self)

    def _setup_state_variables(self) -> None:
        self.translator = QTranslator()
        self.all_entries: List[LogEntry] = []
        self.filtered_entries: List[LogEntry] = []

        self.current_object_backgrounds: List[DetectionBackground] = []
        self.current_bg_index: int = 0

    def _adjust_fields(self) -> None:
        self._populate_class_cmb()
        self._setup_table_style()
        self._init_charts()
        self._load_sessions_list()

        self.ui.grpBackgroundControl.setVisible(False)

    def _populate_class_cmb(self):
        self.ui.cmbFilterClass.clear()
        self.ui.cmbFilterClass.addItem(self.tr("All"))
        for class_obj in self.classes:
            self.ui.cmbFilterClass.addItem(class_obj.name)
        self.ui.cmbFilterClass.setCurrentIndex(0)

    def _setup_table_style(self) -> None:
        t = self.ui.tableLogs
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setWordWrap(True)
        header = t.horizontalHeader()

        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            t.setColumnWidth(0, 120)
            t.setColumnWidth(1, 120)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            t.setColumnWidth(3, 140)
            t.setColumnWidth(4, 180)
            t.setColumnWidth(5, 150)
            t.setColumnWidth(6, 100)
            t.setColumnWidth(7, 100)

    def _init_charts(self) -> None:
        self.chart_gen = StaticChartWidget(self.settings_service)
        self.ui.layoutChartGen.addWidget(self.chart_gen)

        self.chart_target = StaticChartWidget(self.settings_service)
        self.ui.layoutChartTarget.addWidget(self.chart_target)

        self.chart_sit = StaticChartWidget(self.settings_service)
        self.chart_sit.set_chart_type("radar_snapshot")
        self.ui.layoutChartRadarSit.addWidget(self.chart_sit)

    def _load_sessions_list(self) -> None:
        sessions = self.log_service.get_available_sessions()
        sessions.sort(key=lambda s: s.filename, reverse=True)
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
        self.ui.cmbTargetType.currentIndexChanged.connect(self._update_object_tab)

        self.ui.cmbSituationTime.currentIndexChanged.connect(self._update_situation_tab)
        self.ui.btnSituationPrev.clicked.connect(self._prev_situation)
        self.ui.btnSituationNext.clicked.connect(self._next_situation)

        self.ui.btnBgPrev.clicked.connect(self._prev_background)
        self.ui.btnBgNext.clicked.connect(self._next_background)

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
        class_filter: str | None = None
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
            try:
                dt = datetime.fromisoformat(e.timestamp).time()
                if not (time_start <= dt <= time_end):
                    continue
            except ValueError:
                pass

            if type_idx == 1 and not is_detection(e):
                continue
            if type_idx == 2 and not is_false_alarm(e):
                continue

            if class_filter:
                obj_class = getattr(payload, "object_class", "")
                if class_filter != obj_class.lower():
                    continue

            if name_filter:
                det_id = getattr(payload, "id", getattr(payload, "detection_id", ""))
                name = getattr(payload, "name", "")
                search_text = f"{name} {det_id}".lower()
                if name_filter not in search_text:
                    continue

            if is_detection(e):
                if not (dist_min <= e.payload.distance_km <= dist_max):
                    continue
                if not (angle_min <= e.payload.angle <= angle_max):
                    continue

            res.append(cast(LogEntry, e))

        self.filtered_entries = res
        print(f"[LogDialog] Filter result: {len(res)} entries found.")
        self._populate_ui_with_data()

    def _reset_filters(self) -> None:
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
        self._fill_table(self.filtered_entries)
        self._fill_objects_combo()
        self._fill_times_combo()
        self._on_tab_changed()

    def _get_false_ids(self) -> Set[str]:
        return {
            e.payload.detection_id
            for e in self.all_entries
            if is_false_alarm(e) and hasattr(e.payload, "detection_id")
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

            time_item = QTableWidgetItem(time_str)

            if is_detection(entry):
                d1 = datetime.fromisoformat(entry.payload.timestamp)
                d2 = datetime.fromisoformat(entry.timestamp)
                latency_ms = int((d2 - d1).total_seconds() * 1000)
                time_item.setToolTip(self.tr("Latency: {}ms").format(latency_ms))

            t.setItem(row_idx, 0, time_item)

            if is_detection(entry):
                detection_data: DetectionEvent = entry.payload
                t.setItem(row_idx, 1, QTableWidgetItem(str(detection_data.type)))
                short_id = detection_data.id[:25]
                name_item = QTableWidgetItem(
                    self.tr("{}\nID: {}...").format(detection_data.name, short_id)
                )
                name_item.setToolTip(self.tr("Full ID: {}").format(detection_data.id))
                t.setItem(row_idx, 2, name_item)
                t.setItem(row_idx, 3, QTableWidgetItem(detection_data.object_class))

                formatted_frequency: str
                if detection_data.type == SourceType.RF:
                    formatted_frequency = self.tr("{:.1f} MHz").format(
                        convert_hz_to_mhz(detection_data.frequency_hz)
                    )
                else:
                    formatted_frequency = self.tr("{:.0f} Hz").format(
                        detection_data.frequency_hz
                    )

                t.setItem(
                    row_idx,
                    4,
                    QTableWidgetItem(formatted_frequency),
                )
                t.setItem(
                    row_idx,
                    5,
                    QTableWidgetItem(
                        self.tr("{:.3f}km / {:.0f}°").format(
                            detection_data.distance_km, detection_data.angle
                        )
                    ),
                )

                status_text = (
                    self.tr("NO") if detection_data.id in false_ids else self.tr("YES")
                )
                item_status = QTableWidgetItem(status_text)
                item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if detection_data.id in false_ids:
                    item_status.setForeground(Qt.GlobalColor.yellow)
                t.setItem(row_idx, 6, item_status)

            elif is_false_alarm(entry):
                false_alarm_data: FalseAlarmPayload = entry.payload
                short_id = false_alarm_data.detection_id[:25]
                type_item = QTableWidgetItem(self.tr("FALSE ALARM"))
                type_item.setForeground(Qt.GlobalColor.red)
                type_item.setFont(QFont("Roboto", 10, QFont.Weight.Bold))
                t.setItem(row_idx, 1, type_item)
                ref_item = QTableWidgetItem(
                    self.tr("Ref: {}\nID: {}...").format(
                        false_alarm_data.name, short_id
                    )
                )

                ref_item.setToolTip(
                    self.tr("Full ID: {}").format(false_alarm_data.detection_id)
                )
                t.setItem(row_idx, 2, ref_item)
                for c in range(3, 7):
                    t.setItem(row_idx, c, QTableWidgetItem("-"))

        t.resizeRowsToContents()

    def _fill_objects_combo(self) -> None:
        current_id = self.ui.cmbTargetObject.currentData()
        self.ui.cmbTargetObject.clear()
        seen = set()
        for e in self.filtered_entries:
            if is_detection(e):
                key = (e.payload.id, e.payload.name)
                if key not in seen:
                    seen.add(key)
                    short_id = key[0][:6]
                    self.ui.cmbTargetObject.addItem(f"{key[1]} ({short_id})", key[0])
        if current_id:
            idx = self.ui.cmbTargetObject.findData(current_id)
            if idx >= 0:
                self.ui.cmbTargetObject.setCurrentIndex(idx)

    def _fill_times_combo(self) -> None:
        self.ui.cmbSituationTime.clear()
        timestamps = set()
        for e in self.filtered_entries:
            if is_detection(e):
                try:
                    dt = datetime.fromisoformat(e.timestamp)
                    time_key = dt.strftime("%Y-%m-%d %H:%M")
                    timestamps.add(time_key)
                except ValueError:
                    pass
        sorted_times = sorted(list(timestamps), reverse=False)
        for t in sorted_times:
            self.ui.cmbSituationTime.addItem(t)

    def _on_tab_changed(self) -> None:
        idx = self.ui.tabWidget.currentIndex()
        if idx == 1:
            self._update_general_tab()
        elif idx == 2:
            self._update_object_tab()
        elif idx == 3:
            self._update_situation_tab()

    def _update_general_tab(self) -> None:
        idx = self.ui.cmbChartTypeGeneral.currentIndex()
        t = "timeline" if idx == 0 else "bar"
        self.chart_gen.set_chart_type(t)
        detections = [e.payload for e in self.filtered_entries if is_detection(e)]
        false_ids = self._get_false_ids()
        self.chart_gen.set_data(detections, false_ids)

    def _update_object_tab(self) -> None:
        target_id = self.ui.cmbTargetObject.currentData()

        if not target_id:
            self.chart_target.set_data([])
            self._clear_background_ui()
            self.ui.grpBackgroundControl.setVisible(False)
            return

        types = {0: "path", 1: "signal", 2: "spectrum", 3: "waterfall"}
        idx = self.ui.cmbTargetType.currentIndex()
        t = types.get(idx, "path")
        self.chart_target.set_chart_type(t)

        is_spectral = idx in [2, 3]
        self.ui.grpBackgroundControl.setVisible(is_spectral)

        track_events = [
            e.payload
            for e in self.all_entries
            if is_detection(e) and e.payload.id == target_id
        ]

        if not track_events:
            self.chart_target.set_data([])
            self._clear_background_ui()
            return

        if is_spectral:
            print(f"[LogDialog] Loading backgrounds for object ID: {target_id}")

            self.current_object_backgrounds = (
                self.background_service.get_backgrounds_by_target_id(target_id)
            )

            self.current_object_backgrounds.sort(key=lambda x: x.timestamp)

            self.current_bg_index = 0
            self._update_background_view()
        else:
            self._clear_background_ui()

        false_ids = self._get_false_ids()
        self.chart_target.set_data(track_events, false_ids)

    def _update_background_view(self):
        """Оновлює UI контролів фону та передає фон у графік"""
        count = len(self.current_object_backgrounds)

        if count == 0:
            self.ui.lblBgInfo.setText(self.tr("There is no background"))
            self.ui.btnBgPrev.setEnabled(False)
            self.ui.btnBgNext.setEnabled(False)
            if hasattr(self.chart_target, "set_background"):
                self.chart_target.set_background(None)
            return

        if self.current_bg_index >= count:
            self.current_bg_index = count - 1
        if self.current_bg_index < 0:
            self.current_bg_index = 0

        bg_item = self.current_object_backgrounds[self.current_bg_index]

        try:
            dt = datetime.fromisoformat(bg_item.timestamp)
            time_str = dt.strftime("%H:%M:%S")
        except ValueError:
            time_str = "???"

        self.ui.lblBgInfo.setText(
            self.tr("Background {} of {} ({})").format(
                (self.current_bg_index + 1), count, time_str
            )
        )

        self.ui.btnBgPrev.setEnabled(self.current_bg_index > 0)
        self.ui.btnBgNext.setEnabled(self.current_bg_index < count - 1)

        update_element_styles(self.ui.btnBgPrev)
        update_element_styles(self.ui.btnBgNext)

        if hasattr(self.chart_target, "set_background"):
            self.chart_target.set_background(bg_item.spectral_data)

    def _prev_background(self):
        if self.current_object_backgrounds:
            self.current_bg_index -= 1
            self._update_background_view()

    def _next_background(self):
        if self.current_object_backgrounds:
            self.current_bg_index += 1
            self._update_background_view()

    def _clear_background_ui(self):
        self.current_object_backgrounds = []

        self._update_background_view()

    def _update_situation_tab(self) -> None:
        cmb = self.ui.cmbSituationTime
        time_str = cmb.currentText()
        self._update_situation_nav_buttons()

        if not time_str:
            self.chart_sit.set_data([])
            return

        try:
            sel_dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return

        active_objects: List[DetectionEvent] = []
        for e in self.all_entries:
            if not is_detection(e):
                continue
            try:
                dt = datetime.fromisoformat(e.timestamp)
            except ValueError:
                continue

            if (
                dt.year == sel_dt.year
                and dt.month == sel_dt.month
                and dt.day == sel_dt.day
                and dt.hour == sel_dt.hour
                and dt.minute == sel_dt.minute
            ):
                active_objects.append(e.payload)

        false_ids = self._get_false_ids()
        self.chart_sit.set_data(active_objects, false_ids)

    def _update_situation_nav_buttons(self) -> None:
        cmb = self.ui.cmbSituationTime
        btn_prev = self.ui.btnSituationPrev
        btn_next = self.ui.btnSituationNext
        index = cmb.currentIndex()
        count = cmb.count()
        btn_prev.setEnabled(index > 0)
        btn_next.setEnabled(index < count - 1)
        update_element_styles(btn_prev)
        update_element_styles(btn_next)

    def _prev_situation(self):
        self._change_situation_index(-1)

    def _next_situation(self):
        self._change_situation_index(1)

    def _change_situation_index(self, step: int):
        cmb = self.ui.cmbSituationTime
        count = cmb.count()
        current = cmb.currentIndex()
        new_index = current + step
        if 0 <= new_index < count:
            cmb.setCurrentIndex(new_index)
            self._update_situation_nav_buttons()
