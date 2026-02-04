import sys
from PyQt6.QtCore import QCoreApplication, QProcess, QTimer

# def get_wifi_signal_strength(is_windows: bool):
#     """
#     Повертає рівень сигналу Wi-Fi у %, або None якщо не вдалося визначити.
#     Підтримує Windows та Linux.
#     """

#     try:
#         if is_windows:
#             # --- Windows ---
#             output = subprocess.check_output(
#                 ["netsh", "wlan", "show", "interfaces"], encoding="utf-8"
#             )
#             match = re.search(r"Signal\s*:\s*(\d+)%", output)
#             if match:
#                 return int(match.group(1))

#         else:
#             # --- Linux ---
#             # Спроба через nmcli (нові системи)
#             try:
#                 output = subprocess.check_output(
#                     ["nmcli", "-t", "-f", "active,ssid,signal", "dev", "wifi"],
#                     encoding="utf-8",
#                 )
#                 for line in output.splitlines():
#                     if line.startswith("yes:"):
#                         parts = line.split(":")
#                         if len(parts) >= 3:
#                             return int(parts[2])
#             except FileNotFoundError:
#                 # Якщо nmcli недоступний, fallback на iwconfig
#                 output = subprocess.check_output(["iwconfig"], encoding="utf-8")
#                 match = re.search(r"Signal level=(-?\d+) dBm", output)
#                 if match:
#                     dbm = int(match.group(1))
#                     quality = 2 * (dbm + 100)
#                     return max(0, min(100, quality))

#     except subprocess.CalledProcessError:
#         print(f"⚠️ Error reading Wi-Fi signal: {e}")
#         pass
#     except Exception as e:
#         print(f"⚠️ Error reading Wi-Fi signal: {e}")

#     return None


def restart_process():
    QProcess.startDetached(sys.executable, sys.argv)
    QTimer.singleShot(8000, QCoreApplication.quit)
