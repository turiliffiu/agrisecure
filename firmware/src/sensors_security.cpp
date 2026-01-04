/**
 * AgriSecure IoT System - Implementazione Sensori Sicurezza
 * 
 * Include algoritmo di discriminazione persona/animale basato su:
 * - Pattern di movimento dai PIR
 * - Durata del movimento
 * - Conferma da sensore backup
 * - Analisi accelerometro per tamper
 * 
 * @author Turiliffiu
 * @version 1.0.0
 */

#include "sensors_security.h"

// Istanza globale
SensorsSecurity SecuritySensors;

// ============================================================
// Inizializzazione
// ============================================================
bool SensorsSecurity::begin(int pir_main_pin, int pir_backup_pin, int sda, int scl) {
    _pir_main_pin = pir_main_pin;
    _pir_backup_pin = pir_backup_pin;
    _mpu_ok = false;
    _armed = false;
    _person_height_min = PERSON_HEIGHT_MIN;
    _animal_height_max = ANIMAL_HEIGHT_MAX;
    _last_classification = CLASS_NONE;
    _last_motion_time = 0;
    _last_tamper_time = 0;
    _motion_active = false;
    _tamper_active = false;
    _event_callback = nullptr;
    _baseline_set = false;
    
    DEBUG_PRINTLN(F(""));
    DEBUG_PRINTLN(F("=== Inizializzazione Sensori Sicurezza ==="));
    
    // Configura pin PIR come input
    pinMode(_pir_main_pin, INPUT);
    pinMode(_pir_backup_pin, INPUT);
    DEBUG_PRINTF("PIR principale: GPIO%d\n", _pir_main_pin);
    DEBUG_PRINTF("PIR backup: GPIO%d\n", _pir_backup_pin);
    
    // Inizializza I2C per MPU6050
    Wire.begin(sda, scl);
    
    // Inizializza MPU6050
    DEBUG_PRINT(F("Inizializzazione MPU6050... "));
    _mpu.initialize();
    
    if (_mpu.testConnection()) {
        _mpu_ok = true;
        DEBUG_PRINTLN(F("OK"));
        
        // Configura sensibilità
        _mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_4);  // ±4g
        _mpu.setFullScaleGyroRange(MPU6050_GYRO_FS_500);  // ±500°/s
        
        // Calibra baseline dopo un breve delay
        delay(100);
        _calibrateBaseline();
    } else {
        DEBUG_PRINTLN(F("FALLITO!"));
    }
    
    // Attendi stabilizzazione PIR (circa 30-60 secondi in realtà)
    DEBUG_PRINTLN(F("Stabilizzazione PIR..."));
    
    DEBUG_PRINTLN(F("==========================================="));
    
    return true;
}

// ============================================================
// Loop di Aggiornamento
// ============================================================
void SensorsSecurity::update() {
    if (!_armed) return;
    
    uint32_t now = millis();
    
    // Leggi stato PIR
    bool pir_main = digitalRead(_pir_main_pin) == HIGH;
    bool pir_backup = digitalRead(_pir_backup_pin) == HIGH;
    
    // Debounce
    if (now - _last_motion_time < PIR_DEBOUNCE_MS) {
        return;
    }
    
    // Rileva movimento
    if (pir_main || pir_backup) {
        if (!_motion_active) {
            _motion_active = true;
            _last_motion_time = now;
            
            DEBUG_PRINTLN(F(">>> MOVIMENTO RILEVATO <<<"));
            DEBUG_PRINTF("PIR Main: %d, PIR Backup: %d\n", pir_main, pir_backup);
            
            // Classifica intruso
            IntrusionClass classification = _classifyIntrusion();
            _last_classification = classification;
            
            // Genera evento
            _triggerEvent(classification);
        }
    } else {
        _motion_active = false;
    }
    
    // Controlla tamper
    if (_mpu_ok) {
        if (_checkTamper() && !_tamper_active) {
            _tamper_active = true;
            _last_tamper_time = now;
            
            DEBUG_PRINTLN(F(">>> TAMPER RILEVATO <<<"));
            
            // Genera evento tamper
            SensorDataSecurity data;
            read(&data);
            data.tamper_detected = 1;
            
            if (_event_callback) {
                _event_callback(CLASS_UNKNOWN, &data);
            }
        } else if (!_checkTamper()) {
            _tamper_active = false;
        }
    }
}

// ============================================================
// Lettura Sensori
// ============================================================
bool SensorsSecurity::read(SensorDataSecurity* data) {
    if (!data) return false;
    
    memset(data, 0, sizeof(SensorDataSecurity));
    
    // Stato PIR
    data->pir_main = digitalRead(_pir_main_pin);
    data->pir_backup = digitalRead(_pir_backup_pin);
    data->motion_detected = (data->pir_main || data->pir_backup) ? 1 : 0;
    data->classification = _last_classification;
    
    // Accelerometro
    if (_mpu_ok) {
        int16_t ax, ay, az, gx, gy, gz;
        _mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
        
        // Converti in g (sensibilità ±4g = 8192 LSB/g)
        data->accel_x = ax / 8192.0;
        data->accel_y = ay / 8192.0;
        data->accel_z = az / 8192.0;
        
        data->tamper_detected = _tamper_active ? 1 : 0;
    }
    
    return true;
}

// ============================================================
// Algoritmo di Discriminazione Persona/Animale
// ============================================================
IntrusionClass SensorsSecurity::_classifyIntrusion() {
    /**
     * ALGORITMO DI DISCRIMINAZIONE
     * 
     * Analisi basata su:
     * 1. Conferma da entrambi i PIR (dual sensor = più affidabile)
     * 2. Pattern temporale del movimento
     * 3. Persistenza del segnale
     * 
     * Senza sensore di distanza (HC-SR04), usiamo euristica:
     * - Entrambi PIR attivi + movimento prolungato = probabilmente persona
     * - Solo PIR principale + movimento breve = probabilmente animale
     * - Movimento molto breve e erratico = animale piccolo
     */
    
    bool pir_main = digitalRead(_pir_main_pin) == HIGH;
    bool pir_backup = digitalRead(_pir_backup_pin) == HIGH;
    
    // Misura durata movimento
    uint32_t start = millis();
    uint8_t main_count = 0;
    uint8_t backup_count = 0;
    
    // Campiona per 500ms
    for (int i = 0; i < 50; i++) {
        if (digitalRead(_pir_main_pin) == HIGH) main_count++;
        if (digitalRead(_pir_backup_pin) == HIGH) backup_count++;
        delay(10);
    }
    
    uint32_t motion_duration = millis() - start;
    
    DEBUG_PRINTF("Analisi: main_count=%d, backup_count=%d, durata=%dms\n",
                 main_count, backup_count, motion_duration);
    
    // Classificazione basata su pattern
    
    // Caso 1: Entrambi i PIR attivi per la maggior parte del tempo
    // Alta probabilità di persona (bersaglio grande, movimento lineare)
    if (main_count > 40 && backup_count > 30) {
        DEBUG_PRINTLN(F("Classificazione: PERSONA (entrambi PIR, movimento costante)"));
        return CLASS_PERSON;
    }
    
    // Caso 2: Solo PIR principale attivo, movimento lungo
    // Potrebbe essere persona che passa di lato
    if (main_count > 35 && backup_count < 20) {
        DEBUG_PRINTLN(F("Classificazione: PERSONA (PIR main dominante, lungo)"));
        return CLASS_PERSON;
    }
    
    // Caso 3: Movimento moderato su entrambi
    // Animale di media taglia (cane, volpe)
    if (main_count > 20 && main_count <= 40) {
        DEBUG_PRINTLN(F("Classificazione: ANIMALE GRANDE"));
        return CLASS_ANIMAL_LARGE;
    }
    
    // Caso 4: Movimento breve e sporadico
    // Animale piccolo (gatto, uccello, roditore)
    if (main_count <= 20) {
        DEBUG_PRINTLN(F("Classificazione: ANIMALE PICCOLO"));
        return CLASS_ANIMAL_SMALL;
    }
    
    // Caso default
    DEBUG_PRINTLN(F("Classificazione: SCONOSCIUTO"));
    return CLASS_UNKNOWN;
}

// ============================================================
// Tamper Detection
// ============================================================
bool SensorsSecurity::_checkTamper() {
    if (!_mpu_ok || !_baseline_set) return false;
    
    int16_t ax, ay, az, gx, gy, gz;
    _mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
    
    // Converti in g
    float accel_x = ax / 8192.0;
    float accel_y = ay / 8192.0;
    float accel_z = az / 8192.0;
    
    // Calcola differenza dalla baseline
    float diff_x = abs(accel_x - _accel_baseline_x);
    float diff_y = abs(accel_y - _accel_baseline_y);
    float diff_z = abs(accel_z - _accel_baseline_z);
    
    float total_diff = sqrt(diff_x*diff_x + diff_y*diff_y + diff_z*diff_z);
    
    // Se differenza supera soglia, possibile tamper
    if (total_diff > TAMPER_THRESHOLD_G) {
        DEBUG_PRINTF("Tamper check: diff=%.2fg (soglia=%.2fg)\n", 
                     total_diff, TAMPER_THRESHOLD_G);
        return true;
    }
    
    return false;
}

void SensorsSecurity::_calibrateBaseline() {
    if (!_mpu_ok) return;
    
    DEBUG_PRINTLN(F("Calibrazione baseline accelerometro..."));
    
    // Media di 100 campioni
    float sum_x = 0, sum_y = 0, sum_z = 0;
    
    for (int i = 0; i < 100; i++) {
        int16_t ax, ay, az, gx, gy, gz;
        _mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
        
        sum_x += ax / 8192.0;
        sum_y += ay / 8192.0;
        sum_z += az / 8192.0;
        
        delay(10);
    }
    
    _accel_baseline_x = sum_x / 100;
    _accel_baseline_y = sum_y / 100;
    _accel_baseline_z = sum_z / 100;
    _baseline_set = true;
    
    DEBUG_PRINTF("Baseline: X=%.2f, Y=%.2f, Z=%.2f\n",
                 _accel_baseline_x, _accel_baseline_y, _accel_baseline_z);
}

// ============================================================
// Gestione Eventi
// ============================================================
void SensorsSecurity::_triggerEvent(IntrusionClass classification) {
    if (!_event_callback) return;
    
    SensorDataSecurity data;
    read(&data);
    
    _event_callback(classification, &data);
}

void SensorsSecurity::onSecurityEvent(SecurityEventCallback callback) {
    _event_callback = callback;
}

// ============================================================
// Controllo Sistema
// ============================================================
void SensorsSecurity::arm() {
    _armed = true;
    _last_classification = CLASS_NONE;
    _motion_active = false;
    _tamper_active = false;
    
    // Ricalibra baseline
    if (_mpu_ok) {
        _calibrateBaseline();
    }
    
    DEBUG_PRINTLN(F("Sistema di sicurezza ARMATO"));
}

void SensorsSecurity::disarm() {
    _armed = false;
    DEBUG_PRINTLN(F("Sistema di sicurezza DISARMATO"));
}

void SensorsSecurity::resetAlarm() {
    _last_classification = CLASS_NONE;
    _motion_active = false;
    _tamper_active = false;
    DEBUG_PRINTLN(F("Allarme resettato"));
}

// ============================================================
// Utility
// ============================================================
bool SensorsSecurity::isMotionDetected() {
    return digitalRead(_pir_main_pin) == HIGH || 
           digitalRead(_pir_backup_pin) == HIGH;
}

bool SensorsSecurity::isTamperDetected() {
    return _checkTamper();
}

void SensorsSecurity::setThresholds(uint16_t person_min_cm, uint16_t animal_max_cm) {
    _person_height_min = person_min_cm;
    _animal_height_max = animal_max_cm;
    DEBUG_PRINTF("Soglie aggiornate: persona>%dcm, animale<%dcm\n", 
                 person_min_cm, animal_max_cm);
}
