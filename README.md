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

👉 [Vai al README Backend](backend/README.md)

### ⚡ Firmware (`/firmware`)

- **MCU**: ESP32-C6-DevKitC-1
- **Framework**: Arduino/PlatformIO
- **Comunicazione**: ESP-NOW mesh + 4G/LTE
- **Sensori**: BME280, BH1750, soil sensor, PIR, MPU6050

👉 [Vai al README Firmware](firmware/README.md)

---

## 🚀 Quick Start

### 1. Installa il Backend

```bash
# Clona repository
git clone https://github.com/turiliffiu/agrisecure.git
cd agrisecure/backend

# Setup automatico (Ubuntu/Debian)
sudo bash scripts/setup.sh

# Configura
sudo nano /opt/agrisecure/.env

# Inizializza DB
sudo -u agrisecure /opt/agrisecure/venv/bin/python manage.py migrate
sudo -u agrisecure /opt/agrisecure/venv/bin/python manage.py createsuperuser

# Installa e avvia servizi
sudo bash scripts/install_services.sh
sudo bash scripts/start_all.sh
```

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

### 3. Accedi alla Dashboard

- **Admin**: http://localhost/admin/
- **API Docs**: http://localhost/api/v1/docs/

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

## 📅 Roadmap

- [x] Studio di fattibilità
- [x] BOM e lista ordini
- [x] Firmware ESP32-C6
- [x] Backend Django
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
