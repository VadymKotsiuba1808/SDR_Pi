import sys
import socket
import ctypes
from PyQt6.QtCore import QObject

from app.services.system_service import SystemService


class NetworkSignalService(QObject):
    """
    Сервіс для моніторингу стану мережі та рівня сигналу Wi-Fi.
    Працює на Windows (Native API) та Linux (/proc/net/wireless).
    """

    def __init__(self, system_service: SystemService):
        super().__init__()
        self.system_service = system_service

        self.wlanapi = None
        self.ctypes = None

        self._structs = {}

        self._init_os_modules()

    def _init_os_modules(self):
        """Імпортує потрібні модулі та визначає структури залежно від ОС."""

        if self.system_service.is_windows:
            import ctypes

            self.ctypes = ctypes

            try:
                self.wlanapi = ctypes.windll.wlanapi
                self._setup_windows_structures()
            except Exception as e:
                print(f"[NetworkService] Windows API init failed: {e}")
                self.wlanapi = None

        elif self.system_service.is_linux:
            pass

    def _setup_windows_structures(self):
        """
        Визначає структури C++ тільки якщо ми на Windows.
        Зберігає їх у self._structs для використання у методах.
        """
        c_char = self.ctypes.c_char
        c_uint = self.ctypes.c_uint
        c_ubyte = self.ctypes.c_ubyte
        c_bool = self.ctypes.c_bool
        c_wchar = self.ctypes.c_wchar
        c_byte = self.ctypes.c_byte

        class WLAN_INTERFACE_INFO(self.ctypes.Structure):
            _fields_ = [
                ("InterfaceGuid", c_char * 16),
                ("strInterfaceDescription", c_char * 256),
                ("isState", c_uint),
            ]

        class WLAN_INTERFACE_INFO_LIST(self.ctypes.Structure):
            _fields_ = [
                ("dwNumberOfItems", c_uint),
                ("dwIndex", c_uint),
                ("InterfaceInfo", WLAN_INTERFACE_INFO * 1),
            ]

        class WLAN_ASSOCIATION_ATTRIBUTES(self.ctypes.Structure):
            _fields_ = [
                ("dot11Ssid", c_char * 32),
                ("dot11PhyType", c_uint),
                ("dot11BssId", c_ubyte * 6),
                ("dot11BssType", c_uint),
                ("uPhyId", c_uint),
                ("bMorePhyTypes", c_bool),
                ("wlanSignalQuality", c_uint),
                ("ulRxRate", c_uint),
                ("ulTxRate", c_uint),
            ]

        class WLAN_CONNECTION_ATTRIBUTES(self.ctypes.Structure):
            _fields_ = [
                ("isState", c_uint),
                ("wlanConnectionMode", c_uint),
                ("strProfileName", c_wchar * 256),
                ("wlanAssociationAttributes", WLAN_ASSOCIATION_ATTRIBUTES),
                ("wlanSecurityAttributes", c_byte * 1024),
            ]

        # Зберігаємо класи структур, щоб використовувати їх пізніше
        self._structs["WLAN_INTERFACE_INFO_LIST"] = WLAN_INTERFACE_INFO_LIST
        self._structs["WLAN_CONNECTION_ATTRIBUTES"] = WLAN_CONNECTION_ATTRIBUTES

    def get_signal_strength(self) -> int:
        """
        Повертає рівень сигналу 0-100%.
        """
        wifi_level = 0

        if self.system_service.is_windows:
            wifi_level = self._get_windows_wifi_strength()
        elif self.system_service.is_linux:
            wifi_level = self._get_linux_wifi_strength()

        if wifi_level > 0:
            print(f"Network: Wi-Fi signal detected at {wifi_level}%")
            return wifi_level

        print(
            "Network: Wi-Fi signal not found or 0. Checking for Ethernet/USB connection..."
        )
        if self._check_internet_access():
            print("Network: Wired/USB connection detected. Signal set to 100%")
            return 100

        print("Network: No active connection detected. Signal set to 0%")
        return 0

    def _check_internet_access(self, host="8.8.8.8", port=53, timeout=1.0) -> bool:
        try:
            socket.create_connection((host, port), timeout=timeout).close()
            return True
        except OSError:
            return False

    def _get_linux_wifi_strength(self) -> int:
        try:
            with open("/proc/net/wireless", "r") as f:
                lines = f.readlines()
                for line in lines:
                    if "wlan" in line or "wlp" in line:
                        parts = line.split()
                        val_str = parts[2].replace(".", "")
                        return int(float(val_str))
        except (FileNotFoundError, ValueError, IndexError):
            pass
        return 0

    def _get_windows_wifi_strength(self) -> int:
        if not self.wlanapi or not self._structs:
            return 0

        try:
            WLAN_INTERFACE_INFO_LIST = self._structs["WLAN_INTERFACE_INFO_LIST"]
            WLAN_CONNECTION_ATTRIBUTES = self._structs["WLAN_CONNECTION_ATTRIBUTES"]

            negotiated_version = self.ctypes.c_uint()
            client_handle = self.ctypes.c_void_p()

            ret = self.wlanapi.WlanOpenHandle(
                2,
                None,
                self.ctypes.byref(negotiated_version),
                self.ctypes.byref(client_handle),
            )
            if ret != 0:
                return 0

            p_interface_list = self.ctypes.POINTER(WLAN_INTERFACE_INFO_LIST)()
            ret = self.wlanapi.WlanEnumInterfaces(
                client_handle, None, self.ctypes.byref(p_interface_list)
            )

            signal = 0
            if ret == 0 and p_interface_list.contents.dwNumberOfItems > 0:
                for i in range(p_interface_list.contents.dwNumberOfItems):
                    iface_guid = p_interface_list.contents.InterfaceInfo[
                        i
                    ].InterfaceGuid
                    p_attr = self.ctypes.POINTER(WLAN_CONNECTION_ATTRIBUTES)()
                    data_size = self.ctypes.c_uint()

                    res = self.wlanapi.WlanQueryInterface(
                        client_handle,
                        self.ctypes.byref(iface_guid),
                        4,
                        None,
                        self.ctypes.byref(data_size),
                        self.ctypes.byref(p_attr),
                        None,
                    )

                    if res == 0:
                        current_sig = (
                            p_attr.contents.wlanAssociationAttributes.wlanSignalQuality
                        )
                        if current_sig > signal:
                            signal = current_sig
                        self.wlanapi.WlanFreeMemory(p_attr)

            self.wlanapi.WlanFreeMemory(p_interface_list)
            self.wlanapi.WlanCloseHandle(client_handle, None)
            return signal
        except Exception as e:
            print(f"Error getting Windows signal: {e}")
            return 0
