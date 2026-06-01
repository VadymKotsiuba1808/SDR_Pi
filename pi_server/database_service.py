import math
from typing import Any, Callable, List, Optional

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot
from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Integer,
    String,
    create_engine,
    func,
)
from sqlalchemy.engine import Engine
from sqlalchemy.event import listen
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (
    Mapped,
    Session,
    declarative_base,
    joinedload,
    mapped_column,
    relationship,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from app.models.detection_object import DetectionObject
from app.models.object_class import ObjectClass
from app.models.service_response import DbOperation, ServiceResponse, StatusCode

DB_CONNECTION_STRING: str = "sqlite:///./sdr_pi.db"

Base: Any = declarative_base()


class ObjectClassEntity(Base):
    """
    Сутність бази даних для категорій об'єктів.

    Attributes:
        id (int): Унікальний ідентифікатор класу.
        name (str): Унікальна назва класу (наприклад, 'UAV', 'Bird').
        signatures (relationship): Список сигнатур, що належать до цього класу.
    """

    __tablename__ = "object_classes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    signatures = relationship("Signature", back_populates="object_class_rel")


class Signature(Base):
    """
    Сутність бази даних для сигнатур (еталонів) об'єктів.

    Attributes:
        id (int): Унікальний ідентифікатор сигнатури.
        name (str): Назва моделі або типу об'єкта.
        class_id (int): ID пов'язаного класу об'єктів.
        is_dangerous (bool): Прапорець небезпечності об'єкта.
        rf_params (list[str]): Список параметрів радіочастот.
        sound_params (list[int]): Список звукових параметрів.
        object_class_rel (relationship): Посилання на об'єкт класу.
    """

    __tablename__ = "signatures"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("object_classes.id"), nullable=False, index=True
    )
    is_dangerous: Mapped[bool] = mapped_column(Boolean, default=False)
    rf_params: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    sound_params: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    object_class_rel = relationship("ObjectClassEntity", back_populates="signatures")


class DBWorker(QRunnable):
    """
    Виконавець завдань бази даних у фоновому потоці.

    Цей клас дозволяє запускати операції з БД без блокування головного GUI потоку.

    Args:
        func (Callable): Функція, яку необхідно виконати.
        *args: Позиційні аргументи для функції.
        **kwargs: Іменовані аргументи для функції.
    """

    def __init__(self, func: Callable[..., None], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self) -> None:
        """Виконує передану функцію та обробляє можливі винятки."""
        try:
            self.func(*self.args, **self.kwargs)
        except Exception as e:
            print(f"[DB Worker Error] {e}")


class DatabaseService(QObject):
    """
    Головний сервіс для взаємодії з базою даних.

    Використовує асинхронну обробку запитів через QThreadPool та надсилає
    результати через сигнал request_finished.
    """

    # Сигнал для сповіщення про завершення будь-якої операції з БД
    request_finished = pyqtSignal(ServiceResponse)

    def __init__(
        self, db_url: Optional[str] = None, parent: Optional[QObject] = None
    ) -> None:
        """
        Ініціалізує сервіс бази даних.

        Args:
            db_url (str, optional): URL для підключення до БД.
                Якщо не вказано, використовується DB_CONNECTION_STRING.
            parent (QObject, optional): Батьківський об'єкт Qt.
        """
        super().__init__(parent)
        self.threadpool: QThreadPool = QThreadPool()

        self.db_url = db_url or DB_CONNECTION_STRING
        connect_args = {"check_same_thread": False}
        if self.db_url == "sqlite:///:memory:":
            engine_kwargs = {
                "connect_args": connect_args,
                "poolclass": StaticPool,
            }
        else:
            engine_kwargs = {"connect_args": connect_args}

        self.engine: Engine = create_engine(self.db_url, **engine_kwargs, echo=False)
        listen(self.engine, "connect", self._enable_wal)
        Base.metadata.create_all(self.engine)
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.engine)
        print(f"[DB] Service started on {self.db_url}")

    @staticmethod
    def _enable_wal(dbapi_connection, connection_record):
        """
        Увімкнення режиму WAL (Write-Ahead Logging) для SQLite.

        Це покращує продуктивність при одночасному читанні та записі.
        """
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            # WAL може не підтримуватися для баз даних у пам'яті
            pass
        finally:
            cursor.close()

    def request_objects_page(self, page: int = 1, page_size: int = 10) -> None:
        """
        Запит сторінки об'єктів (сигнатур).

        Args:
            page (int): Номер сторінки (починаючи з 1).
            page_size (int): Кількість елементів на сторінці.
        """
        worker = DBWorker(self._fetch_page_task, page, page_size)
        self.threadpool.start(worker)

    def request_all_objects(self) -> None:
        """Запит усіх об'єктів (сигнатур) з бази даних."""
        worker = DBWorker(self._fetch_all_task)
        self.threadpool.start(worker)

    def add_object(self, obj_data: DetectionObject) -> None:
        """
        Додавання нової сигнатури об'єкта.

        Args:
            obj_data (DetectionObject): Дані нового об'єкта.
        """
        worker = DBWorker(self._add_object_task, obj_data)
        self.threadpool.start(worker)

    def update_object(self, obj_data: DetectionObject) -> None:
        """
        Оновлення існуючої сигнатури об'єкта.

        Args:
            obj_data (DetectionObject): Оновлені дані об'єкта (обов'язково з ID).
        """
        worker = DBWorker(self._update_object_task, obj_data)
        self.threadpool.start(worker)

    def delete_object(self, object_id: int) -> None:
        """
        Видалення сигнатури об'єкта за ID.

        Args:
            object_id (int): Ідентифікатор об'єкта для видалення.
        """
        worker = DBWorker(self._delete_object_task, object_id)
        self.threadpool.start(worker)

    def request_classes(self) -> None:
        """Запит усіх доступних класів об'єктів."""
        worker = DBWorker(self._fetch_classes_task)
        self.threadpool.start(worker)

    def add_class(self, class_data: ObjectClass) -> None:
        """
        Додавання нового класу об'єктів.

        Args:
            class_data (ObjectClass): Дані нового класу.
        """
        worker = DBWorker(self._add_class_task, class_data)
        self.threadpool.start(worker)

    def update_class(self, class_data: ObjectClass) -> None:
        """
        Оновлення існуючого класу об'єктів.

        Args:
            class_data (ObjectClass): Оновлені дані класу (обов'язково з ID).
        """
        worker = DBWorker(self._update_class_task, class_data)
        self.threadpool.start(worker)

    def delete_class(self, class_id: int) -> None:
        """
        Видалення класу об'єктів за ID.

        Args:
            class_id (int): Ідентифікатор класу для видалення.
        """
        worker = DBWorker(self._delete_class_task, class_id)
        self.threadpool.start(worker)

    def _signature_to_dto(self, s: Signature) -> DetectionObject:
        """
        Перетворює сутність Signature у DTO об'єкт DetectionObject.

        Args:
            s (Signature): Сутність бази даних.

        Returns:
            DetectionObject: Об'єкт передачі даних.
        """
        return DetectionObject(
            id=s.id,
            name=str(s.name),
            class_id=s.class_id,
            object_class=s.object_class_rel.name if s.object_class_rel else "Unknown",
            is_dangerous=bool(s.is_dangerous),
            rf_params_hz=s.rf_params or [],
            sound_params_hz=s.sound_params or [],
        )

    def _fetch_all_task(self) -> None:
        """Завдання для завантаження всіх об'єктів у фоновому потоці."""
        session: Session = self.Session()

        resp = ServiceResponse(
            operation=DbOperation.GET_ALL_OBJECTS,
            status=StatusCode.INTERNAL_ERROR,
            message="Init",
        )

        try:
            signatures = (
                session.query(Signature)
                .options(joinedload(Signature.object_class_rel))
                .order_by(Signature.id.desc())
                .all()
            )

            items_data = [self._signature_to_dto(s).to_dict() for s in signatures]
            count = len(items_data)

            resp.status = StatusCode.OK
            resp.message = f"Successfully loaded {count} objects"

            resp.data = {"items": items_data, "count": count}

        except Exception as e:
            print(f"[DB Error Fetch All] {e}")
            resp.message = f"Error fetching all objects: {str(e)}"

        finally:
            session.close()
            self.request_finished.emit(resp)

    def _fetch_page_task(self, page: int, page_size: int) -> None:
        """Завдання для завантаження сторінки об'єктів у фоновому потоці."""
        session: Session = self.Session()
        resp = ServiceResponse(
            operation=DbOperation.GET_OBJECTS_PAGE,
            status=StatusCode.INTERNAL_ERROR,
            message="Init",
        )

        try:
            total_items: int = session.query(func.count(Signature.id)).scalar() or 0
            total_pages: int = math.ceil(total_items / page_size) if page_size else 0
            page = max(1, min(page, total_pages)) if total_pages > 0 else 1
            offset: int = (page - 1) * page_size

            signatures = (
                session.query(Signature)
                .options(joinedload(Signature.object_class_rel))
                .order_by(Signature.id.desc())
                .limit(page_size)
                .offset(offset)
                .all()
            )

            items_data = [self._signature_to_dto(s).to_dict() for s in signatures]

            resp.status = StatusCode.OK
            resp.message = "Page loaded"

            resp.data = {
                "items": items_data,
                "page": page,
                "total": total_items,
                "total_pages": total_pages,
            }

        except Exception as e:
            resp.message = str(e)
        finally:
            session.close()
            self.request_finished.emit(resp)

    def _fetch_classes_task(self) -> None:
        """Завдання для завантаження всіх класів у фоновому потоці."""
        session: Session = self.Session()
        resp = ServiceResponse(
            operation=DbOperation.GET_CLASSES,
            status=StatusCode.INTERNAL_ERROR,
            message="Init",
        )

        try:
            results = session.query(ObjectClassEntity).all()
            classes_dicts = [
                ObjectClass(id=row.id, name=str(row.name)).to_dict() for row in results
            ]

            resp.status = StatusCode.OK
            resp.message = "Classes loaded"
            resp.data = {"classes": classes_dicts}

        except Exception as e:
            resp.message = str(e)
        finally:
            session.close()
            self.request_finished.emit(resp)

    def _add_object_task(self, obj_data: DetectionObject) -> None:
        """Завдання для додавання об'єкта у фоновому потоці."""
        session: Session = self.Session()
        resp = ServiceResponse(
            operation=DbOperation.ADD_OBJECT,
            status=StatusCode.INTERNAL_ERROR,
            message="Init",
        )

        try:
            if not obj_data.name:
                raise ValueError("Object name is required")

            target_class_id = obj_data.class_id
            target_class_name = obj_data.object_class

            if not target_class_id:
                obj_class = (
                    session.query(ObjectClassEntity)
                    .filter_by(name=obj_data.object_class)
                    .first()
                )
                if not obj_class:
                    resp.status = StatusCode.BAD_REQUEST
                    resp.message = f"Class '{obj_data.object_class}' not found"
                    return
                target_class_id = obj_class.id
                target_class_name = obj_class.name
            else:
                obj_class = session.query(ObjectClassEntity).get(target_class_id)
                if obj_class:
                    target_class_name = obj_class.name

            new_sig = Signature(
                name=obj_data.name,
                class_id=target_class_id,
                is_dangerous=obj_data.is_dangerous,
                rf_params=obj_data.rf_params_hz,
                sound_params=obj_data.sound_params_hz,
            )

            session.add(new_sig)
            session.commit()
            session.refresh(new_sig)

            created_dto = DetectionObject(
                id=new_sig.id,
                name=new_sig.name,
                class_id=new_sig.class_id,
                object_class=target_class_name,
                is_dangerous=new_sig.is_dangerous,
                rf_params_hz=new_sig.rf_params or [],
                sound_params_hz=new_sig.sound_params or [],
            )

            resp.status = StatusCode.CREATED
            resp.message = "Object successfully added"
            resp.data = created_dto.to_dict()

        except ValueError as e:
            session.rollback()
            resp.status = StatusCode.BAD_REQUEST
            resp.message = str(e)
        except IntegrityError:
            session.rollback()
            resp.status = StatusCode.CONFLICT
            resp.message = "Database integrity error (duplicate?)"
        except Exception as e:
            session.rollback()
            resp.status = StatusCode.INTERNAL_ERROR
            resp.message = f"DB Error: {str(e)}"
        finally:
            session.close()
            self.request_finished.emit(resp)

    def _update_object_task(self, obj_data: DetectionObject) -> None:
        """Завдання для оновлення об'єкта у фоновому потоці."""
        session: Session = self.Session()
        resp = ServiceResponse(
            operation=DbOperation.UPDATE_OBJECT,
            status=StatusCode.INTERNAL_ERROR,
            message="Init",
        )

        try:
            if obj_data.id is None:
                raise ValueError("ID required")

            sig = session.query(Signature).get(obj_data.id)
            if not sig:
                resp.status = StatusCode.NOT_FOUND
                resp.message = f"Object with ID {obj_data.id} not found"
                return

            target_class_id = obj_data.class_id or sig.class_id

            sig.name = obj_data.name
            sig.class_id = target_class_id
            sig.is_dangerous = obj_data.is_dangerous
            sig.rf_params = obj_data.rf_params_hz
            sig.sound_params = obj_data.sound_params_hz

            session.commit()
            session.refresh(sig)

            updated_dto = self._signature_to_dto(sig)

            resp.status = StatusCode.OK
            resp.message = "Object updated"
            resp.data = updated_dto.to_dict()

        except Exception as e:
            session.rollback()
            resp.status = StatusCode.INTERNAL_ERROR
            resp.message = str(e)
        finally:
            session.close()
            self.request_finished.emit(resp)

    def _delete_object_task(self, object_id: int) -> None:
        """Завдання для видалення об'єкта у фоновому потоці."""
        session: Session = self.Session()
        resp = ServiceResponse(
            operation=DbOperation.DELETE_OBJECT,
            status=StatusCode.INTERNAL_ERROR,
            message="Init",
        )

        try:
            rows = session.query(Signature).filter(Signature.id == object_id).delete()
            session.commit()

            if rows == 0:
                resp.status = StatusCode.NOT_FOUND
                resp.message = "Object not found"
            else:
                resp.status = StatusCode.OK
                resp.message = "Object deleted"
                resp.data = {"id": object_id}

        except Exception as e:
            session.rollback()
            resp.status = StatusCode.INTERNAL_ERROR
            resp.message = str(e)
        finally:
            session.close()
            self.request_finished.emit(resp)

    def _add_class_task(self, class_data: ObjectClass) -> None:
        """Завдання для додавання класу у фоновому потоці."""
        session: Session = self.Session()
        resp = ServiceResponse(
            operation=DbOperation.ADD_CLASS,
            status=StatusCode.INTERNAL_ERROR,
            message="Init",
        )

        try:
            if not class_data.name:
                raise ValueError("Class name required")

            existing = (
                session.query(ObjectClassEntity).filter_by(name=class_data.name).first()
            )
            if existing:
                resp.status = StatusCode.CONFLICT
                resp.message = f"Class '{class_data.name}' already exists"
                return

            new_class = ObjectClassEntity(name=class_data.name)
            session.add(new_class)
            session.commit()
            session.refresh(new_class)

            resp.status = StatusCode.CREATED
            resp.message = "Class added"
            resp.data = ObjectClass(id=new_class.id, name=new_class.name).to_dict()

        except ValueError as e:
            resp.status = StatusCode.BAD_REQUEST
            resp.message = str(e)
        except Exception as e:
            session.rollback()
            resp.status = StatusCode.INTERNAL_ERROR
            resp.message = str(e)
        finally:
            session.close()
            self.request_finished.emit(resp)

    def _update_class_task(self, class_data: ObjectClass) -> None:
        """Завдання для оновлення класу у фоновому потоці."""
        session: Session = self.Session()
        resp = ServiceResponse(
            operation=DbOperation.UPDATE_CLASS,
            status=StatusCode.INTERNAL_ERROR,
            message="Init",
        )

        try:
            if not class_data.id:
                raise ValueError("Class ID required")

            entity = session.query(ObjectClassEntity).get(class_data.id)
            if not entity:
                resp.status = StatusCode.NOT_FOUND
                resp.message = "Class not found"
                return

            if entity.name != class_data.name:
                existing = (
                    session.query(ObjectClassEntity)
                    .filter(ObjectClassEntity.name == class_data.name)
                    .first()
                )
                if existing:
                    resp.status = StatusCode.CONFLICT
                    resp.message = "Class name already taken"
                    return

            entity.name = class_data.name
            session.commit()
            session.refresh(entity)

            resp.status = StatusCode.OK
            resp.message = "Class updated"
            resp.data = ObjectClass(id=entity.id, name=entity.name).to_dict()

        except ValueError as e:
            resp.status = StatusCode.BAD_REQUEST
            resp.message = str(e)
        except Exception as e:
            session.rollback()
            resp.status = StatusCode.INTERNAL_ERROR
            resp.message = str(e)
        finally:
            session.close()
            self.request_finished.emit(resp)

    def _delete_class_task(self, class_id: int) -> None:
        """Завдання для видалення класу у фоновому потоці."""
        session: Session = self.Session()
        resp = ServiceResponse(
            operation=DbOperation.DELETE_CLASS,
            status=StatusCode.INTERNAL_ERROR,
            message="Init",
        )

        try:
            usage = (
                session.query(func.count(Signature.id))
                .filter(Signature.class_id == class_id)
                .scalar()
            )
            if usage > 0:
                resp.status = StatusCode.CONFLICT
                resp.message = f"Cannot delete: Class used by {usage} objects"
                return

            rows = (
                session.query(ObjectClassEntity)
                .filter(ObjectClassEntity.id == class_id)
                .delete()
            )
            session.commit()

            if rows == 0:
                resp.status = StatusCode.NOT_FOUND
                resp.message = "Class not found"
            else:
                resp.status = StatusCode.OK
                resp.message = "Class deleted"
                resp.data = {"id": class_id}

        except Exception as e:
            session.rollback()
            resp.status = StatusCode.INTERNAL_ERROR
            resp.message = str(e)
        finally:
            session.close()
            self.request_finished.emit(resp)
