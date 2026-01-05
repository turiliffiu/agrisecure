# AgriSecure Frontend - Django Templates

Dashboard frontend per AgriSecure realizzata con template Django, Tailwind CSS e Chart.js.

## 📦 Contenuto

```
frontend/
├── templates/
│   ├── base.html              # Template base con layout
│   ├── auth/
│   │   └── login.html         # Pagina login
│   ├── dashboard/
│   │   └── index.html         # Dashboard principale
│   ├── nodes/
│   │   ├── list.html          # Lista nodi
│   │   └── detail.html        # Dettaglio nodo
│   ├── sensors/
│   │   └── index.html         # Monitoraggio sensori
│   ├── security/
│   │   ├── alarms.html        # Lista allarmi
│   │   └── arm.html           # Armamento sistema
│   └── settings/
│       └── index.html         # Impostazioni
├── static/
│   ├── css/
│   │   └── style.css          # Stili custom
│   └── js/
│       └── main.js            # JavaScript custom
├── views.py                   # Views Django
├── urls.py                    # URL routing
├── apps.py                    # Configurazione app
└── __init__.py
```

## 🚀 Installazione

### 1. Copia i file sul server

```bash
# Sul server, vai alla cartella backend
cd /opt/agrisecure/backend

# Crea cartella frontend in apps
mkdir -p apps/frontend

# Copia i file (da locale o da GitHub)
# Se hai scaricato lo zip:
unzip frontend-django.zip -d apps/frontend/
```

### 2. Registra l'app in Django

Modifica `/opt/agrisecure/backend/agrisecure/settings.py`:

```python
INSTALLED_APPS = [
    # ... altre app ...
    'apps.frontend',  # <-- Aggiungi questa riga
]

# Aggiungi LOGIN settings
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
```

### 3. Aggiungi gli URL

Modifica `/opt/agrisecure/backend/agrisecure/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.api.urls')),
    path('', include('apps.frontend.urls')),  # <-- Aggiungi questa riga
]
```

### 4. Copia i template nella posizione corretta

```bash
# Crea cartella templates se non esiste
mkdir -p /opt/agrisecure/backend/templates

# Copia templates
cp -r apps/frontend/templates/* templates/

# Copia static files
mkdir -p /opt/agrisecure/backend/static
cp -r apps/frontend/static/* static/
```

### 5. Aggiorna settings.py per i template

Verifica che in `settings.py` ci sia:

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # <-- Deve esserci questo
        'APP_DIRS': True,
        # ...
    },
]

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
```

### 6. Raccogli i file statici

```bash
cd /opt/agrisecure/backend
sudo -u agrisecure venv/bin/python manage.py collectstatic --noinput
```

### 7. Riavvia il server

```bash
sudo systemctl restart agrisecure-web
```

### 8. Accedi alla dashboard

Apri nel browser: `http://IP_SERVER/`

Usa le credenziali del superuser Django creato durante l'installazione.

---

## 🎨 Tecnologie Utilizzate

- **Tailwind CSS** (via CDN) - Styling
- **Chart.js** - Grafici interattivi
- **Lucide Icons** - Icone
- **HTMX** (opzionale) - Interazioni AJAX

---

## 📱 Pagine

| Pagina | URL | Descrizione |
|--------|-----|-------------|
| Login | `/login/` | Autenticazione |
| Dashboard | `/` | Panoramica sistema |
| Nodi | `/nodes/` | Lista nodi IoT |
| Dettaglio Nodo | `/nodes/<id>/` | Info singolo nodo |
| Sensori | `/sensors/` | Grafici sensori |
| Allarmi | `/alarms/` | Gestione allarmi |
| Armamento | `/arm/` | Arma/disarma sistema |
| Impostazioni | `/settings/` | Configurazione |

---

## 🔧 Personalizzazione

### Modifica colori

I colori sono definiti in `base.html` nella configurazione Tailwind:

```javascript
tailwind.config = {
    theme: {
        extend: {
            colors: {
                'agri': {
                    500: '#22c55e',  // Verde principale
                    600: '#16a34a',
                    // ...
                }
            }
        }
    }
}
```

### Modifica logo

Cerca nel file `base.html` il tag SVG del logo e sostituiscilo con il tuo.

---

## 🐛 Troubleshooting

### Template non trovato
Verifica che `TEMPLATES['DIRS']` in settings.py punti alla cartella corretta.

### Stili non caricati
1. Esegui `python manage.py collectstatic`
2. Verifica che Nginx serva correttamente `/static/`

### Errore 403 CSRF
Assicurati che ogni form abbia `{% csrf_token %}`.

### Icone non visibili
Verifica la connessione internet (Lucide è caricato da CDN).

---

## 📄 Licenza

Proprietario - Turiliffiu © 2024-2025
