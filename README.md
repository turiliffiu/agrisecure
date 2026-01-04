# 🌿 AgriSecure IoT System

Sistema IoT completo per **monitoraggio agricolo** e **sicurezza perimetrale**.

Sviluppato da **Turiliffiu** per il Sig. Daniele Li Volsi.

---

## 📋 Panoramica

AgriSecure è un sistema IoT end-to-end per:

- 🌡️ **Monitoraggio Ambientale**: temperatura, umidità, pressione, luminosità, umidità suolo
- 🚨 **Sicurezza Perimetrale**: rilevamento movimento con discriminazione persona/animale
- 📡 **Connettività**: rete mesh WiFi/ESP-NOW + gateway 4G/LTE
- 📱 **Dashboard & API**: interfaccia web e API REST per controllo remoto
- 🔔 **Notifiche**: Telegram, SMS, Email, Push notifications

---

## 🏗️ Architettura

```
┌─────────────────────────────────────────────────────────────┐
│                     📱 DASHBOARD/APP                        │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST API
┌─────────────────────────┴───────────────────────────────────┐
│                   🖥️ BACKEND (Django)                       │
│              PostgreSQL │ Redis │ Celery                    │
└─────────────────────────┬───────────────────────────────────┘
                          │ MQTT
┌─────────────────────────┴───────────────────────────────────┐
│                   📡 MOSQUITTO BROKER                       │
└─────────────────────────┬───────────────────────────────────┘
                          │ 4G/LTE
┌─────────────────────────┴───────────────────────────────────┐
│                   🌐 GATEWAY (ESP32-C6)                     │
│                      SIM7670E + GPS                         │
└─────────────────────────┬───────────────────────────────────┘
                          │ ESP-NOW Mesh
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────┴────┐     ┌────┴────┐     ┌─────┴────┐
    │ 🌡️ AMB  │     │ 🌡️ AMB  │     │ 🚨 SEC  │
    │  Node   │     │  Node   │     │  Node   │
    └─────────┘     └─────────┘     └──────────┘
```

---

## 📦 Componenti del Repository

```
agrisecure/
├── backend/          # Django REST API + MQTT Subscriber
├── firmware/         # ESP32-C6 PlatformIO firmware
└── docs/             # Documentazione aggiuntiva
```

### 🖥️ Backend (`/backend`)

- **Framework**: Django 5.0 + Django REST Framework
- **Database**: PostgreSQL
- **Cache/Broker**: Redis
- **Task Queue**: Celery
- **MQTT**: paho-mqtt

### ⚡ Firmware (`/firmware`)

- **MCU**: ESP32-C6-DevKitC-1
- **Framework**: Arduino/PlatformIO
- **Comunicazione**: ESP-NOW mesh + 4G/LTE
- **Sensori**: BME280, BH1750, soil sensor, PIR, MPU6050

---

## 🚀 Quick Start

### 1. Installa il Backend

**Prerequisiti:** Container LXC Ubuntu 24.04 su Proxmox
- CPU: 2 cores
- RAM: 1 GB
- Disco: 15 GB
- Rete: DHCP

**Installazione automatica:**

Sulla shell del nuovo Container su Proxmox:

```bash
sudo nano /etc/ssh/sshd_config
```

Modificare i seguenti parametri:

```bash
PermitRootLogin yes
PasswordAuthentication yes
PermitEmptyPasswords no
```

Installare ifconfig

```bash
apt update
apt install -y net-tools
apt install -y git
```


Clona repository

```bash
cd /opt
git clone https://github.com/turiliffiu/agrisecure.git
cd agrisecure/backend
```

Esegui installazione automatica

```bash
sudo bash scripts/install.sh
```

Lo script `install.sh` installa automaticamente:
- ✅ PostgreSQL, Redis, Mosquitto MQTT
- ✅ Python 3 + ambiente virtuale
- ✅ Django + tutte le dipendenze
- ✅ Servizi systemd (web, celery, mqtt)
- ✅ Nginx reverse proxy
- ✅ Configurazione `.env` con SECRET_KEY casuale

**Dopo l'installazione:**

```bash
# Crea superuser per accedere all'admin
sudo -u agrisecure /opt/agrisecure/backend/venv/bin/python /opt/agrisecure/backend/manage.py createsuperuser

# (Opzionale) Configura Telegram/Email per notifiche
sudo nano /opt/agrisecure/backend/.env
```

**Accedi alla dashboard:**
- **Admin Django**: `http://IP_CONTAINER/admin/`
- **API Docs (Swagger)**: `http://IP_CONTAINER/api/v1/docs/`
- **API Docs (ReDoc)**: `http://IP_CONTAINER/api/v1/redoc/`

### 2. Compila il Firmware

```bash
cd agrisecure/firmware

# Installa PlatformIO
pip install platformio

# Compila per Gateway
pio run -e node_gateway

# Compila per Nodo Ambientale
pio run -e node_ambient

# Compila per Nodo Sicurezza
pio run -e node_security

# Upload su ESP32
pio run -e node_gateway -t upload
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

## 📊 Specifiche Tecniche

### Hardware Prototipo (3 nodi)

| Componente | Quantità | Costo |
|------------|----------|-------|
| ESP32-C6-DevKitC-1 | 3 | €18,57 |
| SIM7670E-H 4G/LTE | 1 | €16,59 |
| BME280 | 1 | €1,95 |
| PIR HC-SR501 | 2 | €2,90 |
| Pannelli solari | 3 | €28,07 |
| Batterie 18650 | 6 | €20,37 |
| **Totale** | | **~€200** |

### API Endpoints Principali

| Endpoint | Descrizione |
|----------|-------------|
| `GET /api/v1/nodes/` | Lista nodi IoT |
| `GET /api/v1/sensors/readings/latest/` | Ultime letture sensori |
| `GET /api/v1/security/alarms/active/` | Allarmi attivi |
| `POST /api/v1/security/arm/` | Arma/disarma sistema |
| `GET /api/v1/dashboard/summary/` | Riepilogo dashboard |

### Discriminazione Persona/Animale

L'algoritmo analizza il pattern di attivazione di 2 sensori PIR:

| Pattern | Classificazione |
|---------|-----------------|
| Entrambi PIR >80% tempo | 🧑 PERSONA |
| PIR main >70%, backup <40% | 🧑 PERSONA |
| PIR main 40-80% | 🦊 ANIMALE GRANDE |
| PIR main <40% | 🐈 ANIMALE PICCOLO |

---

## 🔔 Configurazione Notifiche

Modifica il file `/opt/agrisecure/backend/.env`:

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

Dopo la modifica riavvia i servizi:
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
Aggiungi l'IP del container in `/opt/agrisecure/backend/.env`:
```
ALLOWED_HOSTS=localhost,127.0.0.1,agrisecure.local,TUO_IP
```
Poi riavvia: `sudo systemctl restart agrisecure-web`

### CSS/stili non caricati nell'admin
Verifica che Nginx punti alla directory corretta. Controlla `/etc/nginx/sites-available/agrisecure`:
```nginx
location /static/ {
    alias /opt/agrisecure/backend/staticfiles/;
}
```
Poi: `sudo systemctl restart nginx`

---

## 📅 Roadmap

- [x] Studio di fattibilità
- [x] BOM e lista ordini
- [x] Firmware ESP32-C6
- [x] Backend Django
- [x] Script installazione automatica
- [ ] Dashboard React
- [ ] App Mobile (React Native)
- [ ] Machine Learning per classificazione
- [ ] Integrazione Home Assistant

---

## 📄 Licenza

Proprietario - Turiliffiu © 2024-2025

---

## 👥 Contatti

- **Progetto**: AgriSecure IoT System
- **Cliente**: Sig. Daniele Li Volsi
- **Sviluppo**: Turiliffiu
