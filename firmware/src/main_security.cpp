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
volatile bool alarm_triggered = false;
uint32_t alarm_start_time = 0;
uint32_t last_alarm_time = 0;
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
    // Inizializza Serial
    Serial.begin(115200);
    delay(100);
    
    Serial.println(F("\n"));
    Serial.println(F("╔═══════════════════════════════════════════╗"));
    Serial.println(F("║   AgriSecure IoT - Nodo Sicurezza         ║"));
    Serial.println(F("╚═══════════════════════════════════════════╝"));
    Serial.printf("Versione: %s\n", FIRMWARE_VERSION);
    Serial.printf("Node ID: %s\n", NODE_ID);
    
    // Configura pin attuatori
    pinMode(RELAY_SIREN_PIN, OUTPUT);
    pinMode(RELAY_LIGHT_PIN, OUTPUT);
    digitalWrite(RELAY_SIREN_PIN, LOW);  // Sirena OFF
    digitalWrite(RELAY_LIGHT_PIN, LOW);  // Luce OFF
    Serial.printf("Sirena su GPIO%d\n", RELAY_SIREN_PIN);
    Serial.printf("Luce su GPIO%d\n", RELAY_LIGHT_PIN);
    
    // LED di stato
    pinMode(LED_STATUS, OUTPUT);
    digitalWrite(LED_STATUS, HIGH);
    
    // Inizializza sensori sicurezza
    Serial.println(F("\nInizializzazione sensori sicurezza..."));
    if (!SecuritySensors.begin()) {
        Serial.println(F("ATTENZIONE: Alcuni sensori non disponibili!"));
    }
    
    // Registra callback eventi sicurezza
    SecuritySensors.onSecurityEvent(onSecurityEvent);
    
    // Inizializza mesh
    Serial.println(F("\nInizializzazione mesh..."));
    if (!Mesh.begin(NODE_ID, NODE_SECURITY)) {
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
        digitalWrite(LED_STATUS, !digitalRead(LED_STATUS));
        delay(1000);
    }
    
    SecuritySensors.arm();
    digitalWrite(LED_STATUS, LOW);
    
    Serial.println(F("\n╔═══════════════════════════════════════════╗"));
    Serial.println(F("║   SISTEMA ARMATO E OPERATIVO              ║"));
    Serial.println(F("╚═══════════════════════════════════════════╝"));
}

// ============================================================
// Loop Principale
// ============================================================
void loop() {
    // Aggiorna mesh
    Mesh.update();
    
    // Aggiorna sensori sicurezza
    SecuritySensors.update();
    
    uint32_t now = millis();
    
    // Gestisci timeout allarme
    if (alarm_triggered && (now - alarm_start_time >= ALARM_DURATION)) {
        Serial.println(F("Timeout allarme, disattivazione..."));
        deactivateAlarm();
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
    
    // LED lampeggia lento se armato, veloce se allarme
    static uint32_t last_blink = 0;
    uint32_t blink_interval = alarm_triggered ? 100 : (system_armed ? 2000 : 500);
    if (now - last_blink > blink_interval) {
        digitalWrite(LED_STATUS, !digitalRead(LED_STATUS));
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
    
    // Cooldown tra allarmi
    if (now - last_alarm_time < ALARM_COOLDOWN) {
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
            // Solo luce, no sirena
            digitalWrite(RELAY_LIGHT_PIN, HIGH);
            delay(3000);
            digitalWrite(RELAY_LIGHT_PIN, LOW);
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
    
    last_alarm_time = now;
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
    
    Serial.printf("Allarme attivo per %d secondi\n", ALARM_DURATION / 1000);
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
