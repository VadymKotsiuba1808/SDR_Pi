#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRANCH=${1:-dev} 

echo "🚀 Starting full SDR_Pi setup (Branch: $BRANCH)..."

# Make internal scripts executable
chmod +x "$SCRIPT_DIR/_os_setup.sh"
chmod +x "$SCRIPT_DIR/_app_setup.sh"

echo "======================================"
"$SCRIPT_DIR/_os_setup.sh" || { echo "❌ OS setup failed"; exit 1; }

echo "======================================"
"$SCRIPT_DIR/_app_setup.sh" "$BRANCH" || { echo "❌ App setup failed"; exit 1; }

echo "======================================"
echo "✅ All setup phases completed successfully!"
echo "⚠️ System needs to reboot to apply X11 and network changes."

# Trigger a graphical dialog window with a 7-second timeout
zenity --question \
    --title="Reboot Required" \
    --text="SDR_Pi setup completed successfully!\n\nSystem will reboot automatically in 7 seconds to apply changes.\nPress 'Cancel' to stop." \
    --ok-label="Reboot Now" \
    --cancel-label="Cancel" \
    --timeout=7

# Store the exit code returned by Zenity
ZENITY_STATUS=$?

# Exit code 0: User clicked "Reboot Now"
# Exit code 5: Timeout reached (7 seconds)
if [ $ZENITY_STATUS -eq 0 ] || [ $ZENITY_STATUS -eq 5 ]; then
    echo -e "\n🚀 Rebooting now..."
    sudo reboot
else
    # Exit code 1: User clicked "Cancel" or closed the window
    echo -e "\n🛑 Reboot cancelled by user. Please reboot manually later using 'sudo reboot'."
fi