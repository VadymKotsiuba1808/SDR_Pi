import math
from typing import List, Any, Optional, TypedDict
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
from sqlalchemy.orm import (
    sessionmaker,
    declarative_base,
    relationship,
    joinedload,
    Session,
)

DB_CONNECTION_STRING = "sqlite:///./sdr_pi.db"

Base = declarative_base()


class DetectionObject(TypedDict):
    """
    Type definition for the signature data dictionary.
    """

    id: Optional[int]
    name: str
    object_class: str
    is_dangerous: bool
    rf_params: List[str]
    sound_params: List[str]


class ObjectClass(Base):
    __tablename__ = "object_classes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)

    signatures = relationship("Signature", back_populates="object_class_rel")


class Signature(Base):
    __tablename__ = "signatures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    class_id = Column(Integer, ForeignKey("object_classes.id"), nullable=False)
    is_dangerous = Column(Boolean, default=False)

    rf_params = Column(JSON, default=list)
    sound_params = Column(JSON, default=list)

    object_class_rel = relationship("ObjectClass", back_populates="signatures")


class DBWorker(QRunnable):
    def __init__(self, func: callable, *args: Any, **kwargs: Any) -> None:
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
    objects_page_loaded = pyqtSignal(list, int, int)
    classes_loaded = pyqtSignal(list)
    operation_status = pyqtSignal(str, bool, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.threadpool = QThreadPool()
        self.engine = create_engine(DB_CONNECTION_STRING)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        print(f"[DB] Service started. Using SQLAlchemy with: {DB_CONNECTION_STRING}")

    def request_classes(self) -> None:
        worker = DBWorker(self._fetch_classes_task)
        self.threadpool.start(worker)

    def request_objects_page(self, page: int = 1, page_size: int = 10) -> None:
        worker = DBWorker(self._fetch_page_task, page, page_size)
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

    def _fetch_classes_task(self) -> None:
        session: Session = self.Session()
        try:
            results = session.query(ObjectClass.name).all()
            classes = [row[0] for row in results]
            self.classes_loaded.emit(classes)
        except Exception as e:
            print(f"[DB Error Fetch Classes] {e}")
        finally:
            session.close()

    def _fetch_page_task(self, page: int, page_size: int) -> None:
        session: Session = self.Session()
        try:
            total_items = session.query(func.count(Signature.id)).scalar()
            total_pages = math.ceil(total_items / page_size)

            if page < 1:
                page = 1
            if page > total_pages and total_pages > 0:
                page = total_pages

            offset = (page - 1) * page_size

            signatures = (
                session.query(Signature)
                .options(joinedload(Signature.object_class_rel))
                .order_by(Signature.id.desc())
                .limit(page_size)
                .offset(offset)
                .all()
            )

            data: List[DetectionObject] = []
            for s in signatures:
                obj_dto: DetectionObject = {
                    "id": s.id,
                    "name": s.name,
                    "object_class": (
                        s.object_class_rel.name if s.object_class_rel else "Unknown"
                    ),
                    "is_dangerous": s.is_dangerous,
                    "rf_params": s.rf_params,
                    "sound_params": s.sound_params,
                }
                data.append(obj_dto)

            self.objects_page_loaded.emit(data, page, total_items)

        except Exception as e:
            print(f"[DB Error Fetch Page] {e}")
            self.objects_page_loaded.emit([], 1, 0)
        finally:
            session.close()

    def _add_object_task(self, obj_data: DetectionObject) -> None:
        session: Session = self.Session()
        try:
            obj_class = (
                session.query(ObjectClass)
                .filter_by(name=obj_data["object_class"])
                .first()
            )

            if not obj_class:
                raise ValueError(f"Class '{obj_data['object_class']}' not found in DB")

            new_sig = Signature(
                name=obj_data["name"],
                class_id=obj_class.id,
                is_dangerous=obj_data.get("is_dangerous", False),
                rf_params=obj_data.get("rf_params", []),
                sound_params=obj_data.get("sound_params", []),
            )

            session.add(new_sig)
            session.commit()

            self.operation_status.emit("add", True, "Object successfully added")
            self.request_objects_page(1)

        except Exception as e:
            session.rollback()
            self.operation_status.emit("add", False, str(e))
        finally:
            session.close()

    def _update_object_task(self, obj_data: DetectionObject) -> None:
        session: Session = self.Session()
        try:
            sig = session.query(Signature).get(obj_data["id"])
            if not sig:
                raise ValueError("Object not found")

            obj_class = (
                session.query(ObjectClass)
                .filter_by(name=obj_data["object_class"])
                .first()
            )
            if not obj_class:
                raise ValueError(f"Class '{obj_data['object_class']}' not found")

            sig.name = obj_data["name"]
            sig.class_id = obj_class.id
            sig.is_dangerous = obj_data.get("is_dangerous", False)
            sig.rf_params = obj_data.get("rf_params", [])
            sig.sound_params = obj_data.get("sound_params", [])

            session.commit()

            self.operation_status.emit("update", True, "Object successfully updated")
            self.request_objects_page(1)

        except Exception as e:
            session.rollback()
            self.operation_status.emit("update", False, str(e))
        finally:
            session.close()

    def _delete_object_task(self, object_id: int) -> None:
        session: Session = self.Session()
        try:
            rows_deleted = (
                session.query(Signature).filter(Signature.id == object_id).delete()
            )

            if rows_deleted == 0:
                raise ValueError("Object not found or already deleted")

            session.commit()

            self.operation_status.emit("delete", True, "Object successfully deleted")
            self.request_objects_page(1)

        except Exception as e:
            session.rollback()
            self.operation_status.emit("delete", False, str(e))
        finally:
            session.close()
