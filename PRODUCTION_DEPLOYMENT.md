# 🚀 Production Deployment Guide - Julia AI Multi-CRM Platform

## ✅ Pre-Deployment Checklist

### 1. Database Setup
- [ ] PostgreSQL 12+ installed and running
- [ ] Database created: `julia_ai`
- [ ] User created with proper permissions
- [ ] Test connection from app server

### 2. Environment Configuration
- [ ] Copy `.env.example` to `.env`
- [ ] Fill in all required credentials
- [ ] Set `DEBUG=False`
- [ ] Update database URL to PostgreSQL

### 3. Required Services
- [ ] Green API (WhatsApp) account configured
- [ ] OpenAI/Gemini API keys obtained
- [ ] At least one company added to database

### 4. Security
- [ ] SSL certificates obtained
- [ ] Firewall rules configured
- [ ] API keys secured (use secrets manager)
- [ ] CORS properly configured

---

## 📋 Step-by-Step Deployment

### Step 1: Prepare Server

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python and dependencies
sudo apt-get install -y python3.10 python3.10-venv python3-pip postgresql postgresql-contrib nginx supervisor git

# Create app user
sudo useradd -m -s /bin/bash julia
```

### Step 2: Clone Repository

```bash
cd /home/julia
git clone <your-repo> app
cd app
```

### Step 3: Setup Python Environment

```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### Step 4: Configure Environment

```bash
# Copy and edit .env
cp .env.example .env
nano .env

# Make sure to update:
# - DATABASE_URL (PostgreSQL connection)
# - API keys (OpenAI, Gemini, Green API)
# - DEBUG=False
```

### Step 5: Initialize Database

```bash
# Run migrations (creates tables)
python -c "
import asyncio
from database import engine, Base
asyncio.run(engine.run_sync(Base.metadata.create_all))
"

# Or run the app once (auto-creates tables on startup)
python main.py &
sleep 5
kill %1
```

### Step 6: Add Default Company

```bash
python add_companies.py
```

Follow the interactive wizard to add your companies.

### Step 7: Create Systemd Service

Create `/etc/systemd/system/julia.service`:

```ini
[Unit]
Description=Julia AI Multi-CRM Platform
After=network.target postgresql.service

[Service]
Type=notify
User=julia
WorkingDirectory=/home/julia/app
Environment="PATH=/home/julia/app/venv/bin"
EnvironmentFile=/home/julia/app/.env

ExecStart=/home/julia/app/venv/bin/gunicorn \
    -w 4 \
    -b 0.0.0.0:8000 \
    -k uvicorn.workers.UvicornWorker \
    --access-logfile /var/log/julia/access.log \
    --error-logfile /var/log/julia/error.log \
    main:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Step 8: Setup Logs

```bash
sudo mkdir -p /var/log/julia
sudo chown julia:julia /var/log/julia
sudo chmod 750 /var/log/julia
```

### Step 9: Configure Nginx Reverse Proxy

Create `/etc/nginx/sites-available/julia`:

```nginx
upstream julia {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.example.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 10M;

    location / {
        proxy_pass http://julia;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /static {
        alias /home/julia/app/static;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/julia /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 10: Setup SSL with Certbot

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot certonly --nginx -d api.example.com
```

### Step 11: Start Services

```bash
# Enable and start Julia service
sudo systemctl enable julia
sudo systemctl start julia

# Check status
sudo systemctl status julia

# View logs
sudo journalctl -u julia -f
```

### Step 12: Verify Deployment

```bash
# Health check
curl https://api.example.com/health

# List companies
curl https://api.example.com/api/companies

# Check dashboard
# Open https://api.example.com/dashboard in browser
```

---

## 🐳 Docker Deployment (Alternative)

### Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy app
COPY . .

# Create logs directory
RUN mkdir -p /var/log/julia

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run gunicorn
CMD ["gunicorn", \
    "-w", "4", \
    "-b", "0.0.0.0:8000", \
    "-k", "uvicorn.workers.UvicornWorker", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "main:app"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: julia_ai
      POSTGRES_USER: julia
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - db_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  app:
    build: .
    environment:
      DATABASE_URL: postgresql+asyncpg://julia:${DB_PASSWORD}@db:5432/julia_ai
      DEBUG: "False"
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      GREEN_API_ID_INSTANCE: ${GREEN_API_ID_INSTANCE}
      GREEN_API_API_TOKEN_INSTANCE: ${GREEN_API_API_TOKEN_INSTANCE}
    ports:
      - "8000:8000"
    depends_on:
      - db
    volumes:
      - ./logs:/var/log/julia
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - app
    restart: always

volumes:
  db_data:
```

Deploy with:
```bash
docker-compose up -d
```

---

## 📊 Monitoring & Maintenance

### Logs

```bash
# App logs
sudo journalctl -u julia -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log

# Database logs
sudo tail -f /var/log/postgresql/postgresql.log
```

### Health Monitoring

```bash
# Check every minute
*/1 * * * * curl -f http://localhost:8000/health || systemctl restart julia
```

### Database Backup

```bash
# Daily backup
0 2 * * * pg_dump julia_ai > /backups/julia_$(date +\%Y\%m\%d).sql

# With compression
0 2 * * * pg_dump julia_ai | gzip > /backups/julia_$(date +\%Y\%m\%d).sql.gz
```

### Log Rotation

Create `/etc/logrotate.d/julia`:

```
/var/log/julia/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 julia julia
    sharedscripts
    postrotate
        systemctl reload julia > /dev/null 2>&1 || true
    endscript
}
```

---

## 🔐 Security Hardening

### 1. Firewall Rules (UFW)

```bash
sudo ufw enable
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 5432/tcp    # PostgreSQL (internal only)
```

### 2. PostgreSQL Security

```sql
-- Create dedicated user
CREATE USER julia WITH PASSWORD 'strong_password';
CREATE DATABASE julia_ai OWNER julia;

-- Restrict access
REVOKE CONNECT ON DATABASE julia_ai FROM PUBLIC;
GRANT CONNECT ON DATABASE julia_ai TO julia;
```

### 3. API Rate Limiting

Add to `main.py`:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/webhook/whatsapp")
@limiter.limit("100/minute")
async def webhook_whatsapp(request: Request):
    ...
```

### 4. HTTPS/SSL

```bash
# Auto-renew Let's Encrypt certificates
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## 📈 Scaling

### Load Balancing (Multiple App Servers)

```nginx
upstream julia_backend {
    server app1.example.com:8000;
    server app2.example.com:8000;
    server app3.example.com:8000;
}

server {
    listen 443 ssl;
    server_name api.example.com;
    
    location / {
        proxy_pass http://julia_backend;
    }
}
```

### Caching Layer (Redis)

```python
# In config.py
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Cache CRM adapters
async def get_crm_adapter(company_id: int):
    cache_key = f"crm_adapter_{company_id}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    # ... create adapter, cache for 1 hour
```

---

## ✅ Post-Deployment Checklist

- [ ] Application running and accessible
- [ ] Health check returning 200
- [ ] API endpoints responding
- [ ] Companies configured
- [ ] CRM connections tested
- [ ] Webhooks working
- [ ] Logs being written
- [ ] Backups configured
- [ ] Monitoring active
- [ ] SSL certificates valid

---

## 🆘 Troubleshooting

### Application not starting

```bash
# Check logs
sudo journalctl -u julia -n 100

# Verify environment
source /home/julia/app/.env
python main.py

# Check database connection
python -c "from database import engine; print(engine.url)"
```

### Database connection errors

```bash
# Test PostgreSQL connection
psql -U julia -d julia_ai -h localhost

# Check credentials in .env
grep DATABASE_URL .env
```

### High memory usage

```bash
# Restart application
sudo systemctl restart julia

# Check logs for memory leaks
sudo journalctl -u julia | grep "memory\|ERROR"
```

---

**Deployment Complete! 🎉 Your Julia AI platform is live and ready for production use.**
