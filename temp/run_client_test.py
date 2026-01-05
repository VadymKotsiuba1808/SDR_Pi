import sys
import os
import time
import random
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass

from PyQt6.QtCore import QCoreApplication, QTimer, QObject, pyqtSlot

# ==========================================
# 1. SETUP PATHS & MOCKS
# ==========================================

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# Кольори для консолі
class C:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


class SettingsService:
    def __init__(self):
        self.pi_is_receiver = False
        self.pi_target_ip = "192.168.1.244"
        self.pi_target_port = 6000


try:
    from app.services.pi_network_service import PiNetworkService
    from app.models.detection_object import DetectionObject
    from app.models.object_class import ObjectClass
except ImportError as e:
    print(f"{C.FAIL}CRITICAL IMPORT ERROR: {e}{C.ENDC}")
    sys.exit(1)

# ==========================================
# 2. TEST CONTEXT (SHARED MEMORY)
# ==========================================


class TestContext:
    """Зберігає дані, які передаються між кроками тестів"""

    def __init__(self):
        self.class_id_1: Optional[int] = None
        self.class_name_1: str = f"AutoTest_Cls_{int(time.time())}"

        self.class_id_2: Optional[int] = None
        self.class_name_2: str = f"AutoTest_Cls_2_{int(time.time())}"

        self.obj_id_1: Optional[int] = None
        self.obj_name_1: str = f"AutoObj_1_{int(time.time())}"

        self.bulk_ids: List[int] = []


# ==========================================
# 3. BASE TEST RUNNER
# ==========================================


class MegaTestOrchestrator(QObject):
    def __init__(self, service: PiNetworkService):
        super().__init__()
        self.service = service
        self.ctx = TestContext()

        self.steps_queue: List[tuple] = []
        self.current_step_index = -1

        self.timeout_timer = QTimer()
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self.on_timeout)
        self.TIMEOUT_MS = 4000

        # Підписка на сигнали
        self.service.connection_status_changed.connect(self.on_connect)

        self.service.db_class_added.connect(self.on_class_added)
        self.service.db_class_renamed.connect(self.on_class_renamed)
        self.service.db_class_deleted.connect(self.on_class_deleted)

        self.service.db_object_added.connect(self.on_object_added)
        self.service.db_object_updated.connect(self.on_object_updated)
        self.service.db_object_deleted.connect(self.on_object_deleted)

        self.service.db_classes_received.connect(self.on_classes_list)
        self.service.db_objects_page_received.connect(self.on_objects_page)
        self.service.db_operation_status.connect(self.on_op_status)

        self.build_test_scenario()

    def build_test_scenario(self):
        # === SUITE 1: BASIC CLASS CRUD ===
        self.add_step(
            "Create Class 1", self.req_create_class_1, self.ver_create_class_1
        )
        self.add_step(
            "Verify Class List", self.req_list_classes, self.ver_list_classes_has_1
        )
        self.add_step(
            "Rename Class 1", self.req_rename_class_1, self.ver_rename_class_1
        )

        # === SUITE 2: ERROR HANDLING (CLASSES) ===
        self.add_step(
            "Create Class 2 (Unique)", self.req_create_class_2, self.ver_create_class_2
        )
        self.add_step(
            "Try Create Duplicate Class 1 (Expect Error)",
            self.req_create_duplicate_class,
            self.ver_error_duplicate,
        )
        # self.add_step("Try Rename Class 2 to Class 1 (Expect Error)", self.req_rename_duplicate, self.ver_error_duplicate_rename)

        # === SUITE 3: BASIC OBJECT CRUD ===
        self.add_step(
            "Create Object 1 in Class 1", self.req_create_obj_1, self.ver_create_obj_1
        )
        self.add_step("Update Object 1", self.req_update_obj_1, self.ver_update_obj_1)

        # === SUITE 4: DATA INTEGRITY ===
        self.add_step(
            "Try Delete Class 1 (In Use) (Expect Error)",
            self.req_delete_class_in_use,
            self.ver_error_class_in_use,
        )

        # === SUITE 5: OBJECT ERROR HANDLING ===
        self.add_step(
            "Try Update Non-Existent Object (Expect Error)",
            self.req_update_fake_obj,
            self.ver_error_obj_not_found,
        )
        self.add_step(
            "Try Delete Non-Existent Object (Expect Error)",
            self.req_delete_fake_obj,
            self.ver_error_obj_not_found,
        )

        # === SUITE 6: CLEANUP ===
        self.add_step(
            "Cleanup: Delete Object 1", self.req_del_obj_1, self.ver_del_obj_1
        )
        self.add_step(
            "Cleanup: Delete Class 1", self.req_del_class_1, self.ver_del_class_1
        )
        self.add_step(
            "Cleanup: Delete Class 2", self.req_del_class_2, self.ver_del_class_2
        )

    def add_step(self, name, req_func, ver_func):
        self.steps_queue.append({"name": name, "req": req_func, "ver": ver_func})

    def start(self):
        print(f"{C.HEADER}{C.BOLD}=== ЗАПУСК МЕГА-ТЕСТІВ SDR PI CLIENT ==={C.ENDC}")
        if (
            self.service.socket
            and self.service.socket.state()
            == self.service.socket.SocketState.ConnectedState
        ):
            self.run_next_step()
        else:
            print(f"{C.WARNING}Очікування з'єднання...{C.ENDC}")
            self.timeout_timer.start(5000)

    def on_connect(self, connected):
        if connected and self.current_step_index == -1:
            print(f"{C.OKGREEN}[CONN] З'єднання встановлено!{C.ENDC}")
            self.timeout_timer.stop()
            self.run_next_step()

    def run_next_step(self):
        self.current_step_index += 1
        if self.current_step_index >= len(self.steps_queue):
            print(f"\n{C.OKGREEN}{C.BOLD}=== ВСІ ТЕСТИ ПРОЙДЕНО УСПІШНО! ==={C.ENDC}")
            QCoreApplication.quit()
            return

        step = self.steps_queue[self.current_step_index]
        print(
            f"\n{C.OKCYAN}[STEP {self.current_step_index + 1}/{len(self.steps_queue)}] {step['name']}...{C.ENDC}"
        )

        self.timeout_timer.start(self.TIMEOUT_MS)
        try:
            step["req"]()
        except Exception as e:
            self.fail_step(f"Exception during Request: {e}")

    def pass_step(self):
        self.timeout_timer.stop()
        print(f"{C.OKGREEN}>>> PASS{C.ENDC}")
        QTimer.singleShot(200, self.run_next_step)

    def fail_step(self, reason):
        self.timeout_timer.stop()
        step_name = self.steps_queue[self.current_step_index]["name"]
        print(f"\n{C.FAIL}!!! FAIL !!!{C.ENDC}")
        print(f"{C.FAIL}Крок: {step_name}{C.ENDC}")
        print(f"{C.FAIL}Причина: {reason}{C.ENDC}")
        QCoreApplication.exit(1)

    def on_timeout(self):
        self.fail_step("Таймаут відповіді від сервера")

    # ==========================================
    # REQUEST HANDLERS (ВИПРАВЛЕНО: ПЕРЕДАЄМО ОБ'ЄКТИ)
    # ==========================================

    def req_create_class_1(self):
        # FIX: Передаємо ObjectClass, а не str
        cls = ObjectClass(id=0, name=self.ctx.class_name_1)
        self.service.request_db_add_class(cls)

    def req_list_classes(self):
        self.service.request_db_classes()

    def req_rename_class_1(self):
        new_name = self.ctx.class_name_1 + "_RENAMED"
        self.ctx.class_name_1 = new_name
        # FIX: Передаємо ObjectClass для old і new
        old_cls = ObjectClass(id=self.ctx.class_id_1, name="OLD_IGNORED")
        new_cls = ObjectClass(id=self.ctx.class_id_1, name=new_name)
        self.service.request_db_rename_class(old_cls, new_cls)

    def req_create_class_2(self):
        cls = ObjectClass(id=0, name=self.ctx.class_name_2)
        self.service.request_db_add_class(cls)

    def req_create_duplicate_class(self):
        cls = ObjectClass(id=0, name=self.ctx.class_name_1)
        self.service.request_db_add_class(cls)

    def req_rename_duplicate(self):
        # FIX: API вимагає об'єкти
        old_cls = ObjectClass(id=self.ctx.class_id_2, name="any")
        new_cls = ObjectClass(id=self.ctx.class_id_2, name=self.ctx.class_name_1)
        self.service.request_db_rename_class(old_cls, new_cls)

    def req_create_obj_1(self):
        # FIX: Передаємо DetectionObject, а не dict
        obj = DetectionObject(
            id=0,
            name=self.ctx.obj_name_1,
            class_id=self.ctx.class_id_1,
            object_class="Unknown",
            is_dangerous=True,
            rf_params_hz=["433.92"],
            sound_params_hz=[],
        )
        self.service.request_db_add_object(obj)

    def req_update_obj_1(self):
        # FIX: Передаємо DetectionObject
        obj = DetectionObject(
            id=self.ctx.obj_id_1,
            name=self.ctx.obj_name_1 + "_UPD",
            class_id=self.ctx.class_id_1,
            object_class="Unknown",
            is_dangerous=False,
            rf_params_hz=["915.0"],
            sound_params_hz=[1200],
        )
        self.service.request_db_update_object(obj)

    def req_delete_class_in_use(self):
        self.service.request_db_delete_class(self.ctx.class_id_1)

    def req_update_fake_obj(self):
        obj = DetectionObject(
            id=999999, name="Fake", class_id=self.ctx.class_id_1, object_class="Unknown"
        )
        self.service.request_db_update_object(obj)

    def req_delete_fake_obj(self):
        self.service.request_db_delete_object(999999)

    def req_del_obj_1(self):
        self.service.request_db_delete_object(self.ctx.obj_id_1)

    def req_del_class_1(self):
        self.service.request_db_delete_class(self.ctx.class_id_1)

    def req_del_class_2(self):
        self.service.request_db_delete_class(self.ctx.class_id_2)

    # ==========================================
    # VERIFICATION HANDLERS (Callbacks)
    # ==========================================

    def _get_verifier(self):
        if 0 <= self.current_step_index < len(self.steps_queue):
            return self.steps_queue[self.current_step_index]["ver"]
        return None

    def on_class_added(self, cls: ObjectClass):
        verifier = self._get_verifier()
        if verifier:
            verifier(event_type="class_added", data=cls)

    def on_class_renamed(self, cls: ObjectClass):
        verifier = self._get_verifier()
        if verifier:
            verifier(event_type="class_renamed", data=cls)

    def on_class_deleted(self, cls_id: int):
        verifier = self._get_verifier()
        if verifier:
            verifier(event_type="class_deleted", data=cls_id)

    def on_object_added(self, obj: DetectionObject):
        verifier = self._get_verifier()
        if verifier:
            verifier(event_type="object_added", data=obj)

    def on_object_updated(self, obj: DetectionObject):
        verifier = self._get_verifier()
        if verifier:
            verifier(event_type="object_updated", data=obj)

    def on_object_deleted(self, obj_id: int):
        verifier = self._get_verifier()
        if verifier:
            verifier(event_type="object_deleted", data=obj_id)

    def on_op_status(self, op: str, success: bool, msg: str):
        verifier = self._get_verifier()
        if verifier:
            verifier(
                event_type="status", data={"op": op, "success": success, "msg": msg}
            )

    def on_classes_list(self, classes: List[ObjectClass]):
        verifier = self._get_verifier()
        if verifier:
            verifier(event_type="list_classes", data=classes)

    def on_objects_page(self, items, page, total):
        verifier = self._get_verifier()
        if verifier:
            verifier(
                event_type="page_objects",
                data={"items": items, "page": page, "total": total},
            )

    # --- SPECIFIC VERIFIERS (LOGIC) ---

    def ver_create_class_1(self, event_type, data):
        if event_type == "class_added":
            if data.name == self.ctx.class_name_1 and data.id > 0:
                self.ctx.class_id_1 = data.id
                self.pass_step()
            else:
                self.fail_step(
                    f"Невірні дані класу: {data.name} vs {self.ctx.class_name_1}"
                )

    def ver_list_classes_has_1(self, event_type, data):
        if event_type == "list_classes":
            found = any(c.id == self.ctx.class_id_1 for c in data)
            if found:
                self.pass_step()
            else:
                self.fail_step("Створений клас не знайдено у списку")

    def ver_rename_class_1(self, event_type, data):
        if event_type in ["class_renamed", "class_updated"]:
            if data.id == self.ctx.class_id_1 and data.name == self.ctx.class_name_1:
                self.pass_step()
            else:
                self.fail_step(f"Перейменування не вдалось: {data.name}")

    def ver_create_class_2(self, event_type, data):
        if event_type == "class_added":
            self.ctx.class_id_2 = data.id
            self.pass_step()

    def ver_error_duplicate(self, event_type, data):
        if event_type == "status":
            if not data["success"]:
                print(f"{C.OKCYAN}Очікувана помилка отримана: {data['msg']}{C.ENDC}")
                self.pass_step()
            else:
                self.fail_step("Сервер дозволив створити дублікат класу!")

    def ver_error_duplicate_rename(self, event_type, data):
        if event_type == "status":
            if not data["success"]:
                print(f"{C.OKCYAN}Очікувана помилка перейменування отримана{C.ENDC}")
                self.pass_step()
            else:
                self.fail_step("Сервер дозволив перейменувати на існуюче ім'я!")

    def ver_create_obj_1(self, event_type, data):
        if event_type == "object_added":
            if data.name == self.ctx.obj_name_1:
                self.ctx.obj_id_1 = data.id
                self.pass_step()
            else:
                self.fail_step("Ім'я об'єкта не співпадає")

    def ver_update_obj_1(self, event_type, data):
        if event_type == "object_updated":
            if data.id == self.ctx.obj_id_1 and data.is_dangerous == False:
                self.pass_step()
            else:
                self.fail_step("Дані об'єкта не оновились")

    def ver_error_class_in_use(self, event_type, data):
        if event_type == "status":
            if not data["success"] and "Used by" in data["msg"]:
                print(f"{C.OKCYAN}Очікувано: {data['msg']}{C.ENDC}")
                self.pass_step()
            else:
                self.fail_step(f"Очікувалась помилка 'Used by', отримано: {data}")

    def ver_error_obj_not_found(self, event_type, data):
        if event_type == "status":
            if not data["success"]:
                self.pass_step()
            else:
                self.fail_step("Сервер дозволив дію з неіснуючим об'єктом")

    def ver_del_obj_1(self, event_type, data):
        if event_type == "object_deleted":
            if data == self.ctx.obj_id_1:
                self.pass_step()

    def ver_del_class_1(self, event_type, data):
        if event_type == "class_deleted":
            if data == self.ctx.class_id_1:
                self.pass_step()

    def ver_del_class_2(self, event_type, data):
        if event_type == "class_deleted":
            if data == self.ctx.class_id_2:
                self.pass_step()


def main():
    app = QCoreApplication(sys.argv)
    settings = SettingsService()
    service = PiNetworkService(settings)
    service.start()

    tester = MegaTestOrchestrator(service)
    QTimer.singleShot(1000, tester.start)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
