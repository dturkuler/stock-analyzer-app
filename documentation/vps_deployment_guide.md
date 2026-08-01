# 🌐 Production VPS Deployment & Cloudflare Tunnel Guide (v2.3.0)

This guide provides step-by-step instructions for deploying **stock-analyzer-app** to a new Linux Virtual Private Server (VPS) (e.g. Hetzner, DigitalOcean, AWS EC2, Linode) using **Docker Compose** for container orchestration, host volume mounting for persistent storage, and **Cloudflare Tunnel (`cloudflared`)** for secure HTTPS access without exposing open inbound ports.

---

## 🏗️ Architecture Overview

```
                          ┌────────────────────────────────────────────────────────┐
                          │                Cloudflare Global Edge Network          │
                          │        (Free SSL/TLS, WAF, DDoS Protection)           │
                          └───────────────────────────┬────────────────────────────┘
                                                      │ Encrypted Outbound Tunnel
                                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ VPS Host Server (Ubuntu / Debian Linux)                                                          │
│                                                                                                  │
│   🔒 Firewall (UFW): Inbound Ports 80 & 443 BLOCKED                                              │
│                                                                                                  │
│   ⚙️ Host Systemd Service: cloudflared daemon                                                    │
│        └── Routes traffic to ──► localhost:6031                                                  │
│                                                                                                  │
│   🐳 Docker Compose Services (restart: always)                                                   │
│        ├── web (FastAPI Server on Port 6031)                                                     │
│        └── scheduler (APScheduler Cron Runner)                                                   │
│                                                                                                  │
│   💾 Persistent Host Volume: ./storage/                                                          │
│        ├── reports/ (Compiled HTML Dashboards & PDFs with Pre-rendered GFX SVG Charts)            │
│        ├── _workspace/ (JSON Metrics & 2-Stage LLM Commentary Cache)                             │
│        ├── app.db (SQLite Index, Watchlist & Versioned Schema Migrations)                        │
│        └── logs/ (cron.log, analysis.log, and errors.log)                                        │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Step 1: VPS Host Preparation & Docker Installation

Connect to your VPS via SSH and update system packages:

```bash
ssh root@YOUR_VPS_IP

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker & Docker Compose plugin
sudo apt install -y curl git ufw
curl -fsSL https://get.docker.com | sh

# Enable and start Docker service
sudo systemctl enable --now docker
```

---

## 📥 Step 2: Repository Cloning & Directory Setup

Clone the repository to your VPS host:

```bash
cd /opt
sudo git clone https://github.com/dturkuler/stock-analyzer-app.git
cd stock-analyzer-app

# Create persistent storage directories
mkdir -p storage/reports storage/_workspace storage/logs
chmod -R 775 storage
```

---

## ⚙️ Step 3: Environment Configuration (`.env`)

Create your production `.env` configuration file:

```bash
cp .env.example .env
nano .env
```

Set your production parameters:

```ini
# Production Admin Security
ADMIN_PASSWORD=YourSecureProductionPassword123!

# Output Report Language (TR or EN)
OUTPUT_LANGUAGE=TR

# LLM Provider Credentials
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-proj-your-production-llm-api-key

# Cron Scheduler Settings
CRON_DELAY_SECONDS=15
LLM_TIMEOUT=120
PORT=6031
```

---

## 🐳 Step 4: Docker Compose Launch & Test Runner Verification

Run automated test runner and deploy the container stack in production detached mode:

```bash
# Verify unit test suite
python3 tests/run_tests.py

# Build & start services
docker compose up -d --build

# Verify container status
docker compose ps
```

You should see both `stock_web` and `stock_scheduler` running cleanly:

```
NAME              IMAGE                     COMMAND                  SERVICE     CREATED         STATUS         PORTS
stock_web         stock-analyzer-app:latest  "python -m uvicorn 3…"   web         10 seconds ago  Up 10 seconds  0.0.0.0:6031->6031/tcp
stock_scheduler   stock-analyzer-app:latest  "python 2_cron_sched…"   scheduler   10 seconds ago  Up 10 seconds  
```

---

## ☁️ Step 5: Cloudflare Tunnel Installation (`cloudflared` Systemd)

1. Log into your [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/).
2. Navigate to **Networks** $\rightarrow$ **Tunnels** $\rightarrow$ **Create a Tunnel**.
3. Select **Cloudflared** connector and give it a name (e.g. `stock-analyzer-vps`).
4. Copy the installation command for **Debian / Ubuntu** and execute it on your VPS:

```bash
# Example Cloudflare Tunnel installation command
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
sudo cloudflared service install YOUR_CLOUDFLARE_TUNNEL_TOKEN
```

5. In Cloudflare Dashboard, configure the **Public Hostname**:
   - **Subdomain / Domain**: `stocks.yourdomain.com`
   - **Service Type**: `HTTP`
   - **URL**: `localhost:6031`

`cloudflared` will automatically establish an encrypted outbound tunnel to Cloudflare and provision a free SSL/TLS certificate for `https://stocks.yourdomain.com`!

---

## 🛡️ Step 6: Firewall Lockdown (UFW)

Since Cloudflare Tunnel routes traffic internally over a secure outbound connection, you can safely lock down all inbound HTTP/HTTPS web ports on your VPS firewall:

```bash
# Allow SSH access
sudo ufw allow 22/tcp

# Deny public inbound access to port 6031, 80, and 443
sudo ufw deny 80/tcp
sudo ufw deny 443/tcp
sudo ufw deny 6031/tcp

# Enable Firewall
sudo ufw enable
sudo ufw status
```

---

## 💾 Step 7: Storage Persistence & VPS Snapshots

All data is stored directly on the VPS host filesystem in `/opt/stock-analyzer-app/storage`:

- **HTML Reports & PDFs**: `/opt/stock-analyzer-app/storage/reports/`
- **Quantitative Metrics & LLM Caches**: `/opt/stock-analyzer-app/storage/_workspace/`
- **SQLite Database Index & Migrations**: `/opt/stock-analyzer-app/storage/app.db`
- **Execution & Error Logs**: `/opt/stock-analyzer-app/storage/logs/` (`cron.log`, `analysis.log`, `errors.log`)

### Disaster Recovery
To back up your deployment, take periodic **Cloud Provider Disk Snapshots** (e.g. Hetzner / DigitalOcean / AWS snapshots) of your VPS disk. If you ever migrate to a new VPS, simply copy your `/opt/stock-analyzer-app/storage` folder and `.env` file to the new server and run `docker compose up -d`.

---

## 🔄 Updating to New Releases

When a new version (e.g. `v2.3.0`+) is released:

```bash
cd /opt/stock-analyzer-app
git pull origin main
python3 tests/run_tests.py
docker compose up -d --build
```
