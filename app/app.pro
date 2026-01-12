# ----------------------------------------------------
# Конфігурація для перекладу SDR_Pi
# ----------------------------------------------------

# 1. Python-код
SOURCES +=  main.py \
            widgets/*.py \
            services/*.py \
            core/*.py \
            ui/*.py \
            utils/*.py \
            validators/*.py

# UI-файли (Qt Designer)
FORMS +=    ui/*.ui

# Файли перекладу
TRANSLATIONS += i18n/app_uk.ts \
                i18n/app_en.ts