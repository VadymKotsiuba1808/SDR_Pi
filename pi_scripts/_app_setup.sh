#!/bin/bash

PROJECT_DIR="/home/admin/SDR_Pi"
REPO_URL="https://github.com/VadymKotsiuba1808/SDR_Pi.git"
SERVICE_PATH="pi_scripts/sdr_pi.service"

BRANCH=${1:-dev} 

echo "--- Phase 2: Application Setup ---"

echo "Downloading code from GitHub (Branch: $BRANCH)..."
if [ -d "$PROJECT_DIR" ]; then
    echo "⚠️ Folder $PROJECT_DIR already exists! Skipping download to protect files."
else
    # Перевіряємо, чи існує гілка на GitHub
    echo "Checking if branch '$BRANCH' exists on remote..."
    if ! git ls-remote --exit-code --heads "$REPO_URL" "$BRANCH" >/dev/null 2>&1; then
        echo "❌ Error: Branch '$BRANCH' does not exist in remote repository!"
        exit 1
    fi
    

    # Якщо перевірка пройшла успішно — клонуємо
    echo "Branch verified. Cloning..."
    git clone -b "$BRANCH" "$REPO_URL" "$PROJECT_DIR"
fi

# Go to project folder or stop script if it doesn't exist
cd "$PROJECT_DIR" || { echo "❌ Error: Project folder not found"; exit 1; }

echo "Creating Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "Installing pip-tools and syncing Python packages..."
pip install --upgrade pip
pip install pip-tools
# Compile and sync (ensure requirements.in exists in your repo)
if [ -f "requirements.in" ]; then
    pip-compile --strip-extras requirements.in
    pip-sync
else
    echo "⚠️ Warning: requirements.in not found. Skipping pip-sync."
fi

echo "Setting up background service (Systemd)..."
if [ -f "$SERVICE_PATH" ]; then
    # Idempotent approach: remove old link if it exists
    sudo rm -f /etc/systemd/system/sdr_pi.service
    
    # Create absolute symlink
    sudo ln -s "$PROJECT_DIR/$SERVICE_PATH" /etc/systemd/system/sdr_pi.service
    
    sudo systemctl daemon-reload
    sudo systemctl enable sdr_pi.service
    sudo systemctl start sdr_pi.service
    echo "✅ Auto-start service configured and running."
else
    echo "⚠️ Warning: $SERVICE_PATH is missing. Auto-start NOT configured."
fi

echo "✅ Phase 2 (Application Setup) completed."