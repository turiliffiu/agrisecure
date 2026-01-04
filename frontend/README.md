# AgriSecure Dashboard - Frontend

Dashboard React per il sistema di monitoraggio AgriSecure IoT.

## 🚀 Tecnologie

- **React 18** - Framework UI
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Router** - Routing
- **Recharts** - Grafici
- **Axios** - HTTP client
- **Lucide React** - Icone

## 📦 Installazione

### Prerequisiti

- Node.js 18+ 
- npm o yarn
- Backend AgriSecure attivo

### Setup Sviluppo

```bash
# Entra nella cartella frontend
cd frontend

# Installa dipendenze
npm install

# Crea file ambiente (opzionale)
cp .env.example .env

# Avvia in modalità sviluppo
npm run dev
```

La dashboard sarà disponibile su http://localhost:3000

### Build Produzione

```bash
# Crea build ottimizzata
npm run build

# I file saranno in dist/
```

## 🔧 Configurazione

### Variabili d'Ambiente

Crea un file `.env` nella root del frontend:

```bash
# URL del backend API (lascia vuoto per proxy locale)
VITE_API_URL=http://192.168.1.160
```

### Proxy Sviluppo

In sviluppo, le chiamate API vengono proxate automaticamente al backend. 
Modifica `vite.config.js` se necessario:

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://192.168.1.160',  // URL del tuo backend
      changeOrigin: true,
    }
  }
}
```

## 📁 Struttura Progetto

```
frontend/
├── public/              # File statici
│   └── favicon.svg
├── src/
│   ├── api/             # Client API
│   │   ├── axios.js     # Configurazione Axios
│   │   └── services.js  # Servizi API
│   ├── components/      # Componenti riutilizzabili
│   │   └── Layout.jsx   # Layout principale
│   ├── context/         # React Context
│   │   └── AuthContext.jsx
│   ├── hooks/           # Custom hooks
│   ├── pages/           # Pagine
│   │   ├── Dashboard.jsx
│   │   ├── Nodes.jsx
│   │   ├── NodeDetail.jsx
│   │   ├── Sensors.jsx
│   │   ├── Alarms.jsx
│   │   ├── ArmSystem.jsx
│   │   ├── Settings.jsx
│   │   └── Login.jsx
│   ├── App.jsx          # Componente principale
│   ├── main.jsx         # Entry point
│   └── index.css        # Stili globali
├── index.html
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
└── package.json
```

## 📱 Pagine

| Pagina | Percorso | Descrizione |
|--------|----------|-------------|
| Login | `/login` | Autenticazione JWT |
| Dashboard | `/` | Panoramica sistema |
| Nodi | `/nodes` | Lista nodi IoT |
| Dettaglio Nodo | `/nodes/:id` | Info singolo nodo |
| Sensori | `/sensors` | Grafici sensori |
| Allarmi | `/alarms` | Gestione allarmi |
| Armamento | `/arm` | Arma/disarma sistema |
| Impostazioni | `/settings` | Configurazione |

## 🔐 Autenticazione

Il frontend usa JWT tokens per l'autenticazione:

1. Login invia credenziali a `/api/v1/auth/token/`
2. Riceve `access` e `refresh` token
3. Token salvati in localStorage
4. Token refresh automatico alla scadenza

## 🎨 Personalizzazione

### Colori

I colori del tema sono definiti in `tailwind.config.js`:

```javascript
colors: {
  'agri': {
    500: '#22c55e',  // Verde principale
    600: '#16a34a',
    // ...
  }
}
```

### Logo

Sostituisci `public/favicon.svg` con il tuo logo.

## 🚀 Deploy in Produzione

### Con Nginx (consigliato)

1. Build del progetto:
```bash
npm run build
```

2. Copia i file in Nginx:
```bash
sudo cp -r dist/* /var/www/agrisecure-dashboard/
```

3. Configura Nginx:
```nginx
server {
    listen 80;
    server_name dashboard.agrisecure.local;
    root /var/www/agrisecure-dashboard;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Servito dal Backend Django

Puoi anche servire il frontend direttamente da Django:

1. Build del progetto
2. Copia `dist/` in `backend/staticfiles/dashboard/`
3. Configura Django per servire i file statici

## 🐛 Troubleshooting

### Errore CORS
Assicurati che il backend abbia CORS configurato correttamente in `settings.py`.

### Token scaduto
Il refresh automatico dovrebbe gestirlo. Se persiste, effettua logout e login.

### API non raggiungibile
Verifica che `VITE_API_URL` sia corretto e che il backend sia online.

## 📄 Licenza

Proprietario - Turiliffiu © 2024-2025
