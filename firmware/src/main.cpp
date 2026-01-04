/**
 * AgriSecure IoT System - Main Entry Point
 * 
 * Questo file seleziona automaticamente il firmware corretto
 * in base alla configurazione NODE_TYPE in platformio.ini
 * 
 * Compilare con:
 *   pio run -e node_gateway    # Per gateway 4G
 *   pio run -e node_ambient    # Per nodo ambientale
 *   pio run -e node_security   # Per nodo sicurezza
 * 
 * @author Turiliffiu
 * @version 1.0.0
 */

// Selezione automatica del firmware basata su NODE_TYPE
// definito in platformio.ini build_flags

#if defined(NODE_TYPE) && NODE_TYPE == NODE_GATEWAY
    // Gateway 4G/LTE
    #include "main_gateway.cpp"
    
#elif defined(NODE_TYPE) && NODE_TYPE == NODE_AMBIENT
    // Nodo ambientale
    #include "main_ambient.cpp"
    
#elif defined(NODE_TYPE) && NODE_TYPE == NODE_SECURITY
    // Nodo sicurezza
    #include "main_security.cpp"
    
#else
    // Default: nodo di test
    #warning "NODE_TYPE non definito, compilazione firmware di test"
    
    #include <Arduino.h>
    #include "agrisecure_config.h"
    
    void setup() {
        Serial.begin(115200);
        delay(1000);
        
        Serial.println(F("\n"));
        Serial.println(F("╔═══════════════════════════════════════════╗"));
        Serial.println(F("║   AgriSecure IoT - TEST MODE              ║"));
        Serial.println(F("╚═══════════════════════════════════════════╝"));
        Serial.println(F(""));
        Serial.println(F("Questo è un firmware di test."));
        Serial.println(F("Per compilare un nodo specifico usa:"));
        Serial.println(F(""));
        Serial.println(F("  pio run -e node_gateway"));
        Serial.println(F("  pio run -e node_ambient"));
        Serial.println(F("  pio run -e node_security"));
        Serial.println(F(""));
        Serial.printf("Firmware version: %s\n", FIRMWARE_VERSION);
        Serial.printf("Free heap: %d bytes\n", ESP.getFreeHeap());
    }
    
    void loop() {
        static uint32_t last_print = 0;
        if (millis() - last_print > 5000) {
            Serial.println(F("Test mode running..."));
            last_print = millis();
        }
        delay(100);
    }
    
#endif
