/**
 * AgriSecure IoT System - Implementazione Sensori Ambientali
 * 
 * @author Turiliffiu
 * @version 1.0.0
 */

#include "sensors_ambient.h"

// Istanza globale
SensorsAmbient AmbientSensors;

// ============================================================
// Inizializzazione
// ============================================================
bool SensorsAmbient::begin(int sda, int scl, int soil_pin) {
    _bme280_ok = false;
    _bh1750_ok = false;
    _soil_pin = soil_pin;
    _soil_dry = SOIL_DRY_VALUE;
    _soil_wet = SOIL_WET_VALUE;
    _last_error[0] = '\0';
    
    DEBUG_PRINTLN(F(""));
    DEBUG_PRINTLN(F("=== Inizializzazione Sensori Ambientali ==="));
    
    // Inizializza I2C
    Wire.begin(sda, scl);
    DEBUG_PRINTF("I2C inizializzato: SDA=%d, SCL=%d\n", sda, scl);
    
    // Scan I2C per debug
    DEBUG_PRINTLN(F("Scan I2C..."));
    for (uint8_t addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            DEBUG_PRINTF("  Trovato dispositivo: 0x%02X\n", addr);
        }
    }
    
    // Inizializza BME280
    DEBUG_PRINT(F("Inizializzazione BME280... "));
    if (_bme.begin(BME280_ADDR, &Wire)) {
        _bme280_ok = true;
        DEBUG_PRINTLN(F("OK"));
        
        // Configurazione per weather monitoring
        _bme.setSampling(Adafruit_BME280::MODE_FORCED,
                         Adafruit_BME280::SAMPLING_X1,  // Temperatura
                         Adafruit_BME280::SAMPLING_X1,  // Pressione
                         Adafruit_BME280::SAMPLING_X1,  // Umidità
                         Adafruit_BME280::FILTER_OFF);
    } else {
        DEBUG_PRINTLN(F("FALLITO!"));
        // Prova indirizzo alternativo
        if (_bme.begin(0x77, &Wire)) {
            _bme280_ok = true;
            DEBUG_PRINTLN(F("BME280 trovato su 0x77"));
        } else {
            _setError("BME280 non trovato");
        }
    }
    
    // Inizializza BH1750
    DEBUG_PRINT(F("Inizializzazione BH1750... "));
    if (_lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, BH1750_ADDR, &Wire)) {
        _bh1750_ok = true;
        DEBUG_PRINTLN(F("OK"));
    } else {
        DEBUG_PRINTLN(F("FALLITO!"));
        _setError("BH1750 non trovato");
    }
    
    // Configura pin analogico per suolo
    pinMode(_soil_pin, INPUT);
    analogReadResolution(12);  // 12 bit = 0-4095
    DEBUG_PRINTF("Sensore suolo su GPIO%d\n", _soil_pin);
    
    DEBUG_PRINTLN(F("==========================================="));
    
    // Ritorna true se almeno un sensore è OK
    return _bme280_ok || _bh1750_ok;
}

// ============================================================
// Lettura Completa
// ============================================================
bool SensorsAmbient::read(SensorDataAmbient* data) {
    if (!data) return false;
    
    // Inizializza a zero
    memset(data, 0, sizeof(SensorDataAmbient));
    
    // BME280
    if (_bme280_ok) {
        _bme.takeForcedMeasurement();  // Necessario in MODE_FORCED
        data->temperature = _bme.readTemperature();
        data->humidity = _bme.readHumidity();
        data->pressure = _bme.readPressure() / 100.0F;  // Pa -> hPa
        
        DEBUG_PRINTF("BME280: T=%.1f°C, H=%.1f%%, P=%.1fhPa\n",
                     data->temperature, data->humidity, data->pressure);
    }
    
    // BH1750
    if (_bh1750_ok) {
        data->light_lux = (uint16_t)_lightMeter.readLightLevel();
        DEBUG_PRINTF("BH1750: %d lux\n", data->light_lux);
    }
    
    // Sensore suolo
    data->soil_moisture = readSoilRaw();
    data->soil_percent = readSoilPercent();
    DEBUG_PRINTF("Suolo: ADC=%d, %d%%\n", data->soil_moisture, data->soil_percent);
    
    return (_bme280_ok || _bh1750_ok);
}

// ============================================================
// Letture Singole
// ============================================================
float SensorsAmbient::readTemperature() {
    if (!_bme280_ok) return NAN;
    _bme.takeForcedMeasurement();
    return _bme.readTemperature();
}

float SensorsAmbient::readHumidity() {
    if (!_bme280_ok) return NAN;
    _bme.takeForcedMeasurement();
    return _bme.readHumidity();
}

float SensorsAmbient::readPressure() {
    if (!_bme280_ok) return NAN;
    _bme.takeForcedMeasurement();
    return _bme.readPressure() / 100.0F;
}

uint16_t SensorsAmbient::readLight() {
    if (!_bh1750_ok) return 0;
    return (uint16_t)_lightMeter.readLightLevel();
}

uint16_t SensorsAmbient::readSoilRaw() {
    // Media di 5 letture per stabilità
    uint32_t sum = 0;
    for (int i = 0; i < 5; i++) {
        sum += analogRead(_soil_pin);
        delay(10);
    }
    return sum / 5;
}

uint8_t SensorsAmbient::readSoilPercent() {
    uint16_t raw = readSoilRaw();
    
    // Converti in percentuale (inversamente proporzionale)
    // Più acqua = meno resistenza = valore ADC più basso
    if (raw >= _soil_dry) return 0;
    if (raw <= _soil_wet) return 100;
    
    // Mappa lineare
    uint8_t percent = map(raw, _soil_dry, _soil_wet, 0, 100);
    return constrain(percent, 0, 100);
}

// ============================================================
// Calibrazione e Utility
// ============================================================
void SensorsAmbient::calibrateSoil(uint16_t dry_value, uint16_t wet_value) {
    _soil_dry = dry_value;
    _soil_wet = wet_value;
    DEBUG_PRINTF("Calibrazione suolo: secco=%d, bagnato=%d\n", dry_value, wet_value);
}

void SensorsAmbient::_setError(const char* msg) {
    strncpy(_last_error, msg, sizeof(_last_error) - 1);
    _last_error[sizeof(_last_error) - 1] = '\0';
}
