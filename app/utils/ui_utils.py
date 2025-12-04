"""
UI Утиліти.
Загальні функції для маніпуляцій з віджетами.
"""


def update_element_styles(element):
    element.style().unpolish(element)
    element.style().polish(element)
    element.update()
