# Генерація та Компоненти UI

Цей розділ містить інформацію про низькорівневі компоненти графічного інтерфейсу, включаючи кастомні рендерери для графіків та класи, згенеровані з `.ui` файлів.

---

## UI Renderers (app.ui.components)

Ці класи відповідають за безпосередню відмальовку даних на графіках та радарі.

### StandardChartRenderer
::: app.ui.components.standard_chart_renderer

### SpectralRenderer
::: app.ui.components.spectral_renderer

### RadarRenderer
::: app.ui.components.radar_renderer

### ChartCrosshair
::: app.ui.components.chart_crosshair

---

## Згенеровані класи (app.ui)

Ці модулі автоматично згенеровані інструментом `pyside6-uic` на основі XML-файлів дизайну. Вони визначають ієрархію віджетів, назви кнопок, полів вводу та лейаутів.

### MainWindow UI
::: app.ui.ui_main_window

### LogDialog UI
::: app.ui.ui_log_dialog

### SettingsDialog UI
::: app.ui.ui_settings_dialog

### ObjectManagerDialog UI
::: app.ui.ui_object_manager_dialog

### ObjectEditorDialog UI
::: app.ui.ui_object_editor_dialog

### ClassManagerDialog UI
::: app.ui.ui_class_manager_dialog

### LoginDialog UI
::: app.ui.ui_login_dialog

### ChangePwdDialog UI
::: app.ui.ui_change_pwd_dialog

### SetMapDialog UI
::: app.ui.ui_set_map_dialog

### ChartMonitorDialog UI
::: app.ui.ui_chart_monitor_dialog

### KeyboardWidget UI
::: app.ui.ui_keyboard_widget

### RecordStatusWidget UI
::: app.ui.ui_record_status_widget
