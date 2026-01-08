# MindStack Deployment Guide

## Overview

Hướng dẫn triển khai MindStack lên các môi trường production khác nhau.

---

## 📋 Pre-Deployment Checklist

- [ ] Database đã có backup
- [ ] Environment variables đã cấu hình
- [ ] Static files đã được tối ưu
- [ ] Requirements đã được kiểm tra

---

## 🌐 Deployment Options

### Option 1: Render (Recommended)

**Ưu điểm**: Free tier, auto-deploy từ GitHub

**Bước 1**: Tạo file `render.yaml`
```yaml
services:
  - type: web
    name: mindstack
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn "mindstack_app:create_app()" --bind 0.0.0.0:$PORT
    envVars:
      - key: SECRET_KEY
        generateValue: true
      - key: FLASK_ENV
        value: production
```

**Bước 2**: Thêm Gunicorn vào requirements
```bash
pip install gunicorn
pip freeze | grep gunicorn >> requirements.txt
```

**Bước 3**: Tạo `Procfile` (optional)
```
web: gunicorn "mindstack_app:create_app()" --bind 0.0.0.0:$PORT
```

---

### Option 2: Railway

**Bước 1**: Đăng nhập Railway CLI
```bash
npm install -g @railway/cli
railway login
```

**Bước 2**: Deploy
```bash
railway init
railway up
```

**Bước 3**: Set environment variables
```bash
railway variables set SECRET_KEY=your_secret_key
railway variables set FLASK_ENV=production
```

---

### Option 3: VPS (Ubuntu)

**Bước 1**: Setup server
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3.12 python3.12-venv python3-pip -y

# Install Nginx
sudo apt install nginx -y
```

**Bước 2**: Clone và setup
```bash
# Clone project
git clone <your-repo> /var/www/mindstack
cd /var/www/mindstack

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

**Bước 3**: Tạo systemd service
```ini
# /etc/systemd/system/mindstack.service
[Unit]
Description=MindStack Flask App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/mindstack
Environment="PATH=/var/www/mindstack/venv/bin"
ExecStart=/var/www/mindstack/venv/bin/gunicorn --workers 3 --bind unix:mindstack.sock -m 007 "mindstack_app:create_app()"

[Install]
WantedBy=multi-user.target
```

**Bước 4**: Cấu hình Nginx
```nginx
# /etc/nginx/sites-available/mindstack
server {
    listen 80;
    server_name your_domain.com;

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/mindstack/mindstack.sock;
    }

    location /static {
        alias /var/www/mindstack/mindstack_app/static;
    }
    
    location /uploads {
        alias /var/www/mindstack/uploads;
    }
}
```

**Bước 5**: Start services
```bash
sudo systemctl start mindstack
sudo systemctl enable mindstack
sudo ln -s /etc/nginx/sites-available/mindstack /etc/nginx/sites-enabled
sudo systemctl restart nginx
```

---

### Option 4: Docker

**Bước 1**: Tạo `Dockerfile`
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy source
COPY . .

# Create directories
RUN mkdir -p database uploads backups

# Expose port
EXPOSE 5000

# Run
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "mindstack_app:create_app()"]
```

**Bước 2**: Tạo `docker-compose.yml`
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - FLASK_ENV=production
    volumes:
      - ./database:/app/database
      - ./uploads:/app/uploads
      - ./backups:/app/backups
```

**Bước 3**: Build và run
```bash
docker-compose up -d --build
```

---

## 🔧 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ | - | Flask secret key |
| `FLASK_ENV` | ❌ | development | Environment mode |
| `SQLALCHEMY_DATABASE_URI` | ❌ | sqlite:///... | Database URI |
| `VAPID_PRIVATE_KEY` | ❌ | (built-in) | Web push private key |
| `VAPID_PUBLIC_KEY` | ❌ | (built-in) | Web push public key |
| `VAPID_EMAIL` | ❌ | admin@mindstack.app | VAPID email |

### Tạo Secret Key
```python
import secrets
print(secrets.token_hex(32))
```

---

## 📁 Directory Structure (Production)

```
/var/www/mindstack/
├── mindstack_app/     # Source code
├── database/          # SQLite database
│   └── mindstack_new.db
├── uploads/           # User uploads
│   └── flashcard/
│       ├── audio/
│       └── images/
├── backups/           # Database backups
├── venv/              # Virtual environment
└── logs/              # Application logs
```

---

## 🔒 SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d your_domain.com

# Auto-renewal
sudo certbot renew --dry-run
```

---

## 📊 Monitoring

### Logs
```bash
# Application logs
journalctl -u mindstack -f

# Nginx access logs
tail -f /var/log/nginx/access.log

# Nginx error logs
tail -f /var/log/nginx/error.log
```

### Health Check
```bash
curl -I http://localhost:5000/
```

---

## 🔄 Update Deployment

```bash
# SSH into server
cd /var/www/mindstack

# Pull latest code
git pull origin main

# Activate venv
source venv/bin/activate

# Update dependencies
pip install -r requirements.txt

# Restart service
sudo systemctl restart mindstack
```

---

## ⚠️ Common Issues

| Issue | Solution |
|-------|----------|
| Database locked | Check file permissions, use WAL mode |
| Static files 404 | Verify Nginx config, run collectstatic |
| Memory error | Increase server RAM or reduce workers |
| Port in use | Check `lsof -i :5000`, kill process |

---

## 📚 References

- [Render Docs](https://render.com/docs)
- [Railway Docs](https://docs.railway.app)
- [Gunicorn Config](https://docs.gunicorn.org/en/stable/configure.html)
- [Nginx + Flask](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu)
