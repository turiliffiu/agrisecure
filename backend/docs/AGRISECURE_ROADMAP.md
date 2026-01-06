# 🗺️ AgriSecure - Roadmap Tecnica Dettagliata

**Versione**: 1.0  
**Data**: 6 Gennaio 2026  
**Ultima Revisione**: 6 Gennaio 2026

---

## 📋 Indice

1. [Fase 0: Consolidamento Immediato (7 giorni)](#fase-0)
2. [Fase 1: Sicurezza e Testing (30 giorni)](#fase-1)
3. [Fase 2: Resilienza e Monitoring (45 giorni)](#fase-2)
4. [Fase 3: Dashboard React (90 giorni)](#fase-3)
5. [Fase 4: App Mobile (120 giorni)](#fase-4)
6. [Fase 5: ML e Analytics (180 giorni)](#fase-5)
7. [Tracking Progress](#tracking)

---

<a name="fase-0"></a>
## 🚨 Fase 0: Consolidamento Immediato (7 Giorni)

**Obiettivo**: Risolvere criticità immediate e preparare base solida

### Task 1: Sicurezza Base (Giorno 1-2)
**Priorità**: 🔴 CRITICA  
**Effort**: 4 ore  
**Assegnato**: Backend Developer

#### Subtask 1.1: Abilitare TLS su Mosquitto MQTT
```bash
# 1. Generare certificati SSL
cd /etc/mosquitto/certs
openssl req -new -x509 -days 3650 -extensions v3_ca \
    -keyout ca.key -out ca.crt

openssl genrsa -out server.key 2048
openssl req -new -out server.csr -key server.key
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out server.crt -days 3650

# 2. Configurare Mosquitto
sudo nano /etc/mosquitto/conf.d/tls.conf
```

**File: `/etc/mosquitto/conf.d/tls.conf`**
```conf
# TLS/SSL Configuration
listener 8883
protocol mqtt

cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key

require_certificate false
use_identity_as_username false

# Disable non-TLS listener
#listener 1883
```

```bash
# 3. Restart Mosquitto
sudo systemctl restart mosquitto
sudo systemctl status mosquitto
```

**Testing**:
```bash
# Test connessione TLS
mosquitto_pub -h localhost -p 8883 \
    --cafile /etc/mosquitto/certs/ca.crt \
    -u agrisecure -P mqtt_secure_password \
    -t "agrisecure/test" -m "Hello TLS"
```

#### Subtask 1.2: Rate Limiting API
**File**: `backend/agrisecure/settings.py`
```python
# Aggiungere a INSTALLED_APPS
INSTALLED_APPS = [
    # ... existing apps
    'rest_framework',
]

# Configurare throttling
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'burst': '20/minute',  # Per endpoint critici
    }
}
```

**File**: `backend/apps/api/throttling.py` (nuovo)
```python
from rest_framework.throttling import UserRateThrottle

class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'

class AlarmActionThrottle(UserRateThrottle):
    scope = 'alarm_action'
    rate = '10/minute'  # Max 10 azioni allarme al minuto
```

**Applicare ai viewsets critici**:
```python
# backend/apps/api/views.py
from .throttling import BurstRateThrottle, AlarmActionThrottle

class AlarmViewSet(viewsets.ModelViewSet):
    throttle_classes = [BurstRateThrottle, AlarmActionThrottle]
    # ...
```

#### Subtask 1.3: Spostare Secrets da Codice
**Action**: Rimuovere tutte le password hardcoded

**File**: `backend/.env`
```bash
# Aggiungere
MESH_ENCRYPTION_KEY=generate_random_32_bytes_hex
MQTT_TLS_CA_FILE=/etc/mosquitto/certs/ca.crt
MQTT_TLS_CERT_FILE=/etc/mosquitto/certs/client.crt
MQTT_TLS_KEY_FILE=/etc/mosquitto/certs/client.key
```

**File**: `firmware/platformio.ini`
```ini
; Rimuovere
; -DMESH_ENCRYPTION_KEY="0123456789ABCDEF0123456789ABCDEF"

; Sostituire con
; -DMESH_ENCRYPTION_KEY=${sysenv.MESH_ENCRYPTION_KEY}
```

**File**: `firmware/.env` (nuovo, NON committare)
```bash
MESH_ENCRYPTION_KEY=your_32_byte_hex_key_here
```

**Checklist**:
- [ ] TLS Mosquitto configurato e testato
- [ ] Rate limiting API implementato e testato
- [ ] Secrets spostati in .env
- [ ] File .env.example aggiornato
- [ ] Documentazione aggiornata

---

### Task 2: Backup Automatico (Giorno 2)
**Priorità**: 🟠 ALTA  
**Effort**: 2 ore

#### Subtask 2.1: Script Backup Database
**File**: `backend/scripts/backup_db.sh`
```bash
#!/bin/bash
# AgriSecure Database Backup Script

BACKUP_DIR="/opt/agrisecure/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="agrisecure"
DB_USER="agrisecure"

# Crea directory se non esiste
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
pg_dump -U $DB_USER -Fc $DB_NAME > $BACKUP_DIR/db_$DATE.dump

# Backup Redis (RDB)
cp /var/lib/redis/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Backup file .env
cp /opt/agrisecure/backend/.env $BACKUP_DIR/env_$DATE.bak

# Comprimi
tar -czf $BACKUP_DIR/agrisecure_backup_$DATE.tar.gz \
    $BACKUP_DIR/db_$DATE.dump \
    $BACKUP_DIR/redis_$DATE.rdb \
    $BACKUP_DIR/env_$DATE.bak

# Rimuovi file intermedi
rm $BACKUP_DIR/db_$DATE.dump
rm $BACKUP_DIR/redis_$DATE.rdb
rm $BACKUP_DIR/env_$DATE.bak

# Rimuovi backup più vecchi di 30 giorni
find $BACKUP_DIR -name "agrisecure_backup_*.tar.gz" -mtime +30 -delete

echo "Backup completato: agrisecure_backup_$DATE.tar.gz"
```

```bash
chmod +x /opt/agrisecure/backend/scripts/backup_db.sh
```

#### Subtask 2.2: Cron Job Backup
```bash
# Aggiungi a crontab
sudo crontab -e

# Backup giornaliero alle 2:00 AM
0 2 * * * /opt/agrisecure/backend/scripts/backup_db.sh >> /var/log/agrisecure_backup.log 2>&1
```

#### Subtask 2.3: Script Restore
**File**: `backend/scripts/restore_db.sh`
```bash
#!/bin/bash
# AgriSecure Database Restore Script

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    exit 1
fi

BACKUP_FILE=$1
TEMP_DIR="/tmp/agrisecure_restore"
DB_NAME="agrisecure"
DB_USER="agrisecure"

# Estrai backup
mkdir -p $TEMP_DIR
tar -xzf $BACKUP_FILE -C $TEMP_DIR

# Stop services
sudo systemctl stop agrisecure-web
sudo systemctl stop agrisecure-celery
sudo systemctl stop agrisecure-mqtt

# Restore database
pg_restore -U $DB_USER -d $DB_NAME -c $TEMP_DIR/db_*.dump

# Restore Redis
sudo systemctl stop redis
sudo cp $TEMP_DIR/redis_*.rdb /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb
sudo systemctl start redis

# Start services
sudo systemctl start agrisecure-mqtt
sudo systemctl start agrisecure-celery
sudo systemctl start agrisecure-web

# Cleanup
rm -rf $TEMP_DIR

echo "Restore completato!"
```

**Checklist**:
- [ ] Script backup creato e testato
- [ ] Cron job configurato
- [ ] Script restore creato e testato
- [ ] Documentazione procedura restore

---

### Task 3: Logging Strutturato (Giorno 3)
**Priorità**: 🟡 MEDIA  
**Effort**: 3 ore

#### Subtask 3.1: Configurare Structlog
**File**: `backend/requirements.txt`
```txt
structlog>=24.1.0
python-json-logger>=2.0.0
```

**File**: `backend/agrisecure/settings.py`
```python
import structlog

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
        'plain': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'plain',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/opt/agrisecure/backend/logs/agrisecure.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/opt/agrisecure/backend/logs/errors.log',
            'maxBytes': 10485760,
            'backupCount': 5,
            'formatter': 'json',
            'level': 'ERROR',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file', 'error_file'],
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.core': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'apps.security': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Structlog configuration
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

#### Subtask 3.2: Usare Logging nel Codice
**Esempio**: `backend/apps/security/views.py`
```python
import structlog

logger = structlog.get_logger(__name__)

class AlarmViewSet(viewsets.ModelViewSet):
    def perform_action(self, request, pk=None):
        alarm = self.get_object()
        action = request.data.get('action')
        
        logger.info(
            "alarm_action_triggered",
            alarm_id=alarm.id,
            action=action,
            user=request.user.username,
            node=alarm.node.node_id
        )
        
        # ... logica
        
        logger.info(
            "alarm_action_completed",
            alarm_id=alarm.id,
            action=action,
            status=alarm.status
        )
```

**Checklist**:
- [ ] Structlog configurato
- [ ] Logging directory creata
- [ ] Log rotation configurato
- [ ] Logging aggiunto a endpoint critici

---

### Task 4: Health Check Endpoint (Giorno 4)
**Priorità**: 🟠 ALTA  
**Effort**: 2 ore

#### Subtask 4.1: Creare Health Check View
**File**: `backend/apps/core/views.py`
```python
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis
import paho.mqtt.client as mqtt

def health_check(request):
    """Endpoint health check per monitoring"""
    health = {
        'status': 'healthy',
        'checks': {}
    }
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health['checks']['database'] = 'ok'
    except Exception as e:
        health['status'] = 'unhealthy'
        health['checks']['database'] = f'error: {str(e)}'
    
    # Check Redis
    try:
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
        health['checks']['redis'] = 'ok'
    except Exception as e:
        health['status'] = 'unhealthy'
        health['checks']['redis'] = f'error: {str(e)}'
    
    # Check MQTT broker
    try:
        client = mqtt.Client()
        client.connect('localhost', 1883, 5)
        client.disconnect()
        health['checks']['mqtt'] = 'ok'
    except Exception as e:
        health['status'] = 'unhealthy'
        health['checks']['mqtt'] = f'error: {str(e)}'
    
    # Check disk space
    import shutil
    stat = shutil.disk_usage('/opt/agrisecure')
    disk_percent = (stat.used / stat.total) * 100
    health['checks']['disk'] = {
        'free_gb': round(stat.free / (1024**3), 2),
        'used_percent': round(disk_percent, 2)
    }
    if disk_percent > 90:
        health['status'] = 'warning'
    
    status_code = 200 if health['status'] == 'healthy' else 503
    return JsonResponse(health, status=status_code)
```

**File**: `backend/agrisecure/urls.py`
```python
from apps.core.views import health_check

urlpatterns = [
    # ... existing urls
    path('health/', health_check, name='health_check'),
]
```

#### Subtask 4.2: Monitorare con Script
**File**: `backend/scripts/check_health.sh`
```bash
#!/bin/bash
# AgriSecure Health Check Script

HEALTH_URL="http://localhost/health/"
ALERT_EMAIL="admin@example.com"

response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $response -eq 200 ]; then
    echo "$(date): System healthy"
    exit 0
else
    echo "$(date): System unhealthy (HTTP $response)"
    # Invia notifica
    echo "AgriSecure health check failed" | mail -s "AgriSecure Alert" $ALERT_EMAIL
    exit 1
fi
```

```bash
# Aggiungi a crontab (ogni 5 minuti)
*/5 * * * * /opt/agrisecure/backend/scripts/check_health.sh >> /var/log/agrisecure_health.log 2>&1
```

**Checklist**:
- [ ] Health check endpoint implementato
- [ ] Testing health check
- [ ] Script monitoring configurato
- [ ] Documentazione endpoint

---

### Task 5: Documentazione Base (Giorno 5-7)
**Priorità**: 🟡 MEDIA  
**Effort**: 1 giorno

#### Subtask 5.1: API Documentation
```bash
# Installare drf-spectacular se non presente
pip install drf-spectacular
```

**File**: `backend/agrisecure/settings.py`
```python
INSTALLED_APPS = [
    # ...
    'drf_spectacular',
]

REST_FRAMEWORK = {
    # ...
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'AgriSecure IoT API',
    'DESCRIPTION': 'API per sistema IoT agricolo',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
```

**File**: `backend/agrisecure/urls.py`
```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # ...
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

Accesso docs: `http://your-server/api/v1/docs/`

#### Subtask 5.2: README Utente Finale
**File**: `docs/USER_GUIDE.md`
```markdown
# AgriSecure - Guida Utente

## Accesso Dashboard
1. Aprire browser
2. Navigare a http://agrisecure.local
3. Login con credenziali

## Funzioni Principali
### Visualizzare Nodi
...

### Grafici Sensori
...

### Gestire Allarmi
...

### Armare/Disarmare Sistema
...
```

**Checklist**:
- [ ] API docs generati e accessibili
- [ ] User guide creata
- [ ] Screenshots dashboard aggiunte
- [ ] FAQ aggiornate

---

## 🔒 Fase 1: Sicurezza e Testing (30 Giorni)

[... continua con task dettagliati per Fase 1 ...]

---

<a name="tracking"></a>
## 📊 Tracking Progress

### Template Task
```markdown
## [TASK-XXX] Titolo Task

**Fase**: X  
**Priorità**: 🔴 CRITICA / 🟠 ALTA / 🟡 MEDIA / 🟢 BASSA  
**Effort**: X ore/giorni  
**Assegnato**: Nome  
**Deadline**: YYYY-MM-DD  
**Status**: 🔵 TODO / 🟡 IN PROGRESS / 🟢 DONE / 🔴 BLOCKED

### Obiettivo
Descrizione chiara dell'obiettivo

### Acceptance Criteria
- [ ] Criterio 1
- [ ] Criterio 2

### Subtasks
- [ ] Subtask 1
- [ ] Subtask 2

### Testing
- [ ] Unit test
- [ ] Integration test
- [ ] Manual test

### Documentazione
- [ ] Code comments
- [ ] API docs
- [ ] User docs

### Deploy
- [ ] Staging
- [ ] Production

### Notes
Note aggiuntive
```

### Board Status (Esempio)
```
TODO (5)              IN PROGRESS (2)      DONE (3)
┌─────────────┐      ┌──────────────┐    ┌──────────────┐
│ TASK-005    │      │ TASK-002     │    │ TASK-001     │
│ TASK-006    │      │ TASK-004     │    │ TASK-003     │
│ TASK-007    │      └──────────────┘    │ TASK-008     │
│ TASK-009    │                           └──────────────┘
│ TASK-010    │
└─────────────┘
```

---

## 📝 Note Finali

**Questa roadmap è un documento vivo** e deve essere aggiornata regolarmente.

### Prossimi Aggiornamenti
- Ogni settimana: Review progresso
- Ogni mese: Aggiornamento priorità
- Ogni trimestre: Revisione strategica

### Contatti
Per domande o suggerimenti sulla roadmap, contattare il team di sviluppo.

---

**Versione**: 1.0  
**Ultima Revisione**: 6 Gennaio 2026
