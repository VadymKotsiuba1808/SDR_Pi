#!/bin/bash

PROJECT_DIR="/home/admin/SDR_Pi"
REPO_URL="https://github.com/VadymKotsiuba1808/SDR_Pi.git" 
SERVICE_PATH="pi_scripts/sdr_pi.service"

echo "🚀 Starting SDR_Pi install..."

# --- 1. Install system tools ---
echo "Installing required system packages..."
sudo apt update
sudo apt install -y git python3-venv python3-pip python3-dev build-essential

# --- 2. Download project (Clone repo) ---
if [ -d "$PROJECT_DIR" ]; then
    echo "❌ Folder $PROJECT_DIR already exists! Stopping install to keep your files safe."
    echo "Please use the update script or delete the folder first."
    exit 1
fi

echo "Downloading code from GitHub..."
git clone -b dev "$REPO_URL" "$PROJECT_DIR"

cd "$PROJECT_DIR" || { echo "❌ Error: Folder not found after download"; exit 1; }

# --- 3. Setup Python virtual environment (.venv) ---
echo "Creating Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing pip-tools..."
pip install --upgrade pip
pip install pip-tools

echo "Installing Python packages..."
pip-compile --strip-extras
pip-sync

# --- 4. Setup auto-start service (Systemd) ---
if [ -f "$SERVICE_PATH" ]; then
    echo "Setting up background service with symlink..."
    
    # Remove old file or symlink if it exists to prevent errors
    sudo rm -f /etc/systemd/system/sdr_pi.service 
    
    # Create a symbolic link pointing to the file in your repository
    sudo ln -s "$PROJECT_DIR/$SERVICE_PATH" /etc/systemd/system/sdr_pi.service
    
    sudo systemctl daemon-reload
    sudo systemctl enable sdr_pi.service
    sudo systemctl start sdr_pi.service
    echo "✅ Service is ready and running!"
else
    echo "⚠️ Warning: $SERVICE_PATH is missing! Auto-start is NOT setup."
    echo "You need to add it later."
fi

echo "✅ Install finished successfully!"