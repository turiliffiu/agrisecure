# Setup TLS su MQTT — AgriSecure

**Data implementazione:** Agosto 2026
**Autore:** Salvo (Turiliffiu)
**Stato:** Completato e testato end-to-end su GW-001

Questo documento descrive come è stato configurato TLS sul broker Mosquitto e sul firmware del gateway, e come replicare/verificare la procedura per i prossimi gateway (GW-002, GW-003).

---

## 1. Architettura

Gateway ESP32-S3 (4G/A7670E)
│ TinyGsmClient (TCP grezzo via modem)
│ SSLClientESP32 (TLS software, mbedTLS su ESP32)
│ porta 8883
▼
Router (port forwarding 8883 → 192.168.1.179:8883)
▼
Server (192.168.1.179) — Mosquitto nativo (systemd, NON Docker)
├── listener 8883 (TLS) → connessioni esterne (gateway)
└── listener 1883 (solo 127.0.0.1) → subscriber Django interno (mqtt_subscriber.py)


Punti chiave della scelta architetturale:

- **TLS lato ESP32 (software), non lato modem**: la libreria TinyGSM (v0.11.7) non ha un'implementazione funzionante di `TinyGsmClientSecure` per il modem SIM7600/A7670E (la classe esiste nel sorgente ma è commentata, vedi [issue #770](https://github.com/vshymanskyy/TinyGSM/issues/770)). Si usa quindi `SSLClientESP32` ([alkonosst/SSLClientESP32](https://github.com/alkonosst/SSLClientESP32)), che aggiunge TLS via mbedTLS **sopra** un `TinyGsmClient` normale (che fa solo da tubo TCP grezzo). Questo evita di dover caricare certificati nella memoria del modem stesso (procedura AT più fragile e meno documentata).
- **CA privata**, non certificato pubblico: dominio interno all'azienda, nessun bisogno di Let's Encrypt. La CA resta esclusivamente sul server, mai distribuita.
- **Listener 1883 ristretto a `127.0.0.1`**: il subscriber Django gira sulla stessa macchina di Mosquitto, quindi non serve TLS per quel traffico (mai lascia il loopback), ma va comunque tolto da `0.0.0.0` per non lasciarlo esposto a internet.
- **Un solo hostname/CA per tutti e 3 i gateway futuri**: `agrisecure.tgs.ovh:8883` sarà lo stesso endpoint per GW-001/002/003 (ridondanza a livello di operatore SIM, non di hostname — vedi knowledge base di progetto). Nessuna generazione di certificati aggiuntiva necessaria quando si aggiungeranno gli altri due gateway: si riusa lo stesso `ca_cert_pem` embeddato nel firmware.

---

## 2. Setup lato server (già eseguito su 192.168.1.179)

### 2.1 Generazione CA privata

```bash
sudo mkdir -p /etc/mosquitto/certs
cd /etc/mosquitto/certs

sudo openssl genrsa -out ca.key 4096
sudo openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
  -out ca.crt \
  -subj "/C=IT/ST=Sicilia/L=Palermo/O=Turiliffiu/OU=AgriSecure/CN=AgriSecure-Root-CA"
```

`ca.key` **non lascia mai il server** — è la chiave che firma tutti i certificati futuri (gateway aggiuntivi, eventuali client mTLS futuri).

### 2.2 Certificato server, firmato dalla CA

```bash
sudo openssl genrsa -out server.key 2048
sudo openssl req -new -key server.key -out server.csr \
  -subj "/C=IT/ST=Sicilia/L=Palermo/O=Turiliffiu/OU=AgriSecure/CN=agrisecure.tgs.ovh"

cat << 'INNEREOF' | sudo tee server_ext.cnf
subjectAltName = DNS:agrisecure.tgs.ovh
INNEREOF

sudo openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 730 -sha256 -extfile server_ext.cnf
```

**Nota SAN obbligatorio**: senza `subjectAltName`, i client TLS moderni (incluso mbedTLS su ESP32) rifiutano il certificato anche se il CN è corretto — non basta più il solo CN come in passato.

**Scadenza**: certificato server valido 2 anni (fino ad Agosto 2028). **Da segnare in calendario**: rigenerare `server.crt` (non serve rigenerare la CA, valida 10 anni) prima della scadenza, altrimenti tutti e 3 i gateway smettono di connettersi.

### 2.3 Permessi

```bash
sudo chown mosquitto:mosquitto /etc/mosquitto/certs/server.key /etc/mosquitto/certs/server.crt /etc/mosquitto/certs/ca.crt
sudo chmod 640 /etc/mosquitto/certs/server.key
sudo chmod 644 /etc/mosquitto/certs/server.crt /etc/mosquitto/certs/ca.crt
sudo chmod 600 /etc/mosquitto/certs/ca.key
```

### 2.4 Config Mosquitto — `/etc/mosquitto/conf.d/agrisecure.conf`

**Attenzione**: la config reale è in `/etc/mosquitto/conf.d/agrisecure.conf` (caricata via `include_dir` dal `mosquitto.conf` principale). Il file `docker/mosquitto/mosquitto.conf` presente nel repo Git **non è quello in uso** — risale a un'ipotesi di deploy Docker mai effettivamente utilizzata in produzione (il server gira Mosquitto nativo via systemd + venv Python per il backend, non container).
AgriSecure MQTT Configuration
TLS su 8883 per connessioni esterne (gateway 4G) + listener 1883 solo localhost per subscriber Django

listener 1883 127.0.0.1

listener 8883
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
tls_version tlsv1.2

allow_anonymous false
password_file /etc/mosquitto/passwd
acl_file /etc/mosquitto/acl


```bash
sudo systemctl restart mosquitto
sudo systemctl status mosquitto --no-pager
ss -tlnp | grep mosquitto
```

### 2.5 Fix di sicurezza collaterale trovato durante il lavoro

La config precedente aveva `allow_anonymous true` nonostante un `password_file`/`acl_file` configurati — significa che chiunque raggiungesse la porta 1883 (esposta su tutte le interfacce, `ufw` inattivo) poteva leggere/scrivere su tutti i topic senza alcuna autenticazione. Chiuso contestualmente al lavoro TLS.

### 2.6 Port forwarding router

Il server è dietro NAT (Nginx Proxy Manager gestisce solo l'inoltro HTTP/HTTPS su un'altra macchina, non è coinvolto per MQTT). Regola diretta sul router:

| WAN | LAN | Protocollo |
|---|---|---|
| 8883 | 192.168.1.179:8883 | TCP |

---

## 3. Setup lato firmware (gateway)

### 3.1 platformio.ini — env node_gateway

```ini
lib_deps = 
    ${env.lib_deps}
    vshymanskyy/TinyGSM@^0.11.7
    https://github.com/alkonosst/SSLClientESP32.git#v2.0.3
    mikalhart/TinyGPSPlus@^1.0.3

build_flags = 
    -DMQTT_BROKER=\"agrisecure.tgs.ovh\"
    -DMQTT_PORT=8883
```

### 3.2 main_gateway.cpp — pattern di utilizzo

```cpp
#include <TinyGsmClient.h>
#include <SSLClientESP32.h>
#include <PubSubClient.h>

static const char ca_cert_pem[] PROGMEM = R"CERT(
-----BEGIN CERTIFICATE-----
... (vedi main_gateway.cpp per il contenuto completo) ...
-----END CERTIFICATE-----
)CERT";

TinyGsmClient gsmClient(modem);
SSLClientESP32 sslClient(&gsmClient);
PubSubClient mqtt(sslClient);

sslClient.setCACert(ca_cert_pem);
mqtt.setServer(MQTT_BROKER, MQTT_PORT);
```

### 3.3 Per i prossimi gateway (GW-002, GW-003)

Nessuna nuova generazione di certificati necessaria:
1. Stesso `ca_cert_pem` nel firmware (identico per tutti e 3)
2. Cambiare solo `NODE_ID` (es. `"GW-002"`)
3. `MQTT_BROKER`/`MQTT_PORT` restano identici

---

## 4. Verifica / troubleshooting

### Test TLS puro
```bash
openssl s_client -connect agrisecure.tgs.ovh:8883 -CAfile ca.crt -servername agrisecure.tgs.ovh </dev/null
```

### Test pub/sub autenticato
```bash
mosquitto_pub -h agrisecure.tgs.ovh -p 8883 --cafile ca.crt --tls-version tlsv1.2 \
  -u agrisecure -P <password> -t "agrisecure/test/x" -m "test"
```

### Errori comuni
- **"A TLS error occurred"** con `-h localhost`: il certificato ha CN/SAN `agrisecure.tgs.ovh`, non `localhost` — usare sempre l'hostname reale nei test.
- **Comando appeso senza risposta**: quasi sempre porta non raggiungibile (port forwarding router mancante), non un problema Mosquitto.

---

## 5. Limitazioni note / roadmap

- Nessun mTLS (solo server-side + user/pass MQTT applicativo)
- Credenziali MQTT condivise tra tutti i gateway — da valutare credenziali per-gateway in futuro
- Certificato server da rinnovare entro Agosto 2028
- ESP-NOW: RSSI dei peer mesh non disponibile con l'API legacy attuale (vedi commit a1e53fb)
