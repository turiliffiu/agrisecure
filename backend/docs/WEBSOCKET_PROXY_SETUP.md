# AgriSecure — Setup Proxy WebSocket (Dashboard Real-time)

*Documentato dopo troubleshooting e fix, agosto 2026*

## 1. Architettura

Browser (wss://agrisecure.tgs.ovh/ws/dashboard/)
│
▼
Nginx Proxy Manager (macchina separata)
│ proxy_pass verso 192.168.1.179:80
▼
Nginx locale sul backend (192.168.1.179:80)
│ location /ws/ → proxy_pass verso 127.0.0.1:8001
▼
Daphne (ASGI server, Django Channels) — bindato SOLO su 127.0.0.1:8001


**Punto chiave**: Daphne è in ascolto solo su `127.0.0.1:8001` (loopback), non su `0.0.0.0`. Questo significa che **solo processi sulla stessa macchina** possono raggiungerlo direttamente. Nginx Proxy Manager (NPM), girando su una macchina diversa, non può connettersi direttamente a `192.168.1.179:8001` — deve invece passare dal Nginx locale del backend sulla porta 80, che poi inoltra internamente a Daphne via loopback.

## 2. Configurazione Nginx Proxy Manager (macchina NPM)

File generato da NPM: `/data/nginx/proxy_host/17.conf` (per `agrisecure.tgs.ovh`).

Va aggiunto tramite la UI di NPM → Proxy Hosts → `agrisecure.tgs.ovh` → tab **Advanced** → campo **Custom Nginx Configuration**:

```nginx
location /ws/ {
    proxy_pass http://192.168.1.179:80;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400;
}
```

**Importante**: usare la porta **80** (non 8001) come target — vedi errore comune in sezione 4.

Dopo il salvataggio dalla UI, verificare e ricaricare:

```bash
grep -A2 "location /ws/" /data/nginx/proxy_host/17.conf
nginx -t && nginx -s reload
```

Nota: `nginx -t`/`reload` su questa macchina produce warning `listen ... http2 is deprecated` per quasi tutti i proxy host esistenti — sono preesistenti, non bloccanti, non legati a questa configurazione.

## 3. Configurazione Nginx locale (macchina backend, 192.168.1.179)

File: `/etc/nginx/sites-available/agrisecure` (symlink in `sites-enabled/`).

Il blocco `location /ws/` verso Daphne era **già presente correttamente** in questo file:

```nginx
upstream agrisecure_websocket {
    server 127.0.0.1:8001 fail_timeout=0;
}
server {
    listen 80;
    server_name agrisecure.local localhost 192.168.1.179;
    ...
    location /ws/ {
        proxy_pass http://agrisecure_websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
    ...
}
```

**Fix applicato**: `server_name` conteneva un IP obsoleto (`192.168.1.190`) invece di quello reale del server (`192.168.1.179`). Corretto con:

```bash
cp /etc/nginx/sites-available/agrisecure /etc/nginx/sites-available/agrisecure.bak_$(date +%Y%m%d_%H%M)
sed -i 's/192\.168\.1\.190/192.168.1.179/' /etc/nginx/sites-available/agrisecure
nginx -t && systemctl reload nginx
```

## 4. Verifica

Nel browser, DevTools → Network → filtro **WS** → click sulla richiesta `dashboard/` → tab Headers:
- **Status Code atteso: `101 Switching Protocols`**

Da terminale, sulla macchina NPM, per debug in tempo reale:

```bash
tail -f /data/logs/proxy-host-17_error.log /data/logs/proxy-host-17_access.log
```

## 5. Problema riscontrato durante il troubleshooting (per riferimento futuro)

**Sintomo**: badge "Disconnected" fisso in dashboard, WebSocket non si connette mai.

**Falsa pista iniziale**: puntare `proxy_pass` in NPM direttamente a `192.168.1.179:8001` (la porta di Daphne). Sembra logico ma **fallisce sempre** con:

connect() failed (111: Connection refused) while connecting to upstream
upstream: "http://192.168.1.179:8001/ws/dashboard/"

perché Daphne è bindato solo su `127.0.0.1:8001`, non raggiungibile da un'altra macchina anche se sulla stessa LAN.

**Fix corretto**: instradare `/ws/` verso `192.168.1.179:80` (il Nginx locale del backend), che ha già il proxy interno verso `127.0.0.1:8001` via loopback.

**Lezione generale**: quando un servizio ASGI/backend è bindato su loopback per sicurezza, un reverse proxy esterno (su macchina diversa) deve sempre passare attraverso il web server locale della macchina target, non tentare di raggiungere la porta interna direttamente — anche se l'IP:porta sembra "raggiungibile" sulla carta.

## 6. Riferimenti

- Config MQTT/TLS (pattern analogo, gateway → broker): `backend/docs/MQTT_TLS_SETUP.md`
- Servizio systemd Daphne: `agrisecure-daphne.service`
