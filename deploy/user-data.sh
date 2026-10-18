#!/bin/bash
# ==============================================================================
# TraceOps AI — AWS EC2 User Data (Cloud-Init) Boot Script
# Paste this into AWS EC2 Launch Instance -> Advanced Details -> User Data
# ==============================================================================
set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Starting automated TraceOps AI deployment on EC2 boot..."

# 1. Update and install prerequisites
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release git

# 2. Install official Docker
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
systemctl start docker

# 3. Clone repository
mkdir -p /opt/traceops
cd /opt/traceops
git clone https://github.com/umeshsatpathi/TraceOps-AI.git .

# 4. Create environment file
if [ ! -f .env ]; then
  cp .env.example .env
fi

# 5. Launch containers with Docker Compose
docker compose up -d --build

echo "TraceOps AI deployment completed successfully on port 80!"
