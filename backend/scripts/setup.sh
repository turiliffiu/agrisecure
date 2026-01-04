#!/bin/bash
# AgriSecure IoT System - Setup Script
# Installazione backend Django con venv su Ubuntu/Debian

set -e

# Colori output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         AgriSecure IoT System - Setup Backend             ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verifica root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Nota: Alcuni comandi potrebbero richiedere sudo${NC}"
fi

# Directory di installazione
INSTALL_DIR="${INSTALL_DIR:-/opt/agrisecure}"
VENV_DIR="$INSTALL_DIR/venv"
USER="${AGRISECURE_USER:-agrisecure}"

echo -e "${GREEN}[1/8] Installazione dipendenze di sistema...${NC}"
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    postgresql \
    postgresql-contrib \
    redis-server \
    mosquitto \
    mosquitto-clients \
    nginx \
    git \
    build-essential \
    libpq-dev \
    supervisor

echo -e "${GREEN}[2/8] Creazione utente di sistema...${NC}"
if ! id "$USER" &>/dev/null; then
    sudo useradd -r -s /bin/bash -m -d /home/$USER $USER
    echo -e "${GREEN}Utente $USER creato${NC}"
else
    echo -e "${YELLOW}Utente $USER già esistente${NC}"
fi

echo -e "${GREEN}[3/8] Creazione directory progetto...${NC}"
sudo mkdir -p $INSTALL_DIR
sudo mkdir -p $INSTALL_DIR/logs
sudo mkdir -p $INSTALL_DIR/media
sudo mkdir -p $INSTALL_DIR/staticfiles

# Copia file se siamo nella directory del progetto
if [ -f "manage.py" ]; then
    echo "Copia file progetto in $INSTALL_DIR..."
    sudo cp -r . $INSTALL_DIR/
fi

sudo chown -R $USER:$USER $INSTALL_DIR

echo -e "${GREEN}[4/8] Configurazione PostgreSQL...${NC}"
# Verifica se il database esiste già
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw agrisecure; then
    echo -e "${YELLOW}Database agrisecure già esistente${NC}"
else
    sudo -u postgres psql << EOF
CREATE USER agrisecure WITH PASSWORD 'agrisecure_db_password';
CREATE DATABASE agrisecure OWNER agrisecure;
GRANT ALL PRIVILEGES ON DATABASE agrisecure TO agrisecure;
EOF
    echo -e "${GREEN}Database PostgreSQL creato${NC}"
fi

echo -e "${GREEN}[5/8] Configurazione Redis...${NC}"
sudo systemctl enable redis-server
sudo systemctl start redis-server

echo -e "${GREEN}[6/8] Configurazione Mosquitto MQTT...${NC}"
# Crea file password Mosquitto
sudo mosquitto_passwd -c -b /etc/mosquitto/passwd agrisecure mqtt_secure_password

# Configurazione Mosquitto
sudo tee /etc/mosquitto/conf.d/agrisecure.conf > /dev/null << 'EOF'
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd

listener 9001
protocol websockets

persistence true
persistence_location /var/lib/mosquitto/

log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
log_type notice
EOF

sudo systemctl enable mosquitto
sudo systemctl restart mosquitto

echo -e "${GREEN}[7/8] Creazione ambiente virtuale Python...${NC}"
sudo -u $USER python3 -m venv $VENV_DIR

# Installa dipendenze Python
sudo -u $USER $VENV_DIR/bin/pip install --upgrade pip
sudo -u $USER $VENV_DIR/bin/pip install -r $INSTALL_DIR/requirements.txt

echo -e "${GREEN}[8/8] Configurazione file .env...${NC}"
if [ ! -f "$INSTALL_DIR/.env" ]; then
    sudo -u $USER cp $INSTALL_DIR/.env.example $INSTALL_DIR/.env
    
    # Genera SECRET_KEY
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
    sudo sed -i "s/your-very-long-and-secure-secret-key-here-change-me/$SECRET_KEY/" $INSTALL_DIR/.env
    
    echo -e "${YELLOW}File .env creato - MODIFICA LE CREDENZIALI!${NC}"
    echo -e "${YELLOW}  sudo nano $INSTALL_DIR/.env${NC}"
else
    echo -e "${YELLOW}File .env già esistente${NC}"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗"
echo -e "║              Setup base completato!                        ║"
echo -e "╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Prossimi passi:"
echo -e "  1. Modifica configurazione: ${YELLOW}sudo nano $INSTALL_DIR/.env${NC}"
echo -e "  2. Esegui migrazioni: ${YELLOW}sudo -u $USER $VENV_DIR/bin/python $INSTALL_DIR/manage.py migrate${NC}"
echo -e "  3. Crea superuser: ${YELLOW}sudo -u $USER $VENV_DIR/bin/python $INSTALL_DIR/manage.py createsuperuser${NC}"
echo -e "  4. Installa servizi: ${YELLOW}sudo bash $INSTALL_DIR/scripts/install_services.sh${NC}"
echo ""
