#!/bin/bash
# AgriSecure IoT System - Installazione Servizi Systemd
# Crea e abilita tutti i servizi necessari

set -e

# Colori
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="/opt/agrisecure"
BACKEND_DIR="$INSTALL_DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"
USER="agrisecure"

echo -e "${GREEN}Installazione servizi systemd per AgriSecure...${NC}"

# ============================================
# Servizio Gunicorn (Django)
# ============================================
echo -e "${GREEN}[1/5] Creazione servizio Gunicorn...${NC}"

sudo tee /etc/systemd/system/agrisecure-web.service > /dev/null << EOF
[Unit]
Description=AgriSecure Django Web Server
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=$USER
Group=$USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$VENV_DIR/bin/gunicorn \\
    --workers 3 \\
    --bind unix:/run/agrisecure/gunicorn.sock \\
    --access-logfile $BACKEND_DIR/logs/gunicorn-access.log \\
    --error-logfile $BACKEND_DIR/logs/gunicorn-error.log \\
    --capture-output \\
    --timeout 120 \\
    agrisecure.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
RuntimeDirectory=agrisecure
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# ============================================
# Servizio Celery Worker
# ============================================
echo -e "${GREEN}[2/5] Creazione servizio Celery Worker...${NC}"

sudo tee /etc/systemd/system/agrisecure-celery.service > /dev/null << EOF
[Unit]
Description=AgriSecure Celery Worker
After=network.target postgresql.service redis.service

[Service]
Type=forking
User=$USER
Group=$USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$VENV_DIR/bin/celery -A agrisecure multi start worker \\
    --pidfile=$BACKEND_DIR/logs/celery-%n.pid \\
    --logfile=$BACKEND_DIR/logs/celery-%n.log \\
    --loglevel=INFO \\
    --concurrency=2
ExecStop=$VENV_DIR/bin/celery -A agrisecure multi stopwait worker \\
    --pidfile=$BACKEND_DIR/logs/celery-%n.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# ============================================
# Servizio Celery Beat (Scheduler)
# ============================================
echo -e "${GREEN}[3/5] Creazione servizio Celery Beat...${NC}"

sudo tee /etc/systemd/system/agrisecure-celery-beat.service > /dev/null << EOF
[Unit]
Description=AgriSecure Celery Beat Scheduler
After=network.target postgresql.service redis.service agrisecure-celery.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$VENV_DIR/bin/celery -A agrisecure beat \\
    --loglevel=INFO \\
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \\
    --pidfile=$BACKEND_DIR/logs/celery-beat.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# ============================================
# Servizio MQTT Subscriber
# ============================================
echo -e "${GREEN}[4/5] Creazione servizio MQTT Subscriber...${NC}"

sudo tee /etc/systemd/system/agrisecure-mqtt.service > /dev/null << EOF
[Unit]
Description=AgriSecure MQTT Subscriber
After=network.target postgresql.service mosquitto.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$VENV_DIR/bin/python manage.py mqtt_subscriber
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# ============================================
# Configurazione Nginx
# ============================================
echo -e "${GREEN}[5/5] Configurazione Nginx...${NC}"

# Ottieni IP del container
CONTAINER_IP=$(hostname -I | awk '{print $1}')

sudo tee /etc/nginx/sites-available/agrisecure > /dev/null << EOF
# AgriSecure IoT System - Nginx Configuration

upstream agrisecure_backend {
    server unix:/run/agrisecure/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name agrisecure.local localhost $CONTAINER_IP;

    # Logs
    access_log /var/log/nginx/agrisecure-access.log;
    error_log /var/log/nginx/agrisecure-error.log;

    # Max upload size
    client_max_body_size 10M;

    # Static files
    location /static/ {
        alias $BACKEND_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias $BACKEND_DIR/media/;
        expires 7d;
    }

    # Django application
    location / {
        proxy_pass http://agrisecure_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeout
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check
    location /health/ {
        proxy_pass http://agrisecure_backend;
        access_log off;
    }
}
EOF

# Abilita sito Nginx
sudo ln -sf /etc/nginx/sites-available/agrisecure /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Test configurazione Nginx
sudo nginx -t

# ============================================
# Abilita e avvia servizi
# ============================================
echo -e "${GREEN}Ricarico systemd e abilito servizi...${NC}"

sudo systemctl daemon-reload

# Abilita servizi
sudo systemctl enable agrisecure-web
sudo systemctl enable agrisecure-celery
sudo systemctl enable agrisecure-celery-beat
sudo systemctl enable agrisecure-mqtt

# Riavvia Nginx
sudo systemctl restart nginx

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗"
echo -e "║           Servizi systemd installati!                      ║"
echo -e "╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Comandi utili:"
echo -e "  ${YELLOW}sudo systemctl start agrisecure-web${NC}      # Avvia Django"
echo -e "  ${YELLOW}sudo systemctl start agrisecure-celery${NC}   # Avvia Celery"
echo -e "  ${YELLOW}sudo systemctl start agrisecure-mqtt${NC}     # Avvia MQTT Subscriber"
echo ""
echo -e "  ${YELLOW}sudo systemctl status agrisecure-*${NC}       # Stato tutti i servizi"
echo -e "  ${YELLOW}sudo journalctl -u agrisecure-web -f${NC}     # Log in tempo reale"
echo ""
echo -e "Avvia tutti i servizi:"
echo -e "  ${YELLOW}sudo bash $BACKEND_DIR/scripts/start_all.sh${NC}"
echo ""
