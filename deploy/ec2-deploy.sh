#!/usr/bin/env bash
# ==============================================================================
# TraceOps AI — Automated AWS EC2 Deployment Script
# Target OS: Ubuntu 22.04 / 24.04 LTS (AMD64 / ARM64)
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo "  TraceOps AI — AWS EC2 Automated Deployment Setup"
echo "=========================================================="

# 1. Update system packages
echo "[1/5] Updating system packages..."
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release git

# 2. Install Docker and Docker Compose plugin if not already installed
if ! command -v docker &> /dev/null; then
    echo "[2/5] Installing Docker Engine & Docker Compose plugin..."
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker "$USER"
    sudo systemctl enable docker
    sudo systemctl start docker
    echo "Docker installed successfully."
else
    echo "[2/5] Docker is already installed: $(docker --version)"
fi

# 3. Setup Project Directory
REPO_DIR="$HOME/TraceOps-AI"
if [ ! -d "$REPO_DIR" ]; then
    echo "[3/5] Cloning TraceOps AI repository..."
    git clone https://github.com/umeshsatpathi/TraceOps-AI.git "$REPO_DIR"
    cd "$REPO_DIR"
else
    echo "[3/5] TraceOps AI directory exists. Pulling latest updates..."
    cd "$REPO_DIR"
    git fetch origin
    git checkout main || git checkout friend-sync
    git pull
fi

# 4. Configure Environment (.env)
echo "[4/5] Checking environment configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "Created .env template."
    read -rp "Enter your GOOGLE_API_KEY (press Enter to skip for deterministic mode): " api_key
    if [ -n "$api_key" ]; then
        sed -i "s|GOOGLE_API_KEY=.*|GOOGLE_API_KEY=$api_key|" .env
    fi
fi

# 5. Build and Launch Containers
echo "[5/5] Building and starting all Docker services..."
sudo docker compose down --remove-orphans || true
sudo docker compose up -d --build

echo ""
echo "=========================================================="
echo "  Deployment Status"
echo "=========================================================="
sudo docker compose ps

PUBLIC_IP=$(curl -s http://checkip.amazonaws.com || curl -s https://ifconfig.me || echo "your-ec2-ip")

echo ""
echo "=========================================================="
echo "  TraceOps AI is LIVE!"
echo "  Dashboard URL: http://$PUBLIC_IP"
echo "  Backend Docs:  http://$PUBLIC_IP/api/docs"
echo "=========================================================="
echo ""
echo "Note: Ensure AWS EC2 Security Group allows inbound traffic on:"
echo "  - Port 22 (SSH)"
echo "  - Port 80 (HTTP)"
echo "  - Port 5173 (Optional alternative dashboard port)"
