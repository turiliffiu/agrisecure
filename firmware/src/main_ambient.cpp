/**
 * AgriSecure IoT System - Firmware Nodo Ambientale
 * 
 * Nodo per monitoraggio parametri climatici e suolo:
 * - Temperatura, Umidità, Pressione (BME280)
 * - Luminosità (BH1750)
 * - Umidità suolo (sensore capacitivo)
 * 
 * Funzionamento:
 * 1. Wake up da deep sleep
 * 2. Leggi sensori
 * 3. Invia dati via mesh al gateway
 * 4. Torna in deep sleep
 * 
 * @author Turiliffiu
 * @version 1.0.0
 */

#include <Arduino.h>
#include "agrisecure_config.h"
#include "mesh_manager.h"
#include "sensors_ambient.h"

// ============================================================
// Configurazione
// ============================================================
#ifndef NODE_ID
#define NODE_ID "AMB-001"
#endif

#ifndef SENSOR_READ_INTERVAL
#define SENSOR_READ_INTERVAL 600000  // 10 minuti in ms
#endif

#ifndef DEEP_SLEEP_DURATION
#define DEEP_SLEEP_DURATION 600  // 10 minuti in secondi
#endif

// ============================================================
// Variabili Globali
// ============================================================
RTC_DATA_ATTR uint32_t boot_count = 0;  // Persistente durante deep sleep
RTC_DATA_ATTR uint32_t total_readings = 0;

uint32_t last_sensor_read = 0;
uint32_t last_heartbeat = 0;
bool mesh_connected = false;

// ============================================================
// Prototipi
// ============================================================
void onMeshMessage(const MeshMessage* msg, const uint8_t* sender_mac);
void readAndSendSensors();
void enterDeepSleep();
void printWakeupReason();

// ============================================================
// Setup
// ============================================================
void setup() {
    // Inizializza Serial
    Serial.begin(115200);
    delay(100);
    
    boot_count++;
    
    Serial.println(F("\n"));
    Serial.println(F("╔═══════════════════════════════════════════╗"));
    Serial.println(F("║   AgriSecure IoT - Nodo Ambientale        ║"));
    Serial.println(F("╚═══════════════════════════════════════════╝"));
    Serial.printf("Versione: %s\n", FIRMWARE_VERSION);
    Serial.printf("Node ID: %s\n", NODE_ID);
    Serial.printf("Boot count: %d\n", boot_count);
    Serial.printf("Letture totali: %d\n", total_readings);
    
    // Motivo wakeup
    printWakeupReason();
    
    // LED di stato
    pinMode(LED_STATUS, OUTPUT);
    digitalWrite(LED_STATUS, HIGH);  // LED acceso durante setup
    
    // Inizializza sensori ambientali
    Serial.println(F("\nInizializzazione sensori..."));
    if (!AmbientSensors.begin()) {
        Serial.println(F("ATTENZIONE: Alcuni sensori non disponibili!"));
    }
    
    // Inizializza mesh
    Serial.println(F("\nInizializzazione mesh..."));
    if (!Mesh.begin(NODE_ID, NODE_AMBIENT)) {
        Serial.println(F("ERRORE: Mesh non inizializzato!"));
        // Continua comunque, prova a riconnettersi
    }
    
    // Registra callback messaggi
    Mesh.onMessage(onMeshMessage);
    
    // Prima lettura sensori
    readAndSendSensors();
    
    // LED spento
    digitalWrite(LED_STATUS, LOW);
    
    Serial.println(F("\nSetup completato!"));
    Serial.println(F("───────────────────────────────────────────"));
    
    #ifdef DEEP_SLEEP_ENABLED
    // Se deep sleep abilitato, dormi subito dopo invio
    Serial.println(F("Deep sleep abilitato, entro in sleep..."));
    delay(1000);  // Attendi invio mesh
    enterDeepSleep();
    #endif
}

// ============================================================
// Loop Principale
// ============================================================
void loop() {
    // Aggiorna mesh
    Mesh.update();
    
    uint32_t now = millis();
    
    // Lettura sensori periodica
    if (now - last_sensor_read >= SENSOR_READ_INTERVAL) {
        readAndSendSensors();
        last_sensor_read = now;
    }
    
    // Heartbeat periodico
    if (now - last_heartbeat >= MESH_HEARTBEAT_INTERVAL) {
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
    
    // LED lampeggia se non connesso
    static uint32_t last_blink = 0;
    if (!mesh_connected && now - last_blink > 1000) {
        digitalWrite(LED_STATUS, !digitalRead(LED_STATUS));
        last_blink = now;
    }
    
    // Piccola pausa per risparmiare energia
    delay(100);
}

// ============================================================
// Lettura e Invio Sensori
// ============================================================
void readAndSendSensors() {
    Serial.println(F("\n>>> Lettura sensori <<<"));
    
    digitalWrite(LED_STATUS, HIGH);
    
    SensorDataAmbient data;
    if (AmbientSensors.read(&data)) {
        Serial.println(F("Dati sensori:"));
        Serial.printf("  Temperatura: %.1f °C\n", data.temperature);
        Serial.printf("  Umidità aria: %.1f %%\n", data.humidity);
        Serial.printf("  Pressione: %.1f hPa\n", data.pressure);
        Serial.printf("  Luce: %d lux\n", data.light_lux);
        Serial.printf("  Umidità suolo: %d%% (raw: %d)\n", 
                      data.soil_percent, data.soil_moisture);
        
        // Invia via mesh
        if (Mesh.sendSensorData(&data)) {
            Serial.println(F("✓ Dati inviati al gateway"));
            total_readings++;
        } else {
            Serial.println(F("✗ Errore invio dati"));
        }
    } else {
        Serial.println(F("Errore lettura sensori!"));
    }
    
    digitalWrite(LED_STATUS, LOW);
}

// ============================================================
// Callback Messaggi Mesh
// ============================================================
void onMeshMessage(const MeshMessage* msg, const uint8_t* sender_mac) {
    Serial.printf("\nMessaggio ricevuto da %s, tipo: %d\n", 
                  msg->sender_id, msg->msg_type);
    
    switch (msg->msg_type) {
        case MSG_COMMAND:
            Serial.println(F("Comando ricevuto"));
            // TODO: gestire comandi (es. calibrazione, config)
            break;
            
        case MSG_CONFIG:
            Serial.println(F("Configurazione ricevuta"));
            // TODO: applicare nuova configurazione
            break;
            
        case MSG_OTA:
            Serial.println(F("Richiesta OTA ricevuta"));
            // TODO: avviare OTA update
            break;
            
        default:
            // Altri messaggi ignorati
            break;
    }
}

// ============================================================
// Deep Sleep
// ============================================================
void enterDeepSleep() {
    Serial.printf("Entro in deep sleep per %d secondi...\n", DEEP_SLEEP_DURATION);
    Serial.flush();
    
    // Configura wakeup timer
    esp_sleep_enable_timer_wakeup(DEEP_SLEEP_DURATION * 1000000ULL);
    
    // Entra in deep sleep
    esp_deep_sleep_start();
}

void printWakeupReason() {
    esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
    
    switch (wakeup_reason) {
        case ESP_SLEEP_WAKEUP_TIMER:
            Serial.println(F("Wakeup: Timer"));
            break;
        case ESP_SLEEP_WAKEUP_EXT0:
            Serial.println(F("Wakeup: External signal (RTC_IO)"));
            break;
        case ESP_SLEEP_WAKEUP_EXT1:
            Serial.println(F("Wakeup: External signal (RTC_CNTL)"));
            break;
        case ESP_SLEEP_WAKEUP_GPIO:
            Serial.println(F("Wakeup: GPIO"));
            break;
        default:
            Serial.println(F("Wakeup: Power on / Reset"));
            break;
    }
}
