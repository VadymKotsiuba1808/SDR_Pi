import math
from typing import List, Any, Optional, Callable

from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    JSON,
    ForeignKey,
    func,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    sessionmaker,
    declarative_base,
    relationship,
    joinedload,
    Session,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.event import listen

from app.models.detection_object import DetectionObject
from app.models.object_class import ObjectClass

DB_CONNECTION_STRING: str = "sqlite:///./temp/sdr_pi.db"

Base: Any = declarative_base()


class ObjectClassEntity(Base):
    __tablename__ = "object_classes"
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String, unique=True, nullable=False)
    signatures = relationship("Signature", back_populates="object_class_rel")


class Signature(Base):
    __tablename__ = "signatures"
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String, nullable=False)
    class_id: int = Column(
        Integer, ForeignKey("object_classes.id"), nullable=False, index=True
    )
    is_dangerous: bool = Column(Boolean, default=False)
    rf_params: Optional[List[str]] = Column(JSON, nullable=True)
    sound_params: Optional[List[float]] = Column(JSON, nullable=True)
    object_class_rel = relationship("ObjectClassEntity", back_populates="signatures")


class DBWorker(QRunnable):
    def __init__(self, func: Callable[..., None], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self) -> None:
        try:
            self.func(*self.args, **self.kwargs)
        except Exception as e:
            print(f"[DB Worker Error] {e}")


class DatabaseService(QObject):
    # Основні сигнали для списків
    objects_all_loaded = pyqtSignal(list, int)
    objects_page_loaded = pyqtSignal(list, int, int)
    classes_loaded = pyqtSignal(list)
    operation_status = pyqtSignal(str, bool, str)

    # Сигнали подій (Event-Driven)
    object_added = pyqtSignal(DetectionObject)
    object_updated = pyqtSignal(DetectionObject)
    object_deleted = pyqtSignal(int)

    class_added = pyqtSignal(ObjectClass)
    class_updated = pyqtSignal(ObjectClass)
    class_deleted = pyqtSignal(int)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.threadpool: QThreadPool = QThreadPool()
        self.engine: Engine = create_engine(
            DB_CONNECTION_STRING,
            connect_args={"check_same_thread": False},
            echo=False,
        )
        listen(self.engine, "connect", self._enable_wal)
        Base.metadata.create_all(self.engine)
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.engine)
        print(f"[DB] Service started. Mode: WAL enabled.")

    @staticmethod
    def _enable_wal(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    # --- Public Methods ---

    def request_objects_page(self, page: int = 1, page_size: int = 10) -> None:
        worker = DBWorker(self._fetch_page_task, page, page_size)
        self.threadpool.start(worker)

    def request_all_objects(self) -> None:
        worker = DBWorker(self._fetch_all_task)
        self.threadpool.start(worker)

    def add_object(self, obj_data: DetectionObject) -> None:
        worker = DBWorker(self._add_object_task, obj_data)
        self.threadpool.start(worker)

    def update_object(self, obj_data: DetectionObject) -> None:
        worker = DBWorker(self._update_object_task, obj_data)
        self.threadpool.start(worker)

    def delete_object(self, object_id: int) -> None:
        worker = DBWorker(self._delete_object_task, object_id)
        self.threadpool.start(worker)

    def request_classes(self) -> None:
        worker = DBWorker(self._fetch_classes_task)
        self.threadpool.start(worker)

    def add_class(self, class_data: ObjectClass) -> None:
        worker = DBWorker(self._add_class_task, class_data)
        self.threadpool.start(worker)

    def update_class(self, class_data: ObjectClass) -> None:
        worker = DBWorker(self._update_class_task, class_data)
        self.threadpool.start(worker)

    def delete_class(self, class_id: int) -> None:
        worker = DBWorker(self._delete_class_task, class_id)
        self.threadpool.start(worker)

    # --- Internal Tasks ---
    def _signature_to_dto(self, s: Signature) -> DetectionObject:
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
        session: Session = self.Session()
        try:
            signatures = (
                session.query(Signature)
                .options(joinedload(Signature.object_class_rel))
                .order_by(Signature.id.desc())
                .all()
            )

            data = [self._signature_to_dto(s) for s in signatures]

            self.objects_all_loaded.emit(data, len(data))

        except Exception as e:
            print(f"[DB Error Fetch All] {e}")
            self.objects_all_loaded.emit([], 0)
        finally:
            session.close()

    def _fetch_page_task(self, page: int, page_size: int) -> None:
        session: Session = self.Session()
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

            data = [self._signature_to_dto(s) for s in signatures]

            self.objects_page_loaded.emit(data, page, total_items)

        except Exception as e:
            print(f"[DB Error Fetch Page] {e}")
            self.objects_page_loaded.emit([], 1, 0)
        finally:
            session.close()

    def _add_object_task(self, obj_data: DetectionObject) -> None:
        session: Session = self.Session()
        try:
            target_class_id = obj_data.class_id
            target_class_name = obj_data.object_class

            if not target_class_id:
                obj_class = (
                    session.query(ObjectClassEntity)
                    .filter_by(name=obj_data.object_class)
                    .first()
                )
                if not obj_class:
                    raise ValueError(f"Class '{obj_data.object_class}' not found")
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
                rf_params_hz=new_sig.rf_params,
                sound_params_hz=new_sig.sound_params,
            )

            self.operation_status.emit("add_object", True, "Object successfully added")

            self.object_added.emit(created_dto)

        except Exception as e:
            session.rollback()
            self.operation_status.emit("add_object", False, str(e))
        finally:
            session.close()

    def _update_object_task(self, obj_data: DetectionObject) -> None:
        session: Session = self.Session()
        try:
            if obj_data.id is None:
                raise ValueError("Object ID is required for update")

            sig = session.query(Signature).get(obj_data.id)
            if not sig:
                raise ValueError("Object not found")

            target_class_id = obj_data.class_id
            target_class_name = obj_data.object_class

            if not target_class_id:
                obj_class = (
                    session.query(ObjectClassEntity)
                    .filter_by(name=obj_data.object_class)
                    .first()
                )
                if not obj_class:
                    raise ValueError(f"Class '{obj_data.object_class}' not found")
                target_class_id = obj_class.id
                target_class_name = obj_class.name
            else:
                obj_class = session.query(ObjectClassEntity).get(target_class_id)
                if obj_class:
                    target_class_name = obj_class.name

            sig.name = obj_data.name
            sig.class_id = target_class_id
            sig.is_dangerous = obj_data.is_dangerous
            sig.rf_params = obj_data.rf_params_hz
            sig.sound_params = obj_data.sound_params_hz

            session.commit()
            session.refresh(sig)

            updated_dto = DetectionObject(
                id=sig.id,
                name=sig.name,
                class_id=sig.class_id,
                object_class=target_class_name,
                is_dangerous=sig.is_dangerous,
                rf_params_hz=sig.rf_params,
                sound_params_hz=sig.sound_params,
            )

            self.operation_status.emit(
                "update_object", True, "Object successfully updated"
            )

            self.object_updated.emit(updated_dto)

        except Exception as e:
            session.rollback()
            self.operation_status.emit("update_object", False, str(e))
        finally:
            session.close()

    def _delete_object_task(self, object_id: int) -> None:
        session: Session = self.Session()
        try:
            rows = session.query(Signature).filter(Signature.id == object_id).delete()
            if rows == 0:
                raise ValueError("Object not found or already deleted")

            session.commit()

            self.operation_status.emit(
                "delete_object", True, "Object successfully deleted"
            )
            self.object_deleted.emit(object_id)

        except Exception as e:
            session.rollback()
            self.operation_status.emit("delete_object", False, str(e))
        finally:
            session.close()

    def _fetch_classes_task(self) -> None:
        session: Session = self.Session()
        try:
            results = session.query(ObjectClassEntity).all()
            classes_dtos = [
                ObjectClass(id=row.id, name=str(row.name)) for row in results
            ]
            self.classes_loaded.emit(classes_dtos)
        except Exception as e:
            print(f"[DB Error Fetch Classes] {e}")
        finally:
            session.close()

    def _add_class_task(self, class_data: ObjectClass) -> None:
        session: Session = self.Session()
        try:
            existing = (
                session.query(ObjectClassEntity).filter_by(name=class_data.name).first()
            )
            if existing:
                raise ValueError(f"Class '{class_data.name}' already exists.")

            new_class = ObjectClassEntity(name=class_data.name)
            session.add(new_class)
            session.commit()
            session.refresh(new_class)

            created_dto = ObjectClass(id=new_class.id, name=new_class.name)

            self.operation_status.emit("add_class", True, "Class successfully added")
            self.class_added.emit(created_dto)

        except Exception as e:
            session.rollback()
            self.operation_status.emit("add_class", False, str(e))
        finally:
            session.close()

    def _update_class_task(self, class_data: ObjectClass) -> None:
        session: Session = self.Session()
        try:
            if not class_data.id:
                raise ValueError("Class ID is required")

            entity = session.query(ObjectClassEntity).get(class_data.id)
            if not entity:
                raise ValueError("Class not found")

            if entity.name != class_data.name:
                existing = (
                    session.query(ObjectClassEntity)
                    .filter(ObjectClassEntity.name == class_data.name)
                    .first()
                )
                if existing:
                    raise ValueError(f"Name '{class_data.name}' is taken")

            entity.name = class_data.name
            session.commit()
            session.refresh(entity)

            updated_dto = ObjectClass(id=entity.id, name=entity.name)

            self.operation_status.emit("update_class", True, "Class updated")
            self.class_updated.emit(updated_dto)

        except Exception as e:
            session.rollback()
            self.operation_status.emit("update_class", False, str(e))
        finally:
            session.close()

    def _delete_class_task(self, class_id: int) -> None:
        session: Session = self.Session()
        try:
            usage_count = (
                session.query(func.count(Signature.id))
                .filter(Signature.class_id == class_id)
                .scalar()
            )
            if usage_count > 0:
                raise ValueError(f"Cannot delete class. Used by {usage_count} objects.")

            rows = (
                session.query(ObjectClassEntity)
                .filter(ObjectClassEntity.id == class_id)
                .delete()
            )
            if rows == 0:
                raise ValueError("Class not found")

            session.commit()

            self.operation_status.emit("delete_class", True, "Class deleted")
            self.class_deleted.emit(class_id)

        except Exception as e:
            session.rollback()
            self.operation_status.emit("delete_class", False, str(e))
        finally:
            session.close()
