from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any, Optional, Union

from app.core.mixins import TranslatorMixin


class DbOperation(str, Enum):
    """
    ### Перелік усіх можливих операцій з базою даних

    Використовується для ідентифікації типу запиту між клієнтом та сервером.
    Це дозволяє GUI коректно обробляти результати різних дій (додавання, видалення тощо).
    """

    # Objects
    ADD_OBJECT = "add_object"
    UPDATE_OBJECT = "update_object"
    DELETE_OBJECT = "delete_object"
    GET_OBJECTS_PAGE = "get_objects_page"
    GET_ALL_OBJECTS = "get_all_objects"

    # Classes
    ADD_CLASS = "add_class"
    UPDATE_CLASS = "update_class"
    DELETE_CLASS = "delete_class"
    GET_CLASSES = "get_classes"
    RENAME_CLASS = "rename_class"

    # Errors/System
    UNKNOWN = "unknown"


class StatusCode(IntEnum):
    """
    ### Стандартні коди статусів відповідей сервісів

    Наслідують логіку HTTP статус-кодів для забезпечення одноманітності
    обробки відповідей як на рівні мережі, так і всередині бізнес-логіки.
    """

    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    NOT_FOUND = 404
    CONFLICT = 409
    INTERNAL_ERROR = 500


class StatusMessage(TranslatorMixin):
    """
    ### Стандартні повідомлення для кодів статусів

    Підтримує локалізацію через `TranslatorMixin`.
    """

    @classmethod
    def get(cls, code: int) -> str:
        """Отримує локалізоване повідомлення для конкретного коду статусу."""
        if code == StatusCode.OK:
            return cls.tr_s("Operation successful.")
        elif code == StatusCode.CREATED:
            return cls.tr_s("Successfully created.")
        elif code == StatusCode.BAD_REQUEST:
            return cls.tr_s("Invalid data. Please check input fields.")
        elif code == StatusCode.NOT_FOUND:
            return cls.tr_s("Object not found.")
        elif code == StatusCode.CONFLICT:
            return cls.tr_s("Data conflict. Item might already exist or used.")
        elif code == StatusCode.INTERNAL_ERROR:
            return cls.tr_s("Internal server error.")

        return cls.tr_s("Unknown error.")


class OperationTitle(TranslatorMixin):
    """
    ### Утиліта для отримання локалізованих заголовків операцій

    Забезпечує консистентність заголовків діалогових вікон та повідомлень про помилки
    у всьому додатку.
    """

    @classmethod
    def get_error(cls, op: Union[DbOperation, str]) -> str:
        """Повертає заголовок помилки для вказаної операції."""
        match op:
            case DbOperation.ADD_OBJECT:
                return cls.tr_s("Error adding object")
            case DbOperation.UPDATE_OBJECT:
                return cls.tr_s("Error updating object")
            case DbOperation.DELETE_OBJECT:
                return cls.tr_s("Error deleting object")
            case DbOperation.GET_OBJECTS_PAGE:
                return cls.tr_s("Error loading list")

            case DbOperation.ADD_CLASS:
                return cls.tr_s("Error creating class")
            case DbOperation.UPDATE_CLASS:
                return cls.tr_s("Error updating class")
            case DbOperation.RENAME_CLASS:
                return cls.tr_s("Error renaming class")
            case DbOperation.DELETE_CLASS:
                return cls.tr_s("Error deleting class")

            case _:
                return cls.tr_s("System Error")

    @classmethod
    def get_success(cls, op: Union[DbOperation, str]) -> str:
        """Повертає заголовок успіху для вказаної операції."""
        match op:
            case DbOperation.ADD_OBJECT:
                return cls.tr_s("Object added")
            case DbOperation.UPDATE_OBJECT:
                return cls.tr_s("Object updated")
            case DbOperation.DELETE_OBJECT:
                return cls.tr_s("Object deleted")

            case DbOperation.ADD_CLASS:
                return cls.tr_s("Class created")
            case DbOperation.UPDATE_CLASS:
                return cls.tr_s("Class updated")
            case DbOperation.RENAME_CLASS:
                return cls.tr_s("Class renamed")
            case DbOperation.DELETE_CLASS:
                return cls.tr_s("Class deleted")

            case _:
                return cls.tr_s("Success")


@dataclass
class ServiceResponse:
    """
    ### Універсальна модель відповіді сервісів системи

    Використовується для стандартизації обміну даними між компонентами додатку
    та для десеріалізації відповідей від віддаленого сервера.

    **Поля:**
    - `status`: Статус операції (`StatusCode`).
    - `message`: Текстове повідомлення (зазвичай детальне пояснення від сервера).
    - `operation`: Тип операції, що виконувалася.
    - `data`: Довільні дані відповіді (об'єкти, списки тощо).
    """

    status: StatusCode
    message: str
    operation: Union[DbOperation, str] = DbOperation.UNKNOWN
    data: Optional[Any] = None

    @property
    def is_success(self) -> bool:
        return 200 <= int(self.status) < 300

    @property
    def is_error(self) -> bool:
        return int(self.status) >= 400

    def get_title(self) -> str:
        """Автоматично підбирає заголовок залежно від статусу та типу операції."""
        if self.is_success:
            return OperationTitle.get_success(self.operation)
        return OperationTitle.get_error(self.operation)

    def get_message_or_default(self) -> str:
        """Повертає повідомлення з відповіді або стандартне повідомлення для коду статусу."""
        msg = StatusMessage.get(self.status)
        if msg:
            return msg
        return self.message

    def to_dict(self) -> dict:
        """Перетворює об'єкт відповіді у словник."""
        return {
            "status": int(self.status),
            "message": self.message,
            "data": self.data,
            "operation": (
                self.operation.value
                if isinstance(self.operation, DbOperation)
                else str(self.operation)
            ),
        }

    @staticmethod
    def from_dict(data: dict) -> "ServiceResponse":
        """Створює об'єкт відповіді зі словника."""
        op_str = data.get("operation", "unknown")
        try:
            op = DbOperation(op_str)
        except ValueError:
            op = op_str

        return ServiceResponse(
            status=StatusCode(data.get("status", 500)),
            message=data.get("message", ""),
            operation=op,
            data=data.get("data"),
        )
