# AgriSecure IoT System - Backend

Backend Django per il sistema di monitoraggio agricolo e sicurezza perimetrale AgriSecure.

## 🏗️ Architettura

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                            │
│                    (React/Mobile App)                       │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST API / WebSocket
┌─────────────────────────┴───────────────────────────────────┐
│                      DJANGO BACKEND                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  REST API   │  │   Celery    │  │  MQTT Subscriber    │ │
│  │  (DRF)      │  │  (Tasks)    │  │  (paho-mqtt)        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└────────┬─────────────────┬────────────────┬─────────────────┘
         │                 │                │
    ┌────┴────┐      ┌────┴────┐     ┌─────┴─────┐
    │PostgreSQL│      │  Redis  │     │ Mosquitto │
    └─────────┘      └─────────┘     └─────┬─────┘
                                           │
                              ┌────────────┴────────────┐
                              │     GATEWAY 4G/LTE     │
                              │      (ESP32-C6)        │
                              └────────────────────────┘
```

## 📦 Requisiti di Sistema

- Ubuntu 22.04/24.04 LTS (o Debian 12)
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Mosquitto 2+
- Nginx

## 🚀 Installazione Rapida (da GitHub)

### 1. Clona il repository

```bash
cd /opt
sudo git clone https://github.com/turiliffiu/agrisecure-backend.git agrisecure
cd agrisecure
```

### 2. Esegui setup automatico

```bash
sudo bash scripts/setup.sh
```

Questo script:
- Installa tutte le dipendenze di sistema
- Crea utente `agrisecure`
- Configura PostgreSQL, Redis, Mosquitto
- Crea ambiente virtuale Python
- Genera file `.env`

### 3. Configura l'ambiente

```bash
sudo nano /opt/agrisecure/.env
```

Modifica almeno:
- `SECRET_KEY` (già generata automaticamente)
- `DB_PASSWORD` (se diversa da default)
- `MQTT_PASSWORD`
- Credenziali notifiche (Telegram, Email, ecc.)

### 4. Inizializza il database

```bash
cd /opt/agrisecure
sudo -u agrisecure venv/bin/python manage.py migrate
sudo -u agrisecure venv/bin/python manage.py createsuperuser
sudo -u agrisecure venv/bin/python manage.py collectstatic --noinput
```

### 5. Installa e avvia i servizi

```bash
sudo bash scripts/install_services.sh
sudo bash scripts/start_all.sh
```

### 6. Verifica installazione

```bash
# Stato servizi
sudo systemctl status agrisecure-*

# Test connessione
curl http://localhost/api/v1/nodes/
```

Accedi a:
- **Admin Django**: http://localhost/admin/
- **API Docs (Swagger)**: http://localhost/api/v1/docs/
- **API Docs (ReDoc)**: http://localhost/api/v1/redoc/

---

## 📖 Installazione Manuale Dettagliata

### Prerequisiti

```bash
# Aggiorna sistema
sudo apt update && sudo apt upgrade -y

# Installa dipendenze
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev \
    redis-server mosquitto mosquitto-clients \
    nginx git build-essential
```

### PostgreSQL

```bash
# Crea database e utente
sudo -u postgres psql << EOF
CREATE USER agrisecure WITH PASSWORD 'tua_password_sicura';
CREATE DATABASE agrisecure OWNER agrisecure;
GRANT ALL PRIVILEGES ON DATABASE agrisecure TO agrisecure;
EOF
```

### Redis

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### Mosquitto MQTT

```bash
# Crea password utente MQTT
sudo mosquitto_passwd -c /etc/mosquitto/passwd agrisecure

# Configurazione
sudo tee /etc/mosquitto/conf.d/agrisecure.conf << EOF
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd
persistence true
EOF

sudo systemctl enable mosquitto
sudo systemctl restart mosquitto
```

### Applicazione Django

```bash
# Crea utente sistema
sudo useradd -r -s /bin/bash -m agrisecure

# Clona repository
cd /opt
sudo git clone https://github.com/turiliffiu/agrisecure-backend.git agrisecure
sudo chown -R agrisecure:agrisecure /opt/agrisecure

# Ambiente virtuale
cd /opt/agrisecure
sudo -u agrisecure python3 -m venv venv
sudo -u agrisecure venv/bin/pip install --upgrade pip
sudo -u agrisecure venv/bin/pip install -r requirements.txt

# Configurazione
sudo -u agrisecure cp .env.example .env
sudo -u agrisecure nano .env  # Modifica le credenziali

# Migrazioni
sudo -u agrisecure venv/bin/python manage.py migrate
sudo -u agrisecure venv/bin/python manage.py createsuperuser
sudo -u agrisecure venv/bin/python manage.py collectstatic --noinput

# Crea directory
sudo -u agrisecure mkdir -p logs media
```

---

## 🔧 Gestione Servizi

### Comandi Utili

```bash
# Avvia tutti i servizi
sudo bash /opt/agrisecure/scripts/start_all.sh

# Ferma tutti i servizi
sudo bash /opt/agrisecure/scripts/stop_all.sh

# Stato servizi
sudo systemctl status agrisecure-web
sudo systemctl status agrisecure-celery
sudo systemctl status agrisecure-celery-beat
sudo systemctl status agrisecure-mqtt

# Log in tempo reale
sudo journalctl -u agrisecure-web -f
sudo journalctl -u agrisecure-mqtt -f

# Riavvio singolo servizio
sudo systemctl restart agrisecure-web
```

### Servizi Installati

| Servizio | Descrizione | Porta |
|----------|-------------|-------|
| `agrisecure-web` | Django + Gunicorn | unix socket |
| `agrisecure-celery` | Task worker asincroni | - |
| `agrisecure-celery-beat` | Scheduler task periodici | - |
| `agrisecure-mqtt` | Subscriber MQTT | - |
| `nginx` | Reverse proxy | 80/443 |
| `mosquitto` | MQTT Broker | 1883/9001 |
| `redis` | Cache/Broker | 6379 |
| `postgresql` | Database | 5432 |

---

## 📁 Struttura Progetto

```
/opt/agrisecure/
├── agrisecure/              # Configurazione Django
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── apps/
│   ├── core/                # MQTT publisher/subscriber
│   ├── nodes/               # Modelli nodi IoT
│   ├── sensors/             # Dati sensori
│   ├── security/            # Allarmi e sicurezza
│   ├── notifications/       # Sistema notifiche
│   └── api/                 # REST API
├── scripts/
│   ├── setup.sh             # Setup iniziale
│   ├── install_services.sh  # Installa systemd
│   ├── start_all.sh         # Avvia servizi
│   └── stop_all.sh          # Ferma servizi
├── logs/                    # File di log
├── media/                   # File caricati
├── staticfiles/             # File statici (collectstatic)
├── venv/                    # Ambiente virtuale Python
├── requirements.txt
├── .env                     # Configurazione (NON in git)
└── .env.example             # Template configurazione
```

---

## 🔌 API Endpoints

### Autenticazione
```
POST /api/v1/auth/token/          # Login, ottieni JWT
POST /api/v1/auth/token/refresh/  # Refresh token
```

### Nodi
```
GET    /api/v1/nodes/                    # Lista nodi
GET    /api/v1/nodes/{id}/               # Dettaglio nodo
GET    /api/v1/nodes/{id}/heartbeats/    # Storico heartbeat
POST   /api/v1/nodes/{id}/send_command/  # Invia comando
```

### Sensori
```
GET  /api/v1/sensors/readings/           # Letture sensori
GET  /api/v1/sensors/readings/latest/    # Ultime letture
GET  /api/v1/sensors/readings/chart_data/# Dati grafici
GET  /api/v1/sensors/alerts/             # Alert sensori
```

### Sicurezza
```
GET  /api/v1/security/events/            # Eventi movimento
GET  /api/v1/security/alarms/            # Lista allarmi
GET  /api/v1/security/alarms/active/     # Allarmi attivi
POST /api/v1/security/alarms/{id}/action/# Azione su allarme
GET  /api/v1/security/arm/               # Stato armamento
POST /api/v1/security/arm/               # Arma/Disarma
```

### Dashboard
```
GET  /api/v1/dashboard/summary/          # Riepilogo
GET  /api/v1/dashboard/charts/           # Dati grafici
```

---

## 📡 Topic MQTT

| Topic | Direzione | Descrizione |
|-------|-----------|-------------|
| `agrisecure/+/sensors/#` | IN | Dati sensori |
| `agrisecure/+/security/#` | IN | Eventi sicurezza |
| `agrisecure/+/status` | IN | Heartbeat |
| `agrisecure/{gw}/command` | OUT | Comandi |

---

## 🔔 Notifiche

Configura in `.env`:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=-100123456789

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_USER=tuo@email.com
EMAIL_PASSWORD=app_password

# SMS (Twilio)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+1234567890
```

---

## 🔄 Aggiornamento

```bash
cd /opt/agrisecure

# Ferma servizi
sudo bash scripts/stop_all.sh

# Pull aggiornamenti
sudo -u agrisecure git pull

# Aggiorna dipendenze
sudo -u agrisecure venv/bin/pip install -r requirements.txt

# Migrazioni
sudo -u agrisecure venv/bin/python manage.py migrate
sudo -u agrisecure venv/bin/python manage.py collectstatic --noinput

# Riavvia
sudo bash scripts/start_all.sh
```

---

## 🐛 Troubleshooting

### Il servizio web non parte
```bash
# Verifica log
sudo journalctl -u agrisecure-web -n 50

# Verifica socket
ls -la /run/agrisecure/

# Test manuale
cd /opt/agrisecure
sudo -u agrisecure venv/bin/python manage.py runserver 0.0.0.0:8000
```

### MQTT non riceve messaggi
```bash
# Verifica Mosquitto
sudo systemctl status mosquitto
sudo tail -f /var/log/mosquitto/mosquitto.log

# Test sottoscrizione
mosquitto_sub -h localhost -u agrisecure -P password -t "agrisecure/#" -v
```

### Database connection error
```bash
# Verifica PostgreSQL
sudo systemctl status postgresql
sudo -u postgres psql -c "\\l"  # Lista database
```

---

## 📄 Licenza

Proprietario - Turiliffiu © 2024

## 👥 Contatti

- **Progetto**: AgriSecure IoT System
- **Cliente**: Sig. Daniele Li Volsi
- **Sviluppo**: Turiliffiu
