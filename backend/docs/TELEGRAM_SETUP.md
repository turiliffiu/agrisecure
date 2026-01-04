# 🔔 Configurazione Notifiche Telegram

Guida per configurare le notifiche Telegram su AgriSecure.

---

## 📱 Creazione Bot Telegram

### Step 1: Crea il Bot

1. Apri **Telegram** sul telefono o desktop
2. Cerca **@BotFather** e avvia la chat
3. Scrivi `/newbot`
4. Inserisci un **nome** per il bot (es. `AgriSecure Alert`)
5. Inserisci uno **username** (deve terminare con `bot`, es. `agrisecure_alert_bot`)
6. BotFather ti invierà il **TOKEN** - **copialo e conservalo!**

Esempio di token:
```
123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

> ⚠️ **IMPORTANTE**: Non condividere mai il token pubblicamente!

---

### Step 2: Ottieni il Chat ID

#### Opzione A: Chat privata (solo tu ricevi le notifiche)

1. Cerca **@userinfobot** su Telegram
2. Avvialo con `/start`
3. Ti mostrerà il tuo **Chat ID** (un numero positivo, es. `562710947`)

#### Opzione B: Gruppo (più persone ricevono le notifiche)

1. Crea un nuovo gruppo Telegram
2. Aggiungi il tuo bot al gruppo
3. Aggiungi **@raw_data_bot** al gruppo
4. Scrivi un messaggio qualsiasi nel gruppo
5. Il bot mostrerà il **Chat ID del gruppo** (numero negativo, es. `-100123456789`)
6. Puoi rimuovere @raw_data_bot dopo aver ottenuto l'ID

---

### Step 3: Avvia il Bot

**Passaggio fondamentale!** Devi avviare la conversazione con il bot:

1. Cerca il tuo bot su Telegram (es. `@agrisecure_alert_bot`)
2. Clicca **Avvia** o scrivi `/start`

> Senza questo passaggio il bot non può inviarti messaggi!

---

## ⚙️ Configurazione Server

### Step 1: Modifica il file .env

```bash
sudo nano /opt/agrisecure/backend/.env
```

Trova e modifica queste righe:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=IL_TUO_TOKEN
TELEGRAM_CHAT_ID=IL_TUO_CHAT_ID
```

Esempio:
```bash
TELEGRAM_BOT_TOKEN=8323273391:AAEMVy0LBWPcN_7STZ3oyH2e728vdd5cUA8
TELEGRAM_CHAT_ID=562710947
```

Salva con `CTRL+O`, `Enter`, `CTRL+X`

### Step 2: Riavvia Celery

```bash
sudo systemctl restart agrisecure-celery
```

---

## 🧪 Test Notifiche

Esegui questo comando per verificare che tutto funzioni:

```bash
cd /opt/agrisecure/backend
sudo -u agrisecure venv/bin/python -c "
import requests
import os

# Carica da .env o inserisci manualmente
TOKEN = 'IL_TUO_TOKEN'
CHAT_ID = 'IL_TUO_CHAT_ID'

url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
response = requests.post(url, json={
    'chat_id': CHAT_ID,
    'text': '🌿 *AgriSecure* - Test notifica!\n\nIl sistema di notifiche funziona correttamente. ✅',
    'parse_mode': 'Markdown'
})
print('✅ OK! Controlla Telegram.' if response.status_code == 200 else f'❌ Errore: {response.text}')
"
```

Se tutto è configurato correttamente, riceverai un messaggio su Telegram.

---

## 📨 Tipi di Notifiche

AgriSecure invia automaticamente notifiche per:

| Evento | Priorità | Descrizione |
|--------|----------|-------------|
| 🚨 **Persona rilevata** | CRITICA | Allarme intrusione persona |
| ⚠️ **Manomissione** | CRITICA | Tentativo di manomissione sensore |
| 🦊 **Animale grande** | ALTA | Rilevato animale di grandi dimensioni |
| 🔋 **Batteria scarica** | MEDIA | Nodo con batteria sotto il 20% |
| 📡 **Nodo offline** | MEDIA | Nodo non raggiungibile da oltre 2 ore |
| 🌡️ **Temperatura critica** | MEDIA | Temperatura fuori range (-5°C / +45°C) |
| 💧 **Suolo secco** | BASSA | Umidità suolo sotto il 15% |

---

## 🔧 Troubleshooting

### Errore: "chat not found"
- **Causa**: Non hai avviato la chat con il bot
- **Soluzione**: Cerca il bot su Telegram e clicca "Avvia"

### Errore: "Unauthorized"
- **Causa**: Token non valido
- **Soluzione**: Verifica il token copiato da BotFather

### Errore: "Bad Request: chat_id is empty"
- **Causa**: Chat ID non configurato
- **Soluzione**: Verifica che TELEGRAM_CHAT_ID sia impostato nel file .env

### Non ricevo notifiche
1. Verifica che Celery sia attivo:
   ```bash
   sudo systemctl status agrisecure-celery
   ```
2. Controlla i log:
   ```bash
   sudo journalctl -u agrisecure-celery -f
   ```
3. Verifica il file .env:
   ```bash
   cat /opt/agrisecure/backend/.env | grep TELEGRAM
   ```

---

## 📚 Comandi Bot (futuri)

In futuro sarà possibile interagire con il bot:

| Comando | Descrizione |
|---------|-------------|
| `/status` | Stato del sistema |
| `/arm` | Arma il sistema |
| `/disarm` | Disarma il sistema |
| `/nodes` | Lista nodi attivi |
| `/silence` | Silenzia notifiche per 1 ora |

> Funzionalità in sviluppo per versioni future.

---

## 🔐 Sicurezza

- **Non condividere** mai il token del bot pubblicamente
- Usa un **gruppo privato** se più persone devono ricevere notifiche
- Il bot può solo **inviare** messaggi, non può leggere le tue chat
- I comandi interattivi (futuri) richiederanno autenticazione
