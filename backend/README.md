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

- Ubuntu 24.04 LTS (container LXC su Proxmox)
- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- Mosquitto 2+

## 🚀 Installazione Rapida

### Prerequisiti

Container LXC Ubuntu 24.04 su Proxmox:
- **CPU**: 2 cores
- **RAM**: 1 GB
- **Disco**: 15 GB
- **Rete**: DHCP

### Installazione Automatica

```bash
# Dentro il container
apt update && apt install -y git

# Clona repository
cd /opt
git clone https://github.com/turiliffiu/agrisecure.git
cd agrisecure/backend

# Esegui installazione automatica
sudo bash scripts/install.sh
```

Lo script installa e configura automaticamente:
- ✅ PostgreSQL (database `agrisecure`)
- ✅ Redis (cache e broker Celery)
- ✅ Mosquitto MQTT (broker IoT)
- ✅ Python 3 + ambiente virtuale
- ✅ Django + dipendenze
- ✅ Servizi systemd
- ✅ Nginx reverse proxy
- ✅ File `.env` con SECRET_KEY casuale

### Post-Installazione

```bash
# Crea superuser per accedere all'admin
sudo -u agrisecure /opt/agrisecure/backend/venv/bin/python /opt/agrisecure/backend/manage.py createsuperuser

# (Opzionale) Configura notifiche
sudo nano /opt/agrisecure/backend/.env
```

### Accesso

- **Admin Django**: http://IP_CONTAINER/admin/
- **API Docs (Swagger)**: http://IP_CONTAINER/api/v1/docs/
- **API Docs (ReDoc)**: http://IP_CONTAINER/api/v1/redoc/

---

## 📁 Struttura Progetto

```
/opt/agrisecure/backend/
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
│   ├── install.sh           # Installazione automatica
│   ├── install_services.sh  # Installa servizi systemd
│   ├── start_all.sh         # Avvia tutti i servizi
│   └── stop_all.sh          # Ferma tutti i servizi
├── logs/                    # File di log
├── media/                   # File caricati
├── staticfiles/             # File statici
├── venv/                    # Ambiente virtuale Python
├── requirements.txt
├── .env                     # Configurazione (NON in git)
└── .env.example             # Template configurazione
```

---

## 🔧 Gestione Servizi

### Comandi Utili

```bash
# Avvia tutti i servizi
sudo bash /opt/agrisecure/backend/scripts/start_all.sh

# Ferma tutti i servizi
sudo bash /opt/agrisecure/backend/scripts/stop_all.sh

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
| `nginx` | Reverse proxy | 80 |
| `mosquitto` | MQTT Broker | 1883 |
| `redis` | Cache/Broker | 6379 |
| `postgresql` | Database | 5432 |

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
POST /api/v1/security/alarms/{id}/perform_action/  # Azione su allarme
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

Configura in `/opt/agrisecure/backend/.env`:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=-100123456789

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=tuo@email.com
EMAIL_PASSWORD=app_password

# SMS (Twilio)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+1234567890
```

Dopo la modifica:
```bash
sudo systemctl restart agrisecure-celery
```

---

## 🔄 Aggiornamento

```bash
cd /opt/agrisecure

# Ferma servizi
sudo bash backend/scripts/stop_all.sh

# Pull aggiornamenti
sudo git pull

# Aggiorna dipendenze
sudo -u agrisecure backend/venv/bin/pip install -r backend/requirements.txt

# Migrazioni
sudo -u agrisecure backend/venv/bin/python backend/manage.py migrate
sudo -u agrisecure backend/venv/bin/python backend/manage.py collectstatic --noinput

# Riavvia
sudo bash backend/scripts/start_all.sh
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
cd /opt/agrisecure/backend
sudo -u agrisecure venv/bin/python manage.py runserver 0.0.0.0:8000
```

### MQTT non riceve messaggi
```bash
# Verifica Mosquitto
sudo systemctl status mosquitto
sudo tail -f /var/log/mosquitto/mosquitto.log

# Test sottoscrizione
mosquitto_sub -h localhost -u agrisecure -P mqtt_secure_password -t "agrisecure/#" -v
```

### Errore "Bad Request (400)"
Aggiungi l'IP del container in `.env`:
```
ALLOWED_HOSTS=localhost,127.0.0.1,agrisecure.local,TUO_IP
```
Poi: `sudo systemctl restart agrisecure-web`

### CSS/stili non caricati
Verifica `/etc/nginx/sites-available/agrisecure`:
```nginx
location /static/ {
    alias /opt/agrisecure/backend/staticfiles/;
}
```
Poi: `sudo systemctl restart nginx`

### Database connection error
```bash
# Verifica PostgreSQL
sudo systemctl status postgresql
sudo -u postgres psql -c "\l"
```

---

## 📄 Licenza

Proprietario - Turiliffiu © 2024-2025

## 👥 Contatti

- **Progetto**: AgriSecure IoT System
- **Cliente**: Sig. Daniele Li Volsi
- **Sviluppo**: Turiliffiu
