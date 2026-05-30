#!/bin/bash

PROJECT_DIR="/home/admin/SDR_Pi"
BRANCH=${1:-dev} 

echo "Start SDR_Pi updating (Branch: $BRANCH)..."

cd "$PROJECT_DIR" || { echo "Directory not found"; exit 1; }

git fetch origin

# Запитуємо у Git хеш гілки
git rev-parse --verify origin/"$BRANCH" >/dev/null 2>&1

# Перевіряємо статус виконання (якщо він НЕ дорівнює 0, значить гілки немає)
if [ $? -ne 0 ]; then
    echo "❌ Error: Branch '$BRANCH' does not exist on origin!"
    exit 1
fi

git reset --hard origin/"$BRANCH"

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