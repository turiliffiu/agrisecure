/**
 * AgriSecure IoT System - Firmware Nodo Gateway
 * 
 * Gateway centrale con:
 * - Connettività 4G/LTE (modulo A7670E/SIM7600)
 * - MQTT per comunicazione con backend
 * - Raccolta dati da mesh e inoltro a cloud
 * - GPS per localizzazione
 * - Gestione comandi remoti
 * 
 * Funzionamento:
 * - Always-on
 * - Riceve dati da nodi mesh via ESP-NOW
 * - Inoltra a backend via MQTT over 4G
 * - Riceve comandi da backend e li inoltra ai nodi
 * 
 * @author Turiliffiu
 * @version 1.0.0
 */

#include <Arduino.h>
#include "agrisecure_config.h"
#include "mesh_manager.h"

// TinyGSM per modem 4G
#define TINY_GSM_MODEM_SIM7600  // Compatibile anche con A7670
#include <TinyGsmClient.h>
#include <SSLClientESP32.h>
#include <Adafruit_NeoPixel.h>
#include <WebServer.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ============================================================
// Configurazione
// ============================================================
#ifndef NODE_ID
#define NODE_ID "GW-001"
#endif

// Pin Modem 4G
#ifndef MODEM_TX
#define MODEM_TX 17
#endif

#ifndef MODEM_RX
#define MODEM_RX 18
#endif

#ifndef MODEM_PWRKEY
#define MODEM_PWRKEY 4
#endif

#ifndef MODEM_RST
#define MODEM_RST 5
#endif

// APN Italia (modificare per il proprio operatore)
#define GSM_APN "internet.it"  // Very Mobile (WindTre MVNO) - "internet" generico dava DNS rotto + network failure
#define GSM_USER ""
#define GSM_PASS ""

// MQTT
#ifndef MQTT_BROKER
#define MQTT_BROKER "mqtt.agrisecure.local"
#endif

#ifndef MQTT_PORT
#define MQTT_PORT 1883
#endif

#ifndef MQTT_USER
#define MQTT_USER "agrisecure"
#endif

#ifndef MQTT_PASS
#define MQTT_PASS "secure_password"
#endif

// Topic MQTT
#define MQTT_TOPIC_ROOT "agrisecure/gw001"
#define MQTT_TOPIC_SENSORS MQTT_TOPIC_ROOT "/sensors"
#define MQTT_TOPIC_SECURITY MQTT_TOPIC_ROOT "/security"
#define MQTT_TOPIC_STATUS MQTT_TOPIC_ROOT "/status"
#define MQTT_TOPIC_COMMAND MQTT_TOPIC_ROOT "/command"
#define MQTT_TOPIC_CONFIG MQTT_TOPIC_ROOT "/config"

// ============================================================
// Certificato CA per TLS (broker MQTT agrisecure.tgs.ovh:8883)
// ============================================================
static const char ca_cert_pem[] PROGMEM = R"CERT(
-----BEGIN CERTIFICATE-----
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
HUEzzgs=
-----END CERTIFICATE-----
)CERT";

// ============================================================
// Oggetti Globali
// ============================================================
HardwareSerial SerialGSM(1);  // UART1 per modem
TinyGsm modem(SerialGSM);
TinyGsmClient gsmClient(modem);
SSLClientESP32 sslClient(&gsmClient);
Adafruit_NeoPixel statusRGB(1, 48, NEO_GRB + NEO_KHZ800);  // LED RGB WS2812, GPIO48 (verificato fisicamente)
WebServer configServer(80);
Preferences prefs;
String cfgAPN;
String cfgMQTTBroker;
uint16_t cfgMQTTPort;
String cfgMQTTUser;
String cfgMQTTPass;
String cfgNodeId;
String cfgAPSSID;
String cfgAPPassword;
String cfgGSMUser;
String cfgGSMPass;
uint32_t cfgStatusInterval;
uint32_t cfgHeartbeatInterval;
String topicRoot;
String topicStatus;
String topicCommand;
String topicConfig;
String topicSensors;
String topicSecurity;
PubSubClient mqtt(sslClient);

// ============================================================
// Variabili Globali
// ============================================================
bool modem_ready = false;
bool gprs_connected = false;
bool mqtt_connected = false;
uint32_t last_reconnect_attempt = 0;
uint32_t last_heartbeat = 0;
uint32_t last_status_publish = 0;
uint32_t message_count = 0;

// Buffer JSON
StaticJsonDocument<512> json_doc;
char json_buffer[512];

// ============================================================
// Prototipi
// ============================================================
void onMeshMessage(const MeshMessage* msg, const uint8_t* sender_mac);
void mqttCallback(char* topic, byte* payload, unsigned int length);
bool initModem();
bool connectGPRS();
bool connectMQTT();
void publishSensorData(const char* node_id, const SensorDataAmbient* data);
void publishSecurityAlarm(const char* node_id, IntrusionClass classification, 
                          const SensorDataSecurity* data);
void publishStatus();
void processCommand(const char* command, const char* target);
void checkConnections();
void handleButton();
void updateStatusRGB();
void enableAPMode();
void disableAPMode();
extern bool apModeActive;
void loadConfig();
void handleConfigGet();
void handleConfigPost();

// ============================================================
// Setup
// ============================================================
void setup() {
    // Inizializza Serial
    Serial.begin(115200);
    delay(100);

    statusRGB.begin();
    statusRGB.show();  // spento di default
    loadConfig();
    pinMode(BUTTON_AP, INPUT_PULLUP);
    
    Serial.println(F("\n"));
    Serial.println(F("╔═══════════════════════════════════════════╗"));
    Serial.println(F("║   AgriSecure IoT - Gateway 4G             ║"));
    Serial.println(F("╚═══════════════════════════════════════════╝"));
    Serial.printf("Versione: %s\n", FIRMWARE_VERSION);
    Serial.printf("Node ID: %s\n", NODE_ID);
    
    // LED di stato
    pinMode(LED_STATUS, OUTPUT);
    digitalWrite(LED_STATUS, HIGH);
    
    // Inizializza modem 4G
    updateStatusRGB();  // rosso: modem non ancora pronto
    Serial.println(F("\nInizializzazione modem 4G..."));
    if (initModem()) {
        modem_ready = true;
        updateStatusRGB();  // giallo lampeggiante: modem ok, GPRS in corso
        Serial.println(F("✓ Modem pronto"));
        
        // Connetti GPRS
        if (connectGPRS()) {
            gprs_connected = true;
            updateStatusRGB();  // giallo fisso: GPRS ok, MQTT in corso
            Serial.println(F("✓ GPRS connesso"));
            
            // DNS manuali (Google Public DNS): necessario, questo operatore/APN non fornisce DNS funzionanti di default
            SerialGSM.print("AT+CDNSCFG=\"8.8.8.8\",\"8.8.4.4\"\r\n");
            { uint32_t t0 = millis(); while (millis() - t0 < 3000) { if (SerialGSM.available()) SerialGSM.read(); } }

            // Configura TLS + MQTT
            sslClient.setCACert(ca_cert_pem);
            mqtt.setServer(cfgMQTTBroker.c_str(), cfgMQTTPort);
            mqtt.setKeepAlive(60);  // 15s default troppo stretto: checkConnections() puo bloccare il loop per diversi secondi
            mqtt.setCallback(mqttCallback);
            mqtt.setBufferSize(512);
            
            // Connetti MQTT
            if (connectMQTT()) {
                mqtt_connected = true;
                updateStatusRGB();  // verde: tutto operativo
                Serial.println(F("✓ MQTT connesso"));
            }
        }
    } else {
        Serial.println(F("✗ Modem non disponibile - modalità offline"));
    }
    
    // Inizializza mesh
    Serial.println(F("\nInizializzazione mesh ESP-NOW..."));
    if (!Mesh.begin(cfgNodeId.c_str(), NODE_GATEWAY)) {
        Serial.println(F("ERRORE: Mesh non inizializzato!"));
    } else {
        Serial.println(F("✓ Mesh pronto"));
    }
    
    // Registra callback messaggi mesh
    Mesh.onMessage(onMeshMessage);
    
    digitalWrite(LED_STATUS, LOW);
    
    Serial.println(F("\n╔═══════════════════════════════════════════╗"));
    Serial.println(F("║   GATEWAY OPERATIVO                       ║"));
    Serial.println(F("╚═══════════════════════════════════════════╝"));
    Serial.printf("Modem: %s\n", modem_ready ? "OK" : "OFFLINE");
    Serial.printf("GPRS: %s\n", gprs_connected ? "Connesso" : "Disconnesso");
    Serial.printf("MQTT: %s\n", mqtt_connected ? "Connesso" : "Disconnesso");
    Serial.println(F("───────────────────────────────────────────"));
}

// ============================================================
// Loop Principale
// ============================================================
void loop() {
    // Aggiorna mesh
    Mesh.update();
    
    // Aggiorna MQTT
    if (mqtt_connected) {
        mqtt.loop();
    }
    
    uint32_t now = millis();
    
    // Verifica connessioni ogni 30 secondi
    static uint32_t last_connection_check = 0;
    if (now - last_connection_check > 30000) {
        checkConnections();
        last_connection_check = now;
    }
    
    // Pubblica status ogni 5 minuti
    if (mqtt_connected && (now - last_status_publish > cfgStatusInterval)) {
        publishStatus();
        last_status_publish = now;
    }
    
    // Heartbeat mesh
    if (now - last_heartbeat >= cfgHeartbeatInterval) {
        Serial.println(F("Invio heartbeat mesh..."));
        Mesh.sendHeartbeat();
        last_heartbeat = now;
    }
    
    // Gestione pulsante AP (toggle a pressione singola, con debounce)
    handleButton();
    
    // Web server di configurazione, solo se AP attivo
    if (apModeActive) {
        configServer.handleClient();
    }
    
    // LED RGB indica stato (sostituisce il vecchio LED_STATUS singolo colore)
    updateStatusRGB();
    
    delay(10);
}

// ============================================================
// Pulsante AP - toggle a pressione singola, con debounce
// ============================================================
bool apModeActive = false;

void handleButton() {
    static bool lastReading = HIGH;
    static bool buttonState = HIGH;
    static uint32_t lastDebounceTime = 0;
    const uint32_t debounceDelay = 50;

    bool reading = digitalRead(BUTTON_AP);

    if (reading != lastReading) {
        lastDebounceTime = millis();
    }

    if ((millis() - lastDebounceTime) > debounceDelay) {
        if (reading != buttonState) {
            buttonState = reading;
            // Pulsante collegato a GND: pressione = LOW
            if (buttonState == LOW) {
                apModeActive = !apModeActive;
                Serial.printf("[BUTTON] AP mode: %s\n", apModeActive ? "ON" : "OFF");
                if (apModeActive) {
                    enableAPMode();
                } else {
                    disableAPMode();
                }
            }
        }
    }

    lastReading = reading;
}

// ============================================================
// LED RGB - sinottico di stato
// ============================================================
void loadConfig() {
    prefs.begin("agrisecure", false);  // read-write: crea il namespace al primo avvio, evita errore NOT_FOUND
    cfgAPN = prefs.getString("apn", GSM_APN);
    cfgMQTTBroker = prefs.getString("mqtt_broker", MQTT_BROKER);
    cfgMQTTPort = prefs.getUShort("mqtt_port", MQTT_PORT);
    cfgMQTTUser = prefs.getString("mqtt_user", MQTT_USER);
    cfgMQTTPass = prefs.getString("mqtt_pass", MQTT_PASS);
    cfgNodeId = prefs.getString("node_id", NODE_ID);
    cfgAPSSID = prefs.getString("ap_ssid", AP_SSID);
    cfgAPPassword = prefs.getString("ap_pass", AP_PASSWORD);
    cfgGSMUser = prefs.getString("gsm_user", GSM_USER);
    cfgGSMPass = prefs.getString("gsm_pass", GSM_PASS);
    cfgStatusInterval = prefs.getULong("status_intv", 300000);
    cfgHeartbeatInterval = prefs.getULong("hb_intv", MESH_HEARTBEAT_INTERVAL);
    prefs.end();

    // Topic MQTT derivati dal Node ID (minuscolo), per supportare piu' gateway senza ricompilare
    String rootLower = cfgNodeId;
    rootLower.toLowerCase();
    topicRoot = "agrisecure/" + rootLower;
    topicStatus = topicRoot + "/status";
    topicCommand = topicRoot + "/command";
    topicConfig = topicRoot + "/config";
    topicSensors = topicRoot + "/sensors";
    topicSecurity = topicRoot + "/security";
    Serial.println(F("[CONFIG] Parametri caricati da NVS (o default se prima esecuzione)"));
}

void handleConfigRoot() {
    String html = "<!DOCTYPE html><html><head><meta charset='utf-8'>";
    html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
    html += "<title>AgriSecure GW-001</title>";
    html += "<style>body{font-family:sans-serif;max-width:480px;margin:20px auto;padding:0 15px;}";
    html += "h1{color:#2c5f2d;} .row{padding:8px 0;border-bottom:1px solid #eee;}";
    html += ".ok{color:#2c5f2d;font-weight:bold;} .ko{color:#c0392b;font-weight:bold;}</style></head><body>";
    html += "<h1>AgriSecure - " + String(NODE_ID) + "</h1>";
    html += "<div class='row'>Firmware: " + String(FIRMWARE_VERSION) + "</div>";
    html += "<div class='row'>Modem: <span class='" + String(modem_ready ? "ok'>OK" : "ko'>OFFLINE") + "</span></div>";
    html += "<div class='row'>GPRS: <span class='" + String(gprs_connected ? "ok'>Connesso" : "ko'>Disconnesso") + "</span></div>";
    html += "<div class='row'>MQTT: <span class='" + String(mqtt_connected ? "ok'>Connesso" : "ko'>Disconnesso") + "</span></div>";
    html += "<div class='row'>IP AP: " + WiFi.softAPIP().toString() + "</div>";
    html += "<div class='row'>Uptime: " + String(millis() / 1000) + " s</div>";
    html += "<p><a href='/config'>Modifica configurazione</a></p>";
    html += "</body></html>";
    configServer.send(200, "text/html", html);
}

void handleConfigGet() {
    String html = "<!DOCTYPE html><html><head><meta charset='utf-8'>";
    html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
    html += "<title>Configurazione GW-001</title>";
    html += "<style>body{font-family:sans-serif;max-width:480px;margin:20px auto;padding:0 15px;}";
    html += "h1{color:#2c5f2d;} label{display:block;margin-top:12px;font-weight:bold;}";
    html += "input{width:100%;padding:8px;box-sizing:border-box;margin-top:4px;}";
    html += "button{margin-top:20px;padding:10px 20px;background:#2c5f2d;color:#fff;border:none;border-radius:4px;}";
    html += "small{color:#888;}</style></head><body>";
    html += "<h1>Configurazione</h1>";
    html += "<form method='POST' action='/config'>";
    html += "<label>APN</label><input name='apn' value='" + cfgAPN + "'>";
    html += "<label>MQTT Broker</label><input name='mqtt_broker' value='" + cfgMQTTBroker + "'>";
    html += "<label>MQTT Porta</label><input name='mqtt_port' type='number' value='" + String(cfgMQTTPort) + "'>";
    html += "<label>MQTT Utente</label><input name='mqtt_user' value='" + cfgMQTTUser + "'>";
    html += "<label>MQTT Password</label><input name='mqtt_pass' type='password' value=''>";
    html += "<small>Lascia vuoto per non modificare la password attuale</small>";
    html += "<br><button type='submit'>Salva e riavvia</button>";
    html += "</form><p><a href='/'>Torna allo stato</a></p></body></html>";
    configServer.send(200, "text/html", html);
}

void handleConfigPost() {
    prefs.begin("agrisecure", false);
    if (configServer.hasArg("apn")) prefs.putString("apn", configServer.arg("apn"));
    if (configServer.hasArg("mqtt_broker")) prefs.putString("mqtt_broker", configServer.arg("mqtt_broker"));
    if (configServer.hasArg("mqtt_port")) prefs.putUShort("mqtt_port", configServer.arg("mqtt_port").toInt());
    if (configServer.hasArg("mqtt_user")) prefs.putString("mqtt_user", configServer.arg("mqtt_user"));
    if (configServer.hasArg("mqtt_pass") && configServer.arg("mqtt_pass").length() > 0) {
        prefs.putString("mqtt_pass", configServer.arg("mqtt_pass"));
    }
    prefs.end();

    String html = "<!DOCTYPE html><html><head><meta charset='utf-8'>";
    html += "<meta name='viewport' content='width=device-width, initial-scale=1'></head><body>";
    html += "<h1>Configurazione salvata</h1><p>Il gateway si sta riavviando...</p></body></html>";
    configServer.send(200, "text/html", html);

    Serial.println(F("[CONFIG] Nuovi parametri salvati su NVS, riavvio..."));
    delay(1000);
    ESP.restart();
}

void enableAPMode() {
    WiFi.mode(WIFI_MODE_APSTA);
    WiFi.softAP(cfgAPSSID.c_str(), cfgAPPassword.c_str(), MESH_CHANNEL);
    Serial.print(F("[AP] Attivo - SSID: "));
    Serial.print(cfgAPSSID);
    Serial.print(F(" - IP: "));
    Serial.println(WiFi.softAPIP());
    configServer.on("/", handleConfigRoot);
    configServer.on("/config", HTTP_GET, handleConfigGet);
    configServer.on("/config", HTTP_POST, handleConfigPost);
    configServer.begin();
    Serial.println(F("[AP] Web server avviato su porta 80"));
}

void disableAPMode() {
    configServer.stop();
    WiFi.softAPdisconnect(true);
    WiFi.mode(WIFI_STA);
    esp_wifi_set_channel(MESH_CHANNEL, WIFI_SECOND_CHAN_NONE);
    Serial.println(F("[AP] Disattivato, tornato a WIFI_STA"));
}

void updateStatusRGB() {
    static uint32_t lastToggle = 0;
    static bool blinkPhase = false;
    uint32_t now = millis();

    if (now - lastToggle > 200) {
        blinkPhase = !blinkPhase;
        lastToggle = now;
    }

    uint32_t color;

    if (apModeActive) {
        color = statusRGB.Color(0, 0, 255);           // Blu fisso: AP configurazione attiva
    } else if (!modem_ready) {
        color = statusRGB.Color(255, 0, 0);            // Rosso fisso: modem non disponibile
    } else if (!gprs_connected) {
        color = blinkPhase ? statusRGB.Color(255, 200, 0) : statusRGB.Color(0, 0, 0);  // Giallo lampeggiante veloce
    } else if (!mqtt_connected) {
        color = statusRGB.Color(255, 200, 0);           // Giallo fisso: GPRS ok, MQTT in connessione
    } else {
        color = statusRGB.Color(0, 255, 0);             // Verde fisso: tutto operativo
    }

    statusRGB.setPixelColor(0, color);
    statusRGB.show();
}

// ============================================================
// Inizializzazione Modem
// ============================================================
bool initModem() {
    // Configura pin modem
    pinMode(MODEM_PWRKEY, OUTPUT);
    pinMode(MODEM_RST, OUTPUT);
    
    // Reset modem
    digitalWrite(MODEM_RST, LOW);
    delay(100);
    digitalWrite(MODEM_RST, HIGH);
    delay(100);
    
    // Power on
    digitalWrite(MODEM_PWRKEY, LOW);
    delay(1000);
    digitalWrite(MODEM_PWRKEY, HIGH);
    delay(2000);
    
    // Inizializza UART
    SerialGSM.begin(115200, SERIAL_8N1, MODEM_RX, MODEM_TX);
    delay(3000);
    
    // Test modem
    Serial.println(F("Test comunicazione modem..."));
    if (!modem.testAT()) {
        Serial.println(F("Modem non risponde, riprovo..."));
        delay(5000);
        if (!modem.testAT()) {
            return false;
        }
    }
    
    // Info modem
    String modemInfo = modem.getModemInfo();
    Serial.printf("Modem: %s\n", modemInfo.c_str());
    
    // Attendi registrazione rete
    Serial.println(F("Attesa registrazione rete..."));
    if (!modem.waitForNetwork(60000)) {
        Serial.println(F("Rete non disponibile"));
        return false;
    }
    
    Serial.printf("Segnale: %d\n", modem.getSignalQuality());
    
    return true;
}

bool connectGPRS() {
    Serial.printf("Connessione GPRS (APN: %s)...\n", cfgAPN.c_str());
    
    if (!modem.gprsConnect(cfgAPN.c_str(), cfgGSMUser.c_str(), cfgGSMPass.c_str())) {
        Serial.println(F("Connessione GPRS fallita"));
        return false;
    }
    
    Serial.printf("IP: %s\n", modem.localIP().toString().c_str());
    return true;
}

bool connectMQTT() {
    Serial.printf("Connessione MQTT (%s:%d)...\n", cfgMQTTBroker.c_str(), cfgMQTTPort);
    
    // Apri prima il socket TCP di base tramite il modem (AT+CIPOPEN, DNS via rete cellulare)
    // Necessario perche' SSLClientESP32 non sa risolvere hostname senza un'interfaccia di rete nativa (WiFi)
    if (!gsmClient.connected()) {
        Serial.println(F("Apertura socket TCP verso il broker (via modem)..."));
        if (!gsmClient.connect(cfgMQTTBroker.c_str(), cfgMQTTPort)) {
            Serial.println(F("Impossibile aprire il socket TCP verso il broker"));
            return false;
        }
    }
    
    String clientId = "agrisecure-" + cfgNodeId;
    
    // Last Will Testament
    String lwt_topic = topicStatus + "/online";
    
    if (mqtt.connect(clientId.c_str(), cfgMQTTUser.c_str(), cfgMQTTPass.c_str(), 
                     lwt_topic.c_str(), 1, true, "false")) {
        Serial.println(F("MQTT connesso!"));
        
        // Pubblica stato online
        mqtt.publish(lwt_topic.c_str(), "true", true);
        
        // Subscribe a topic comandi
        mqtt.subscribe(topicCommand.c_str());
        mqtt.subscribe(topicConfig.c_str());
        
        Serial.println(F("Sottoscritto a topic comandi"));
        return true;
    }
    
    Serial.printf("MQTT fallito, errore: %d\n", mqtt.state());
    return false;
}

void checkConnections() {

    // Verifica GPRS
    if (modem_ready && !modem.isGprsConnected()) {
        Serial.println(F("GPRS disconnesso, riconnessione..."));
        gprs_connected = connectGPRS();
    }
    
    // Verifica MQTT
    if (gprs_connected && !mqtt.connected()) {
        Serial.println(F("MQTT disconnesso, riconnessione..."));
        mqtt_connected = connectMQTT();
    }
}

// ============================================================
// Callback Messaggi Mesh (da altri nodi)
// ============================================================
void onMeshMessage(const MeshMessage* msg, const uint8_t* sender_mac) {
    message_count++;
    
    Serial.printf("\n[MESH] Messaggio #%d da %s, tipo: %d\n", 
                  message_count, msg->sender_id, msg->msg_type);
    
    switch (msg->msg_type) {
        case MSG_SENSOR_DATA: {
            // Dati sensori ambientali
            if (msg->payload_len == sizeof(SensorDataAmbient)) {
                SensorDataAmbient* data = (SensorDataAmbient*)msg->payload;
                Serial.printf("  T=%.1f°C, H=%.1f%%, P=%.1fhPa, Lux=%d, Soil=%d%%\n",
                              data->temperature, data->humidity, data->pressure,
                              data->light_lux, data->soil_percent);
                
                publishSensorData(msg->sender_id, data);
            }
            break;
        }
        
        case MSG_ALARM_PERSON:
        case MSG_ALARM_ANIMAL: {
            // Allarme sicurezza
            if (msg->payload_len == sizeof(SensorDataSecurity)) {
                SensorDataSecurity* data = (SensorDataSecurity*)msg->payload;
                IntrusionClass classification = (msg->msg_type == MSG_ALARM_PERSON) ? 
                                                 CLASS_PERSON : CLASS_ANIMAL_LARGE;
                
                Serial.printf("  !!! ALLARME: classificazione=%d !!!\n", classification);
                
                publishSecurityAlarm(msg->sender_id, classification, data);
            }
            break;
        }
        
        case MSG_HEARTBEAT: {
            // Heartbeat da nodo
            if (msg->payload_len == sizeof(HeartbeatData)) {
                HeartbeatData* hb = (HeartbeatData*)msg->payload;
                Serial.printf("  Heartbeat: uptime=%ds, heap=%dKB, RSSI=%d, batt=%d%%\n",
                              hb->uptime_sec, hb->free_heap, hb->rssi, hb->battery_pct);
                
                // Pubblica status nodo
                json_doc.clear();
                json_doc["node_id"] = msg->sender_id;
                json_doc["type"] = hb->node_type;
                json_doc["uptime"] = hb->uptime_sec;
                json_doc["heap_kb"] = hb->free_heap;
                json_doc["rssi"] = hb->rssi;
                json_doc["battery"] = hb->battery_pct;
                json_doc["neighbors"] = hb->mesh_neighbors;
                json_doc["timestamp"] = msg->timestamp;
                
                serializeJson(json_doc, json_buffer);
                
                String topic = topicStatus + "/" + msg->sender_id;
                mqtt.publish(topic.c_str(), json_buffer);
            }
            break;
        }
        
        case MSG_BATTERY: {
            // Status batteria
            if (msg->payload_len == sizeof(BatteryStatus)) {
                BatteryStatus* batt = (BatteryStatus*)msg->payload;
                Serial.printf("  Batteria: %dmV (%d%%), carica=%d, solar=%dmV\n",
                              batt->voltage_mv, batt->percentage, 
                              batt->charging, batt->solar_mv);
            }
            break;
        }
        
        default:
            Serial.printf("  Tipo messaggio non gestito: %d\n", msg->msg_type);
            break;
    }
}

// ============================================================
// Callback MQTT (comandi da backend)
// ============================================================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
    Serial.printf("\n[MQTT] Messaggio su %s\n", topic);
    
    // Converti payload in stringa
    char message[256];
    size_t len = min((size_t)length, sizeof(message) - 1);
    memcpy(message, payload, len);
    message[len] = '\0';
    
    Serial.printf("  Payload: %s\n", message);
    
    // Parsing JSON
    DeserializationError error = deserializeJson(json_doc, message);
    if (error) {
        Serial.printf("  Errore parsing JSON: %s\n", error.c_str());
        return;
    }
    
    // Estrai comando e target
    const char* command = json_doc["command"] | "";
    const char* target = json_doc["target"] | "*";
    
    processCommand(command, target);
}

void processCommand(const char* command, const char* target) {
    Serial.printf("  Comando: %s -> %s\n", command, target);
    
    if (strcmp(command, "arm") == 0) {
        // Arma sistema
        Mesh.broadcast(MSG_ARM, nullptr, 0, PRIORITY_HIGH);
        Serial.println(F("  -> Inviato comando ARM"));
        
    } else if (strcmp(command, "disarm") == 0) {
        // Disarma sistema
        Mesh.broadcast(MSG_DISARM, nullptr, 0, PRIORITY_HIGH);
        Serial.println(F("  -> Inviato comando DISARM"));
        
    } else if (strcmp(command, "test_siren") == 0) {
        // Test sirena
        uint8_t cmd = 0x01;
        Mesh.sendMessage(target, MSG_COMMAND, &cmd, 1, PRIORITY_HIGH);
        Serial.println(F("  -> Inviato test sirena"));
        
    } else if (strcmp(command, "test_light") == 0) {
        // Test luce
        uint8_t cmd = 0x02;
        Mesh.sendMessage(target, MSG_COMMAND, &cmd, 1, PRIORITY_HIGH);
        Serial.println(F("  -> Inviato test luce"));
        
    } else if (strcmp(command, "stop_alarm") == 0) {
        // Stop allarme
        uint8_t cmd = 0x03;
        Mesh.sendMessage(target, MSG_COMMAND, &cmd, 1, PRIORITY_HIGH);
        Serial.println(F("  -> Inviato stop allarme"));
        
    } else if (strcmp(command, "status") == 0) {
        // Richiedi status
        publishStatus();
        
    } else {
        Serial.println(F("  Comando sconosciuto"));
    }
}

// ============================================================
// Pubblicazione MQTT
// ============================================================
void publishSensorData(const char* node_id, const SensorDataAmbient* data) {
    if (!mqtt_connected) return;
    
    json_doc.clear();
    json_doc["node_id"] = node_id;
    json_doc["temperature"] = round(data->temperature * 10) / 10.0;
    json_doc["humidity"] = round(data->humidity * 10) / 10.0;
    json_doc["pressure"] = round(data->pressure * 10) / 10.0;
    json_doc["light"] = data->light_lux;
    json_doc["soil_moisture"] = data->soil_percent;
    json_doc["soil_raw"] = data->soil_moisture;
    json_doc["timestamp"] = millis() / 1000;
    
    serializeJson(json_doc, json_buffer);
    
    String topic = topicSensors + "/" + node_id;
    if (mqtt.publish(topic.c_str(), json_buffer)) {
        Serial.printf("[MQTT] Pubblicato su %s\n", topic.c_str());
    }
}

void publishSecurityAlarm(const char* node_id, IntrusionClass classification,
                          const SensorDataSecurity* data) {
    if (!mqtt_connected) return;
    
    json_doc.clear();
    json_doc["node_id"] = node_id;
    json_doc["classification"] = classification;
    json_doc["classification_name"] = 
        (classification == CLASS_PERSON) ? "PERSON" :
        (classification == CLASS_ANIMAL_LARGE) ? "ANIMAL_LARGE" :
        (classification == CLASS_ANIMAL_SMALL) ? "ANIMAL_SMALL" : "UNKNOWN";
    json_doc["pir_main"] = data->pir_main;
    json_doc["pir_backup"] = data->pir_backup;
    json_doc["tamper"] = data->tamper_detected;
    json_doc["accel_x"] = data->accel_x;
    json_doc["accel_y"] = data->accel_y;
    json_doc["accel_z"] = data->accel_z;
    json_doc["timestamp"] = millis() / 1000;
    json_doc["priority"] = (classification == CLASS_PERSON) ? "CRITICAL" : "WARNING";
    
    serializeJson(json_doc, json_buffer);
    
    String topic = topicSecurity + "/" + node_id;
    if (mqtt.publish(topic.c_str(), json_buffer, true)) {  // Retained
        Serial.printf("[MQTT] ALLARME pubblicato su %s\n", topic.c_str());
    }
}

void publishStatus() {
    if (!mqtt_connected) return;
    
    json_doc.clear();
    json_doc["node_id"] = NODE_ID;
    json_doc["type"] = "GATEWAY";
    json_doc["uptime"] = millis() / 1000;
    json_doc["heap_free"] = ESP.getFreeHeap();
    json_doc["signal"] = modem.getSignalQuality();
    json_doc["gprs"] = gprs_connected;
    json_doc["mqtt"] = mqtt_connected;
    json_doc["mesh_peers"] = Mesh.getActivePeerCount();
    json_doc["messages_processed"] = message_count;
    json_doc["firmware"] = FIRMWARE_VERSION;
    
    serializeJson(json_doc, json_buffer);
    
    if (mqtt.publish(topicStatus.c_str(), json_buffer)) {
        Serial.println(F("[MQTT] Status pubblicato"));
    }
}
