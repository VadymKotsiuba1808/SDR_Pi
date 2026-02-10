import socket
import re
import subprocess
from PyQt6.QtCore import QObject
from app.services.system_service import SystemService


class NetworkSignalService(QObject):
    """
    Сервіс для отримання рівня мережевого сигналу (0-100%)
    - WiFi: реальний відсоток сигналу
    - Дротове з'єднання: 100%
    - Без з'єднання: 0%
    """

    # TODO - Перевірити пінгування при підключеній распберрі по Ethernet
    def __init__(self, system_service: SystemService):
        super().__init__()
        self.system_service = system_service

    def get_signal_strength(self) -> int:
        """
        Повертає рівень сигналу 0-100%
        Спочатку пробує WiFi, потім перевіряє дротове з'єднання
        """

        wifi_signal = self._get_wifi_signal()

        if wifi_signal is not None and wifi_signal > 0:
            print(f"[Network] ✓ WiFi signal: {wifi_signal}%")
            return wifi_signal

        if self._has_wired_connection():
            print("[Network] ✓ Wired connection detected: 100%")
            return 100

        print("[Network] ✗ No connection: 0%")
        return 0

    def _get_wifi_signal(self) -> int:
        """
        Отримує рівень WiFi сигналу
        Повертає None якщо не вдалося визначити
        """
        try:
            if self.system_service.is_windows:
                return self._get_windows_wifi_signal()
            elif self.system_service.is_linux:
                return self._get_linux_wifi_signal()
        except Exception as e:
            print(f"[Network] ⚠️ Error reading WiFi signal: {e}")

        return None

    def _get_windows_wifi_signal(self) -> int:
        """Windows: netsh wlan show interfaces"""
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE

            output = subprocess.check_output(
                ["netsh", "wlan", "show", "interfaces"],
                encoding="cp866",
                errors="ignore",
                startupinfo=si,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=3,
            )

            patterns = [
                r"Signal\s*:\s*(\d+)%",
                r"Сигнал\s*:\s*(\d+)%",
            ]

            for pattern in patterns:
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    return int(match.group(1))

        except subprocess.CalledProcessError as e:
            print(
                f"[Network] netsh failed (code {e.returncode}) - WiFi likely disabled"
            )
        except FileNotFoundError:
            print("[Network] netsh not found")
        except subprocess.TimeoutExpired:
            print("[Network] netsh timeout")
        except Exception as e:
            print(f"[Network] Windows WiFi error: {e}")

        return None

    def _get_linux_wifi_signal(self) -> int:
        """Linux: nmcli або iwconfig"""

        try:
            output = subprocess.check_output(
                ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "dev", "wifi"],
                encoding="utf-8",
                timeout=2,
            )

            for line in output.splitlines():
                if line.startswith("yes:"):
                    parts = line.split(":")
                    if len(parts) >= 3 and parts[2].strip().isdigit():
                        signal = int(parts[2].strip())
                        if 0 <= signal <= 100:
                            return signal

        except FileNotFoundError:
            print("[Network] nmcli not available, trying iwconfig...")
        except subprocess.CalledProcessError:
            pass
        except Exception as e:
            print(f"[Network] nmcli error: {e}")

        try:
            output = subprocess.check_output(
                ["iwconfig"], encoding="utf-8", stderr=subprocess.DEVNULL, timeout=2
            )

            match = re.search(r"Link Quality[=:](\d+)/(\d+)", output)
            if match:
                current = int(match.group(1))
                maximum = int(match.group(2))
                if maximum > 0:
                    return int((current / maximum) * 100)

            match = re.search(r"Signal level[=:](-?\d+)\s*dBm", output)
            if match:
                dbm = int(match.group(1))

                quality = 2 * (dbm + 100)
                return max(0, min(100, quality))

        except FileNotFoundError:
            print("[Network] iwconfig not available")
        except subprocess.CalledProcessError:
            pass
        except Exception as e:
            print(f"[Network] iwconfig error: {e}")

        try:
            with open("/proc/net/wireless", "r") as f:
                lines = f.readlines()
                for line in lines[2:]:
                    if ":" in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            link = parts[2].rstrip(".")
                            quality = int(float(link))

                            return min(100, int((quality / 70.0) * 100))
        except Exception as e:
            print(f"[Network] /proc/net/wireless error: {e}")

        return None

    def _has_wired_connection(self) -> bool:
        """
        Перевіряє наявність дротового з'єднання (Ethernet, USB тощо)
        """
        return self._check_internet_connectivity()

    def _check_internet_connectivity(self) -> bool:
        """
        Швидка перевірка інтернет з'єднання
        Пробує підключитися до Google DNS (8.8.8.8:53)
        """
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2).close()
            return True
        except (OSError, socket.timeout):
            pass

        try:
            socket.create_connection(("1.1.1.1", 53), timeout=2).close()
            return True
        except (OSError, socket.timeout):
            return False

    def get_connection_type(self) -> str:
        """
        Визначає тип підключення
        Повертає: 'wifi', 'ethernet', або 'none'
        """
        wifi_signal = self._get_wifi_signal()

        if wifi_signal is not None and wifi_signal > 0:
            return "wifi"

        if self._has_wired_connection():
            return "ethernet"

        return "none"

    def is_connected(self) -> bool:
        """Перевіряє чи є будь-яке підключення до мережі"""
        return self.get_signal_strength() > 0

    def get_detailed_info(self) -> dict:
        """
        Повертає детальну інформацію про з'єднання
        """
        signal = self.get_signal_strength()
        conn_type = self.get_connection_type()

        return {
            "signal_strength": signal,
            "connection_type": conn_type,
            "is_connected": signal > 0,
            "is_wifi": conn_type == "wifi",
            "is_wired": conn_type == "ethernet",
        }
