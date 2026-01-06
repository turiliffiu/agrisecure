# 📚 AgriSecure - Best Practices & Developer Guidelines

**Versione**: 1.0  
**Data**: 6 Gennaio 2026

---

## 📑 Indice

1. [Convenzioni Codice](#code-conventions)
2. [Git Workflow](#git-workflow)
3. [Testing Guidelines](#testing)
4. [Security Guidelines](#security)
5. [Performance Guidelines](#performance)
6. [API Design Guidelines](#api-design)
7. [Database Guidelines](#database)
8. [Firmware Guidelines](#firmware)
9. [Deployment Guidelines](#deployment)
10. [Troubleshooting Common Issues](#troubleshooting)

---

<a name="code-conventions"></a>
## 💻 Convenzioni Codice

### Python / Django

#### Stile Codice
```python
# Usa Black per formatting automatico
black --line-length 100 .

# Usa isort per import
isort --profile black .

# Usa flake8 per linting
flake8 --max-line-length=100 --exclude=migrations .
```

#### Naming Conventions
```python
# Classi: PascalCase
class SensorReading(models.Model):
    pass

# Funzioni/metodi: snake_case
def calculate_average_temperature(readings):
    pass

# Costanti: UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
MQTT_TIMEOUT_SECONDS = 30

# Variabili: snake_case
sensor_value = 25.5
is_active = True
```

#### Docstrings
```python
def process_sensor_data(node_id: str, readings: dict) -> SensorReading:
    """
    Processa dati sensore e salva nel database.
    
    Args:
        node_id: ID univoco del nodo (es. "AMB-001")
        readings: Dizionario con letture sensori
            {
                "temperature": 25.5,
                "humidity": 65.0,
                "pressure": 1013.25
            }
    
    Returns:
        SensorReading: Istanza salvata nel database
    
    Raises:
        ValueError: Se node_id non valido
        ValidationError: Se readings non validi
    
    Example:
        >>> readings = {"temperature": 25.5, "humidity": 65}
        >>> sensor = process_sensor_data("AMB-001", readings)
        >>> sensor.temperature
        Decimal('25.50')
    """
    pass
```

#### Type Hints
```python
from typing import List, Dict, Optional, Union
from decimal import Decimal

def get_temperature_range(
    node: Node,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Optional[Decimal]]:
    """Ritorna range temperatura per periodo."""
    return {
        "min": Decimal("15.5"),
        "max": Decimal("28.3"),
        "avg": Decimal("22.1")
    }
```

#### Django Models Best Practices
```python
class SensorReading(models.Model):
    """
    Sempre includere:
    - Docstring della classe
    - __str__ method
    - Meta class (ordering, indexes)
    - Property methods per logica derivata
    """
    
    # Relazioni prima
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    
    # Poi campi normali
    timestamp = models.DateTimeField(default=timezone.now)
    temperature = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Meta class
    class Meta:
        db_table = 'sensor_readings'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['node', '-timestamp']),
        ]
        verbose_name = 'Lettura Sensore'
        verbose_name_plural = 'Letture Sensori'
    
    # Metodi speciali
    def __str__(self):
        return f"{self.node.node_id} @ {self.timestamp}"
    
    # Property methods
    @property
    def is_temperature_critical(self) -> bool:
        """Verifica se temperatura fuori range."""
        return self.temperature < 0 or self.temperature > 40
    
    # Metodi normali
    def save(self, *args, **kwargs):
        """Override save per validazione custom."""
        self.full_clean()
        super().save(*args, **kwargs)
```

### C++ / Arduino (Firmware)

#### Stile Codice
```cpp
// Usa clang-format
// File: .clang-format
BasedOnStyle: Google
IndentWidth: 4
ColumnLimit: 100
```

#### Naming Conventions
```cpp
// Classi: PascalCase
class MeshManager {
    // ...
};

// Funzioni: camelCase
void setupMesh() {
    // ...
}

// Costanti: UPPER_SNAKE_CASE
#define MAX_NODES 25
const int RETRY_DELAY_MS = 1000;

// Variabili: snake_case
int sensor_value = 0;
bool is_connected = false;
```

#### Comments & Documentation
```cpp
/**
 * @brief Legge temperatura dal sensore BME280
 * 
 * @return float Temperatura in gradi Celsius
 * @throws SensorError Se sensore non risponde
 * 
 * @note Richiede inizializzazione previva con setup_bme280()
 * 
 * @example
 *   float temp = read_temperature();
 *   if (temp > 30.0) {
 *       trigger_alert();
 *   }
 */
float read_temperature() {
    // Implementation
}

// Single-line comments: doppio slash
// Questo è un commento
```

#### Error Handling
```cpp
// Usa return codes
enum ErrorCode {
    SUCCESS = 0,
    ERROR_SENSOR_NOT_FOUND = 1,
    ERROR_TIMEOUT = 2,
    ERROR_INVALID_DATA = 3
};

ErrorCode read_sensor(float* value) {
    if (!sensor_initialized) {
        return ERROR_SENSOR_NOT_FOUND;
    }
    
    *value = sensor.read();
    return SUCCESS;
}

// Uso
float temp;
ErrorCode err = read_sensor(&temp);
if (err != SUCCESS) {
    log_error("Sensor read failed", err);
    return;
}
```

---

<a name="git-workflow"></a>
## 🌿 Git Workflow

### Branch Strategy

```
main (production)
├── develop (staging)
    ├── feature/api-rate-limiting
    ├── feature/dashboard-react
    ├── bugfix/mqtt-reconnect
    └── hotfix/security-patch
```

#### Branch Naming
```bash
# Features
feature/short-description
feature/api-rate-limiting
feature/ml-classification

# Bugfix
bugfix/short-description
bugfix/mqtt-connection-issue
bugfix/sensor-timeout

# Hotfix (per production)
hotfix/critical-security-patch
hotfix/database-connection

# Release
release/v1.1.0
```

### Commit Messages

#### Formato
```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Types
- `feat`: Nuova feature
- `fix`: Bug fix
- `docs`: Documentazione
- `style`: Formatting, no code change
- `refactor`: Refactoring
- `perf`: Performance improvement
- `test`: Test
- `chore`: Build, CI, dependencies

#### Esempi
```bash
# Good
feat(api): add rate limiting to alarm endpoints

Implemented DRF throttling classes for alarm actions
to prevent abuse. Default limit: 10 requests/minute.

Closes #42

# Good
fix(mqtt): reconnect on connection loss

Added automatic reconnection logic with exponential
backoff (1s, 2s, 4s, 8s, max 30s).

Fixes #156

# Bad
fixed bug
updated code
changes
```

### Pull Request Guidelines

#### Template PR
```markdown
## Description
Breve descrizione della PR

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- Cambiamento 1
- Cambiamento 2

## Testing
- [ ] Unit tests passed
- [ ] Integration tests passed
- [ ] Manual testing completed

## Screenshots
(se applicabile)

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests added
```

---

<a name="testing"></a>
## 🧪 Testing Guidelines

### Test Structure

```
backend/
├── apps/
    ├── nodes/
    │   ├── tests/
    │   │   ├── __init__.py
    │   │   ├── test_models.py
    │   │   ├── test_views.py
    │   │   └── test_api.py
    │   └── ...
```

### Django Tests

#### Test Models
```python
# apps/nodes/tests/test_models.py
from django.test import TestCase
from apps.nodes.models import Node, NodeStatus

class NodeModelTests(TestCase):
    def setUp(self):
        """Setup eseguito prima di ogni test"""
        self.node = Node.objects.create(
            node_id='TEST-001',
            name='Test Node',
            node_type='AMB',
            status=NodeStatus.ONLINE
        )
    
    def test_is_online_with_recent_heartbeat(self):
        """Test che nodo con heartbeat recente sia online"""
        self.node.last_seen = timezone.now()
        self.node.save()
        
        self.assertTrue(self.node.is_online)
    
    def test_is_online_with_old_heartbeat(self):
        """Test che nodo con heartbeat vecchio sia offline"""
        self.node.last_seen = timezone.now() - timedelta(hours=3)
        self.node.save()
        
        self.assertFalse(self.node.is_online)
    
    def test_battery_status_critical(self):
        """Test status batteria critico"""
        self.node.battery_percentage = 5
        self.assertEqual(self.node.battery_status, 'critical')
```

#### Test API
```python
# apps/nodes/tests/test_api.py
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User

class NodeAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_list_nodes(self):
        """Test lista nodi"""
        response = self.client.get('/api/v1/nodes/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
    
    def test_create_node(self):
        """Test creazione nodo"""
        data = {
            'node_id': 'AMB-002',
            'name': 'Nuovo Nodo',
            'node_type': 'AMB'
        }
        response = self.client.post('/api/v1/nodes/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['node_id'], 'AMB-002')
```

#### Test Factories (factory-boy)
```python
# apps/nodes/tests/factories.py
import factory
from apps.nodes.models import Node

class NodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Node
    
    node_id = factory.Sequence(lambda n: f'TEST-{n:03d}')
    name = factory.Faker('company')
    node_type = 'AMB'
    status = 'online'
    battery_percentage = factory.Faker('pyint', min_value=20, max_value=100)

# Uso nei test
def test_multiple_nodes(self):
    nodes = NodeFactory.create_batch(10)
    self.assertEqual(Node.objects.count(), 10)
```

### Running Tests

```bash
# Tutti i test
pytest

# Test specifici
pytest apps/nodes/tests/

# Con coverage
pytest --cov=apps --cov-report=html

# Paralleli (più veloci)
pytest -n auto

# Verbose
pytest -v

# Stop al primo fallimento
pytest -x
```

### Coverage Target
- **Minimum**: 70%
- **Target**: 80%
- **Excellent**: 90%+

```bash
# Genera report coverage
pytest --cov=apps --cov-report=html
# Apri htmlcov/index.html
```

---

<a name="security"></a>
## 🔒 Security Guidelines

### General Security Practices

#### 1. Secrets Management
```python
# ❌ MAI hardcodare secrets
API_KEY = "sk-1234567890abcdef"

# ✅ Usa environment variables
import os
API_KEY = os.getenv('API_KEY')

# ✅ Validazione
if not API_KEY:
    raise ValueError("API_KEY environment variable not set")
```

#### 2. Input Validation
```python
# ✅ Validazione input API
from rest_framework import serializers

class SensorDataSerializer(serializers.Serializer):
    temperature = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=-50,
        max_value=70
    )
    
    def validate_temperature(self, value):
        if value < -50 or value > 70:
            raise serializers.ValidationError(
                "Temperature out of valid range"
            )
        return value
```

#### 3. SQL Injection Prevention
```python
# ❌ MAI usare raw SQL con input utente
query = f"SELECT * FROM nodes WHERE node_id = '{node_id}'"

# ✅ Usa Django ORM
node = Node.objects.get(node_id=node_id)

# ✅ O parametrized queries
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute(
        "SELECT * FROM nodes WHERE node_id = %s",
        [node_id]
    )
```

#### 4. XSS Prevention
```python
# Django templates auto-escape di default
# {{ user_input }}  -> safe

# Se serve HTML raw (raro!)
# {{ user_input|safe }}  -> SOLO se validato!

# In API responses
from rest_framework.utils.html import escape
safe_text = escape(user_input)
```

#### 5. CSRF Protection
```python
# Django ha CSRF protection di default
# Per API REST, usa JWT invece di session

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}
```

#### 6. Rate Limiting
```python
# Implementare sempre rate limiting su API pubbliche
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    }
}
```

### Security Checklist

- [ ] Tutti i secrets in .env (non in codice)
- [ ] .env in .gitignore
- [ ] HTTPS/TLS abilitato (Nginx)
- [ ] MQTT con TLS (Mosquitto)
- [ ] Rate limiting su API
- [ ] Input validation su tutti gli endpoint
- [ ] CSRF protection abilitata
- [ ] SQL injection prevented (ORM usage)
- [ ] XSS prevention (auto-escaping)
- [ ] Strong passwords policy
- [ ] Regular security updates (pip, npm)
- [ ] Error messages non espongono info sensibili
- [ ] Logging per audit trail
- [ ] 2FA per admin (opzionale)

---

<a name="performance"></a>
## ⚡ Performance Guidelines

### Database Optimization

#### 1. Use Indexes
```python
class SensorReading(models.Model):
    # ...
    
    class Meta:
        indexes = [
            # Single field
            models.Index(fields=['timestamp']),
            # Composite index
            models.Index(fields=['node', '-timestamp']),
            # Con nome custom
            models.Index(
                fields=['node', 'timestamp'],
                name='idx_node_timestamp'
            ),
        ]
```

#### 2. Select Related / Prefetch Related
```python
# ❌ N+1 queries problem
nodes = Node.objects.all()
for node in nodes:
    print(node.gateway.name)  # Query per ogni nodo!

# ✅ Use select_related (ForeignKey)
nodes = Node.objects.select_related('gateway').all()
for node in nodes:
    print(node.gateway.name)  # Single query

# ✅ Use prefetch_related (ManyToMany, reverse FK)
zones = SecurityZone.objects.prefetch_related('nodes').all()
for zone in zones:
    for node in zone.nodes.all():  # No extra queries
        print(node.name)
```

#### 3. Bulk Operations
```python
# ❌ Slow: N queries
for reading in readings_data:
    SensorReading.objects.create(**reading)

# ✅ Fast: 1 query
readings = [SensorReading(**data) for data in readings_data]
SensorReading.objects.bulk_create(readings, batch_size=1000)

# ✅ Bulk update
SensorReading.objects.filter(
    timestamp__lt=cutoff_date
).update(is_archived=True)
```

#### 4. Query Optimization
```python
# ❌ Fetch tutto
readings = SensorReading.objects.all()

# ✅ Solo campi necessari
readings = SensorReading.objects.only(
    'timestamp', 'temperature'
)

# ✅ Aggregazione nel database
from django.db.models import Avg, Max, Min

stats = SensorReading.objects.filter(
    node_id='AMB-001'
).aggregate(
    avg_temp=Avg('temperature'),
    max_temp=Max('temperature'),
    min_temp=Min('temperature')
)
```

### Caching

#### 1. Redis Cache
```python
from django.core.cache import cache

# Cache view
def get_dashboard_summary(request):
    cache_key = 'dashboard_summary'
    data = cache.get(cache_key)
    
    if data is None:
        data = compute_dashboard_summary()
        cache.set(cache_key, data, timeout=300)  # 5 min
    
    return Response(data)

# Cache invalidation
def create_alarm(request):
    # ... create alarm
    cache.delete('dashboard_summary')
```

#### 2. Django Cache Decorators
```python
from django.views.decorators.cache import cache_page

# Cache view per 5 minuti
@cache_page(60 * 5)
def sensor_chart(request, node_id):
    # ...
```

### Celery Task Optimization

```python
# ❌ Task sincrono nella view
def trigger_alarm(request):
    send_telegram_notification()  # Blocca response
    send_email_notification()
    return Response({'status': 'ok'})

# ✅ Task asincrono
def trigger_alarm(request):
    send_telegram_notification.delay()  # Background
    send_email_notification.delay()
    return Response({'status': 'ok'})

@shared_task
def send_telegram_notification():
    # ...
```

---

<a name="api-design"></a>
## 🔌 API Design Guidelines

### RESTful Principles

#### URLs
```
# ✅ Good
GET    /api/v1/nodes/              # List
GET    /api/v1/nodes/{id}/         # Detail
POST   /api/v1/nodes/              # Create
PUT    /api/v1/nodes/{id}/         # Update
PATCH  /api/v1/nodes/{id}/         # Partial update
DELETE /api/v1/nodes/{id}/         # Delete

# Custom actions
POST   /api/v1/nodes/{id}/send_command/
GET    /api/v1/sensors/readings/latest/

# ❌ Bad
GET /api/v1/getNodes
POST /api/v1/createNode
GET /api/v1/node_detail?id=123
```

#### HTTP Status Codes
```
200 OK - Success
201 Created - Resource created
204 No Content - Success, no body
400 Bad Request - Validation error
401 Unauthorized - Auth required
403 Forbidden - Not allowed
404 Not Found - Resource not found
429 Too Many Requests - Rate limit
500 Internal Server Error - Server error
503 Service Unavailable - Service down
```

#### Response Format
```json
// ✅ Success response
{
  "data": {
    "id": "AMB-001",
    "name": "Nodo Ambientale 1",
    "temperature": 25.5
  },
  "meta": {
    "timestamp": "2026-01-06T10:30:00Z"
  }
}

// ✅ List response
{
  "data": [...],
  "meta": {
    "count": 10,
    "next": "/api/v1/nodes/?page=2",
    "previous": null
  }
}

// ✅ Error response
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid temperature value",
    "details": {
      "temperature": ["Must be between -50 and 70"]
    }
  }
}
```

---

## 📝 Conclusione

Queste linee guida sono un documento vivo e devono essere:
- Seguite da tutto il team
- Aggiornate quando necessario
- Discusse nelle code reviews

**Ricorda**: Il codice si legge più spesso di quanto si scrive. Scrivi codice chiaro e manutenibile!

---

**Versione**: 1.0  
**Ultima Revisione**: 6 Gennaio 2026
