#!/bin/bash
# ============================================================================
# AgriSecure IoT System - Script di Installazione Automatica
# Versione 2.0 - Con supporto WebSocket Real-time
# ============================================================================
# Eseguire su un container LXC Ubuntu 24.04 appena creato su Proxmox
# 
# Uso:
#   wget https://raw.githubusercontent.com/tuousername/agrisecure/main/backend/scripts/install.sh
#   chmod +x install.sh
#   sudo bash install.sh
#
# Oppure:
#   curl -sSL https://raw.githubusercontent.com/tuousername/agrisecure/main/backend/scripts/install.sh | sudo bash
# ============================================================================

set -e

# Colori output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurazione
INSTALL_DIR="/opt/agrisecure"
BACKEND_DIR="$INSTALL_DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"
USER="agrisecure"
REPO_URL="https://github.com/turiliffiu/agrisecure.git"

# Password di default (CAMBIARE IN PRODUZIONE!)
DB_PASSWORD="${DB_PASSWORD:-agrisecure_db_password}"
MQTT_PASSWORD="${MQTT_PASSWORD:-mqtt_secure_password}"

# ============================================================================
# Funzioni di utilità
# ============================================================================

print_header() {
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║    AgriSecure IoT - Installazione con WebSocket Real-time    ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}[$1/$TOTAL_STEPS]${NC} ${GREEN}$2${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "Questo script deve essere eseguito come root"
        echo "Usa: sudo bash install.sh"
        exit 1
    fi
}

TOTAL_STEPS=12

# ============================================================================
# Inizio installazione
# ============================================================================

print_header
check_root

echo ""
echo "Questo script installerà:"
echo "  - PostgreSQL, Redis, Mosquitto MQTT"
echo "  - Python 3, Nginx"
echo "  - Django backend con tutti i servizi"
echo "  - WebSocket real-time (Daphne, Channels)"
echo ""
echo "Directory di installazione: $INSTALL_DIR"
echo ""
read -p "Continuare? (s/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Installazione annullata."
    exit 0
fi

# ============================================================================
# Step 1: Aggiornamento sistema
# ============================================================================
print_step 1 "Aggiornamento sistema..."

apt update
apt upgrade -y

print_success "Sistema aggiornato"

# ============================================================================
# Step 2: Installazione dipendenze
# ============================================================================
print_step 2 "Installazione dipendenze di sistema..."

apt install -y \
    python3 python3-pip python3-venv python3-dev python3-paho-mqtt \
    postgresql postgresql-contrib libpq-dev \
    redis-server mosquitto mosquitto-clients \
    nginx git build-essential curl

print_success "Dipendenze installate"

# ============================================================================
# Step 3: Creazione utente di sistema
# ============================================================================
print_step 3 "Creazione utente di sistema..."

if ! id "$USER" &>/dev/null; then
    useradd -r -s /bin/bash -m -d /home/$USER $USER
    print_success "Utente $USER creato"
else
    print_warning "Utente $USER già esistente"
fi

# ============================================================================
# Step 4: Clone repository
# ============================================================================
print_step 4 "Download repository da GitHub..."

if [ -d "$INSTALL_DIR" ]; then
    print_warning "Directory $INSTALL_DIR già esistente, aggiornamento..."
    cd $INSTALL_DIR
    git pull
else
    git clone $REPO_URL $INSTALL_DIR
fi

# Crea directory necessarie
mkdir -p $BACKEND_DIR/logs
mkdir -p $BACKEND_DIR/media
mkdir -p $BACKEND_DIR/staticfiles
mkdir -p $BACKEND_DIR/static

chown -R $USER:$USER $INSTALL_DIR
print_success "Repository clonato in $INSTALL_DIR"

# ============================================================================
# Step 5: Configurazione PostgreSQL
# ============================================================================
print_step 5 "Configurazione PostgreSQL..."

# Verifica se il database esiste già
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw agrisecure; then
    print_warning "Database agrisecure già esistente"
else
    sudo -u postgres psql << EOF
CREATE USER agrisecure WITH PASSWORD '$DB_PASSWORD';
CREATE DATABASE agrisecure OWNER agrisecure;
GRANT ALL PRIVILEGES ON DATABASE agrisecure TO agrisecure;
EOF
    print_success "Database PostgreSQL creato"
fi

# ============================================================================
# Step 6: Configurazione Redis
# ============================================================================
print_step 6 "Configurazione Redis..."

# Configura Redis per Channel Layers
if ! grep -q "maxmemory" /etc/redis/redis.conf; then
    echo "maxmemory 256mb" >> /etc/redis/redis.conf
    echo "maxmemory-policy allkeys-lru" >> /etc/redis/redis.conf
    print_success "Redis configurato per Channel Layers"
fi

systemctl enable redis-server
systemctl restart redis-server

# Verifica connessione
if redis-cli ping | grep -q "PONG"; then
    print_success "Redis attivo e funzionante"
else
    print_error "Redis non risponde"
    exit 1
fi

# ============================================================================
# Step 7: Configurazione Mosquitto MQTT
# ============================================================================
print_step 7 "Configurazione Mosquitto MQTT con ACL..."

# Crea utente MQTT
mosquitto_passwd -c -b /etc/mosquitto/passwd agrisecure "$MQTT_PASSWORD"

# Configurazione Mosquitto con ACL per localhost
tee /etc/mosquitto/conf.d/agrisecure.conf > /dev/null << 'EOF'
# AgriSecure MQTT Configuration
listener 1883
allow_anonymous true
password_file /etc/mosquitto/passwd
acl_file /etc/mosquitto/acl

# Logging
log_dest file /var/log/mosquitto/mosquitto.log
log_type all

# Persistence
persistence true
persistence_location /var/lib/mosquitto/
EOF

# Crea ACL file
tee /etc/mosquitto/acl > /dev/null << 'EOF'
# AgriSecure ACL Configuration

# Permessi per utente autenticato agrisecure
user agrisecure
topic readwrite #

# Permessi per connessioni localhost (MQTT Bridge)
pattern readwrite #
EOF

# Imposta permessi
chown mosquitto:mosquitto /etc/mosquitto/passwd /etc/mosquitto/acl
chmod 640 /etc/mosquitto/passwd /etc/mosquitto/acl

systemctl enable mosquitto
systemctl restart mosquitto

# Verifica Mosquitto
sleep 2
if systemctl is-active --quiet mosquitto; then
    print_success "Mosquitto MQTT configurato con ACL"
else
    print_error "Mosquitto non si avvia"
    journalctl -u mosquitto -n 20
    exit 1
fi

# ============================================================================
# Step 8: Ambiente virtuale Python
# ============================================================================
print_step 8 "Creazione ambiente virtuale Python..."

cd $BACKEND_DIR

# Crea virtual environment
sudo -u $USER python3 -m venv venv
sudo -u $USER venv/bin/pip install --upgrade pip

# Installa requirements.txt
if [ -f requirements.txt ]; then
    sudo -u $USER venv/bin/pip install -r requirements.txt
else
    print_error "File requirements.txt non trovato!"
    exit 1
fi

# IMPORTANTE: Installa dipendenze WebSocket se non in requirements.txt
echo "  Verifica dipendenze WebSocket..."
sudo -u $USER venv/bin/pip install channels==4.0.0 channels-redis==4.1.0 daphne==4.0.0

# Verifica installazione
if sudo -u $USER venv/bin/python -c "import channels, daphne, channels_redis" 2>/dev/null; then
    print_success "Ambiente virtuale creato con supporto WebSocket"
else
    print_error "Errore installazione dipendenze WebSocket"
    exit 1
fi

# ============================================================================
# Step 9: Configurazione .env
# ============================================================================
print_step 9 "Creazione file di configurazione..."

# Genera SECRET_KEY casuale
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(45))')

# Ottieni IP del container
CONTAINER_IP=$(hostname -I | awk '{print $1}')

cat > $BACKEND_DIR/.env << EOF
# AgriSecure - Configurazione Ambiente
# Generato automaticamente il $(date)

# Django
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=localhost,127.0.0.1,agrisecure.local,$CONTAINER_IP

# Database
DATABASE_URL=postgres://agrisecure:$DB_PASSWORD@localhost:5432/agrisecure

# Redis
REDIS_URL=redis://localhost:6379/0

# MQTT
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USER=agrisecure
MQTT_PASSWORD=$MQTT_PASSWORD

# Telegram (configurare manualmente)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Email (configurare manualmente)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=
EMAIL_PASSWORD=
DEFAULT_FROM_EMAIL=AgriSecure <noreply@agrisecure.local>
EOF

chown $USER:$USER $BACKEND_DIR/.env
chmod 600 $BACKEND_DIR/.env
print_success "File .env creato con SECRET_KEY casuale"

# ============================================================================
# Step 10: Migrazioni Django
# ============================================================================
print_step 10 "Inizializzazione database Django..."

cd $BACKEND_DIR

# Crea le migrazioni per tutti i modelli
echo "  Creazione migrazioni..."
sudo -u $USER venv/bin/python manage.py makemigrations nodes sensors security core

# Applica tutte le migrazioni
echo "  Applicazione migrazioni..."
sudo -u $USER venv/bin/python manage.py migrate

# Raccogli file statici
echo "  Raccolta file statici..."
sudo -u $USER venv/bin/python manage.py collectstatic --noinput

print_success "Database inizializzato e file statici raccolti"

# ============================================================================
# Step 11: Creazione servizi systemd
# ============================================================================
print_step 11 "Installazione servizi systemd..."

# ============================================================================
# Servizio Gunicorn (Django HTTP)
# ============================================================================
cat > /etc/systemd/system/agrisecure-web.service << EOF
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

# ============================================================================
# Servizio Daphne (WebSocket) - NUOVO!
# ============================================================================
cat > /etc/systemd/system/agrisecure-daphne.service << EOF
[Unit]
Description=AgriSecure Daphne (WebSocket Server)
After=network.target redis.service postgresql.service
Requires=redis.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="PYTHONPATH=$BACKEND_DIR"
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$VENV_DIR/bin/daphne -b 127.0.0.1 -p 8001 agrisecure.asgi:application
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ============================================================================
# Servizio MQTT to WebSocket Bridge - NUOVO!
# ============================================================================
cat > /etc/systemd/system/agrisecure-mqtt-bridge.service << EOF
[Unit]
Description=AgriSecure MQTT to WebSocket Bridge
After=network.target mosquitto.service redis.service agrisecure-daphne.service
Requires=mosquitto.service redis.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="PYTHONPATH=$BACKEND_DIR"
Environment="DJANGO_SETTINGS_MODULE=agrisecure.settings"
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$VENV_DIR/bin/python scripts/mqtt_websocket_bridge.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ============================================================================
# Servizio Celery Worker
# ============================================================================
cat > /etc/systemd/system/agrisecure-celery.service << EOF
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

# ============================================================================
# Servizio Celery Beat
# ============================================================================
cat > /etc/systemd/system/agrisecure-celery-beat.service << EOF
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

# ============================================================================
# Servizio MQTT Subscriber (per salvataggio DB)
# ============================================================================
cat > /etc/systemd/system/agrisecure-mqtt.service << EOF
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

print_success "Servizi systemd creati (inclusi Daphne e MQTT Bridge)"

# ============================================================================
# Step 12: Configurazione Nginx
# ============================================================================
print_step 12 "Configurazione Nginx con supporto WebSocket..."

cat > /etc/nginx/sites-available/agrisecure << EOF
# AgriSecure IoT System - Nginx Configuration
# Con supporto WebSocket Real-time

upstream agrisecure_backend {
    server unix:/run/agrisecure/gunicorn.sock fail_timeout=0;
}

upstream agrisecure_websocket {
    server 127.0.0.1:8001 fail_timeout=0;
}

server {
    listen 80;
    server_name agrisecure.local localhost $CONTAINER_IP;

    access_log /var/log/nginx/agrisecure-access.log;
    error_log /var/log/nginx/agrisecure-error.log;

    client_max_body_size 10M;

    # WebSocket proxy per Daphne
    location /ws/ {
        proxy_pass http://agrisecure_websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }

    location /static/ {
        alias $BACKEND_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias $BACKEND_DIR/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://agrisecure_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        proxy_http_version 1.1;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health/ {
        proxy_pass http://agrisecure_backend;
        access_log off;
    }
}
EOF

# Abilita sito
ln -sf /etc/nginx/sites-available/agrisecure /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Test e riavvio Nginx
if nginx -t; then
    systemctl restart nginx
    print_success "Nginx configurato con supporto WebSocket"
else
    print_error "Errore nella configurazione Nginx"
    exit 1
fi

# ============================================================================
# Abilitazione e avvio servizi
# ============================================================================
echo ""
echo -e "${BLUE}Avvio servizi...${NC}"

systemctl daemon-reload

# Abilita tutti i servizi
systemctl enable agrisecure-web
systemctl enable agrisecure-daphne
systemctl enable agrisecure-mqtt-bridge
systemctl enable agrisecure-celery
systemctl enable agrisecure-celery-beat
systemctl enable agrisecure-mqtt

# Avvia servizi in ordine
systemctl start agrisecure-web
systemctl start agrisecure-daphne
systemctl start agrisecure-mqtt-bridge
systemctl start agrisecure-celery
systemctl start agrisecure-celery-beat
systemctl start agrisecure-mqtt

# Attendi che i servizi si avviino
sleep 5

# ============================================================================
# Verifica finale
# ============================================================================
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗"
echo -e "║           INSTALLAZIONE COMPLETATA CON SUCCESSO!              ║"
echo -e "╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}Stato servizi:${NC}"
for service in agrisecure-web agrisecure-daphne agrisecure-mqtt-bridge agrisecure-celery agrisecure-celery-beat agrisecure-mqtt; do
    if systemctl is-active --quiet $service; then
        echo -e "  ${GREEN}✓${NC} $service: ${GREEN}attivo${NC}"
    else
        echo -e "  ${RED}✗${NC} $service: ${RED}non attivo${NC}"
        echo -e "     ${YELLOW}Vedi log: journalctl -u $service -n 20${NC}"
    fi
done

echo ""
echo -e "${BLUE}Verifica componenti:${NC}"

# Verifica Redis
if redis-cli ping | grep -q "PONG"; then
    echo -e "  ${GREEN}✓${NC} Redis: ${GREEN}attivo${NC}"
else
    echo -e "  ${RED}✗${NC} Redis: ${RED}non risponde${NC}"
fi

# Verifica Mosquitto
if systemctl is-active --quiet mosquitto; then
    echo -e "  ${GREEN}✓${NC} Mosquitto: ${GREEN}attivo${NC}"
else
    echo -e "  ${RED}✗${NC} Mosquitto: ${RED}non attivo${NC}"
fi

# Verifica PostgreSQL
if systemctl is-active --quiet postgresql; then
    echo -e "  ${GREEN}✓${NC} PostgreSQL: ${GREEN}attivo${NC}"
else
    echo -e "  ${RED}✗${NC} PostgreSQL: ${RED}non attivo${NC}"
fi

# Verifica Nginx
if systemctl is-active --quiet nginx; then
    echo -e "  ${GREEN}✓${NC} Nginx: ${GREEN}attivo${NC}"
else
    echo -e "  ${RED}✗${NC} Nginx: ${RED}non attivo${NC}"
fi

echo ""
echo -e "${BLUE}Accessi:${NC}"
echo -e "  Dashboard Web: ${GREEN}http://$CONTAINER_IP/${NC}"
echo -e "  Admin Django:  ${GREEN}http://$CONTAINER_IP/admin/${NC}"
echo -e "  API Docs:      ${GREEN}http://$CONTAINER_IP/api/v1/docs/${NC}"
echo ""
echo -e "${GREEN}✓ WebSocket Real-time: abilitato${NC}"
echo -e "  Dashboard e Allarmi si aggiorneranno automaticamente!"
echo ""
echo -e "${YELLOW}IMPORTANTE: Crea un superuser per accedere al sistema:${NC}"
echo -e "  ${GREEN}sudo -u agrisecure $VENV_DIR/bin/python $BACKEND_DIR/manage.py createsuperuser${NC}"
echo ""
echo -e "${YELLOW}Configura Telegram/Email modificando:${NC}"
echo -e "  ${GREEN}nano $BACKEND_DIR/.env${NC}"
echo ""
echo -e "${BLUE}Comandi utili:${NC}"
echo -e "  Stato servizi:     ${GREEN}systemctl status agrisecure-*${NC}"
echo -e "  Log web:           ${GREEN}journalctl -u agrisecure-web -f${NC}"
echo -e "  Log WebSocket:     ${GREEN}journalctl -u agrisecure-daphne -f${NC}"
echo -e "  Log MQTT Bridge:   ${GREEN}journalctl -u agrisecure-mqtt-bridge -f${NC}"
echo -e "  Riavvia tutto:     ${GREEN}systemctl restart agrisecure-*${NC}"
echo ""
echo -e "${BLUE}Test WebSocket:${NC}"
echo -e "  1. Apri browser: ${GREEN}http://$CONTAINER_IP/${NC}"
echo -e "  2. Apri Console (F12)"
echo -e "  3. Cerca: ${GREEN}✅ Dashboard WebSocket connected${NC}"
echo -e "  4. Avvia simulator: ${GREEN}cd $BACKEND_DIR/scripts && python3 simulator_enhanced.py --auto --scenario stress_test --duration 60${NC}"
echo ""
echo -e "${GREEN}Per documentazione completa: docs/WEBSOCKET_SETUP.md${NC}"
echo ""
