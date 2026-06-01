import re
import socket
import subprocess
from typing import Optional

from PyQt6.QtCore import QObject

from app.protocols import OSService


class NetworkSignalService(QObject):
    """
    Сервіс моніторингу мережевого з'єднання та рівня сигналу.

    Забезпечує визначення якості WiFi-сигналу для Windows та Linux,
    виявлення дротового підключення (Ethernet) та перевірку
    фактичного доступу до мережі.
    """

    def __init__(self, system_service: OSService):
        """
        Ініціалізує сервіс мережевого сигналу.

        Args:
            system_service (OSService): Сервіс для визначення поточної ОС.
        """
        super().__init__()
        self.system_service = system_service

    def get_signal_strength(self) -> int:
        """
        Обчислює загальний рівень сигналу (0-100%).

        Пріоритетність: WiFi (реальне значення) -> Ethernet (100%) -> Немає з'єднання (0%).

        Returns:
            int: Рівень сигналу у відсотках.
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

    def _get_wifi_signal(self) -> Optional[int]:
        """Отримує рівень WiFi сигналу.

        Returns:
            Optional[int]: Рівень сигналу (0-100) або None, якщо не вдалося визначити.
        """
        try:
            if self.system_service.is_windows:
                return self._get_windows_wifi_signal()
            elif self.system_service.is_linux:
                return self._get_linux_wifi_signal()
        except Exception as e:
            print(f"[Network] ⚠️ Error reading WiFi signal: {e}")

        return None

    def _get_windows_wifi_signal(self) -> Optional[int]:
        """Отримує рівень сигналу на Windows через netsh.

        Returns:
            Optional[int]: Рівень сигналу (0-100) або None.
        """
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

    def _get_linux_wifi_signal(self) -> Optional[int]:
        """Отримує рівень сигналу на Linux.

        Пробує послідовно: `nmcli`, `iwconfig` та читання `/proc/net/wireless`.

        Returns:
            Optional[int]: Рівень сигналу (0-100) або None.
        """

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

            # Обробка формату Link Quality=XX/YY
            match = re.search(r"Link Quality[=:](\d+)/(\d+)", output)
            if match:
                current = int(match.group(1))
                maximum = int(match.group(2))
                if maximum > 0:
                    return int((current / maximum) * 100)

            # Обробка формату Signal level=-XX dBm
            match = re.search(r"Signal level[=:](-?\d+)\s*dBm", output)
            if match:
                dbm = int(match.group(1))
                # Наближена формула конвертації dBm у відсотки
                quality = 2 * (dbm + 100)
                return max(0, min(100, quality))

        except FileNotFoundError:
            print("[Network] iwconfig not available")
        except subprocess.CalledProcessError:
            pass
        except Exception as e:
            print(f"[Network] iwconfig error: {e}")

        try:
            # Читання напряму з ядра, якщо утиліти недоступні
            with open("/proc/net/wireless", "r") as f:
                lines = f.readlines()
                for line in lines[2:]:
                    if ":" in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            link = parts[2].rstrip(".")
                            quality = int(float(link))
                            # Для більшості драйверів макс. якість у proc це 70
                            return min(100, int((quality / 70.0) * 100))
        except Exception as e:
            print(f"[Network] /proc/net/wireless error: {e}")

        return None

    def _has_wired_connection(self) -> bool:
        """Перевіряє наявність дротового з'єднання (Ethernet, USB тощо).

        Returns:
            bool: True, якщо з'єднання виявлено.
        """
        return self._check_internet_connectivity()

    def _check_internet_connectivity(self) -> bool:
        """Швидка перевірка фактичного доступу до Інтернету.

        Пробує встановити TCP з'єднання з публічними DNS серверами (Google, Cloudflare).

        Returns:
            bool: True, якщо хоча б один вузол доступний.
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
        """Визначає тип активного підключення.

        Returns:
            str: 'wifi', 'ethernet' або 'none'.
        """
        wifi_signal = self._get_wifi_signal()

        if wifi_signal is not None and wifi_signal > 0:
            return "wifi"

        if self._has_wired_connection():
            return "ethernet"

        return "none"

    def is_connected(self) -> bool:
        """Перевіряє чи є будь-яке підключення до мережі.

        Returns:
            bool: True, якщо рівень сигналу > 0.
        """
        return self.get_signal_strength() > 0

    def get_detailed_info(self) -> dict:
        """Повертає детальну інформацію про стан з'єднання.

        Returns:
            dict: Словник з ключами signal_strength, connection_type, is_connected та ін.
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
