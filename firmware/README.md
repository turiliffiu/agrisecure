# AgriSecure IoT System - Firmware

Firmware per il sistema di monitoraggio agricolo e sicurezza perimetrale AgriSecure.

## 📋 Requisiti

- [PlatformIO](https://platformio.org/) (VSCode extension o CLI)
- ESP32-C6-DevKitC-1 (3 unità per il prototipo)
- Componenti hardware come da BOM

## 🏗️ Struttura Progetto

```
agrisecure-firmware/
├── platformio.ini          # Configurazione PlatformIO
├── include/
│   ├── agrisecure_config.h # Configurazioni e definizioni comuni
│   ├── mesh_manager.h      # Gestione rete mesh ESP-NOW
│   ├── sensors_ambient.h   # Sensori ambientali (BME280, BH1750, Soil)
│   └── sensors_security.h  # Sensori sicurezza (PIR, MPU6050)
├── src/
│   ├── main.cpp            # Entry point (selettore firmware)
│   ├── main_gateway.cpp    # Firmware nodo Gateway 4G
│   ├── main_ambient.cpp    # Firmware nodo Ambientale
│   ├── main_security.cpp   # Firmware nodo Sicurezza
│   ├── mesh_manager.cpp    # Implementazione mesh
│   ├── sensors_ambient.cpp # Implementazione sensori ambientali
│   └── sensors_security.cpp# Implementazione sensori sicurezza
├── lib/                    # Librerie locali
├── test/                   # Test unitari
└── docs/                   # Documentazione
```

## 🚀 Compilazione

### Nodo Gateway (4G/LTE)
```bash
pio run -e node_gateway
pio run -e node_gateway -t upload
```

### Nodo Ambientale
```bash
pio run -e node_ambient
pio run -e node_ambient -t upload
```

### Nodo Sicurezza
```bash
pio run -e node_security
pio run -e node_security -t upload
```

### Monitor Seriale
```bash
pio device monitor -b 115200
```

## 📡 Architettura Mesh

```
                    ┌─────────────┐
                    │   BACKEND   │
                    │  (Django)   │
                    └──────┬──────┘
                           │ MQTT/4G
                    ┌──────┴──────┐
                    │   GATEWAY   │
                    │   (GW-001)  │
                    └──────┬──────┘
                           │ ESP-NOW
              ┌────────────┼────────────┐
              │            │            │
       ┌──────┴──────┐ ┌───┴───┐ ┌──────┴──────┐
       │  AMBIENT    │ │ AMB-n │ │  SECURITY   │
       │  (AMB-001)  │ │       │ │  (SEC-001)  │
       └─────────────┘ └───────┘ └─────────────┘
```

## 📊 Tipi di Messaggio

| Tipo | Codice | Priorità | Descrizione |
|------|--------|----------|-------------|
| MSG_HEARTBEAT | 0x01 | MEDIUM | Heartbeat periodico |
| MSG_SENSOR_DATA | 0x02 | LOW | Dati sensori ambientali |
| MSG_ALARM_PERSON | 0x03 | CRITICAL | Allarme: persona rilevata |
| MSG_ALARM_ANIMAL | 0x04 | HIGH | Allarme: animale rilevato |
| MSG_ALARM_TAMPER | 0x05 | CRITICAL | Allarme: manomissione |
| MSG_COMMAND | 0x06 | HIGH | Comando da gateway |
| MSG_ARM | 0x0C | HIGH | Arma sistema |
| MSG_DISARM | 0x0D | HIGH | Disarma sistema |

## 🔧 Configurazione

### WiFi/Mesh
Modificare in `platformio.ini`:
```ini
-DMESH_CHANNEL=1
-DMESH_ENCRYPTION_KEY=\"chiave_32_caratteri\"
```

### MQTT (Gateway)
```ini
-DMQTT_BROKER=\"mqtt.example.com\"
-DMQTT_PORT=1883
-DMQTT_USER=\"user\"
-DMQTT_PASS=\"password\"
```

### APN 4G (Gateway)
Modificare in `main_gateway.cpp`:
```cpp
#define GSM_APN "ibox.tim.it"  // TIM
// oppure "web.omnitel.it"    // Vodafone
```

## 🔋 Gestione Energia

### Nodo Ambientale
- Deep sleep tra le letture (10 min default)
- Consumo medio: ~60 mAh/giorno
- Autonomia: 4-5 giorni senza sole

### Nodo Sicurezza
- Always-on per risposta rapida
- Consumo medio: ~180 mAh/giorno
- Autonomia: 3-4 giorni senza sole

### Gateway
- Always-on
- Consumo medio: ~300 mAh/giorno
- Autonomia: 2-3 giorni senza sole

## 🐛 Debug

Abilitare debug in `platformio.ini`:
```ini
-DSERIAL_DEBUG=1
-DCORE_DEBUG_LEVEL=4
```

## 📝 TODO

- [ ] Implementare OTA updates
- [ ] Aggiungere encryption AES-128 ai messaggi mesh
- [ ] Implementare coda messaggi con retry
- [ ] Aggiungere supporto GPS nel gateway
- [ ] Implementare calibrazione automatica sensori
- [ ] Aggiungere watchdog timer
- [ ] Testing unitario con Unity

## 📄 Licenza

Proprietario - Turiliffiu © 2024

## 👥 Contatti

- **Progetto**: AgriSecure IoT System
- **Cliente**: Sig. Daniele Li Volsi
- **Sviluppo**: Turiliffiu
