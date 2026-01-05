# AgriSecure IoT Simulator

Simulatore per testare il backend e frontend AgriSecure senza hardware reale.

## 🚀 Installazione

Il simulatore è già incluso nell'ambiente AgriSecure. Per usarlo:

```bash
cd /opt/agrisecure/backend
source venv/bin/activate
python scripts/simulator.py
```

## 📋 Requisiti

- Python 3.8+
- paho-mqtt (già installato con requirements.txt)

## 🎮 Utilizzo

### Modalità Interattiva (default)

```bash
python scripts/simulator.py
```

Comandi disponibili:
| Comando | Descrizione |
|---------|-------------|
| `s`, `status` | Mostra stato simulatore e nodi |
| `n`, `normal` | Scenario: funzionamento normale |
| `a`, `alarm` | Scenario: simula intrusioni |
| `e`, `sensor` | Scenario: alert sensori |
| `f`, `failure` | Scenario: guasto nodo |
| `b`, `battery` | Scenario: batterie scariche |
| `t`, `test` | Ciclo completo tutti gli scenari |
| `!`, `trigger` | Triggera allarme immediato |
| `q`, `quit` | Esci |

### Modalità Automatica

```bash
# Esecuzione infinita
python scripts/simulator.py --auto

# Esecuzione per 5 minuti
python scripts/simulator.py --auto --duration 300

# Con scenario specifico
python scripts/simulator.py --auto --scenario alarm
```

### Opzioni

| Opzione | Default | Descrizione |
|---------|---------|-------------|
| `--auto` | - | Modalità automatica senza input |
| `--duration` | 0 | Durata in secondi (0=infinito) |
| `--scenario` | normal | Scenario iniziale |
| `--broker` | localhost | Host broker MQTT |
| `--port` | 1883 | Porta broker MQTT |
| `--username` | agrisecure | Username MQTT |
| `--password` | mqtt_secure_password | Password MQTT |

## 🎬 Scenari

### `normal` - Funzionamento Normale
- Letture sensori realistiche con variazioni naturali
- Temperatura varia con l'ora del giorno
- Luce segue ciclo giorno/notte
- Batterie si scaricano di notte, ricaricano di giorno
- Occasionali eventi movimento (animali)

### `alarm` - Intrusione
- Alta probabilità di eventi sicurezza
- Rilevamenti di persone che triggerano allarmi
- Utile per testare notifiche e gestione allarmi

### `sensor_alert` - Alert Sensori
- Temperature fuori range (>38°C)
- Suolo molto secco (<15%)
- Utile per testare alert ambientali

### `node_failure` - Guasto Nodo
- Un nodo casuale va offline
- Utile per testare rilevamento guasti

### `battery_low` - Batterie Scariche
- Tutti i nodi con batteria <20%
- Utile per testare warning batterie

### `full_test` - Test Completo
- Cicla automaticamente tutti gli scenari
- 60 secondi per scenario
- Utile per demo o test completi

## 📡 Nodi Simulati

Il simulatore crea automaticamente:

| ID | Tipo | Nome |
|----|------|------|
| GW-001 | Gateway | Gateway Principale |
| AMB-001 | Ambient | Sensore Campo Nord |
| AMB-002 | Ambient | Sensore Campo Sud |
| AMB-003 | Ambient | Sensore Serra |
| SEC-001 | Security | Sicurezza Ingresso |
| SEC-002 | Security | Sicurezza Perimetro Est |
| SEC-003 | Security | Sicurezza Perimetro Ovest |

## 📊 Topic MQTT Generati

```
agrisecure/GW-001/status          # Heartbeat gateway
agrisecure/AMB-001/status         # Heartbeat nodo ambientale
agrisecure/AMB-001/sensors/ambient  # Dati sensori
agrisecure/SEC-001/status         # Heartbeat nodo sicurezza
agrisecure/SEC-001/security/event  # Eventi movimento/allarme
```

## 🔧 Esempio Sessione

```
$ python scripts/simulator.py

    ╔═══════════════════════════════════════════════════════════╗
    ║           🌿 AgriSecure IoT Simulator 🌿                  ║
    ╚═══════════════════════════════════════════════════════════╝

🔌 Connessione a localhost:1883...
✅ Connesso al broker MQTT localhost:1883
🎬 Scenario attivato: normal
▶️  Simulazione avviata con 7 nodi
   Scenario: normal

--------------------------------------------------
🎮 COMANDI DISPONIBILI:
--------------------------------------------------
  s, status    - Mostra stato simulatore
  n, normal    - Scenario: normale
  a, alarm     - Scenario: allarme intrusione
  ...
--------------------------------------------------

> s

============================================================
📊 STATO SIMULATORE - 14:32:15
============================================================
Scenario: normal
Connesso MQTT: ✅

📈 Statistiche:
   messages_sent: 28
   heartbeats_sent: 14
   sensor_readings_sent: 9
   security_events_sent: 2
   alarms_triggered: 0

📡 Nodi (7):
   🟢 🌐 GW-001: Gateway Principale | 🔋 100%
   🟢 🌡️ AMB-001: Sensore Campo Nord | 🔋 85% | 🌡️ 23.4°C | 💧 62%
   🟢 🌡️ AMB-002: Sensore Campo Sud | 🔋 72% | 🌡️ 22.8°C | 💧 58%
   🟢 🌡️ AMB-003: Sensore Serra | 🔋 90% | 🌡️ 28.1°C | 💧 78%
   🟢 🛡️ SEC-001: Sicurezza Ingresso | 🔋 95% | 🔒
   🟢 🛡️ SEC-002: Sicurezza Perimetro Est | 🔋 88% | 🔒
   🟢 🛡️ SEC-003: Sicurezza Perimetro Ovest | 🔋 78% | 🔒
============================================================

> a
🎬 Scenario attivato: alarm
🚨 ALLARME TRIGGERATO da SEC-001: person

> q
⏹️  Simulazione fermata

📊 Statistiche finali:
   messages_sent: 156
   heartbeats_sent: 42
   sensor_readings_sent: 27
   security_events_sent: 15
   alarms_triggered: 3
```

## 🐛 Troubleshooting

### Errore connessione MQTT
```
❌ Errore connessione MQTT: [Errno 111] Connection refused
```
Verifica che Mosquitto sia attivo:
```bash
sudo systemctl status mosquitto
```

### Nessun dato nella dashboard
1. Verifica che il simulatore sia connesso
2. Controlla che le migrazioni siano applicate
3. Verifica i log del servizio MQTT subscriber:
```bash
sudo journalctl -u agrisecure-mqtt -f
```

## 📄 Licenza

Proprietario - Turiliffiu © 2025-2026
