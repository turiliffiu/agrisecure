/**
 * AgriSecure IoT System - Firmware Nodo Sicurezza
 * 
 * Nodo per sicurezza perimetrale con:
 * - Rilevamento movimento (PIR HC-SR501 + AM312)
 * - Discriminazione persona/animale
 * - Tamper detection (MPU6050)
 * - Attuazione locale (sirena + LED)
 * 
 * Funzionamento:
 * - Always-on (no deep sleep)
 * - Interrupt-driven per risposta rapida
 * - Allarme locale immediato + notifica mesh
 * 
 * @author Turiliffiu
 * @version 1.0.0
 */

#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <Preferences.h>
#include <WebServer.h>
#include "agrisecure_config.h"
#include "mesh_manager.h"
#include "sensors_security.h"

// ============================================================
// Configurazione
// ============================================================
#ifndef NODE_ID
#define NODE_ID "SEC-001"
#endif

// Pin attuatori
#ifndef RELAY_SIREN_PIN
#define RELAY_SIREN_PIN 10
#endif

#ifndef RELAY_LIGHT_PIN
#define RELAY_LIGHT_PIN 11
#endif

// Durata allarme
#ifndef ALARM_DURATION
#define ALARM_DURATION 30000  // 30 secondi
#endif

#ifndef ALARM_COOLDOWN
#define ALARM_COOLDOWN 60000  // 1 minuto tra allarmi
#endif

// ============================================================
// Variabili Globali
// ============================================================
// LED RGB di stato WS2812 (settembre 2026): GPIO48 su hardware S3-N16R8, stesso
// pattern di GW-001/AMB-001. Sostituisce il vecchio LED singolo-colore
// (digitalWrite su LED_STATUS) del prototipo su ESP32-WROOM-32.
#ifndef LED_RGB_PIN
#define LED_RGB_PIN 48
#endif
Adafruit_NeoPixel statusRGB(1, LED_RGB_PIN, NEO_GRB + NEO_KHZ800);

static void setLed(uint8_t r, uint8_t g, uint8_t b) {
    statusRGB.setPixelColor(0, statusRGB.Color(r, g, b));
    statusRGB.show();
}

// ============================================================
// Configurazione NVS (settembre 2026, pattern GW-001/AMB-001)
// Identita' e parametri AP letti da NVS (namespace "agrisecure"), con default
// dalle macro di platformio.ini: stesso firmware su tutti i nodi SEC, ID
// impostato da web senza ricompilare. Node ID massimo NODE_ID_SIZE-1 (11)
// caratteri: la mesh lo copia con strncpy in un buffer da 12 byte.
// ============================================================
#ifndef AP_SSID
#define AP_SSID "AgriSecure-SEC"
#endif
#ifndef AP_PASSWORD
#define AP_PASSWORD "ChangeMe2026"
#endif

Preferences prefs;
String cfgNodeId;
String cfgAPSSID;
String cfgAPPassword;
// Parametri di allarme e mesh configurabili da web (ms in NVS, secondi nel form)
uint32_t cfgAlarmDuration;
uint32_t cfgAlarmCooldown;
uint32_t cfgHeartbeatInterval;

void loadConfig() {
    prefs.begin("agrisecure", false);  // read-write: crea il namespace al primo avvio
    cfgNodeId = prefs.getString("node_id", NODE_ID);
    cfgAPSSID = prefs.getString("ap_ssid", AP_SSID);
    cfgAPPassword = prefs.getString("ap_pass", AP_PASSWORD);
    cfgAlarmDuration = prefs.getULong("alarm_dur", ALARM_DURATION);
    cfgAlarmCooldown = prefs.getULong("alarm_cool", ALARM_COOLDOWN);
    cfgHeartbeatInterval = prefs.getULong("hb_intv", MESH_HEARTBEAT_INTERVAL);
    prefs.end();

    // Valori fuori intervallo (NVS corrotta o scritta a mano): torna al default.
    // Evita ad esempio un heartbeat a 0 che genererebbe una raffica di invii.
    if (cfgAlarmDuration < 5000 || cfgAlarmDuration > 600000) cfgAlarmDuration = ALARM_DURATION;
    if (cfgAlarmCooldown < 10000 || cfgAlarmCooldown > 3600000) cfgAlarmCooldown = ALARM_COOLDOWN;
    if (cfgHeartbeatInterval < 60000 || cfgHeartbeatInterval > 1800000) cfgHeartbeatInterval = MESH_HEARTBEAT_INTERVAL;

    if (cfgNodeId.length() >= NODE_ID_SIZE) {
        Serial.printf("[CONFIG] ATTENZIONE: Node ID '%s' troppo lungo (max %d), troncato\n",
                      cfgNodeId.c_str(), NODE_ID_SIZE - 1);
        cfgNodeId = cfgNodeId.substring(0, NODE_ID_SIZE - 1);
    }
    Serial.println(F("[CONFIG] Parametri caricati da NVS (o default se prima esecuzione)"));
}

// ============================================================
// AP-config on-demand (settembre 2026, pattern GW-001 adattato)
// A differenza di AMB-001 (blocca e poi dorme) qui l'AP e il web server
// girano DENTRO loop(): il nodo resta armato e operativo durante la
// configurazione. Pressione lunga (BUTTON_HOLD_MS) per aprire/chiudere,
// timeout di inattivita', link di uscita. Salvataggio = restart del nodo
// (durante il riavvio il nodo e' scoperto per il conto alla rovescia).
// ============================================================
#ifndef BUTTON_HOLD_MS
#define BUTTON_HOLD_MS 5000  // 5 secondi
#endif
#ifndef AP_CONFIG_TIMEOUT_MS
#define AP_CONFIG_TIMEOUT_MS 300000  // 5 minuti senza richieste HTTP
#endif

extern bool system_armed;  // definita piu' sotto

WebServer configServer(80);
bool apModeActive = false;
bool apCloseRequested = false;
uint32_t apStartTime = 0;

static String esc(const String& s) {
    String o;
    for (size_t i = 0; i < s.length(); i++) {
        char c = s[i];
        if (c == '&') o += "&amp;";
        else if (c == '<') o += "&lt;";
        else if (c == '>') o += "&gt;";
        else if (c == '\'') o += "&#39;";
        else o += c;
    }
    return o;
}

static String pageHead(const String& title) {
    String html = "<!DOCTYPE html><html><head><meta charset='utf-8'>";
    html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
    html += "<title>" + title + "</title>";
    html += "<style>body{font-family:sans-serif;max-width:480px;margin:20px auto;padding:0 15px;}";
    html += "h1{color:#2c5f2d;} .row{padding:8px 0;border-bottom:1px solid #eee;}";
    html += "label{display:block;margin-top:12px;font-weight:bold;}";
    html += "input{width:100%;padding:8px;box-sizing:border-box;margin-top:4px;}";
    html += "button{margin-top:20px;padding:10px 20px;background:#2c5f2d;color:#fff;border:none;border-radius:4px;}";
    html += "small{color:#888;}</style></head><body>";
    return html;
}

void handleConfigRoot() {
    apStartTime = millis();
    String html = pageHead("AgriSecure " + esc(cfgNodeId));
    html += "<h1>AgriSecure - " + esc(cfgNodeId) + "</h1>";
    html += "<div class='row'>Firmware: " + String(FIRMWARE_VERSION) + "</div>";
    html += "<div class='row'>Tipo nodo: Sicurezza</div>";
    html += "<div class='row'>Sistema: " + String(system_armed ? "ARMATO (resta attivo durante la configurazione)" : "DISARMATO") + "</div>";
    html += "<div class='row'>IP AP: " + WiFi.softAPIP().toString() + "</div>";
    html += "<div class='row'>Uptime: " + String(millis() / 1000) + " s</div>";
    html += "<p><a href='/config'>Modifica configurazione</a></p>";
    html += "<p><a href='/exit' style='color:#c0392b;'>Esci senza salvare</a></p>";
    html += "</body></html>";
    configServer.send(200, "text/html", html);
}

void handleConfigGet() {
    apStartTime = millis();
    String html = pageHead("Configurazione " + esc(cfgNodeId));
    html += "<h1>Configurazione</h1>";
    html += "<form method='POST' action='/config'>";
    html += "<label>Node ID</label><input name='node_id' maxlength='" + String(NODE_ID_SIZE - 1) + "' value='" + esc(cfgNodeId) + "'>";
    html += "<small>Es. SEC-001, SEC-002... massimo " + String(NODE_ID_SIZE - 1) + " caratteri</small>";
    html += "<label>AP SSID</label><input name='ap_ssid' value='" + esc(cfgAPSSID) + "'>";
    html += "<label>AP Password</label><input name='ap_pass' type='password' value=''>";
    html += "<small>Lascia vuoto per non modificare (minimo 8 caratteri se la cambi)</small>";
    html += "<hr><label>Durata allarme (secondi)</label><input name='alarm_dur' type='number' min='5' max='600' value='" + String(cfgAlarmDuration / 1000) + "'>";
    html += "<small>Da 5 a 600. Tempo di sirena e luce dopo il rilevamento di una persona</small>";
    html += "<label>Cooldown tra eventi (secondi)</label><input name='alarm_cool' type='number' min='10' max='3600' value='" + String(cfgAlarmCooldown / 1000) + "'>";
    html += "<small>Da 10 a 3600. Pausa minima tra due eventi dello stesso livello</small>";
    html += "<label>Intervallo heartbeat mesh (secondi)</label><input name='hb_intv' type='number' min='60' max='1800' value='" + String(cfgHeartbeatInterval / 1000) + "'>";
    html += "<small>Da 60 a 1800. Oltre, gli altri nodi potrebbero considerare questo nodo inattivo</small>";
    html += "<br><button type='submit'>Salva e riavvia</button>";
    html += "</form><p><a href='/'>Torna allo stato</a></p></body></html>";
    configServer.send(200, "text/html", html);
}

void handleConfigPost() {
    apStartTime = millis();
    String nid = configServer.arg("node_id");
    nid.trim();
    String newPass = configServer.arg("ap_pass");
    String newSsid = configServer.arg("ap_ssid");
    newSsid.trim();

    if (nid.length() == 0 || nid.length() >= NODE_ID_SIZE) {
        configServer.send(400, "text/plain", "Node ID non valido: da 1 a 11 caratteri");
        return;
    }
    if (newSsid.length() == 0) {
        configServer.send(400, "text/plain", "AP SSID non puo' essere vuoto");
        return;
    }
    if (newPass.length() > 0 && newPass.length() < 8) {
        configServer.send(400, "text/plain", "AP Password: minimo 8 caratteri");
        return;
    }

    long durS = configServer.arg("alarm_dur").toInt();
    long coolS = configServer.arg("alarm_cool").toInt();
    long hbS = configServer.arg("hb_intv").toInt();
    if (durS < 5 || durS > 600) {
        configServer.send(400, "text/plain", "Durata allarme: da 5 a 600 secondi");
        return;
    }
    if (coolS < 10 || coolS > 3600) {
        configServer.send(400, "text/plain", "Cooldown: da 10 a 3600 secondi");
        return;
    }
    if (hbS < 60 || hbS > 1800) {
        configServer.send(400, "text/plain", "Heartbeat: da 60 a 1800 secondi");
        return;
    }

    prefs.begin("agrisecure", false);
    prefs.putString("node_id", nid);
    prefs.putString("ap_ssid", newSsid);
    if (newPass.length() > 0) prefs.putString("ap_pass", newPass);
    prefs.putULong("alarm_dur", (uint32_t)durS * 1000);
    prefs.putULong("alarm_cool", (uint32_t)coolS * 1000);
    prefs.putULong("hb_intv", (uint32_t)hbS * 1000);
    prefs.end();

    String html = pageHead("Salvato");
    html += "<h1>Configurazione salvata</h1><p>Il nodo si sta riavviando...</p></body></html>";
    configServer.send(200, "text/html", html);

    Serial.println(F("[CONFIG] Nuovi parametri salvati su NVS, riavvio..."));
    delay(1000);
    ESP.restart();
}

void handleConfigExit() {
    String html = pageHead("Uscita");
    html += "<h1>Uscita in corso</h1><p>Il nodo torna al normale funzionamento...</p></body></html>";
    configServer.send(200, "text/html", html);
    apCloseRequested = true;  // chiusura eseguita in loop(), dopo aver risposto
}

void enableAPMode() {
    static bool handlersRegistered = false;
    WiFi.mode(WIFI_MODE_APSTA);
    WiFi.softAP(cfgAPSSID.c_str(), cfgAPPassword.c_str(), MESH_CHANNEL);
    Serial.print(F("[AP] Attivo - SSID: "));
    Serial.print(cfgAPSSID);
    Serial.print(F(" - IP: "));
    Serial.println(WiFi.softAPIP());
    if (!handlersRegistered) {
        configServer.on("/", handleConfigRoot);
        configServer.on("/config", HTTP_GET, handleConfigGet);
        configServer.on("/config", HTTP_POST, handleConfigPost);
        configServer.on("/exit", handleConfigExit);
        handlersRegistered = true;
    }
    configServer.begin();
    apModeActive = true;
    apStartTime = millis();
    Serial.println(F("[AP] Web server avviato su porta 80 (il sistema resta armato)"));
}

void disableAPMode() {
    configServer.stop();
    WiFi.softAPdisconnect(true);
    WiFi.mode(WIFI_STA);
    esp_wifi_set_channel(MESH_CHANNEL, WIFI_SECOND_CHAN_NONE);
    apModeActive = false;
    Serial.println(F("[AP] Disattivato, tornato a WIFI_STA"));
}

// Pressione lunga non bloccante: va chiamata a ogni giro di loop()
void handleButton() {
    static uint32_t pressStart = 0;
    static bool pressHandled = false;

    if (digitalRead(BUTTON_AP) == HIGH) {
        if (pressStart != 0 && !pressHandled) {
            Serial.println(F("[BUTTON] Rilasciato troppo presto, ignorato"));
        }
        pressStart = 0;
        pressHandled = false;
        return;
    }

    if (pressStart == 0) {
        pressStart = millis();
        Serial.printf("[BUTTON] Pressione rilevata, tieni premuto %d s\n", BUTTON_HOLD_MS / 1000);
        return;
    }

    if (!pressHandled && (millis() - pressStart >= BUTTON_HOLD_MS)) {
        pressHandled = true;
        Serial.println(F("[BUTTON] Pressione confermata"));
        if (apModeActive) disableAPMode(); else enableAPMode();
    }
}

volatile bool alarm_triggered = false;
uint32_t alarm_start_time = 0;
// Cooldown separato per livello di gravita' (settembre 2026): un evento di
// livello basso (warning/info) non deve mettere in ombra un allarme critico.
// Indici: 0 = info, 1 = warning, 2 = critico.
uint32_t last_event_time[3] = {0, 0, 0};

static uint8_t alarmLevel(IntrusionClass c, const SensorDataSecurity* d) {
    if (c == CLASS_PERSON) return 2;
    if (c == CLASS_UNKNOWN && d->tamper_detected) return 2;
    if (c == CLASS_ANIMAL_LARGE) return 1;
    return 0;
}
uint32_t last_heartbeat = 0;
bool system_armed = true;  // Armato di default
bool mesh_connected = false;

// ============================================================
// Prototipi
// ============================================================
void onMeshMessage(const MeshMessage* msg, const uint8_t* sender_mac);
void onSecurityEvent(IntrusionClass classification, const SensorDataSecurity* data);
void activateAlarm(IntrusionClass classification);
void deactivateAlarm();
void IRAM_ATTR pirInterrupt();

// ============================================================
// Setup
// ============================================================
void setup() {
    // Attuatori nello stato sicuro PRIMA di qualsiasi altra cosa (settembre 2026):
    // fino a questo punto i pin sono flottanti e un relè attivo-alto potrebbe
    // scattare per un istante all'accensione. Il blocco piu' sotto ripete la
    // configurazione (innocuo) e stampa i numeri di pin.
    pinMode(RELAY_SIREN_PIN, OUTPUT);
    pinMode(RELAY_LIGHT_PIN, OUTPUT);
    digitalWrite(RELAY_SIREN_PIN, LOW);
    digitalWrite(RELAY_LIGHT_PIN, LOW);

    // Inizializza Serial
    Serial.begin(115200);
    delay(100);
    
    Serial.println(F("\n"));
    Serial.println(F("╔═══════════════════════════════════════════╗"));
    Serial.println(F("║   AgriSecure IoT - Nodo Sicurezza         ║"));
    Serial.println(F("╚═══════════════════════════════════════════╝"));
    Serial.printf("Versione: %s\n", FIRMWARE_VERSION);
    loadConfig();
    Serial.printf("Node ID: %s\n", cfgNodeId.c_str());
    pinMode(BUTTON_AP, INPUT_PULLUP);  // pulsante a GND, pressione = LOW
    
    // Configura pin attuatori
    pinMode(RELAY_SIREN_PIN, OUTPUT);
    pinMode(RELAY_LIGHT_PIN, OUTPUT);
    digitalWrite(RELAY_SIREN_PIN, LOW);  // Sirena OFF
    digitalWrite(RELAY_LIGHT_PIN, LOW);  // Luce OFF
    Serial.printf("Sirena su GPIO%d\n", RELAY_SIREN_PIN);
    Serial.printf("Luce su GPIO%d\n", RELAY_LIGHT_PIN);
    
    // LED RGB di stato: blu durante avvio e armamento
    statusRGB.begin();
    statusRGB.setBrightness(50);
    setLed(0, 0, 255);
    
    // Inizializza sensori sicurezza
    Serial.println(F("\nInizializzazione sensori sicurezza..."));
    if (!SecuritySensors.begin()) {
        Serial.println(F("ATTENZIONE: Alcuni sensori non disponibili!"));
    }
    
    // Registra callback eventi sicurezza
    SecuritySensors.onSecurityEvent(onSecurityEvent);
    
    // Inizializza mesh
    Serial.println(F("\nInizializzazione mesh..."));
    if (!Mesh.begin(cfgNodeId.c_str(), NODE_SECURITY)) {
        Serial.println(F("ERRORE: Mesh non inizializzato!"));
    }
    
    // Registra callback messaggi
    Mesh.onMessage(onMeshMessage);
    
    // Configura interrupt PIR per risposta rapida
    attachInterrupt(digitalPinToInterrupt(PIR_MAIN_PIN), pirInterrupt, RISING);
    
    // Test attuatori all'avvio (breve)
    Serial.println(F("\nTest attuatori..."));
    digitalWrite(RELAY_LIGHT_PIN, HIGH);
    delay(200);
    digitalWrite(RELAY_LIGHT_PIN, LOW);
    
    // Arma il sistema dopo 10 secondi (tempo per allontanarsi)
    Serial.println(F("\nSistema si armerà tra 10 secondi..."));
    for (int i = 10; i > 0; i--) {
        Serial.printf("%d...\n", i);
        setLed(0, 0, (i % 2) ? 255 : 0);  // blu lampeggiante nel conto alla rovescia
        delay(1000);
    }
    
    SecuritySensors.arm();
    // Fix (agosto 2026): last_event_time[] (ex last_alarm_time) parte da 0, e ALARM_COOLDOWN (60s)
    // viene confrontato con millis() dal boot, non dall'armamento. Senza
    // questo seed, qualunque evento PIR nei primi ~60s dall'accensione
    // veniva silenziosamente scartato come "falso cooldown" (mai un
    // evento precedente era realmente avvenuto). Impostando last_event_time[]
    // nel passato di un cooldown intero, il primo evento reale viene
    // processato normalmente.
    for (int i = 0; i < 3; i++) last_event_time[i] = millis() - cfgAlarmCooldown;
    setLed(0, 0, 0);
    
    Serial.println(F("\n╔═══════════════════════════════════════════╗"));
    Serial.println(F("║   SISTEMA ARMATO E OPERATIVO              ║"));
    Serial.println(F("╚═══════════════════════════════════════════╝"));
}

// ============================================================
// Loop Principale
// ============================================================
void loop() {
    // Pulsante AP-config (pressione lunga) e web server: non bloccanti
    handleButton();
    if (apModeActive) {
        configServer.handleClient();
        if (apCloseRequested) {
            apCloseRequested = false;
            delay(500);  // lascia finire l'invio della pagina di uscita
            disableAPMode();
        } else if (millis() - apStartTime > AP_CONFIG_TIMEOUT_MS) {
            Serial.println(F("[AP] Timeout di inattivita', chiusura"));
            disableAPMode();
        }
    }

    // Aggiorna mesh
    Mesh.update();
    
    // Aggiorna sensori sicurezza
    SecuritySensors.update();
    
    uint32_t now = millis();
    
    // Gestisci timeout allarme
    if (alarm_triggered && (now - alarm_start_time >= cfgAlarmDuration)) {
        Serial.println(F("Timeout allarme, disattivazione..."));
        deactivateAlarm();
    }
    
    // Heartbeat periodico
    if (now - last_heartbeat >= cfgHeartbeatInterval) {
        Serial.println(F("Invio heartbeat..."));
        Mesh.sendHeartbeat();
        last_heartbeat = now;
    }
    
    // Verifica connessione gateway
    bool connected = Mesh.isConnectedToGateway();
    if (connected != mesh_connected) {
        mesh_connected = connected;
        if (connected) {
            Serial.println(F("✓ Connesso al gateway"));
        } else {
            Serial.println(F("✗ Disconnesso dal gateway"));
        }
    }
    
    // LED lampeggia lento se armato, veloce se allarme
    static uint32_t last_blink = 0;
    static bool led_on = false;
    uint32_t blink_interval = alarm_triggered ? 100 : (system_armed ? 2000 : 500);
    if (apModeActive) {
        // blu fisso mentre l'AP di configurazione e' aperto
        static uint32_t last_ap_led = 0;
        if (now - last_ap_led > 500) {
            setLed(0, 0, 255);
            last_ap_led = now;
        }
    } else if (now - last_blink > blink_interval) {
        led_on = !led_on;
        if (!led_on) {
            setLed(0, 0, 0);
        } else if (alarm_triggered) {
            setLed(255, 0, 0);      // rosso: allarme
        } else if (system_armed) {
            setLed(0, 255, 0);      // verde: armato
        } else {
            setLed(255, 150, 0);    // giallo: disarmato
        }
        last_blink = now;
    }
    
    // Piccola pausa
    delay(10);
}

// ============================================================
// Interrupt PIR (risposta rapida)
// ============================================================
void IRAM_ATTR pirInterrupt() {
    // Segnala solo, processing nel loop principale
    // per evitare problemi con funzioni non IRAM-safe
}

// ============================================================
// Callback Eventi Sicurezza
// ============================================================
void onSecurityEvent(IntrusionClass classification, const SensorDataSecurity* data) {
    uint32_t now = millis();
    
    // Cooldown per livello di gravita' (vedi last_event_time)
    uint8_t level = alarmLevel(classification, data);
    if (now - last_event_time[level] < cfgAlarmCooldown) {
        Serial.println(F("Allarme in cooldown, ignorato"));
        return;
    }
    
    Serial.println(F("\n╔═══════════════════════════════════════════╗"));
    Serial.println(F("║   >>> EVENTO SICUREZZA <<<                ║"));
    Serial.println(F("╚═══════════════════════════════════════════╝"));
    
    Serial.printf("Classificazione: %d\n", classification);
    Serial.printf("PIR Main: %d, PIR Backup: %d\n", data->pir_main, data->pir_backup);
    Serial.printf("Tamper: %d\n", data->tamper_detected);
    
    // Invia allarme via mesh
    Serial.println(F("Invio allarme al gateway..."));
    if (Mesh.sendSecurityAlarm(classification, data)) {
        Serial.println(F("✓ Allarme inviato"));
    } else {
        Serial.println(F("✗ Errore invio allarme"));
    }
    
    // Attiva allarme locale basato su classificazione
    switch (classification) {
        case CLASS_PERSON:
            Serial.println(F("!!! PERSONA RILEVATA - ALLARME CRITICO !!!"));
            activateAlarm(classification);
            break;
            
        case CLASS_ANIMAL_LARGE:
            Serial.println(F("Animale grande rilevato - Warning"));
            // Solo luce, no sirena. Se un allarme e' gia' attivo la luce e' gia'
            // accesa: non toccarla, altrimenti il LOW finale la spegnerebbe.
            if (!alarm_triggered) {
                digitalWrite(RELAY_LIGHT_PIN, HIGH);
                delay(3000);
                digitalWrite(RELAY_LIGHT_PIN, LOW);
            }
            break;
            
        case CLASS_ANIMAL_SMALL:
            Serial.println(F("Animale piccolo - Ignorato"));
            // Nessuna azione
            break;
            
        case CLASS_UNKNOWN:
            if (data->tamper_detected) {
                Serial.println(F("!!! TAMPER RILEVATO !!!"));
                activateAlarm(classification);
            }
            break;
            
        default:
            break;
    }
    
    last_event_time[level] = now;
}

// ============================================================
// Attivazione/Disattivazione Allarme
// ============================================================
void activateAlarm(IntrusionClass classification) {
    if (alarm_triggered) return;  // Già attivo
    
    Serial.println(F(">>> ATTIVAZIONE ALLARME <<<"));
    
    alarm_triggered = true;
    alarm_start_time = millis();
    
    // Attiva sirena e luce
    digitalWrite(RELAY_SIREN_PIN, HIGH);
    digitalWrite(RELAY_LIGHT_PIN, HIGH);
    
    Serial.printf("Allarme attivo per %lu secondi\n", (unsigned long)(cfgAlarmDuration / 1000));
}

void deactivateAlarm() {
    Serial.println(F(">>> DISATTIVAZIONE ALLARME <<<"));
    
    alarm_triggered = false;
    
    // Disattiva sirena e luce
    digitalWrite(RELAY_SIREN_PIN, LOW);
    digitalWrite(RELAY_LIGHT_PIN, LOW);
    
    // Reset stato sensori
    SecuritySensors.resetAlarm();
}

// ============================================================
// Callback Messaggi Mesh
// ============================================================
void onMeshMessage(const MeshMessage* msg, const uint8_t* sender_mac) {
    Serial.printf("\nMessaggio da %s, tipo: %d\n", msg->sender_id, msg->msg_type);
    
    switch (msg->msg_type) {
        case MSG_ARM:
            Serial.println(F("Comando: ARMA SISTEMA"));
            system_armed = true;
            SecuritySensors.arm();
            break;
            
        case MSG_DISARM:
            Serial.println(F("Comando: DISARMA SISTEMA"));
            system_armed = false;
            SecuritySensors.disarm();
            deactivateAlarm();
            break;
            
        case MSG_COMMAND:
            Serial.println(F("Comando generico ricevuto"));
            // Analizza payload per comando specifico
            if (msg->payload_len > 0) {
                uint8_t cmd = msg->payload[0];
                switch (cmd) {
                    case 0x01:  // Test sirena
                        Serial.println(F("Test sirena"));
                        digitalWrite(RELAY_SIREN_PIN, HIGH);
                        delay(500);
                        digitalWrite(RELAY_SIREN_PIN, LOW);
                        break;
                    case 0x02:  // Test luce
                        Serial.println(F("Test luce"));
                        digitalWrite(RELAY_LIGHT_PIN, HIGH);
                        delay(1000);
                        digitalWrite(RELAY_LIGHT_PIN, LOW);
                        break;
                    case 0x03:  // Stop allarme manuale
                        Serial.println(F("Stop allarme manuale"));
                        deactivateAlarm();
                        break;
                }
            }
            break;
            
        case MSG_CONFIG:
            Serial.println(F("Configurazione ricevuta"));
            // TODO: applicare nuova configurazione soglie
            break;
            
        case MSG_OTA:
            Serial.println(F("Richiesta OTA"));
            // TODO: avviare OTA update
            break;
            
        default:
            break;
    }
}
