# TraceOps AI — AWS EC2 Deployment Guide

This guide details how to deploy the complete **TraceOps AI** stack on a single **AWS EC2** instance using Docker Compose.

In this setup, all 4 services run securely on your instance:
* **React + Vite Dashboard** (Nginx on Port 80 & 5173 with built-in `/api/` reverse proxy)
* **FastAPI Backend** (Internal Port 8000, auto-seeded on startup)
* **FalkorDB Graph Database** (Internal Port 6379 with persistent volume)
* **DemoShop Target App** (Internal Port 5001 for authorized scanning)

---

## 1. Launching the EC2 Instance

### Recommended Configuration
| Setting | Recommended Value |
|---|---|
| **Instance Type** | `t3.small` (2 vCPU, 2 GB RAM) or `t3.medium` (2 vCPU, 4 GB RAM) |
| **AMI / OS** | **Ubuntu Server 24.04 LTS** or **22.04 LTS** (64-bit x86) |
| **Storage** | 20 GB – 30 GB (General Purpose SSD `gp3`) |
| **Key Pair** | Create or select an existing `.pem` key pair for SSH |

### Configure Security Group (Firewall)
Under **Network settings** > **Security Group**, configure the following inbound rules:

| Type | Port | Protocol | Source | Description |
|---|---|---|---|---|
| **SSH** | `22` | TCP | My IP *(or 0.0.0.0/0)* | Terminal access |
| **HTTP** | `80` | TCP | `0.0.0.0/0` | Public Dashboard |
| **Custom TCP** | `5173` | TCP | `0.0.0.0/0` | *(Optional) Alternative UI port* |

> 🔒 **Security Notice:** Do **NOT** expose port `6379` (FalkorDB) or port `8000` (FastAPI) to the public internet. The frontend container's Nginx reverse-proxies `/api/` calls internally within the private Docker bridge network.

---

## 2. Deployment Methods

### Method A: Automated 1-Command SSH Deployment (Fastest)

1. Connect to your EC2 instance via SSH:
   ```bash
   ssh -i /path/to/your-key.pem ubuntu@<EC2-PUBLIC-IP>
   ```

2. Run the automated deployment script:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/umeshsatpathi/TraceOps-AI/main/deploy/ec2-deploy.sh | bash
   ```

The script will automatically:
- Install Docker & Docker Compose
- Clone the repository
- Prompt for your optional `GOOGLE_API_KEY`
- Build and launch all 4 containers
- Verify container health and output your live URL!

---

### Method B: Zero-Touch Boot via AWS User Data (No SSH Required)

When creating your instance in the AWS Management Console:
1. Scroll down to **Advanced details**.
2. Locate the **User data** field.
3. Paste the contents of [`deploy/user-data.sh`](../deploy/user-data.sh).
4. Launch the instance!
5. In approximately 2–3 minutes, open your browser and navigate to `http://<EC2-PUBLIC-IP>`. TraceOps AI will already be live!

---

### Method C: Manual Step-by-Step Setup

If you prefer to run each step manually:

1. **Connect to your EC2 instance**:
   ```bash
   ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
   ```

2. **Install Docker and Docker Compose Plugin**:
   ```bash
   sudo apt-get update -y
   sudo apt-get install -y ca-certificates curl git
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker ubuntu
   newgrp docker
   ```

3. **Clone the Repository**:
   ```bash
   git clone https://github.com/umeshsatpathi/TraceOps-AI.git
   cd TraceOps-AI
   ```

4. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   nano .env
   ```
   Add your Gemini key if using AI features:
   ```dotenv
   GOOGLE_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-2.5-flash-lite
   ```

5. **Start All Services**:
   ```bash
   docker compose up -d --build
   ```

6. **Verify Status**:
   ```bash
   docker compose ps
   ```

---

## 3. Accessing Your Deployment

Once started, open your browser and access:
* **TraceOps AI Dashboard**: `http://<EC2-PUBLIC-IP>`
* **FastAPI Swagger API Docs**: `http://<EC2-PUBLIC-IP>/api/docs`

---

## 4. Useful Operations & Maintenance

### View Live Container Logs
```bash
# View backend logs:
docker compose logs -f backend

# View frontend logs:
docker compose logs -f frontend

# View FalkorDB logs:
docker compose logs -f falkordb
```

### Pull Updates & Redeploy
When you push new changes to GitHub, update your EC2 deployment with:
```bash
cd ~/TraceOps-AI
git pull origin main
docker compose up -d --build
```

### Stop or Restart
```bash
# Restart all containers:
docker compose restart

# Stop all containers:
docker compose down
```
