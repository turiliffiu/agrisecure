/**
 * AgriSecure IoT System - Modulo Sensori Ambientali
 * 
 * Gestisce i sensori per il monitoraggio climatico e del suolo:
 * - BME280: Temperatura, Umidità, Pressione
 * - BH1750: Luminosità
 * - Sensore Capacitivo: Umidità suolo
 * 
 * @author Turiliffiu
 * @version 1.0.0
 */

#ifndef SENSORS_AMBIENT_H
#define SENSORS_AMBIENT_H

#include "agrisecure_config.h"
#include <Wire.h>
#include <Adafruit_BME280.h>
#include <BH1750.h>

// ============================================================
// Configurazione Sensori
// ============================================================

// BME280
#ifndef BME280_ADDR
#define BME280_ADDR 0x76  // Alcuni moduli usano 0x77
#endif

// BH1750
#ifndef BH1750_ADDR
#define BH1750_ADDR 0x23  // ADDR pin LOW, 0x5C se HIGH
#endif

// Soil Sensor
#ifndef SOIL_PIN
#define SOIL_PIN 0  // GPIO0 - ADC
#endif

// Calibrazione suolo (valori ADC)
#define SOIL_DRY_VALUE 3500    // Valore ADC quando suolo secco
#define SOIL_WET_VALUE 1500    // Valore ADC quando suolo bagnato

// ============================================================
// Classe SensorsAmbient
// ============================================================
class SensorsAmbient {
public:
    /**
     * Inizializza tutti i sensori ambientali
     * @param sda Pin SDA per I2C
     * @param scl Pin SCL per I2C
     * @param soil_pin Pin analogico per sensore suolo
     * @return true se almeno un sensore è stato inizializzato
     */
    bool begin(int sda = I2C_SDA, int scl = I2C_SCL, int soil_pin = SOIL_PIN);
    
    /**
     * Legge tutti i sensori e popola la struttura dati
     * @param data Puntatore alla struttura da popolare
     * @return true se lettura OK
     */
    bool read(SensorDataAmbient* data);
    
    /**
     * Legge solo temperatura (°C)
     */
    float readTemperature();
    
    /**
     * Legge solo umidità aria (%)
     */
    float readHumidity();
    
    /**
     * Legge solo pressione (hPa)
     */
    float readPressure();
    
    /**
     * Legge luminosità (lux)
     */
    uint16_t readLight();
    
    /**
     * Legge umidità suolo (valore ADC raw)
     */
    uint16_t readSoilRaw();
    
    /**
     * Legge umidità suolo (percentuale 0-100%)
     */
    uint8_t readSoilPercent();
    
    /**
     * Verifica se BME280 è disponibile
     */
    bool isBME280Available() { return _bme280_ok; }
    
    /**
     * Verifica se BH1750 è disponibile
     */
    bool isBH1750Available() { return _bh1750_ok; }
    
    /**
     * Calibra sensore suolo con valori secco/bagnato
     */
    void calibrateSoil(uint16_t dry_value, uint16_t wet_value);
    
    /**
     * Ottiene l'ultimo errore
     */
    const char* getLastError() { return _last_error; }

private:
    Adafruit_BME280 _bme;
    BH1750 _lightMeter;
    
    bool _bme280_ok;
    bool _bh1750_ok;
    int _soil_pin;
    uint16_t _soil_dry;
    uint16_t _soil_wet;
    
    char _last_error[64];
    
    void _setError(const char* msg);
};

// Istanza globale
extern SensorsAmbient AmbientSensors;

#endif // SENSORS_AMBIENT_H
