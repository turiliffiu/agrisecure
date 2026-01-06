# 🚀 AgriSecure - Quick Reference Guide

**Guida rapida** per operazioni comuni

---

## 📋 Comandi Rapidi

### Gestione Servizi

```bash
# Avvia tutti i servizi
sudo bash /opt/agrisecure/backend/scripts/start_all.sh

# Ferma tutti i servizi
sudo bash /opt/agrisecure/backend/scripts/stop_all.sh

# Riavvia servizio specifico
sudo systemctl restart agrisecure-web
sudo systemctl restart agrisecure-celery
sudo systemctl restart agrisecure-mqtt

# Verifica stato
sudo systemctl status agrisecure-web
```

### Log e Debug

```bash
# Log real-time
sudo journalctl -u agrisecure-web -f
sudo journalctl -u agrisecure-mqtt -f

# Ultimi 100 log
sudo journalctl -u agrisecure-web -n 100

# Log con errori
sudo journalctl -u agrisecure-web | grep ERROR

# Log ultime 24 ore
sudo journalctl -u agrisecure-web --since "24 hours ago"
```

### Database

```bash
# Backup manuale
sudo bash /opt/agrisecure/backend/scripts/backup_db.sh

# Accesso PostgreSQL
sudo -u postgres psql agrisecure

# Query rapide
sudo -u agrisecure /opt/agrisecure/backend/venv/bin/python \
    /opt/agrisecure/backend/manage.py shell

>>> from apps.nodes.models import Node
>>> Node.objects.count()
>>> Node.objects.filter(status='online')
```

### Django Management

```bash
# Attiva virtual environment
cd /opt/agrisecure/backend
source venv/bin/activate

# Crea superuser
python manage.py createsuperuser

# Migrations
python manage.py makemigrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Shell interattiva
python manage.py shell
```

---

## 🔧 Troubleshooting Veloce

### Servizio Web Non Risponde

```bash
# 1. Verifica status
sudo systemctl status agrisecure-web

# 2. Controlla log
sudo journalctl -u agrisecure-web -n 50

# 3. Test manuale
cd /opt/agrisecure/backend
sudo -u agrisecure venv/bin/python manage.py runserver 0.0.0.0:8000

# 4. Riavvia
sudo systemctl restart agrisecure-web
```

### MQTT Non Riceve Messaggi

```bash
# 1. Verifica Mosquitto
sudo systemctl status mosquitto

# 2. Test sottoscrizione
mosquitto_sub -h localhost -u agrisecure -P mqtt_secure_password \
    -t "agrisecure/#" -v

# 3. Test pubblicazione
mosquitto_pub -h localhost -u agrisecure -P mqtt_secure_password \
    -t "agrisecure/test" -m "hello"

# 4. Controlla log
sudo tail -f /var/log/mosquitto/mosquitto.log
```

### Database Non Connette

```bash
# 1. Verifica PostgreSQL
sudo systemctl status postgresql

# 2. Test connessione
sudo -u postgres psql -l

# 3. Verifica credenziali in .env
cat /opt/agrisecure/backend/.env | grep DATABASE

# 4. Riavvia database
sudo systemctl restart postgresql
```

### Errore "Bad Request (400)"

```bash
# Aggiungi IP in ALLOWED_HOSTS
sudo nano /opt/agrisecure/backend/.env

# Aggiungi:
ALLOWED_HOSTS=localhost,127.0.0.1,agrisecure.local,192.168.1.100

# Riavvia
sudo systemctl restart agrisecure-web
```

---

## 🔍 Verifiche Salute Sistema

### Check Rapido Sistema

```bash
#!/bin/bash
# Quick health check

echo "=== Services Status ==="
systemctl is-active agrisecure-web agrisecure-celery agrisecure-mqtt

echo -e "\n=== Disk Space ==="
df -h /opt/agrisecure

echo -e "\n=== Memory Usage ==="
free -h

echo -e "\n=== Last 5 Errors ==="
journalctl -u agrisecure-web --since "1 hour ago" | grep ERROR | tail -5

echo -e "\n=== MQTT Test ==="
timeout 2 mosquitto_sub -h localhost -u agrisecure -P mqtt_secure_password \
    -t 'agrisecure/#' -C 1 && echo "MQTT OK" || echo "MQTT FAIL"

echo -e "\n=== Database Test ==="
sudo -u agrisecure /opt/agrisecure/backend/venv/bin/python \
    /opt/agrisecure/backend/manage.py check --database default
```

### Monitoraggio Performance

```bash
# Top processi
htop

# Database queries attive
sudo -u postgres psql agrisecure -c "SELECT * FROM pg_stat_activity;"

# Redis info
redis-cli INFO

# Nginx status
curl http://localhost/nginx_status
```

---

## 🔐 Security Quick Commands

```bash
# Genera nuovo SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Cambia password utente Django
cd /opt/agrisecure/backend
source venv/bin/activate
python manage.py changepassword username

# Lista utenti attivi
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.filter(is_active=True).values('username', 'email')
```

---

## 📊 Query Utili Database

```sql
-- Conta nodi per tipo
SELECT node_type, COUNT(*) 
FROM nodes 
GROUP BY node_type;

-- Nodi offline
SELECT node_id, name, last_seen 
FROM nodes 
WHERE status = 'offline';

-- Ultime letture sensori
SELECT n.node_id, s.timestamp, s.temperature, s.humidity
FROM sensor_readings s
JOIN nodes n ON s.node_id = n.id
ORDER BY s.timestamp DESC
LIMIT 10;

-- Allarmi attivi
SELECT a.id, n.node_id, a.classification, a.triggered_at
FROM alarms a
JOIN nodes n ON a.node_id = n.id
WHERE a.status = 'active'
ORDER BY a.triggered_at DESC;

-- Statistiche giornaliere
SELECT 
    DATE(timestamp) as date,
    AVG(temperature) as avg_temp,
    MAX(temperature) as max_temp,
    MIN(temperature) as min_temp
FROM sensor_readings
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

---

## 📱 Test MQTT da CLI

```bash
# Sottoscrizione topic
mosquitto_sub -h localhost -p 1883 \
    -u agrisecure -P mqtt_secure_password \
    -t "agrisecure/#" -v

# Pubblicazione test sensori
mosquitto_pub -h localhost -p 1883 \
    -u agrisecure -P mqtt_secure_password \
    -t "agrisecure/AMB-001/sensors/data" \
    -m '{"temperature": 25.5, "humidity": 65.0, "timestamp": 1704547200}'

# Pubblicazione test allarme
mosquitto_pub -h localhost -p 1883 \
    -u agrisecure -P mqtt_secure_password \
    -t "agrisecure/SEC-001/security/event" \
    -m '{"classification": "person", "pir_main": true, "timestamp": 1704547200}'

# Pubblicazione heartbeat
mosquitto_pub -h localhost -p 1883 \
    -u agrisecure -P mqtt_secure_password \
    -t "agrisecure/GW-001/status" \
    -m '{"uptime": 3600, "battery": 85, "rssi": -65}'
```

---

## 🔄 Update & Maintenance

### Aggiornamento Backend

```bash
# 1. Backup
sudo bash /opt/agrisecure/backend/scripts/backup_db.sh

# 2. Pull codice
cd /opt/agrisecure
sudo git pull origin main

# 3. Aggiorna dipendenze
cd backend
sudo -u agrisecure venv/bin/pip install -r requirements.txt --upgrade

# 4. Migrations
sudo -u agrisecure venv/bin/python manage.py migrate

# 5. Collect static
sudo -u agrisecure venv/bin/python manage.py collectstatic --noinput

# 6. Riavvia servizi
sudo bash scripts/stop_all.sh
sudo bash scripts/start_all.sh
```

### Pulizia Database

```bash
# Django shell
cd /opt/agrisecure/backend
source venv/bin/activate
python manage.py shell

# Elimina vecchi heartbeat (>30 giorni)
>>> from apps.nodes.models import NodeHeartbeat
>>> from django.utils import timezone
>>> from datetime import timedelta
>>> cutoff = timezone.now() - timedelta(days=30)
>>> NodeHeartbeat.objects.filter(timestamp__lt=cutoff).delete()

# Elimina vecchi eventi (>90 giorni)
>>> from apps.security.models import SecurityEvent
>>> cutoff = timezone.now() - timedelta(days=90)
>>> SecurityEvent.objects.filter(timestamp__lt=cutoff).delete()
```

---

## 📞 Contatti Emergenza

```
🔴 Sistema Down
1. Verifica servizi: systemctl status agrisecure-*
2. Check logs: journalctl -u agrisecure-web -n 100
3. Restart: sudo bash scripts/start_all.sh
4. Contatta: [email/telefono support]

🟠 Database Issues
1. Check PostgreSQL: systemctl status postgresql
2. Backup disponibile: /opt/agrisecure/backups/
3. Restore: sudo bash scripts/restore_db.sh [file]

🟡 MQTT Issues
1. Test broker: mosquitto_sub -h localhost -t '#'
2. Restart: sudo systemctl restart mosquitto
3. Check config: /etc/mosquitto/mosquitto.conf
```

---

## 🎯 Best Practices Quotidiane

### 📅 Daily
- [ ] Verifica dashboard accessibile
- [ ] Check nodi online
- [ ] Review allarmi attivi

### 📅 Weekly
- [ ] Check disk space: `df -h`
- [ ] Review error logs
- [ ] Verify backup funzionante

### 📅 Monthly
- [ ] Update sistema: `apt update && apt upgrade`
- [ ] Review performance metrics
- [ ] Test disaster recovery

---

## 💡 Tips & Tricks

### Performance

```bash
# Pulizia cache Redis
redis-cli FLUSHALL

# Ottimizzazione PostgreSQL
sudo -u postgres psql agrisecure -c "VACUUM ANALYZE;"

# Restart Celery per liberare memoria
sudo systemctl restart agrisecure-celery
```

### Development

```bash
# Run in development mode
cd /opt/agrisecure/backend
DEBUG=True python manage.py runserver 0.0.0.0:8000

# Django shell plus (con import automatici)
pip install django-extensions
python manage.py shell_plus

# Reset migrations (solo dev!)
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
```

### Monitoring

```bash
# Watch logs live con highlight
sudo journalctl -u agrisecure-web -f | grep --color -E "ERROR|WARNING|$"

# Monitor CPU/RAM in tempo reale
watch -n 2 'ps aux | grep agrisecure | grep -v grep'

# Network connections
sudo netstat -tulpn | grep -E "8000|1883|5432|6379"
```

---

## 📖 Link Utili

- **Dashboard**: http://agrisecure.local/
- **Admin**: http://agrisecure.local/admin/
- **API Docs**: http://agrisecure.local/api/v1/docs/
- **Health Check**: http://agrisecure.local/health/
- **GitHub**: https://github.com/turiliffiu/agrisecure

---

## 🔑 Credenziali Default

```
# Django Admin
Username: admin
Password: [da impostare]

# MQTT
Username: agrisecure
Password: mqtt_secure_password [CAMBIARE IN PRODUZIONE]

# PostgreSQL
Username: agrisecure
Password: [configurato in .env]
Database: agrisecure
```

⚠️ **IMPORTANTE**: Cambiare tutte le password di default in produzione!

---

## 📝 Note Finali

Questa è una guida di riferimento rapido. Per informazioni dettagliate:
- Leggere documentazione completa in `/docs/`
- Consultare README.md
- Controllare commenti nel codice

**Mantieni questa guida aggiornata** con nuovi comandi e procedure!

---

**Versione**: 1.0  
**Ultima Revisione**: 6 Gennaio 2026
