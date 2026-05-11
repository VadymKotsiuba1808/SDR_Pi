#!/bin/bash

# Network configuration variables
STATIC_IP="192.168.1.10/24"
GATEWAY_IP="192.168.1.1"

echo "--- Phase 1: OS Configuration ---"

echo "Removing heavy desktop bloatware (Office, Games, EdTech)..."
sudo apt purge -y libreoffice* wolfram-engine scratch scratch2 sonic-pi dillo xpdf geany

echo "Removing CUPS (Printing service) to free up RAM..."
sudo apt purge -y cups*

echo "Cleaning up unused dependencies and cache..."
sudo apt autoremove -y
sudo apt clean

echo "Disabling Bluetooth service to save CPU cycles (can be re-enabled later)..."
sudo systemctl stop bluetooth
sudo systemctl disable bluetooth

echo "Installing system tools and VLC..."
sudo apt update
sudo apt install -y git python3-venv python3-pip python3-dev build-essential vlc

echo "Removing on-screen keyboards to prevent UI blocking..."
sudo apt purge -y wvkbd matchbox-keyboard onboard
sudo apt autoremove -y

echo "Switching display server from Wayland to X11..."
# Uses the non-interactive mode of raspi-config
sudo raspi-config nonint do_wayland W1

echo "Configuring US and UA keyboard layouts (Switch: Right Alt)..."
# Replace existing layout and option lines in the config file
sudo sed -i 's/XKBLAYOUT=.*/XKBLAYOUT="us,ua"/' /etc/default/keyboard
sudo sed -i 's/XKBOPTIONS=.*/XKBOPTIONS="grp:toggle"/' /etc/default/keyboard
# Apply keyboard changes immediately
sudo udevadm trigger --subsystem-match=input --action=change

echo "Setting up static IP for LAN interface (eth0)..."
# Create or modify the wired connection using NetworkManager
sudo nmcli connection modify "Wired connection 1" \
    ipv4.addresses "$STATIC_IP" \
    ipv4.method manual \
    ipv4.gateway "" \
    ipv4.never-default yes
sudo nmcli connection up "Wired connection 1"

echo "Applying custom taskbar settings for X11 (LXDE)..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/configs/panel" 

POSSIBLE_PATHS=(
    "$HOME/.config/lxpanel-pi/panels"
    "$HOME/.config/lxpanel/LXDE-pi/panels"
)

if [ -f "$CONFIG_FILE" ]; then
    for TARGET_PATH in "${POSSIBLE_PATHS[@]}"; do
        echo "Checking path: $TARGET_PATH"
        mkdir -p "$TARGET_PATH"
        cp "$CONFIG_FILE" "$TARGET_PATH/panel"
    done
    
    # Restart the panel to apply changes immediately
    lxpanelctl restart
    echo "✅ Taskbar config copied to all possible locations."
else
    echo "⚠️ Warning: Custom panel config not found at $CONFIG_FILE. Skipping taskbar setup."
fi

echo "✅ Phase 1 (OS Setup) completed."