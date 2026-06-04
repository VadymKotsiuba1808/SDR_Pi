import re
import socket
import subprocess
from typing import Optional

from PyQt6.QtCore import QObject

from app.core.logging_config import get_logger
from app.protocols import OSService

logger = get_logger(__name__)


class NetworkSignalService(QObject):
    """
    ### Сервіс моніторингу мережевого з'єднання

    Забезпечує визначення якості WiFi-сигналу для Windows та Linux,
    виявлення дротового підключення (Ethernet) та перевірку
    фактичного доступу до мережі.
    """

    def __init__(self, system_service: OSService):
        super().__init__()
        self.system_service = system_service

    def get_signal_strength(self) -> int:
        """Обчислює загальний рівень сигналу (0-100%)."""

        wifi_signal = self._get_wifi_signal()

        if wifi_signal is not None and wifi_signal > 0:
            logger.debug(f"WiFi signal: {wifi_signal}%")
            return wifi_signal

        if self._has_wired_connection():
            logger.debug("Wired connection detected: 100%")
            return 100

        logger.debug("No connection: 0%")
        return 0

    def _get_wifi_signal(self) -> Optional[int]:
        """Отримує рівень WiFi сигналу залежно від ОС."""
        try:
            if self.system_service.is_windows:
                return self._get_windows_wifi_signal()
            elif self.system_service.is_linux:
                return self._get_linux_wifi_signal()
        except Exception as e:
            logger.error(f"Error reading WiFi signal: {e}")

        return None

    def _get_windows_wifi_signal(self) -> Optional[int]:
        """Отримує рівень сигналу на Windows через netsh."""
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
            logger.warning(
                f"netsh returned error {e.returncode} - WiFi probably disabled"
            )
        except FileNotFoundError:
            logger.error("netsh utility not found")
        except subprocess.TimeoutExpired:
            logger.warning("netsh timeout")
        except Exception as e:
            logger.error(f"Windows WiFi error: {e}")

        return None

    def _get_linux_wifi_signal(self) -> Optional[int]:
        """Отримує рівень сигналу на Linux через nmcli, iwconfig або /proc."""

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
            logger.debug("nmcli unavailable, trying iwconfig...")
        except subprocess.CalledProcessError:
            pass
        except Exception as e:
            logger.error(f"nmcli error: {e}")

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
            logger.debug("iwconfig unavailable")
        except subprocess.CalledProcessError:
            pass
        except Exception as e:
            logger.error(f"iwconfig error: {e}")

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
            logger.error(f"Error reading /proc/net/wireless: {e}")

        return None

    def _has_wired_connection(self) -> bool:
        """Перевіряє наявність дротового з'єднання."""
        return self._check_internet_connectivity()

    def _check_internet_connectivity(self) -> bool:
        """Швидка перевірка фактичного доступу до мережі через TCP до DNS."""
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
        """Визначає тип активного підключення (wifi, ethernet, none)."""
        wifi_signal = self._get_wifi_signal()

        if wifi_signal is not None and wifi_signal > 0:
            return "wifi"

        if self._has_wired_connection():
            return "ethernet"

        return "none"

    def is_connected(self) -> bool:
        return self.get_signal_strength() > 0

    def get_detailed_info(self) -> dict:
        """Повертає розширену інформацію про стан мережі."""
        signal = self.get_signal_strength()
        conn_type = self.get_connection_type()

        return {
            "signal_strength": signal,
            "connection_type": conn_type,
            "is_connected": signal > 0,
            "is_wifi": conn_type == "wifi",
            "is_wired": conn_type == "ethernet",
        }
