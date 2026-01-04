/**
 * AgriSecure IoT System - Modulo Sensori Sicurezza
 * 
 * Gestisce i sensori per la sicurezza perimetrale:
 * - PIR HC-SR501: Rilevamento movimento principale
 * - PIR AM312: Rilevamento backup (basso consumo)
 * - MPU6050: Accelerometro per tamper detection
 * 
 * Include algoritmo di discriminazione persona/animale
 * 
 * @author Turiliffiu
 * @version 1.0.0
 */

#ifndef SENSORS_SECURITY_H
#define SENSORS_SECURITY_H

#include "agrisecure_config.h"
#include <Wire.h>
#include <MPU6050.h>

// ============================================================
// Configurazione Sensori
// ============================================================

// PIR principale (HC-SR501)
#ifndef PIR_MAIN_PIN
#define PIR_MAIN_PIN 2
#endif

// PIR backup (AM312)
#ifndef PIR_BACKUP_PIN
#define PIR_BACKUP_PIN 3
#endif

// Soglie discriminazione (cm)
#ifndef PERSON_HEIGHT_MIN
#define PERSON_HEIGHT_MIN 120  // Altezza minima persona (cm)
#endif

#ifndef ANIMAL_HEIGHT_MAX
#define ANIMAL_HEIGHT_MAX 80   // Altezza massima animale grande (cm)
#endif

// Soglie accelerometro per tamper detection
#define TAMPER_THRESHOLD_G 1.5    // Accelerazione soglia (g)
#define TAMPER_SAMPLES 10         // Campioni per conferma

// Timeout tra rilevamenti (antirimbalzo)
#define PIR_DEBOUNCE_MS 2000

// ============================================================
// Callback per eventi di sicurezza
// ============================================================
typedef void (*SecurityEventCallback)(IntrusionClass classification, 
                                       const SensorDataSecurity* data);

// ============================================================
// Classe SensorsSecurity
// ============================================================
class SensorsSecurity {
public:
    /**
     * Inizializza tutti i sensori di sicurezza
     * @param pir_main_pin Pin PIR principale
     * @param pir_backup_pin Pin PIR backup
     * @param sda Pin SDA per MPU6050
     * @param scl Pin SCL per MPU6050
     * @return true se inizializzazione OK
     */
    bool begin(int pir_main_pin = PIR_MAIN_PIN, 
               int pir_backup_pin = PIR_BACKUP_PIN,
               int sda = I2C_SDA, 
               int scl = I2C_SCL);
    
    /**
     * Loop di aggiornamento - chiamare frequentemente
     * Controlla sensori e genera eventi
     */
    void update();
    
    /**
     * Legge stato corrente di tutti i sensori
     * @param data Struttura da popolare
     * @return true se lettura OK
     */
    bool read(SensorDataSecurity* data);
    
    /**
     * Verifica se c'è movimento rilevato
     */
    bool isMotionDetected();
    
    /**
     * Verifica se c'è tentativo di manomissione
     */
    bool isTamperDetected();
    
    /**
     * Ottiene l'ultima classificazione
     */
    IntrusionClass getLastClassification() { return _last_classification; }
    
    /**
     * Registra callback per eventi di sicurezza
     */
    void onSecurityEvent(SecurityEventCallback callback);
    
    /**
     * Arma il sistema di sicurezza
     */
    void arm();
    
    /**
     * Disarma il sistema di sicurezza
     */
    void disarm();
    
    /**
     * Verifica se il sistema è armato
     */
    bool isArmed() { return _armed; }
    
    /**
     * Imposta soglie discriminazione
     */
    void setThresholds(uint16_t person_min_cm, uint16_t animal_max_cm);
    
    /**
     * Verifica disponibilità MPU6050
     */
    bool isMPU6050Available() { return _mpu_ok; }
    
    /**
     * Reset stato dopo allarme
     */
    void resetAlarm();

private:
    MPU6050 _mpu;
    
    int _pir_main_pin;
    int _pir_backup_pin;
    bool _mpu_ok;
    bool _armed;
    
    uint16_t _person_height_min;
    uint16_t _animal_height_max;
    
    IntrusionClass _last_classification;
    uint32_t _last_motion_time;
    uint32_t _last_tamper_time;
    bool _motion_active;
    bool _tamper_active;
    
    SecurityEventCallback _event_callback;
    
    // Baseline accelerometro per tamper detection
    float _accel_baseline_x;
    float _accel_baseline_y;
    float _accel_baseline_z;
    bool _baseline_set;
    
    // Metodi interni
    IntrusionClass _classifyIntrusion();
    bool _checkTamper();
    void _calibrateBaseline();
    void _triggerEvent(IntrusionClass classification);
};

// Istanza globale
extern SensorsSecurity SecuritySensors;

#endif // SENSORS_SECURITY_H
