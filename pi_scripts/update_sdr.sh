#!/bin/bash

PROJECT_DIR="/home/admin/SDR_Pi" 

echo "Start SDR_Pi updating..."

cd "$PROJECT_DIR" || { echo "Directory not found"; exit 1; }

git fetch origin
git reset --hard origin/dev

# --- Verifying and creating .venv ---
if [ ! -d ".venv" ]; then
    echo ".venv not found. Creating a new virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Installing pip-tools..."
    pip install --upgrade pip
    pip install pip-tools
else
    echo ".venv found. Activating..."
    source .venv/bin/activate
fi
# -----------------------------------

echo "Syncing dependencies..."
pip-compile --strip-extras
pip-sync

# Restarting system configs
sudo systemctl daemon-reload

echo "🚀 Restarting service..."
sudo systemctl restart sdr_pi.service

echo "✅ Updating successfully completed! App restarted"