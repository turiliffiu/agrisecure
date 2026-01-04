/**
 * AgriSecure IoT System - Header principale
 * 
 * Definizioni comuni per tutti i tipi di nodo
 * 
 * @author Turiliffiu
 * @version 1.0.0
 * @date 2024-12
 */

#ifndef AGRISECURE_CONFIG_H
#define AGRISECURE_CONFIG_H

#include <Arduino.h>
#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>

// ============================================================
// Versione e Build Info
// ============================================================
#ifndef FIRMWARE_VERSION
#define FIRMWARE_VERSION "1.0.0-dev"
#endif

// ============================================================
// Tipi di Nodo
// ============================================================
typedef enum {
    NODE_GATEWAY = 0,    // Gateway con connettività 4G
    NODE_AMBIENT = 1,    // Nodo ambientale (sensori clima/suolo)
    NODE_SECURITY = 2,   // Nodo sicurezza (PIR, allarmi)
    NODE_TEST = 99       // Nodo di test/debug
} NodeType;

// ============================================================
// Priorità Messaggi (QoS)
// ============================================================
typedef enum {
    PRIORITY_CRITICAL = 0,  // Allarme intrusione persona (<2s)
    PRIORITY_HIGH = 1,      // Comandi controllo (<5s)
    PRIORITY_MEDIUM = 2,    // Status, heartbeat (<30s)
    PRIORITY_LOW = 3        // Dati ambientali (<60s)
} MessagePriority;

// ============================================================
// Tipi di Messaggio Mesh
// ============================================================
typedef enum {
    MSG_HEARTBEAT = 0x01,       // Heartbeat periodico
    MSG_SENSOR_DATA = 0x02,     // Dati sensori ambientali
    MSG_ALARM_PERSON = 0x03,    // Allarme: persona rilevata
    MSG_ALARM_ANIMAL = 0x04,    // Allarme: animale rilevato
    MSG_ALARM_TAMPER = 0x05,    // Allarme: manomissione
    MSG_COMMAND = 0x06,         // Comando da gateway
    MSG_ACK = 0x07,             // Acknowledgment
    MSG_CONFIG = 0x08,          // Configurazione remota
    MSG_OTA = 0x09,             // OTA update
    MSG_BATTERY = 0x0A,         // Status batteria
    MSG_MESH_TOPOLOGY = 0x0B,   // Topologia rete
    MSG_ARM = 0x0C,             // Arma sistema
    MSG_DISARM = 0x0D           // Disarma sistema
} MessageType;

// ============================================================
// Classificazione Intrusione
// ============================================================
typedef enum {
    CLASS_NONE = 0,         // Nessun movimento
    CLASS_PERSON = 1,       // Persona (allarme critico)
    CLASS_ANIMAL_LARGE = 2, // Animale grande (warning)
    CLASS_ANIMAL_SMALL = 3, // Animale piccolo (ignorato)
    CLASS_UNKNOWN = 4       // Non classificabile
} IntrusionClass;

// ============================================================
// Struttura Messaggio Mesh
// ============================================================
#define MESH_MSG_MAX_SIZE 200
#define NODE_ID_SIZE 12

#pragma pack(push, 1)
typedef struct {
    char sender_id[NODE_ID_SIZE];    // ID nodo mittente
    char target_id[NODE_ID_SIZE];    // ID nodo destinatario ("*" = broadcast)
    uint8_t msg_type;                // Tipo messaggio
    uint8_t priority;                // Priorità
    uint32_t timestamp;              // Unix timestamp
    uint16_t sequence;               // Numero sequenza
    uint8_t hop_count;               // Numero hop (per routing)
    uint8_t payload_len;             // Lunghezza payload
    uint8_t payload[MESH_MSG_MAX_SIZE]; // Dati
    uint16_t crc;                    // CRC16 per integrità
} MeshMessage;
#pragma pack(pop)

// ============================================================
// Struttura Dati Sensori Ambientali
// ============================================================
#pragma pack(push, 1)
typedef struct {
    float temperature;       // °C
    float humidity;          // %
    float pressure;          // hPa
    uint16_t light_lux;      // Lux
    uint16_t soil_moisture;  // 0-4095 (ADC)
    uint8_t soil_percent;    // 0-100%
} SensorDataAmbient;
#pragma pack(pop)

// ============================================================
// Struttura Dati Sensori Sicurezza
// ============================================================
#pragma pack(push, 1)
typedef struct {
    uint8_t pir_main;           // 0/1 PIR principale
    uint8_t pir_backup;         // 0/1 PIR backup
    uint8_t motion_detected;    // 0/1 movimento confermato
    uint8_t classification;     // IntrusionClass
    float distance_cm;          // Distanza stimata (se disponibile)
    float accel_x;              // Accelerometro X
    float accel_y;              // Accelerometro Y
    float accel_z;              // Accelerometro Z
    uint8_t tamper_detected;    // 0/1 manomissione
} SensorDataSecurity;
#pragma pack(pop)

// ============================================================
// Struttura Status Batteria
// ============================================================
#pragma pack(push, 1)
typedef struct {
    uint16_t voltage_mv;     // Tensione in mV
    uint8_t percentage;      // Percentuale carica
    uint8_t charging;        // 0/1 in carica
    uint16_t solar_mv;       // Tensione pannello solare
    int16_t current_ma;      // Corrente (+ carica, - scarica)
} BatteryStatus;
#pragma pack(pop)

// ============================================================
// Struttura Heartbeat
// ============================================================
#pragma pack(push, 1)
typedef struct {
    uint8_t node_type;       // Tipo nodo
    uint8_t status;          // 0=OK, 1=Warning, 2=Error
    uint32_t uptime_sec;     // Secondi dall'avvio
    uint16_t free_heap;      // Heap libero (KB)
    int8_t rssi;             // WiFi RSSI
    uint8_t battery_pct;     // Batteria %
    uint8_t mesh_neighbors;  // Numero vicini mesh
} HeartbeatData;
#pragma pack(pop)

// ============================================================
// Configurazione Rete Mesh
// ============================================================
#ifndef MESH_CHANNEL
#define MESH_CHANNEL 1
#endif

#ifndef MESH_MAX_NODES
#define MESH_MAX_NODES 25
#endif

#ifndef MESH_HEARTBEAT_INTERVAL
#define MESH_HEARTBEAT_INTERVAL 1800000  // 30 minuti
#endif

#define MESH_BROADCAST_ADDR {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF}

// ============================================================
// Pin di Default (possono essere sovrascritti in platformio.ini)
// ============================================================

// I2C
#ifndef I2C_SDA
#define I2C_SDA 6
#endif

#ifndef I2C_SCL
#define I2C_SCL 7
#endif

// LED di stato (built-in su ESP32-C6-DevKit)
#ifndef LED_STATUS
#define LED_STATUS 8
#endif

// ============================================================
// Macro Utility
// ============================================================
#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))

// Debug logging
#ifdef SERIAL_DEBUG
    #define DEBUG_PRINT(x) Serial.print(x)
    #define DEBUG_PRINTLN(x) Serial.println(x)
    #define DEBUG_PRINTF(fmt, ...) Serial.printf(fmt, ##__VA_ARGS__)
#else
    #define DEBUG_PRINT(x)
    #define DEBUG_PRINTLN(x)
    #define DEBUG_PRINTF(fmt, ...)
#endif

// ============================================================
// Funzioni Utility
// ============================================================

/**
 * Calcola CRC16 per verifica integrità messaggio
 */
uint16_t calculateCRC16(const uint8_t* data, size_t length);

/**
 * Converte MAC address in stringa
 */
String macToString(const uint8_t* mac);

/**
 * Ottiene timestamp corrente (secondi da boot o Unix time se sincronizzato)
 */
uint32_t getCurrentTimestamp();

#endif // AGRISECURE_CONFIG_H
