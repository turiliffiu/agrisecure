#!/bin/bash
# ============================================================================
# AgriSecure IoT System - Script di Installazione Automatica
# ============================================================================
# Eseguire su un container LXC Ubuntu 24.04 appena creato su Proxmox
# 
# Uso:
#   wget https://raw.githubusercontent.com/turiliffiu/agrisecure/main/backend/scripts/install.sh
#   chmod +x install.sh
#   sudo bash install.sh
#
# Oppure:
#   curl -sSL https://raw.githubusercontent.com/turiliffiu/agrisecure/main/backend/scripts/install.sh | sudo bash
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
    echo "║         AgriSecure IoT System - Installazione Automatica      ║"
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
    python3 python3-pip python3-venv python3-dev \
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
    git pull > /dev/null 2>&1
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

systemctl enable redis-server
systemctl start redis-server
print_success "Redis avviato"

# ============================================================================
# Step 7: Configurazione Mosquitto MQTT
# ============================================================================
print_step 7 "Configurazione Mosquitto MQTT..."

# Crea utente MQTT
mosquitto_passwd -c -b /etc/mosquitto/passwd agrisecure "$MQTT_PASSWORD"

# Configurazione Mosquitto (senza persistence_location per evitare duplicati)
tee /etc/mosquitto/conf.d/agrisecure.conf > /dev/null << 'EOF'
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd
EOF

systemctl enable mosquitto
systemctl restart mosquitto
print_success "Mosquitto MQTT configurato"

# ============================================================================
# Step 8: Ambiente virtuale Python
# ============================================================================
print_step 8 "Creazione ambiente virtuale Python..."

cd $BACKEND_DIR
sudo -u $USER python3 -m venv venv
sudo -u $USER venv/bin/pip install --upgrade pip
sudo -u $USER venv/bin/pip install -r requirements.txt
print_success "Ambiente virtuale creato e dipendenze installate"

# ============================================================================
# Step 9: Configurazione .env
# ============================================================================
print_step 9 "Creazione file di configurazione..."

# Genera SECRET_KEY casuale
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')

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

# Servizio Gunicorn (Django)
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

# Servizio Celery Worker
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

# Servizio Celery Beat
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

# Servizio MQTT Subscriber
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

print_success "Servizi systemd creati"

# ============================================================================
# Step 12: Configurazione Nginx
# ============================================================================
print_step 12 "Configurazione Nginx..."

cat > /etc/nginx/sites-available/agrisecure << EOF
# AgriSecure IoT System - Nginx Configuration

upstream agrisecure_backend {
    server unix:/run/agrisecure/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name agrisecure.local localhost $CONTAINER_IP;

    access_log /var/log/nginx/agrisecure-access.log;
    error_log /var/log/nginx/agrisecure-error.log;

    client_max_body_size 10M;

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
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
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
rm -f /etc/nginx/sites-enabled/default 2

# Test e riavvio Nginx
nginx -t
systemctl restart nginx

print_success "Nginx configurato"

# ============================================================================
# Abilitazione e avvio servizi
# ============================================================================
echo ""
echo -e "${BLUE}Avvio servizi...${NC}"

systemctl daemon-reload

systemctl enable agrisecure-web
systemctl enable agrisecure-celery
systemctl enable agrisecure-celery-beat
systemctl enable agrisecure-mqtt

systemctl start agrisecure-web
systemctl start agrisecure-celery
systemctl start agrisecure-celery-beat
systemctl start agrisecure-mqtt

# Attendi che i servizi si avviino
sleep 3

# ============================================================================
# Verifica finale
# ============================================================================
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗"
echo -e "║           INSTALLAZIONE COMPLETATA CON SUCCESSO!              ║"
echo -e "╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}Stato servizi:${NC}"
for service in agrisecure-web agrisecure-celery agrisecure-celery-beat agrisecure-mqtt; do
    if systemctl is-active --quiet $service; then
        echo -e "  ${GREEN}✓${NC} $service: ${GREEN}attivo${NC}"
    else
        echo -e "  ${RED}✗${NC} $service: ${RED}non attivo${NC}"
    fi
done

echo ""
echo -e "${BLUE}Accessi:${NC}"
echo -e "  Dashboard Web: ${GREEN}http://$CONTAINER_IP/${NC}"
echo -e "  Admin Django:  ${GREEN}http://$CONTAINER_IP/admin/${NC}"
echo -e "  API Docs:      ${GREEN}http://$CONTAINER_IP/api/v1/docs/${NC}"
echo ""
echo -e "${YELLOW}IMPORTANTE: Crea un superuser per accedere al sistema:${NC}"
echo -e "  ${GREEN}sudo -u agrisecure $VENV_DIR/bin/python $BACKEND_DIR/manage.py createsuperuser${NC}"
echo ""
echo -e "${YELLOW}Configura Telegram/Email modificando:${NC}"
echo -e "  ${GREEN}nano $BACKEND_DIR/.env${NC}"
echo ""
echo -e "${BLUE}Comandi utili:${NC}"
echo -e "  Stato servizi:  ${GREEN}systemctl status agrisecure-*${NC}"
echo -e "  Log web:        ${GREEN}journalctl -u agrisecure-web -f${NC}"
echo -e "  Riavvia tutto:  ${GREEN}systemctl restart agrisecure-*${NC}"
echo ""
