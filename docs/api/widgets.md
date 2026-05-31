# Віджети та Графічний Інтерфейс (Widgets)

Цей розділ описує основні візуальні компоненти додатка, розроблені на базі PyQt6. Кожен віджет інкапсулює власну логіку відображення та взаємодії з користувачем.

---

## MainWindow
Головне вікно системи, що об'єднує всі компоненти моніторингу та керування.

::: app.widgets.main_window

---

## DynamicChartWidget
Спеціалізований віджет для відмальовки радіоспектрів та водоспадів у реальному часі.

::: app.widgets.dynamic_chart_widget

---

## StaticChartWidget
Віджет для перегляду та аналізу історичних даних або сигнатур.

::: app.widgets.static_chart_widget

---

## LogDialog
Діалогове вікно перегляду та фільтрації журналів подій.

::: app.widgets.log_dialog

---

## LoginDialog
Вікно автентифікації користувача.

::: app.widgets.login_dialog

---

## SettingsDialog
Централізоване вікно налаштувань конфігурації додатка.

::: app.widgets.settings_dialog

---

## ObjectManagerDialog / ClassManagerDialog
Інструменти для керування базою даних об'єктів та їхніх сигнатур.

::: app.widgets.object_manager_dialog
::: app.widgets.class_manager_dialog

---

## MapView (Logic Integration)
Хоча мапа використовує сторонні бібліотеки, її інтеграція з UI описана тут.

::: app.widgets.set_map_dialog
