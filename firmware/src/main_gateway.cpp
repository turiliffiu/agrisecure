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
#define GSM_APN "internet"  // TIM: "ibox.tim.it", Vodafone: "web.omnitel.it"
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
// Oggetti Globali
// ============================================================
HardwareSerial SerialGSM(1);  // UART1 per modem
TinyGsm modem(SerialGSM);
TinyGsmClient gsmClient(modem);
PubSubClient mqtt(gsmClient);

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

// ============================================================
// Setup
// ============================================================
void setup() {
    // Inizializza Serial
    Serial.begin(115200);
    delay(100);
    
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
    Serial.println(F("\nInizializzazione modem 4G..."));
    if (initModem()) {
        modem_ready = true;
        Serial.println(F("✓ Modem pronto"));
        
        // Connetti GPRS
        if (connectGPRS()) {
            gprs_connected = true;
            Serial.println(F("✓ GPRS connesso"));
            
            // Configura MQTT
            mqtt.setServer(MQTT_BROKER, MQTT_PORT);
            mqtt.setCallback(mqttCallback);
            mqtt.setBufferSize(512);
            
            // Connetti MQTT
            if (connectMQTT()) {
                mqtt_connected = true;
                Serial.println(F("✓ MQTT connesso"));
            }
        }
    } else {
        Serial.println(F("✗ Modem non disponibile - modalità offline"));
    }
    
    // Inizializza mesh
    Serial.println(F("\nInizializzazione mesh ESP-NOW..."));
    if (!Mesh.begin(NODE_ID, NODE_GATEWAY)) {
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
    if (mqtt_connected && (now - last_status_publish > 300000)) {
        publishStatus();
        last_status_publish = now;
    }
    
    // Heartbeat mesh
    if (now - last_heartbeat >= MESH_HEARTBEAT_INTERVAL) {
        Serial.println(F("Invio heartbeat mesh..."));
        Mesh.sendHeartbeat();
        last_heartbeat = now;
    }
    
    // LED indica stato
    static uint32_t last_blink = 0;
    if (now - last_blink > 1000) {
        if (mqtt_connected) {
            // LED acceso fisso se tutto OK
            digitalWrite(LED_STATUS, HIGH);
        } else if (gprs_connected) {
            // Lampeggio lento se GPRS OK ma MQTT no
            digitalWrite(LED_STATUS, !digitalRead(LED_STATUS));
        } else {
            // Lampeggio veloce se disconnesso
            digitalWrite(LED_STATUS, (now / 200) % 2);
        }
        last_blink = now;
    }
    
    delay(10);
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
    Serial.printf("Connessione GPRS (APN: %s)...\n", GSM_APN);
    
    if (!modem.gprsConnect(GSM_APN, GSM_USER, GSM_PASS)) {
        Serial.println(F("Connessione GPRS fallita"));
        return false;
    }
    
    Serial.printf("IP: %s\n", modem.localIP().toString().c_str());
    return true;
}

bool connectMQTT() {
    Serial.printf("Connessione MQTT (%s:%d)...\n", MQTT_BROKER, MQTT_PORT);
    
    String clientId = "agrisecure-" + String(NODE_ID);
    
    // Last Will Testament
    String lwt_topic = String(MQTT_TOPIC_STATUS) + "/online";
    
    if (mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASS, 
                     lwt_topic.c_str(), 1, true, "false")) {
        Serial.println(F("MQTT connesso!"));
        
        // Pubblica stato online
        mqtt.publish(lwt_topic.c_str(), "true", true);
        
        // Subscribe a topic comandi
        mqtt.subscribe(MQTT_TOPIC_COMMAND);
        mqtt.subscribe(MQTT_TOPIC_CONFIG);
        
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
                
                String topic = String(MQTT_TOPIC_STATUS) + "/" + msg->sender_id;
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
    
    String topic = String(MQTT_TOPIC_SENSORS) + "/" + node_id;
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
    
    String topic = String(MQTT_TOPIC_SECURITY) + "/" + node_id;
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
    
    if (mqtt.publish(MQTT_TOPIC_STATUS, json_buffer)) {
        Serial.println(F("[MQTT] Status pubblicato"));
    }
}
