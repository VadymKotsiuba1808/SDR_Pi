import os
import sys
import time
from typing import List, Optional

from PyQt6.QtCore import QCoreApplication, QObject, QTimer

# ==========================================
# 1. SETUP PATHS & MOCKS
# ==========================================

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


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
        self.pi_target_ip = "192.168.0.162"  # Ваша IP
        self.pi_target_port = 6000


try:
    from app.models.detection_object import DetectionObject
    from app.models.object_class import ObjectClass
    from app.models.service_response import DbOperation, ServiceResponse, StatusCode
    from app.services.pi_network_service import PiNetworkService
except ImportError as e:
    print(f"{C.FAIL}CRITICAL IMPORT ERROR: {e}{C.ENDC}")
    sys.exit(1)


# ==========================================
# 2. TEST CONTEXT
# ==========================================


class TestContext:
    def __init__(self):
        timestamp = int(time.time())
        self.class_id_1: Optional[int] = None
        self.class_name_1: str = f"TestCls_{timestamp}"

        self.class_id_2: Optional[int] = None
        self.class_name_2: str = f"TestCls_2_{timestamp}"

        self.obj_id_1: Optional[int] = None
        self.obj_name_1: str = f"TestObj_{timestamp}"


# ==========================================
# 3. ROBUST TEST RUNNER
# ==========================================


class MegaTestOrchestrator(QObject):
    def __init__(self, service: PiNetworkService):
        super().__init__()
        self.service = service
        self.ctx = TestContext()

        self.steps_queue: List[dict] = []
        self.current_step_index = -1

        # --- STATE FLAGS ---
        self.is_step_active = False  # Щоб уникнути подвійного pass/fail

        self.timeout_timer = QTimer()
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self.on_timeout)
        self.TIMEOUT_MS = 4000

        self.service.connection_status_changed.connect(self.on_connect)
        self.service.request_finished.connect(self.on_response)

        self.build_test_scenario()

    def build_test_scenario(self):
        # 1. Classes
        self.add_step(
            "Create Class 1", self.req_create_class_1, self.ver_create_class_1
        )
        self.add_step(
            "Verify Class List", self.req_list_classes, self.ver_list_classes_has_1
        )
        self.add_step(
            "Rename Class 1", self.req_rename_class_1, self.ver_rename_class_1
        )
        self.add_step(
            "Create Class 2", self.req_create_class_2, self.ver_create_class_2
        )

        # 2. Error Handling (Classes)
        self.add_step(
            "Try Duplicate Class 1 (Error)",
            self.req_create_duplicate_class,
            self.ver_error_duplicate,
        )

        # 3. Objects
        self.add_step("Create Object 1", self.req_create_obj_1, self.ver_create_obj_1)
        self.add_step("Update Object 1", self.req_update_obj_1, self.ver_update_obj_1)

        # 4. Integrity
        self.add_step(
            "Try Delete Class 1 (Used) (Error)",
            self.req_delete_class_in_use,
            self.ver_error_class_in_use,
        )

        # 5. Object Errors
        self.add_step(
            "Update Fake Object (Error)",
            self.req_update_fake_obj,
            self.ver_error_obj_not_found,
        )
        self.add_step(
            "Delete Fake Object (Error)",
            self.req_delete_fake_obj,
            self.ver_error_obj_not_found,
        )

        # 6. Cleanup
        self.add_step("Cleanup: Del Object 1", self.req_del_obj_1, self.ver_del_obj_1)
        self.add_step(
            "Cleanup: Del Class 1", self.req_del_class_1, self.ver_del_class_1
        )
        self.add_step(
            "Cleanup: Del Class 2", self.req_del_class_2, self.ver_del_class_2
        )

    def add_step(self, name, req_func, ver_func):
        self.steps_queue.append({"name": name, "req": req_func, "ver": ver_func})

    def start(self):
        print(f"{C.HEADER}{C.BOLD}=== RUNNING SDR PI CLIENT TESTS ==={C.ENDC}")
        if (
            self.service.socket
            and self.service.socket.state()
            == self.service.socket.SocketState.ConnectedState
        ):
            self.run_next_step()
        else:
            print(f"{C.WARNING}Waiting for connection...{C.ENDC}")
            self.timeout_timer.start(5000)

    def on_connect(self, connected):
        if connected and self.current_step_index == -1:
            print(f"{C.OKGREEN}[CONN] Connected!{C.ENDC}")
            self.timeout_timer.stop()
            self.run_next_step()

    def run_next_step(self):
        self.current_step_index += 1
        if self.current_step_index >= len(self.steps_queue):
            print(f"\n{C.OKGREEN}{C.BOLD}=== ALL TESTS PASSED! ==={C.ENDC}")
            QCoreApplication.quit()
            return

        step = self.steps_queue[self.current_step_index]
        print(
            f"\n{C.OKCYAN}[STEP {self.current_step_index + 1}/{len(self.steps_queue)}] {step['name']}...{C.ENDC}"
        )

        # Активуємо крок. Всі відповіді до цього моменту ігноруються.
        self.is_step_active = True
        self.timeout_timer.start(self.TIMEOUT_MS)

        try:
            step["req"]()
        except Exception as e:
            self.fail_step(f"Exception during Request: {e}")

    def pass_step(self):
        if not self.is_step_active:
            return  # Захист від подвійного виклику
        self.is_step_active = False

        self.timeout_timer.stop()
        print(f"{C.OKGREEN}>>> PASS{C.ENDC}")
        # Затримка перед наступним кроком, щоб логи не злипалися
        QTimer.singleShot(300, self.run_next_step)

    def fail_step(self, reason):
        if not self.is_step_active:
            return
        self.is_step_active = False

        self.timeout_timer.stop()
        step_name = self.steps_queue[self.current_step_index]["name"]
        print(f"\n{C.FAIL}!!! FAIL !!!{C.ENDC}")
        print(f"{C.FAIL}Step: {step_name}{C.ENDC}")
        print(f"{C.FAIL}Reason: {reason}{C.ENDC}")

        # Виводимо контекст для дебагу
        print(f"CTX: Class1 ID={self.ctx.class_id_1}, Obj1 ID={self.ctx.obj_id_1}")

        QCoreApplication.exit(1)

    def on_timeout(self):
        self.fail_step("Timeout waiting for server response")

    def on_response(self, response: ServiceResponse):
        """
        Main response handler.
        """
        # Ігноруємо пакети, якщо крок вже завершено (наприклад, під час таймера переходу)
        if not self.is_step_active:
            # print(f"Ignored packet (Step inactive): {response.operation}")
            return

        if isinstance(response.operation, DbOperation):
            print(f"[PiNet] {response.operation.value} -> {response.status.value}")

        verifier = self._get_verifier()
        if verifier:
            verifier(response)

    def _get_verifier(self):
        if 0 <= self.current_step_index < len(self.steps_queue):
            return self.steps_queue[self.current_step_index]["ver"]
        return None

    # ==========================================
    # REQUESTS
    # ==========================================

    def req_create_class_1(self):
        self.service.request_db_add_class(ObjectClass(id=0, name=self.ctx.class_name_1))

    def req_list_classes(self):
        self.service.request_db_classes()

    def req_rename_class_1(self):
        new_name = self.ctx.class_name_1 + "_RENAMED"
        self.ctx.class_name_1 = new_name
        old_cls = ObjectClass(id=self.ctx.class_id_1, name="old")
        new_cls = ObjectClass(id=self.ctx.class_id_1, name=new_name)
        self.service.request_db_rename_class(old_cls, new_cls)

    def req_create_class_2(self):
        self.service.request_db_add_class(ObjectClass(id=0, name=self.ctx.class_name_2))

    def req_create_duplicate_class(self):
        self.service.request_db_add_class(ObjectClass(id=0, name=self.ctx.class_name_1))

    def req_create_obj_1(self):
        obj = DetectionObject(
            id=0,
            name=self.ctx.obj_name_1,
            class_id=self.ctx.class_id_1 or 0,
            object_class="Unknown",
            is_dangerous=True,
            rf_params_hz=["433.92"],
            sound_params_hz=[],
        )
        self.service.request_db_add_object(obj)

    def req_update_obj_1(self):
        obj = DetectionObject(
            id=self.ctx.obj_id_1,
            name=self.ctx.obj_name_1 + "_UPD",
            class_id=self.ctx.class_id_1 or 0,
            object_class="Unknown",
            is_dangerous=False,
            rf_params_hz=["915.0"],
            sound_params_hz=[1200],
        )
        self.service.request_db_update_object(obj)

    def req_delete_class_in_use(self):
        if self.ctx.class_id_1 is not None:
            self.service.request_db_delete_class(self.ctx.class_id_1)

    def req_update_fake_obj(self):
        obj = DetectionObject(
            id=999999, name="Fake", class_id=1, object_class="Unknown"
        )
        self.service.request_db_update_object(obj)

    def req_delete_fake_obj(self):
        self.service.request_db_delete_object(999999)

    def req_del_obj_1(self):
        print(f"   -> Requesting delete for ID: {self.ctx.obj_id_1}")
        if self.ctx.obj_id_1 is not None:
            self.service.request_db_delete_object(self.ctx.obj_id_1)

    def req_del_class_1(self):
        if self.ctx.class_id_1 is not None:
            self.service.request_db_delete_class(self.ctx.class_id_1)

    def req_del_class_2(self):
        if self.ctx.class_id_2 is not None:
            self.service.request_db_delete_class(self.ctx.class_id_2)

    # ==========================================
    # VERIFIERS
    # ==========================================

    def ver_create_class_1(self, r: ServiceResponse):
        if r.operation == DbOperation.ADD_CLASS and r.status == StatusCode.CREATED:
            if isinstance(r.data, dict):
                data = ObjectClass.from_dict(r.data)
                self.ctx.class_id_1 = data.id
                self.pass_step()
        elif r.is_error:
            self.fail_step(r.message)

    def ver_list_classes_has_1(self, r: ServiceResponse):
        if r.operation == DbOperation.GET_CLASSES and r.is_success:
            if isinstance(r.data, dict):
                classes = [ObjectClass.from_dict(c) for c in r.data.get("classes", [])]
                if any(c.id == self.ctx.class_id_1 for c in classes):
                    self.pass_step()
                else:
                    self.fail_step("Class 1 not found in list")

    def ver_rename_class_1(self, r: ServiceResponse):
        if (
            r.operation in [DbOperation.UPDATE_CLASS, DbOperation.RENAME_CLASS]
            and r.is_success
        ):
            self.pass_step()
        elif r.is_error:
            self.fail_step(r.message)

    def ver_create_class_2(self, r: ServiceResponse):
        if r.operation == DbOperation.ADD_CLASS and r.status == StatusCode.CREATED:
            if isinstance(r.data, dict):
                self.ctx.class_id_2 = ObjectClass.from_dict(r.data).id
                self.pass_step()
        elif r.is_error:
            self.fail_step(r.message)

    def ver_error_duplicate(self, r: ServiceResponse):
        if r.operation == DbOperation.ADD_CLASS:
            if r.status == StatusCode.CONFLICT:
                self.pass_step()
            elif r.is_success:
                self.fail_step("Duplicate allowed!")

    def ver_create_obj_1(self, r: ServiceResponse):
        if r.operation == DbOperation.ADD_OBJECT and r.status == StatusCode.CREATED:
            if isinstance(r.data, dict):
                self.ctx.obj_id_1 = DetectionObject.from_dict(r.data).id
                self.pass_step()
        elif r.is_error:
            self.fail_step(r.message)

    def ver_update_obj_1(self, r: ServiceResponse):
        if r.operation == DbOperation.UPDATE_OBJECT and r.is_success:
            self.pass_step()
        elif r.is_error:
            self.fail_step(r.message)

    def ver_error_class_in_use(self, r: ServiceResponse):
        if r.operation == DbOperation.DELETE_CLASS:
            if r.status == StatusCode.CONFLICT:
                self.pass_step()
            elif r.is_success:
                self.fail_step("Deleted class in use!")

    def ver_error_obj_not_found(self, r: ServiceResponse):
        if r.status == StatusCode.NOT_FOUND:
            self.pass_step()
        elif r.is_success:
            self.fail_step("Action allowed on non-existent object")

    def ver_del_obj_1(self, r: ServiceResponse):
        if r.operation == DbOperation.DELETE_OBJECT:
            if r.is_success:
                self.pass_step()
            else:
                self.fail_step(f"Delete failed. Code: {r.status}. Msg: {r.message}")

    def ver_del_class_1(self, r: ServiceResponse):
        if r.operation == DbOperation.DELETE_CLASS and r.is_success:
            self.pass_step()
        elif r.is_error:
            self.fail_step(r.message)

    def ver_del_class_2(self, r: ServiceResponse):
        if r.operation == DbOperation.DELETE_CLASS and r.is_success:
            self.pass_step()
        elif r.is_error:
            self.fail_step(r.message)


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
