# Файл конфігурації проекту Qt.
# Використовується утилітою lupdate для сканування Python-файлів та генерації файлів перекладу (.ts). Містить шляхи до всіх джерел.

#.py файли віджетів
SOURCES = main.py widgets/main_window.py widgets/login_dialog.py  widgets/change_pwd_dialog.py  widgets/set_map_dialog.py  widgets/record_status_widget.py

#.ui файли
FORMS = ui/main_window.ui ui/login_dialog.ui  ui/change_pwd_dialog.ui  ui/set_map_dialog.ui  ui/record_status_widget.ui

#.ts файли перекладів
TRANSLATIONS = i18n/app_uk.ts i18n/app_en.ts